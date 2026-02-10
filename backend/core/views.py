import logging
from datetime import date

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DailySummary, Meeting, NoteReference, WordDocument
from .serializers import (
    DailySummaryDetailSerializer,
    DailySummaryListSerializer,
    MeetingSerializer,
    NoteReferenceSerializer,
    WordDocumentSerializer,
)

logger = logging.getLogger(__name__)


class DailySummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailySummary.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return DailySummaryListSerializer
        return DailySummaryDetailSerializer

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        today = date.today()
        summary = DailySummary.objects.filter(date=today).first()
        if not summary:
            return Response(
                {'detail': 'No summary for today. Run collection first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DailySummaryDetailSerializer(summary)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        url_path='by-date/(?P<target_date>[0-9-]+)',
    )
    def by_date(self, request, target_date=None):
        parsed = parse_date(target_date)
        if not parsed:
            return Response(
                {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        summary = DailySummary.objects.filter(date=parsed).first()
        if not summary:
            return Response(
                {'detail': f'No summary for {target_date}.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DailySummaryDetailSerializer(summary)
        return Response(serializer.data)


class SearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'detail': 'Query parameter "q" is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meetings = Meeting.objects.filter(
            Q(subject__icontains=query) | Q(body_preview__icontains=query)
        ).select_related('daily_summary').order_by('-start_time')[:20]

        notes = NoteReference.objects.filter(
            Q(page_title__icontains=query) | Q(content_snippet__icontains=query)
        ).select_related('daily_summary').order_by('-last_modified')[:20]

        documents = WordDocument.objects.filter(
            Q(file_name__icontains=query) | Q(content_text__icontains=query)
        ).select_related('daily_summary').order_by('-modified_at')[:20]

        summaries = DailySummary.objects.filter(
            Q(summary_text__icontains=query) | Q(notes__icontains=query)
        ).order_by('-date')[:10]

        return Response({
            'meetings': MeetingSerializer(meetings, many=True).data,
            'notes': NoteReferenceSerializer(notes, many=True).data,
            'documents': WordDocumentSerializer(documents, many=True).data,
            'summaries': DailySummaryListSerializer(summaries, many=True).data,
        })


class CollectView(APIView):
    def post(self, request):
        target_date_str = request.data.get('date')
        if target_date_str:
            target_date = parse_date(target_date_str)
            if not target_date:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = date.today()

        try:
            from .services.summary_service import SummaryService
            service = SummaryService()
            summary = service.collect_and_summarize(target_date)
            serializer = DailySummaryDetailSerializer(summary)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Collection failed: {e}", exc_info=True)
            return Response(
                {'detail': f'Collection failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuthStatusView(APIView):
    def get(self, request):
        try:
            from .services.auth_service import AuthService
            auth = AuthService.get_instance()
            return Response({
                'authenticated': auth.is_authenticated(),
                'account': auth.get_account_info(),
            })
        except Exception as e:
            return Response({
                'authenticated': False,
                'account': None,
                'error': str(e),
            })


class AuthLoginView(APIView):
    def post(self, request):
        try:
            from .services.auth_service import AuthService
            auth = AuthService.get_instance()
            auth.get_access_token()
            return Response({
                'authenticated': True,
                'account': auth.get_account_info(),
            })
        except Exception as e:
            return Response(
                {'detail': f'Login failed: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class AuthLogoutView(APIView):
    def post(self, request):
        try:
            from .services.auth_service import AuthService
            auth = AuthService.get_instance()
            auth.logout()
            return Response({'detail': 'Logged out successfully.'})
        except Exception as e:
            return Response(
                {'detail': f'Logout failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

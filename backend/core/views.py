import logging
import threading
from datetime import date

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from collections import defaultdict

from .models import DailySummary, Meeting, NoteReference, WordDocument
from .serializers import (
    DailySummaryDetailSerializer,
    DailySummaryListSerializer,
    MeetingSerializer,
    NoteReferenceSerializer,
    WordDocumentSerializer,
)
from .services.auth_service import GraphAuthService

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
            Q(subject__icontains=query)
            | Q(body_preview__icontains=query)
            | Q(organizer_name__icontains=query)
            | Q(organizer_email__icontains=query)
            | Q(attendees_json__icontains=query)
            | Q(location__icontains=query)
        ).select_related('daily_summary').order_by('-start_time')[:20]

        notes = NoteReference.objects.filter(
            Q(page_title__icontains=query)
            | Q(content_snippet__icontains=query)
            | Q(content_text__icontains=query)
            | Q(notebook_name__icontains=query)
            | Q(section_name__icontains=query)
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
        # Validate config before attempting collection
        try:
            from .services.config_service import ConfigService
            config = ConfigService.get_instance()
        except Exception as e:
            return Response(
                {'detail': f'Configuration error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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


class StatusView(APIView):
    def get(self, request):
        # Get config info
        config_info = {
            'word_doc_directories': [],
            'outlook_enabled': False,
            'onenote_enabled': False,
            'onenote_notebooks': [],
        }
        try:
            from .services.config_service import ConfigService
            config = ConfigService.get_instance()
            config_info['word_doc_directories'] = getattr(config, 'word_doc_directories', [])
            config_info['outlook_enabled'] = getattr(config, 'outlook_enabled', False)
            config_info['onenote_enabled'] = getattr(config, 'onenote_enabled', False)
            config_info['onenote_notebooks'] = getattr(config, 'onenote_notebooks', [])
        except Exception:
            pass

        # Check Graph auth status
        graph_auth_info = {
            'graph_enabled': False,
            'graph_authenticated': False,
            'graph_account': None,
        }
        try:
            graph_auth = GraphAuthService.get_instance()
            graph_auth_info['graph_enabled'] = graph_auth.graph_enabled
            graph_auth_info['graph_authenticated'] = graph_auth.is_authenticated()
            if graph_auth.is_authenticated():
                graph_auth_info['graph_account'] = graph_auth.get_account_info()
        except Exception:
            pass

        return Response({
            'outlook_enabled': config_info['outlook_enabled'],
            'onenote_enabled': config_info['onenote_enabled'],
            'word_doc_directories': config_info['word_doc_directories'],
            'onenote_notebooks': config_info['onenote_notebooks'],
            'graph_enabled': graph_auth_info['graph_enabled'],
            'graph_authenticated': graph_auth_info['graph_authenticated'],
            'graph_account': graph_auth_info['graph_account'],
            'version': '1.0.0',
        })


class GraphAuthStatusView(APIView):
    """GET /api/auth/status/ - Return current Graph authentication state."""

    def get(self, request):
        try:
            auth = GraphAuthService.get_instance()
            accounts = auth.get_accounts()
            return Response({
                'authenticated': auth.is_authenticated(),
                'accounts': [
                    {
                        'username': a.get('username', ''),
                        'name': a.get('name', ''),
                    }
                    for a in accounts
                ],
                'graph_enabled': auth.graph_enabled,
                'login_error': auth.login_error,
            })
        except Exception as e:
            logger.error("Failed to get Graph auth status: %s", e, exc_info=True)
            return Response({
                'authenticated': False,
                'accounts': [],
                'graph_enabled': False,
                'login_error': None,
            })


class GraphAuthLoginView(APIView):
    """POST /api/auth/login/ - Open browser for interactive Microsoft login."""

    def post(self, request):
        try:
            auth = GraphAuthService.get_instance()

            if not auth.graph_enabled:
                return Response(
                    {'detail': 'Graph authentication service not available.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Run interactive login in a background thread because it blocks
            # until the user completes sign-in in the browser.  The frontend
            # polls /api/auth/status/ to detect completion.
            def _do_interactive_login():
                try:
                    auth.login_interactive()
                except Exception:
                    logger.error("Interactive login failed.", exc_info=True)

            threading.Thread(target=_do_interactive_login, daemon=True).start()

            return Response({
                'status': 'browser_opened',
                'message': 'A browser window has been opened. '
                           'Please sign in with your Microsoft account.',
            })
        except Exception as e:
            logger.error("Graph login failed: %s", e, exc_info=True)
            return Response(
                {'detail': f'Login failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GraphAuthLogoutView(APIView):
    """POST /api/auth/logout/ - Clear cached Graph tokens."""

    def post(self, request):
        try:
            auth = GraphAuthService.get_instance()
            auth.logout()
            return Response({'detail': 'Logged out'})
        except Exception as e:
            logger.error("Graph logout failed: %s", e, exc_info=True)
            return Response(
                {'detail': f'Logout failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SaveConfigView(APIView):
    """POST /api/config/ - Save configuration values."""

    def post(self, request):
        import json
        from .services.config_service import ConfigService, CONFIG_FILE

        try:
            config = ConfigService.get_instance()

            # Read current config file
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
            else:
                config_data = {}

            # Update allowed fields
            allowed = ['word_doc_directories',
                       'recordings_directories', 'onenote_paths',
                       'onenote_notebooks']
            updated = []
            for key in allowed:
                if key in request.data:
                    config_data[key] = request.data[key]
                    updated.append(key)

            # Write back
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)

            # Reset singleton so changes take effect
            ConfigService.reset()

            return Response({
                'detail': f'Config updated: {", ".join(updated)}',
                'updated': updated,
            })
        except Exception as e:
            logger.error("Config save failed: %s", e, exc_info=True)
            return Response(
                {'detail': f'Failed to save config: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OpenNoteView(APIView):
    """POST /api/notes/<uuid>/open/ - Open a OneNote page in the desktop app."""

    def post(self, request, note_id):
        import os
        import sys

        try:
            note = NoteReference.objects.get(id=note_id)
        except NoteReference.DoesNotExist:
            return Response(
                {'detail': 'Note not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Try web_url first (onenote: protocol links from COM)
        if note.web_url:
            return Response({'action': 'open_url', 'url': note.web_url})

        # Try COM navigation to the specific page by title
        if note.page_title:
            try:
                from .services.win32_onenote_service import OneNoteLocalService
                onenote = OneNoteLocalService()
                section_file = None
                if note.page_graph_id and note.page_graph_id.startswith('file://'):
                    section_file = note.page_graph_id[len('file://'):]
                if onenote.navigate_to_page_by_title(note.page_title, section_file):
                    return Response({
                        'action': 'navigated',
                        'detail': f'Navigated to "{note.page_title}" in OneNote.',
                    })
            except Exception as e:
                logger.debug("COM navigation failed, falling back: %s", e)

        # Fallback: open the .one section file
        if note.page_graph_id and note.page_graph_id.startswith('file://'):
            file_path = note.page_graph_id[len('file://'):]
            if os.path.isfile(file_path):
                try:
                    if sys.platform == 'win32':
                        os.startfile(file_path)
                    return Response({
                        'action': 'opened_local',
                        'detail': f'Opened "{note.page_title}" section in OneNote.',
                    })
                except Exception as e:
                    logger.error("Failed to open note file: %s", e)
                    return Response(
                        {'detail': f'Failed to open file: {e}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                return Response(
                    {'detail': f'File not found: {os.path.basename(file_path)}'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return Response(
            {'detail': 'No link available for this note.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class AttendeeSearchView(APIView):
    """GET /api/attendees/?q=name -- Search meetings by attendee name/email."""

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'detail': 'Query parameter "q" is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Search meetings where attendees_json contains the query
        meetings = Meeting.objects.filter(
            attendees_json__icontains=query
        ).select_related('daily_summary').order_by('-start_time')[:50]

        results = []
        for meeting in meetings:
            results.append({
                'id': str(meeting.id),
                'subject': meeting.subject,
                'start_time': meeting.start_time.isoformat() if meeting.start_time else '',
                'end_time': meeting.end_time.isoformat() if meeting.end_time else '',
                'date': meeting.daily_summary.date.isoformat(),
                'organizer_name': meeting.organizer_name,
                'attendee_count': len(meeting.attendees_json) if meeting.attendees_json else 0,
                'is_online_meeting': meeting.is_online_meeting,
                'location': meeting.location,
            })

        return Response({
            'query': query,
            'count': len(results),
            'meetings': results,
        })


class AttendeeTopView(APIView):
    """GET /api/attendees/top/ -- Return most frequent meeting collaborators."""

    def get(self, request):
        limit = int(request.query_params.get('limit', 20))

        # Scan all meetings for attendee frequency
        attendee_counts = defaultdict(lambda: {
            'name': '', 'email': '', 'meeting_count': 0, 'last_seen': ''
        })

        meetings = Meeting.objects.all().order_by('-start_time')
        for meeting in meetings:
            if not meeting.attendees_json:
                continue
            for attendee in meeting.attendees_json:
                name = attendee.get('name', '')
                email = attendee.get('email', '')
                key = email.lower() if email else name.lower()
                if not key:
                    continue

                entry = attendee_counts[key]
                entry['name'] = name or entry['name']
                entry['email'] = email or entry['email']
                entry['meeting_count'] += 1
                meeting_date = meeting.start_time.isoformat() if meeting.start_time else ''
                if not entry['last_seen'] or meeting_date > entry['last_seen']:
                    entry['last_seen'] = meeting_date

        # Sort by meeting count descending
        sorted_attendees = sorted(
            attendee_counts.values(),
            key=lambda x: x['meeting_count'],
            reverse=True,
        )[:limit]

        return Response({
            'attendees': sorted_attendees,
            'total_unique': len(attendee_counts),
        })

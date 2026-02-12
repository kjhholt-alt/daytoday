from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailySummaryViewSet,
    SearchView,
    CollectView,
    StatusView,
    GraphAuthStatusView,
    GraphAuthLoginView,
    GraphAuthLogoutView,
    SaveConfigView,
    OpenNoteView,
    AttendeeSearchView,
    AttendeeTopView,
    CalendarImportView,
    BulkCalendarImportView,
    WeeklyRecapView,
    ActionItemListCreateView,
    ActionItemDetailView,
    CalendarHeatmapView,
)

router = DefaultRouter()
router.register(r'summaries', DailySummaryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('search/', SearchView.as_view(), name='search'),
    path('collect/', CollectView.as_view(), name='collect'),
    path('status/', StatusView.as_view(), name='status'),
    path('auth/status/', GraphAuthStatusView.as_view(), name='auth-status'),
    path('auth/login/', GraphAuthLoginView.as_view(), name='auth-login'),
    path('auth/logout/', GraphAuthLogoutView.as_view(), name='auth-logout'),
    path('config/', SaveConfigView.as_view(), name='save-config'),
    path('notes/<uuid:note_id>/open/', OpenNoteView.as_view(), name='open-note'),
    path('calendar/import/', CalendarImportView.as_view(), name='calendar-import'),
    path('calendar/bulk-import/', BulkCalendarImportView.as_view(), name='calendar-bulk-import'),
    path('attendees/', AttendeeSearchView.as_view(), name='attendee-search'),
    path('attendees/top/', AttendeeTopView.as_view(), name='attendee-top'),
    path('weekly/', WeeklyRecapView.as_view(), name='weekly-recap'),
    path('action-items/', ActionItemListCreateView.as_view(), name='action-items'),
    path('action-items/<uuid:item_id>/', ActionItemDetailView.as_view(), name='action-item-detail'),
    path('heatmap/', CalendarHeatmapView.as_view(), name='calendar-heatmap'),
]

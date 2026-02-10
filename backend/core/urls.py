from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailySummaryViewSet,
    SearchView,
    CollectView,
    AuthStatusView,
    AuthLoginView,
    AuthLogoutView,
)

router = DefaultRouter()
router.register(r'summaries', DailySummaryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('search/', SearchView.as_view(), name='search'),
    path('collect/', CollectView.as_view(), name='collect'),
    path('auth/status/', AuthStatusView.as_view(), name='auth-status'),
    path('auth/login/', AuthLoginView.as_view(), name='auth-login'),
    path('auth/logout/', AuthLogoutView.as_view(), name='auth-logout'),
]

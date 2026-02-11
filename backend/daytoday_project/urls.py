from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import HttpResponse
from pathlib import Path


def serve_react(request):
    """
    Serve the React app's index.html for any non-API route.
    This enables client-side routing in the React app.
    """
    react_index = settings.PROJECT_ROOT / 'frontend' / 'build' / 'index.html'
    if react_index.exists():
        return HttpResponse(react_index.read_text(), content_type='text/html')
    return HttpResponse(
        '<h1>DayToDay</h1>'
        '<p>Frontend not built yet. Run <code>npm run build</code> in the frontend directory.</p>',
        content_type='text/html',
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
]

# Serve React static files and catch-all for client-side routing
if (settings.PROJECT_ROOT / 'frontend' / 'build').exists():
    from django.views.static import serve as static_serve
    import os

    build_dir = str(settings.PROJECT_ROOT / 'frontend' / 'build')

    def serve_build_file(request, path=''):
        """Serve files from the React build directory."""
        file_path = os.path.join(build_dir, path)
        if os.path.isfile(file_path):
            return static_serve(request, path, document_root=build_dir)
        # For any non-file path, serve index.html (React client-side routing)
        return serve_react(request)

    urlpatterns += [
        # Serve manifest.json, favicon.ico, etc. from build root
        re_path(r'^(?!api/)(?P<path>.+\..+)$', serve_build_file),
        # Catch-all for React client-side routes
        re_path(r'^(?!api/).*$', serve_react),
    ]
else:
    urlpatterns += [
        re_path(r'^$', serve_react),
    ]

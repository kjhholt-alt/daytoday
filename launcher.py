"""
DayToDay Application Launcher

Single-entry-point script that:
1. Runs the Django data collection for today
2. Starts the Django server serving both API and React static files
3. Opens the browser to the application
4. Handles graceful shutdown on Ctrl+C or window close
"""

import os
import sys
import threading
import time
import webbrowser
import logging
from pathlib import Path

# Determine base directory - handles both normal and PyInstaller frozen mode
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BASE_DIR = Path(sys._MEIPASS)
    # User data directory for database and config (writable location)
    USER_DATA_DIR = Path(os.environ.get(
        'DAYTODAY_DATA_DIR',
        Path.home() / '.daytoday'
    ))
else:
    # Running from source
    BASE_DIR = Path(__file__).resolve().parent
    USER_DATA_DIR = BASE_DIR

# Ensure user data directory exists
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Tell Django settings where to store the database and config
os.environ['DAYTODAY_DATA_DIR'] = str(USER_DATA_DIR)

# Set up Django settings before importing anything
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daytoday_project.settings')

# Add backend to path
backend_dir = str(BASE_DIR / 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger('daytoday.launcher')

# Server configuration
HOST = '127.0.0.1'
PORT = int(os.environ.get('DAYTODAY_PORT', '8000'))
URL = f'http://{HOST}:{PORT}'


def setup_django():
    """Initialize Django."""
    import django
    django.setup()


def run_migrations():
    """Run database migrations if needed."""
    from django.core.management import call_command
    logger.info("Checking database migrations...")
    call_command('migrate', '--run-syncdb', verbosity=0)
    logger.info("Database is up to date.")


def collect_today_data():
    """Run data collection for today."""
    from datetime import date
    logger.info("Collecting data for today...")
    try:
        from core.services.summary_service import SummaryService
        service = SummaryService()
        summary = service.collect_and_summarize(date.today())

        meetings = summary.meetings.count()
        notes = summary.note_references.count()
        docs = summary.word_documents.count()

        if summary.status == 'complete':
            logger.info(
                f"Collection complete: {meetings} meeting(s), "
                f"{notes} note(s), {docs} document(s)"
            )
        else:
            logger.warning(
                f"Collection completed with errors: {summary.error_message}"
            )
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        logger.info("The app will still start - you can retry collection from the UI.")


def open_browser():
    """Open the default web browser after a short delay."""
    time.sleep(1.5)
    logger.info(f"Opening browser at {URL}")
    webbrowser.open(URL)


def run_server():
    """Start the Django development server."""
    from django.core.management import call_command

    # Pre-check: verify WSGI app loads before starting server
    try:
        from daytoday_project.wsgi import application  # noqa: F401
    except Exception as e:
        logger.error("WSGI pre-check failed: %s", e, exc_info=True)
        raise RuntimeError(
            f"Could not load WSGI application: {e}\n"
            f"This usually means a Python package is missing."
        )

    logger.info(f"Starting DayToDay server at {URL}")
    logger.info("Press Ctrl+C to stop.")

    try:
        call_command(
            'runserver',
            f'{HOST}:{PORT}',
            '--noreload',
            use_reloader=False,
            verbosity=1,
        )
    except KeyboardInterrupt:
        pass


def main():
    """Main entry point for the DayToDay application."""
    print()
    print("=" * 50)
    print("  DayToDay - Daily Productivity Dashboard")
    print("=" * 50)
    print()

    # Initialize Django
    setup_django()

    # Run migrations
    try:
        run_migrations()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\nError setting up database: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Collect today's data in a background thread
    collection_thread = threading.Thread(target=collect_today_data, daemon=True)
    collection_thread.start()

    # Open browser in a background thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Run the server (blocks until Ctrl+C)
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nShutting down DayToDay...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"\nServer error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == '__main__':
    main()

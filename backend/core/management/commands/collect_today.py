from datetime import date

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Collect data for today (or a specified date) and generate a daily summary.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target date in YYYY-MM-DD format (default: today)',
        )

    def handle(self, *args, **options):
        target_date_str = options.get('date')
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                raise CommandError(
                    f'Invalid date format: {target_date_str}. '
                    'Use YYYY-MM-DD.'
                )
        else:
            target_date = date.today()

        self.stdout.write(
            f"Collecting data for {target_date.strftime('%A, %B %d, %Y')}..."
        )

        try:
            from core.services.summary_service import SummaryService
            service = SummaryService()
            summary = service.collect_and_summarize(target_date)
        except Exception as e:
            raise CommandError(f'Collection failed: {e}')

        meetings_count = summary.meetings.count()
        notes_count = summary.note_references.count()
        docs_count = summary.word_documents.count()

        if summary.status == 'complete':
            self.stdout.write(self.style.SUCCESS(
                f"Done! {meetings_count} meeting(s), "
                f"{notes_count} note(s), "
                f"{docs_count} document(s) collected."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Completed with errors ({meetings_count} meetings, "
                f"{notes_count} notes, {docs_count} docs):"
            ))
            self.stdout.write(self.style.WARNING(summary.error_message))

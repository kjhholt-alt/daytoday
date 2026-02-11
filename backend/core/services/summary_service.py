import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction

from ..models import (
    DailySummary, Meeting, NoteReference, WordDocument, Recording,
)
from .config_service import ConfigService
from .win32_outlook_service import OutlookCalendarService
from .win32_onenote_service import OneNoteLocalService
from .word_service import WordService
from .recording_service import RecordingService
from .auth_service import GraphAuthService
from .graph_calendar_service import GraphCalendarService
from .graph_onenote_service import GraphOneNoteService

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(self):
        self._config = ConfigService.get_instance()

        self._calendar = None
        if self._config.outlook_enabled:
            self._calendar = OutlookCalendarService()

        self._onenote = None
        if self._config.onenote_enabled:
            self._onenote = OneNoteLocalService()

        # Graph API auth (optional - only if graph_client_id configured and authenticated)
        self._graph_auth = None
        self._graph_calendar = None
        self._graph_onenote = None
        if self._config.get('graph_client_id'):
            self._graph_auth = GraphAuthService.get_instance()
            if self._graph_auth.is_authenticated():
                self._graph_calendar = GraphCalendarService(self._graph_auth)
                self._graph_onenote = GraphOneNoteService(self._graph_auth)

        self._word = WordService(self._config.word_doc_directories)
        self._recordings = RecordingService(self._config.recordings_directories)

    @transaction.atomic
    def collect_and_summarize(self, target_date=None):
        if target_date is None:
            target_date = date.today()

        logger.info(f"Starting data collection for {target_date}...")

        summary, created = DailySummary.objects.get_or_create(
            date=target_date,
            defaults={'status': 'collecting'},
        )
        if not created:
            summary.status = 'collecting'
            summary.error_message = ''
            summary.save()
            summary.meetings.all().delete()
            summary.note_references.all().delete()
            summary.word_documents.all().delete()
            summary.recordings.all().delete()
            logger.info(f"Re-collecting data for {target_date} (existing record).")

        errors = []

        # 1. Calendar events  (priority: COM > Graph API)
        #    COM via Classic Outlook gives full data with no auth required.
        #    Graph API is fallback but requires admin consent in many orgs.
        calendar_done = False

        # Try COM (Classic Outlook) first - gives most complete data
        if self._calendar and not calendar_done:
            try:
                events = self._calendar.get_events_for_date(target_date)
                if events:
                    self._store_meetings(summary, events)
                    logger.info(f"Stored {len(events)} meeting(s) via COM.")
                    calendar_done = True
            except Exception as e:
                logger.warning(f"COM calendar failed: {e}")

        # Try Graph API as fallback
        if self._graph_calendar and not calendar_done:
            try:
                events = self._graph_calendar.get_events_for_date(target_date)
                if events:
                    self._store_meetings(summary, events)
                    logger.info(f"Stored {len(events)} meeting(s) via Graph API.")
                    calendar_done = True
            except Exception as e:
                logger.error(f"Graph calendar failed: {e}", exc_info=True)

        if not calendar_done:
            logger.info("Calendar collection: no source available or all returned empty.")

        # 2. OneNote pages
        if self._onenote:
            try:
                self._collect_notes(summary, target_date)
                logger.info("Collected OneNote pages via COM.")
            except Exception as e:
                logger.warning(f"COM OneNote failed: {e}")
                # Fall back to Graph API
                if self._graph_onenote:
                    try:
                        self._collect_notes_graph(summary, target_date)
                        logger.info("Collected OneNote pages via Graph API (fallback).")
                    except Exception as e2:
                        logger.error(f"Graph OneNote also failed: {e2}", exc_info=True)
                        errors.append(f"OneNote: COM: {e}, Graph: {e2}")
                else:
                    errors.append(f"OneNote: {e}")
        elif self._graph_onenote:
            try:
                self._collect_notes_graph(summary, target_date)
                logger.info("Collected OneNote pages via Graph API.")
            except Exception as e:
                logger.error(f"Graph OneNote failed: {e}", exc_info=True)
                errors.append(f"OneNote: {e}")
        else:
            logger.info("OneNote collection disabled (no COM or Graph).")

        # 3. Word documents
        try:
            self._collect_word_docs(summary, target_date)
        except Exception as e:
            logger.error(f"Word doc collection failed: {e}", exc_info=True)
            errors.append(f"Word docs: {e}")

        # 4. Recordings and transcripts
        try:
            self._collect_recordings(summary, target_date)
        except Exception as e:
            logger.error(f"Recording collection failed: {e}", exc_info=True)
            errors.append(f"Recordings: {e}")

        # Generate summary
        summary.summary_text = self._generate_summary_text(summary)
        summary.status = 'error' if errors else 'complete'
        summary.error_message = '\n'.join(errors)
        summary.save()

        logger.info(
            f"Collection {'completed with errors' if errors else 'completed'} "
            f"for {target_date}."
        )
        return summary

    def _store_meetings(self, summary, events):
        meetings = []
        for event in events:
            meetings.append(Meeting(
                daily_summary=summary,
                graph_event_id=event['graph_id'],
                subject=event['subject'],
                start_time=event['start_time'],
                end_time=event['end_time'],
                organizer_name=event['organizer_name'],
                organizer_email=event['organizer_email'],
                attendees_json=event['attendees'],
                body_preview=event['body_preview'],
                location=event['location'],
                is_online_meeting=event['is_online_meeting'],
                online_meeting_url=event['online_meeting_url'],
                web_link=event['web_link'],
            ))
        Meeting.objects.bulk_create(meetings)

    def _collect_notes(self, summary, target_date):
        # Look back 7 days for OneNote pages because:
        # 1. OneNote backup/cache files may not update in real-time
        # 2. Users want to see recent notes, not just today's
        # The change detection (new/updated/unchanged) handles the rest
        modified_since = datetime.combine(target_date - timedelta(days=7), datetime.min.time())
        pages = self._onenote.list_recent_pages(modified_since=modified_since)

        # Load yesterday's notes for comparison
        previous_notes = self._get_previous_notes(target_date)

        notes = []
        for page in pages:
            parent = page.get('parentSection', {})
            page_id = page.get('id', '')

            # Fetch content via COM
            content_text = ''
            try:
                content_text = self._onenote.get_page_content(page_id)
            except Exception as exc:
                logger.debug("Could not fetch COM page content for %s: %s", page_id, exc)

            # Detect changes
            change_type, changes_summary = self._detect_changes(
                page_id, content_text, previous_notes
            )

            notes.append(NoteReference(
                daily_summary=summary,
                page_title=page.get('title', 'Untitled'),
                page_graph_id=page_id,
                section_name=parent.get('displayName', '') if parent else '',
                content_snippet=content_text[:500] if content_text else '',
                content_text=content_text[:50000] if content_text else '',
                change_type=change_type,
                changes_summary=changes_summary,
                last_modified=page.get('lastModifiedDateTime'),
            ))
        if notes:
            NoteReference.objects.bulk_create(notes)
            logger.info(f"Stored {len(notes)} OneNote reference(s) via COM.")

    def _collect_notes_graph(self, summary, target_date):
        """Collect OneNote pages via Graph API (fallback for COM)."""
        modified_since = datetime.combine(target_date - timedelta(days=7), datetime.min.time())
        pages = self._graph_onenote.list_recent_pages(modified_since=modified_since)

        # Load yesterday's notes for comparison
        previous_notes = self._get_previous_notes(target_date)

        notes = []
        for page in pages:
            parent = page.get('parentSection', {})
            page_id = page.get('id', '')

            # Fetch page content via Graph API
            content_text = ''
            try:
                content_text = self._graph_onenote.fetch_page_content(page_id)
            except Exception as exc:
                logger.debug(
                    "Could not fetch Graph page content for %s: %s",
                    page_id, exc,
                )

            # Detect changes against previous version
            change_type, changes_summary = self._detect_changes(
                page_id, content_text, previous_notes
            )

            notes.append(NoteReference(
                daily_summary=summary,
                page_title=page.get('title', 'Untitled'),
                page_graph_id=page_id,
                section_name=parent.get('displayName', '') if parent else '',
                content_snippet=content_text[:500] if content_text else '',
                content_text=content_text[:50000] if content_text else '',
                change_type=change_type,
                changes_summary=changes_summary,
                last_modified=page.get('lastModifiedDateTime'),
            ))
        if notes:
            NoteReference.objects.bulk_create(notes)
            logger.info(f"Stored {len(notes)} OneNote reference(s) via Graph API.")

    # ------------------------------------------------------------------
    # Change detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_previous_notes(target_date):
        """Load NoteReference objects from the most recent prior summary.

        Returns a dict mapping ``page_graph_id`` to the stored
        ``content_text`` so we can compare against today's content.
        """
        # Look for the most recent summary before target_date (could be
        # yesterday or earlier if weekends / gaps exist).
        prev_summary = (
            DailySummary.objects
            .filter(date__lt=target_date)
            .order_by('-date')
            .first()
        )
        if prev_summary is None:
            return {}

        previous_notes = {}
        for note in prev_summary.note_references.all():
            if note.page_graph_id:
                previous_notes[note.page_graph_id] = note.content_text or ''
        return previous_notes

    @staticmethod
    def _detect_changes(page_id, current_content, previous_notes):
        """Compare current page content against previous version.

        Returns
        -------
        tuple[str, str]
            ``(change_type, changes_summary)`` where *change_type* is
            one of ``'new'``, ``'updated'``, or ``'unchanged'`` and
            *changes_summary* is a human-readable description.
        """
        if not page_id or page_id not in previous_notes:
            # No previous version found -- this is a new page
            return 'new', 'New page'

        prev_content = previous_notes[page_id]

        # If we couldn't fetch content for either version, we can't diff
        if not current_content and not prev_content:
            return 'updated', 'Page modified (content not available for comparison)'

        if not current_content:
            return 'updated', 'Page modified (current content not available)'

        # Simple line-based comparison
        prev_lines = prev_content.splitlines()
        curr_lines = current_content.splitlines()

        prev_set = set(prev_lines)
        new_lines = [line for line in curr_lines if line.strip() and line not in prev_set]

        if not new_lines and len(curr_lines) == len(prev_lines):
            return 'unchanged', 'No changes detected'

        if not new_lines and len(curr_lines) != len(prev_lines):
            line_diff = len(curr_lines) - len(prev_lines)
            if line_diff > 0:
                return 'updated', f'Updated - added {line_diff} new line(s)'
            else:
                return 'updated', f'Updated - removed {abs(line_diff)} line(s)'

        # Build a summary of new content
        new_line_count = len(new_lines)
        new_text_preview = '\n'.join(new_lines)[:200]
        summary = f'Updated - added {new_line_count} new line(s): {new_text_preview}'
        return 'updated', summary

    def _collect_word_docs(self, summary, target_date):
        docs = self._word.find_documents(modified_since=target_date)
        word_docs = []
        for doc_meta in docs:
            extracted = self._word.extract_text(doc_meta['file_path'])
            content_text = '\n'.join(
                block.get('text', str(block.get('rows', '')))
                for block in extracted.get('content', [])
            )
            word_docs.append(WordDocument(
                daily_summary=summary,
                file_name=doc_meta['file_name'],
                file_path=doc_meta['file_path'],
                content_text=content_text[:50000],
                modified_at=doc_meta['modified_at'],
                size_bytes=doc_meta.get('size_bytes', 0),
            ))
        if word_docs:
            WordDocument.objects.bulk_create(word_docs)
            logger.info(f"Stored {len(word_docs)} Word document(s).")

    def _collect_recordings(self, summary, target_date):
        found = self._recordings.find_recordings(modified_since=target_date)
        recording_objs = []
        for rec_meta in found:
            transcript_text = ''
            if rec_meta['file_type'] == 'transcript':
                transcript_text = self._recordings.extract_transcript_text(
                    rec_meta['file_path']
                )
                transcript_text = transcript_text[:50000]

            recording_objs.append(Recording(
                daily_summary=summary,
                file_name=rec_meta['file_name'],
                file_path=rec_meta['file_path'],
                file_type=rec_meta['file_type'],
                transcript_text=transcript_text,
                modified_at=rec_meta['modified_at'],
                size_bytes=rec_meta.get('size_bytes', 0),
            ))
        if recording_objs:
            Recording.objects.bulk_create(recording_objs)
            logger.info(f"Stored {len(recording_objs)} recording(s).")

    def _generate_summary_text(self, summary):
        local_tz = ZoneInfo("America/Chicago")
        parts = [
            f"# Daily Summary - {summary.date.strftime('%A, %B %d, %Y')}",
            '',
        ]

        meetings = summary.meetings.all()
        if meetings:
            parts.append(f"## Meetings ({meetings.count()})")
            parts.append('')
            for m in meetings:
                start_local = m.start_time.astimezone(local_tz)
                end_local = m.end_time.astimezone(local_tz)
                time_str = start_local.strftime('%I:%M %p')
                end_str = end_local.strftime('%I:%M %p')
                parts.append(f"### {time_str} - {end_str}: {m.subject}")
                parts.append(f"- **Organizer:** {m.organizer_name}")
                if m.location:
                    parts.append(f"- **Location:** {m.location}")
                if m.body_preview and len(m.body_preview.strip()) > 10:
                    preview = m.body_preview[:150]
                    parts.append(f"- **Preview:** {preview}")
                attendee_count = len(m.attendees_json) if m.attendees_json else 0
                if attendee_count:
                    names = ', '.join(
                        a.get('name', a.get('email', ''))
                        for a in m.attendees_json[:10]
                    )
                    parts.append(f"- **Attendees ({attendee_count}):** {names}")
                if m.transcripts.exists():
                    parts.append(
                        f"- **Transcript available** "
                        f"({m.transcripts.count()} file(s))"
                    )
                parts.append('')

        notes = summary.note_references.all()
        if notes:
            parts.append(f"## OneNote Pages Modified ({notes.count()})")
            parts.append('')
            for n in notes:
                # Build status label
                if n.change_type == 'new':
                    status = '[NEW]'
                elif n.change_type == 'updated':
                    status = '[UPDATED]'
                else:
                    status = '[UNCHANGED]'

                line = f"- {status} {n.page_title}"
                if n.section_name:
                    line += f" (Section: {n.section_name})"
                parts.append(line)

                # Show changes summary if available
                if n.changes_summary and n.change_type != 'unchanged':
                    changes_preview = n.changes_summary[:200]
                    parts.append(f"  - {changes_preview}")
            parts.append('')

        docs = summary.word_documents.all()
        if docs:
            parts.append(f"## Word Documents Modified ({docs.count()})")
            parts.append('')
            for d in docs:
                size_kb = d.size_bytes / 1024
                parts.append(f"- {d.file_name} ({size_kb:.1f} KB)")
            parts.append('')

        recordings = summary.recordings.all()
        if recordings:
            parts.append(f"## Recordings & Transcripts ({recordings.count()})")
            parts.append('')
            for r in recordings:
                size_kb = r.size_bytes / 1024
                type_label = r.get_file_type_display()
                parts.append(f"- [{type_label}] {r.file_name} ({size_kb:.1f} KB)")
                if r.transcript_text:
                    preview = r.transcript_text[:200].replace('\n', ' ')
                    parts.append(f"  - **Transcript preview:** {preview}")
            parts.append('')

        if not meetings and not notes and not docs and not recordings:
            parts.append(
                '*No meetings, notes, documents, or recordings found for today.*'
            )
            parts.append('')

        return '\n'.join(parts)

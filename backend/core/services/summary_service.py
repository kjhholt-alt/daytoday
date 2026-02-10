import logging
from datetime import date, datetime

from django.db import transaction

from ..models import (
    DailySummary, Meeting, Transcript, NoteReference, WordDocument,
)
from .config_service import ConfigService
from .auth_service import AuthService
from .graph_client import GraphClient
from .calendar_service import CalendarService
from .teams_service import TeamsService
from .onenote_service import OneNoteService
from .word_service import WordService

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(self):
        self._config = ConfigService.get_instance()
        self._auth = AuthService.get_instance()
        self._graph = GraphClient(self._auth)
        self._calendar = CalendarService(self._graph)
        self._teams = TeamsService(self._graph)
        self._onenote = OneNoteService(self._graph)
        self._word = WordService(self._config.word_doc_directories)

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
            logger.info(f"Re-collecting data for {target_date} (existing record).")

        errors = []

        # 1. Calendar events
        try:
            events = self._calendar.get_events_for_date(target_date)
            self._store_meetings(summary, events)
            logger.info(f"Stored {len(events)} meeting(s).")
        except Exception as e:
            logger.error(f"Calendar collection failed: {e}", exc_info=True)
            errors.append(f"Calendar: {e}")

        # 2. Teams transcripts
        try:
            self._collect_transcripts(summary)
        except Exception as e:
            logger.error(f"Transcript collection failed: {e}", exc_info=True)
            errors.append(f"Transcripts: {e}")

        # 3. OneNote pages
        try:
            self._collect_notes(summary, target_date)
        except Exception as e:
            logger.error(f"OneNote collection failed: {e}", exc_info=True)
            errors.append(f"OneNote: {e}")

        # 4. Word documents
        try:
            self._collect_word_docs(summary, target_date)
        except Exception as e:
            logger.error(f"Word doc collection failed: {e}", exc_info=True)
            errors.append(f"Word docs: {e}")

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

    def _collect_transcripts(self, summary):
        online_meetings = summary.meetings.filter(is_online_meeting=True)
        transcript_count = 0
        for meeting_obj in online_meetings:
            event_dict = {
                'is_online_meeting': True,
                'online_meeting_url': meeting_obj.online_meeting_url,
                'subject': meeting_obj.subject,
            }
            transcripts = self._teams.get_transcripts_for_event(event_dict)
            for t in transcripts:
                Transcript.objects.create(
                    meeting=meeting_obj,
                    transcript_graph_id=t.get('transcript_id', ''),
                    content_vtt=t.get('content_vtt', ''),
                    content_plain=self._parse_vtt_to_plain(
                        t.get('content_vtt', '')
                    ),
                    created_at=t.get('created_at') or None,
                )
                transcript_count += 1
        if transcript_count:
            logger.info(f"Stored {transcript_count} transcript(s).")

    def _collect_notes(self, summary, target_date):
        modified_since = datetime.combine(target_date, datetime.min.time())
        pages = self._onenote.list_recent_pages(modified_since=modified_since)
        notes = []
        for page in pages:
            parent = page.get('parentSection', {})
            notes.append(NoteReference(
                daily_summary=summary,
                page_title=page.get('title', 'Untitled'),
                page_graph_id=page.get('id', ''),
                section_name=parent.get('displayName', '') if parent else '',
                content_snippet='',
                last_modified=page.get('lastModifiedDateTime'),
            ))
        if notes:
            NoteReference.objects.bulk_create(notes)
            logger.info(f"Stored {len(notes)} OneNote reference(s).")

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

    def _parse_vtt_to_plain(self, vtt_content):
        if not vtt_content:
            return ''
        lines = vtt_content.split('\n')
        plain_lines = []
        for line in lines:
            line = line.strip()
            if (line
                    and not line.startswith('WEBVTT')
                    and '-->' not in line
                    and not line.isdigit()):
                plain_lines.append(line)
        return '\n'.join(plain_lines)

    def _generate_summary_text(self, summary):
        parts = [
            f"# Daily Summary - {summary.date.strftime('%A, %B %d, %Y')}",
            '',
        ]

        meetings = summary.meetings.all()
        if meetings:
            parts.append(f"## Meetings ({meetings.count()})")
            parts.append('')
            for m in meetings:
                time_str = m.start_time.strftime('%I:%M %p')
                end_str = m.end_time.strftime('%I:%M %p')
                parts.append(f"### {time_str} - {end_str}: {m.subject}")
                parts.append(f"- **Organizer:** {m.organizer_name}")
                if m.location:
                    parts.append(f"- **Location:** {m.location}")
                if m.body_preview:
                    preview = m.body_preview[:200]
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
                line = f"- {n.page_title}"
                if n.section_name:
                    line += f" (Section: {n.section_name})"
                parts.append(line)
            parts.append('')

        docs = summary.word_documents.all()
        if docs:
            parts.append(f"## Word Documents Modified ({docs.count()})")
            parts.append('')
            for d in docs:
                size_kb = d.size_bytes / 1024
                parts.append(f"- {d.file_name} ({size_kb:.1f} KB)")
            parts.append('')

        if not meetings and not notes and not docs:
            parts.append('*No meetings, notes, or documents found for today.*')
            parts.append('')

        return '\n'.join(parts)

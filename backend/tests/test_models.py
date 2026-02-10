from datetime import date, datetime, timezone
from django.test import TestCase
from django.db import IntegrityError
from core.models import (
    DailySummary, Meeting, Transcript, NoteReference, WordDocument,
)


class DailySummaryModelTest(TestCase):
    def test_create_summary(self):
        summary = DailySummary.objects.create(date=date(2025, 1, 15))
        self.assertEqual(str(summary), 'Summary for 2025-01-15')
        self.assertEqual(summary.status, 'pending')
        self.assertEqual(summary.summary_text, '')

    def test_unique_date_constraint(self):
        DailySummary.objects.create(date=date(2025, 1, 15))
        with self.assertRaises(IntegrityError):
            DailySummary.objects.create(date=date(2025, 1, 15))

    def test_ordering_descending_by_date(self):
        DailySummary.objects.create(date=date(2025, 1, 10))
        DailySummary.objects.create(date=date(2025, 1, 15))
        DailySummary.objects.create(date=date(2025, 1, 12))
        dates = list(
            DailySummary.objects.values_list('date', flat=True)
        )
        self.assertEqual(dates, [
            date(2025, 1, 15),
            date(2025, 1, 12),
            date(2025, 1, 10),
        ])


class MeetingModelTest(TestCase):
    def setUp(self):
        self.summary = DailySummary.objects.create(date=date(2025, 1, 15))

    def test_create_meeting(self):
        meeting = Meeting.objects.create(
            daily_summary=self.summary,
            subject='Test Meeting',
            start_time=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            organizer_name='John Doe',
        )
        self.assertEqual(str(meeting), 'Test Meeting (2025-01-15 09:00:00+00:00)')

    def test_cascade_delete(self):
        Meeting.objects.create(
            daily_summary=self.summary,
            subject='Meeting 1',
            start_time=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(Meeting.objects.count(), 1)
        self.summary.delete()
        self.assertEqual(Meeting.objects.count(), 0)

    def test_attendees_json(self):
        attendees = [
            {'name': 'Alice', 'email': 'alice@example.com', 'response': 'accepted'},
            {'name': 'Bob', 'email': 'bob@example.com', 'response': 'tentative'},
        ]
        meeting = Meeting.objects.create(
            daily_summary=self.summary,
            subject='Team Sync',
            start_time=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            attendees_json=attendees,
        )
        meeting.refresh_from_db()
        self.assertEqual(len(meeting.attendees_json), 2)
        self.assertEqual(meeting.attendees_json[0]['name'], 'Alice')


class TranscriptModelTest(TestCase):
    def setUp(self):
        self.summary = DailySummary.objects.create(date=date(2025, 1, 15))
        self.meeting = Meeting.objects.create(
            daily_summary=self.summary,
            subject='Teams Call',
            start_time=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            is_online_meeting=True,
        )

    def test_create_transcript(self):
        transcript = Transcript.objects.create(
            meeting=self.meeting,
            content_vtt='WEBVTT\n\n00:00.000 --> 00:05.000\nHello everyone',
            content_plain='Hello everyone',
        )
        self.assertIn('Teams Call', str(transcript))

    def test_cascade_from_meeting(self):
        Transcript.objects.create(
            meeting=self.meeting,
            content_plain='Test content',
        )
        self.meeting.delete()
        self.assertEqual(Transcript.objects.count(), 0)


class NoteReferenceModelTest(TestCase):
    def test_create_note(self):
        summary = DailySummary.objects.create(date=date(2025, 1, 15))
        note = NoteReference.objects.create(
            daily_summary=summary,
            page_title='Project Notes',
            notebook_name='Work',
            section_name='Projects',
        )
        self.assertEqual(str(note), 'Note: Project Notes')


class WordDocumentModelTest(TestCase):
    def test_create_word_doc(self):
        summary = DailySummary.objects.create(date=date(2025, 1, 15))
        doc = WordDocument.objects.create(
            daily_summary=summary,
            file_name='report.docx',
            file_path='C:\\docs\\report.docx',
            content_text='Report content here',
            size_bytes=15000,
        )
        self.assertEqual(str(doc), 'Doc: report.docx')

import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase
from docx import Document

from core.services.word_service import WordService


class WordServiceTest(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_find_documents_empty_dir(self):
        service = WordService([self.tmpdir])
        docs = service.find_documents()
        self.assertEqual(docs, [])

    def test_find_documents_with_docx(self):
        doc = Document()
        doc.add_paragraph('Test content')
        path = os.path.join(self.tmpdir, 'test.docx')
        doc.save(path)

        service = WordService([self.tmpdir])
        docs = service.find_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['file_name'], 'test.docx')

    def test_skip_temp_files(self):
        doc = Document()
        doc.add_paragraph('Test')
        doc.save(os.path.join(self.tmpdir, '~$temp.docx'))
        doc.save(os.path.join(self.tmpdir, 'real.docx'))

        service = WordService([self.tmpdir])
        docs = service.find_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['file_name'], 'real.docx')

    def test_extract_text(self):
        doc = Document()
        doc.add_paragraph('Hello World')
        doc.add_paragraph('Second paragraph')
        path = os.path.join(self.tmpdir, 'test.docx')
        doc.save(path)

        service = WordService([self.tmpdir])
        result = service.extract_text(path)
        self.assertEqual(len(result['content']), 2)
        self.assertEqual(result['content'][0]['text'], 'Hello World')
        self.assertEqual(result['content'][1]['text'], 'Second paragraph')

    def test_extract_text_invalid_file(self):
        path = os.path.join(self.tmpdir, 'notreal.docx')
        service = WordService([self.tmpdir])
        result = service.extract_text(path)
        self.assertIn('error', result)

    def test_nonexistent_directory(self):
        service = WordService(['/nonexistent/path/abc123'])
        docs = service.find_documents()
        self.assertEqual(docs, [])

    def test_find_documents_with_date_filter(self):
        doc = Document()
        doc.add_paragraph('Old content')
        path = os.path.join(self.tmpdir, 'old.docx')
        doc.save(path)
        # Set modification time to the past
        old_time = datetime(2020, 1, 1).timestamp()
        os.utime(path, (old_time, old_time))

        doc2 = Document()
        doc2.add_paragraph('New content')
        path2 = os.path.join(self.tmpdir, 'new.docx')
        doc2.save(path2)

        service = WordService([self.tmpdir])
        docs = service.find_documents(modified_since=date.today())
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['file_name'], 'new.docx')


class CalendarServiceTest(TestCase):
    def test_normalize_event(self):
        from core.services.calendar_service import CalendarService

        mock_graph = MagicMock()
        service = CalendarService(mock_graph)

        raw_event = {
            'id': 'evt-123',
            'subject': 'Team Standup',
            'start': {'dateTime': '2025-01-15T09:00:00', 'timeZone': 'UTC'},
            'end': {'dateTime': '2025-01-15T09:30:00', 'timeZone': 'UTC'},
            'organizer': {
                'emailAddress': {
                    'name': 'John Doe',
                    'address': 'john@example.com',
                }
            },
            'attendees': [
                {
                    'emailAddress': {'name': 'Jane', 'address': 'jane@example.com'},
                    'status': {'response': 'accepted'},
                }
            ],
            'bodyPreview': 'Daily standup meeting',
            'location': {'displayName': 'Room 101'},
            'isOnlineMeeting': True,
            'onlineMeeting': {'joinUrl': 'https://teams.microsoft.com/meet/123'},
            'webLink': 'https://outlook.office.com/calendar/item/123',
        }

        normalized = service._normalize_event(raw_event)
        self.assertEqual(normalized['graph_id'], 'evt-123')
        self.assertEqual(normalized['subject'], 'Team Standup')
        self.assertEqual(normalized['organizer_name'], 'John Doe')
        self.assertEqual(len(normalized['attendees']), 1)
        self.assertTrue(normalized['is_online_meeting'])
        self.assertIn('teams.microsoft.com', normalized['online_meeting_url'])


class VTTParserTest(TestCase):
    def test_parse_vtt(self):
        from core.services.summary_service import SummaryService
        service = SummaryService.__new__(SummaryService)

        vtt = (
            "WEBVTT\n\n"
            "1\n"
            "00:00:00.000 --> 00:00:05.000\n"
            "Hello everyone, welcome to the meeting.\n\n"
            "2\n"
            "00:00:05.000 --> 00:00:10.000\n"
            "Let's get started with the agenda.\n"
        )

        plain = service._parse_vtt_to_plain(vtt)
        self.assertIn('Hello everyone', plain)
        self.assertIn("Let's get started", plain)
        self.assertNotIn('WEBVTT', plain)
        self.assertNotIn('-->', plain)

    def test_parse_empty_vtt(self):
        from core.services.summary_service import SummaryService
        service = SummaryService.__new__(SummaryService)
        self.assertEqual(service._parse_vtt_to_plain(''), '')
        self.assertEqual(service._parse_vtt_to_plain(None), '')

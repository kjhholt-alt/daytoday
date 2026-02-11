from datetime import date, datetime, timezone
from django.test import TestCase
from rest_framework.test import APIClient
from core.models import (
    DailySummary, Meeting, NoteReference, WordDocument,
)


class DailySummaryViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.summary = DailySummary.objects.create(
            date=date(2025, 1, 15),
            status='complete',
            summary_text='Test summary text',
        )
        Meeting.objects.create(
            daily_summary=self.summary,
            subject='Morning Standup',
            start_time=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            organizer_name='Jane',
        )

    def test_list_summaries(self):
        response = self.client.get('/api/summaries/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['date'], '2025-01-15')
        self.assertEqual(results[0]['meeting_count'], 1)

    def test_detail_summary(self):
        response = self.client.get(f'/api/summaries/{self.summary.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['date'], '2025-01-15')
        self.assertEqual(len(response.data['meetings']), 1)
        self.assertEqual(
            response.data['meetings'][0]['subject'], 'Morning Standup'
        )

    def test_by_date(self):
        response = self.client.get('/api/summaries/by-date/2025-01-15/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['date'], '2025-01-15')

    def test_by_date_not_found(self):
        response = self.client.get('/api/summaries/by-date/2025-12-31/')
        self.assertEqual(response.status_code, 404)

    def test_by_date_invalid(self):
        # "not-a-date" doesn't match URL regex [0-9-]+ so Django returns 404
        response = self.client.get('/api/summaries/by-date/not-a-date/')
        self.assertEqual(response.status_code, 404)

    def test_by_date_invalid_format(self):
        # "99-99-99" matches regex but parse_date returns None -> 400
        response = self.client.get('/api/summaries/by-date/99-99-99/')
        self.assertEqual(response.status_code, 400)

    def test_today_not_found(self):
        response = self.client.get('/api/summaries/today/')
        # Today won't match 2025-01-15 so it should 404
        self.assertEqual(response.status_code, 404)


class SearchViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        summary = DailySummary.objects.create(
            date=date(2025, 1, 15), status='complete'
        )
        Meeting.objects.create(
            daily_summary=summary,
            subject='Budget Review',
            start_time=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            body_preview='Discussing Q1 budget allocations',
        )
        NoteReference.objects.create(
            daily_summary=summary,
            page_title='Budget Notes',
        )
        WordDocument.objects.create(
            daily_summary=summary,
            file_name='budget_report.docx',
            file_path='C:\\docs\\budget_report.docx',
            content_text='Budget details for Q1',
        )

    def test_search_meetings(self):
        response = self.client.get('/api/search/?q=Budget')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['meetings']), 1)

    def test_search_notes(self):
        response = self.client.get('/api/search/?q=Budget')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['notes']), 1)

    def test_search_documents(self):
        response = self.client.get('/api/search/?q=budget')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['documents']), 1)

    def test_search_no_query(self):
        response = self.client.get('/api/search/')
        self.assertEqual(response.status_code, 400)

    def test_search_no_results(self):
        response = self.client.get('/api/search/?q=zzzznonexistent')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['meetings']), 0)


class StatusViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_status_endpoint(self):
        response = self.client.get('/api/status/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('outlook_available', response.data)
        self.assertIn('onenote_available', response.data)
        self.assertIn('outlook_enabled', response.data)
        self.assertIn('onenote_enabled', response.data)
        self.assertIn('word_doc_directories', response.data)
        self.assertIn('version', response.data)

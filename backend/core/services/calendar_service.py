import logging
from datetime import datetime, timedelta

from .graph_client import GraphClient

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self, graph_client: GraphClient):
        self._client = graph_client

    def get_events_for_date(self, target_date=None):
        if target_date is None:
            target_date = datetime.now().date()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)

        params = {
            'startDateTime': start_dt.isoformat() + 'Z',
            'endDateTime': end_dt.isoformat() + 'Z',
            '$select': (
                'id,subject,start,end,organizer,attendees,'
                'bodyPreview,location,isOnlineMeeting,'
                'onlineMeeting,onlineMeetingProvider,webLink'
            ),
            '$orderby': 'start/dateTime',
            '$top': 100,
        }

        logger.info(f"Fetching calendar events for {target_date}...")
        events = self._client.get_paginated('/me/calendarView', params=params)
        logger.info(f"Retrieved {len(events)} events for {target_date}.")
        return [self._normalize_event(e) for e in events]

    def _normalize_event(self, raw_event):
        organizer = raw_event.get('organizer', {}).get('emailAddress', {})
        online_meeting = raw_event.get('onlineMeeting')
        return {
            'graph_id': raw_event.get('id', ''),
            'subject': raw_event.get('subject', '(No subject)'),
            'start_time': raw_event.get('start', {}).get('dateTime', ''),
            'end_time': raw_event.get('end', {}).get('dateTime', ''),
            'timezone': raw_event.get('start', {}).get('timeZone', 'UTC'),
            'organizer_name': organizer.get('name', 'Unknown'),
            'organizer_email': organizer.get('address', ''),
            'attendees': [
                {
                    'name': a.get('emailAddress', {}).get('name', ''),
                    'email': a.get('emailAddress', {}).get('address', ''),
                    'response': a.get('status', {}).get('response', 'none'),
                }
                for a in raw_event.get('attendees', [])
            ],
            'body_preview': raw_event.get('bodyPreview', ''),
            'location': raw_event.get('location', {}).get('displayName', ''),
            'is_online_meeting': raw_event.get('isOnlineMeeting', False),
            'online_meeting_url': (
                online_meeting.get('joinUrl', '') if online_meeting else ''
            ),
            'web_link': raw_event.get('webLink', ''),
        }

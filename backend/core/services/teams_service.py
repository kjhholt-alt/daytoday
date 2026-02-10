import logging

from .graph_client import GraphClient, GraphClientError

logger = logging.getLogger(__name__)


class TeamsService:
    def __init__(self, graph_client: GraphClient):
        self._client = graph_client

    def get_transcripts_for_event(self, event: dict):
        if not event.get('is_online_meeting') or not event.get('online_meeting_url'):
            return []

        try:
            meeting_id = self._resolve_meeting_id(event['online_meeting_url'])
            if not meeting_id:
                logger.debug(
                    f"No online meeting ID found for: {event.get('subject', '')}"
                )
                return []

            transcripts_meta = self._list_transcripts(meeting_id)
            transcripts = []
            for t_meta in transcripts_meta:
                content = self._get_transcript_content(
                    meeting_id, t_meta['id']
                )
                if content:
                    transcripts.append({
                        'transcript_id': t_meta['id'],
                        'created_at': t_meta.get('createdDateTime', ''),
                        'content_vtt': content,
                    })

            logger.info(
                f"Retrieved {len(transcripts)} transcript(s) for: "
                f"{event.get('subject', '')}"
            )
            return transcripts

        except GraphClientError as e:
            if e.status_code == 403:
                logger.warning(
                    f"Permission denied for transcripts: "
                    f"{event.get('subject', '')}. "
                    "OnlineMeetingTranscript.Read.All may not be consented."
                )
            elif e.status_code == 404:
                logger.debug(
                    f"No transcripts available for: {event.get('subject', '')}"
                )
            else:
                logger.error(
                    f"Error fetching transcripts for "
                    f"{event.get('subject', '')}: {e}"
                )
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching transcripts: {e}")
            return []

    def _resolve_meeting_id(self, join_url):
        try:
            result = self._client.get(
                '/me/onlineMeetings',
                params={'$filter': f"JoinWebUrl eq '{join_url}'"},
            )
            meetings = result.get('value', [])
            if meetings:
                return meetings[0]['id']
            return None
        except GraphClientError as e:
            logger.debug(f"Could not resolve meeting ID: {e}")
            return None

    def _list_transcripts(self, meeting_id):
        endpoint = f'/me/onlineMeetings/{meeting_id}/transcripts'
        return self._client.get_paginated(endpoint)

    def _get_transcript_content(self, meeting_id, transcript_id):
        endpoint = (
            f'/me/onlineMeetings/{meeting_id}'
            f'/transcripts/{transcript_id}/content'
        )
        try:
            return self._client.get_raw(
                endpoint, params={'$format': 'text/vtt'}
            )
        except GraphClientError as e:
            logger.warning(f"Could not fetch transcript content: {e}")
            return None

import logging
from datetime import datetime

from .graph_client import GraphClient, GraphClientError

logger = logging.getLogger(__name__)


class OneNoteService:
    def __init__(self, graph_client: GraphClient):
        self._client = graph_client

    def list_notebooks(self):
        try:
            notebooks = self._client.get_paginated(
                '/me/onenote/notebooks',
                params={
                    '$select': 'id,displayName,lastModifiedDateTime,links',
                },
            )
            return [
                {
                    'notebook_id': nb['id'],
                    'name': nb.get('displayName', 'Untitled'),
                    'last_modified': nb.get('lastModifiedDateTime', ''),
                    'web_url': (
                        nb.get('links', {})
                        .get('oneNoteWebUrl', {})
                        .get('href', '')
                    ),
                }
                for nb in notebooks
            ]
        except GraphClientError as e:
            logger.error(f"Failed to list notebooks: {e}")
            return []

    def list_sections(self, notebook_id):
        try:
            sections = self._client.get_paginated(
                f'/me/onenote/notebooks/{notebook_id}/sections',
                params={
                    '$select': 'id,displayName,lastModifiedDateTime',
                },
            )
            return [
                {
                    'section_id': s['id'],
                    'name': s.get('displayName', ''),
                    'last_modified': s.get('lastModifiedDateTime', ''),
                }
                for s in sections
            ]
        except GraphClientError as e:
            logger.error(f"Failed to list sections: {e}")
            return []

    def list_recent_pages(self, modified_since=None):
        params = {
            '$select': (
                'id,title,lastModifiedDateTime,'
                'parentSection,createdDateTime'
            ),
            '$orderby': 'lastModifiedDateTime desc',
            '$top': 50,
        }
        if modified_since:
            if isinstance(modified_since, datetime):
                filter_dt = modified_since.isoformat() + 'Z'
            else:
                filter_dt = modified_since.isoformat() + 'T00:00:00Z'
            params['$filter'] = (
                f"lastModifiedDateTime ge {filter_dt}"
            )

        try:
            pages = self._client.get_paginated(
                '/me/onenote/pages', params=params
            )
            logger.info(f"Retrieved {len(pages)} recent OneNote page(s).")
            return pages
        except GraphClientError as e:
            logger.error(f"Failed to list pages: {e}")
            return []

    def get_page_content(self, page_id):
        try:
            return self._client.get_raw(
                f'/me/onenote/pages/{page_id}/content'
            )
        except GraphClientError as e:
            logger.error(f"Failed to get page content for {page_id}: {e}")
            return ''

"""
Graph OneNote Service - retrieves recently modified OneNote pages via the
Microsoft Graph API.

This service is a fallback for when OneNote COM automation
(``win32_onenote_service.OneNoteLocalService``) is not available -- for
example on machines running the UWP/Store edition of OneNote, or when
pywin32 is not installed.

The public method ``list_recent_pages`` returns page dicts in the exact
same shape consumed by ``SummaryService._collect_notes``:

.. code-block:: python

    {
        "id": "<graph page id>",
        "title": "Page Title",
        "lastModifiedDateTime": "2026-02-10T14:30:00+00:00",
        "parentSection": {
            "displayName": "Section Name",
        },
    }

Requirements
------------
- requests  (`pip install requests`)
- A valid ``AuthService`` instance that can provide OAuth2 bearer tokens
  with the ``Notes.Read`` or ``Notes.Read.All`` scope.
"""

import logging
import re
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Union

import requests

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
ONENOTE_PAGES_ENDPOINT = "/me/onenote/pages"

# Sensible defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGES = 20  # safety cap to avoid runaway pagination
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # base delay in seconds for exponential back-off


class GraphOneNoteService:
    """Retrieve OneNote pages from Microsoft Graph API.

    Parameters
    ----------
    auth_service:
        An instance of ``AuthService`` (or any object that exposes
        ``get_headers() -> dict`` and ``get_access_token() -> str``).
    """

    def __init__(self, auth_service):
        self._auth = auth_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_recent_pages(
        self, modified_since: Optional[Union[datetime, date]] = None
    ) -> List[Dict]:
        """Return recently modified OneNote pages from Graph API.

        Parameters
        ----------
        modified_since:
            If provided, only pages whose ``lastModifiedDateTime`` is on
            or after this value are returned.  Accepts both
            ``datetime.datetime`` and ``datetime.date`` objects.

        Returns
        -------
        list[dict]
            A list of page dicts compatible with the format expected by
            ``SummaryService._collect_notes``.  Returns an empty list
            when authentication fails or if the API call errors out.
        """
        logger.info(
            "Fetching recent OneNote pages from Graph API "
            "(modified_since=%s)",
            modified_since,
        )

        # Build query parameters
        params = self._build_query_params(modified_since)

        try:
            raw_pages = self._fetch_all_pages(params)
        except Exception as exc:
            logger.error(
                "Failed to retrieve OneNote pages from Graph API: %s",
                exc,
                exc_info=True,
            )
            return []

        # Normalise into the dict shape expected by SummaryService
        pages = [self._normalise_page(p) for p in raw_pages]

        logger.info(
            "Graph API returned %d OneNote page(s) (modified_since=%s).",
            len(pages),
            modified_since,
        )
        return pages

    # ------------------------------------------------------------------
    # Query building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_query_params(
        modified_since: Optional[Union[datetime, date]] = None,
    ) -> Dict[str, str]:
        """Construct the OData query parameters for the pages endpoint."""
        params: Dict[str, str] = {
            "$select": "id,title,lastModifiedDateTime,parentSection",
            "$expand": "parentSection($select=displayName)",
            "$orderby": "lastModifiedDateTime desc",
            "$top": str(DEFAULT_PAGE_SIZE),
        }

        if modified_since is not None:
            filter_dt = _to_iso_utc(modified_since)
            params["$filter"] = (
                f"lastModifiedDateTime ge {filter_dt}"
            )

        return params

    # ------------------------------------------------------------------
    # HTTP / pagination
    # ------------------------------------------------------------------

    def _fetch_all_pages(self, params: Dict[str, str]) -> List[Dict]:
        """Fetch all matching pages, following ``@odata.nextLink`` for
        pagination.

        Raises on unrecoverable HTTP or auth errors.
        """
        url = f"{GRAPH_BASE_URL}{ONENOTE_PAGES_ENDPOINT}"
        all_items: List[Dict] = []
        page_count = 0

        while url and page_count < MAX_PAGES:
            # On the first request we pass our OData params; for
            # subsequent pages the nextLink URL already contains them.
            request_params = params if page_count == 0 else None

            data = self._get_json(url, params=request_params)
            items = data.get("value", [])
            all_items.extend(items)

            url = data.get("@odata.nextLink")
            page_count += 1

            if url:
                logger.debug(
                    "Following @odata.nextLink (page %d, %d items so far)",
                    page_count,
                    len(all_items),
                )

        if page_count >= MAX_PAGES:
            logger.warning(
                "Reached pagination safety cap (%d pages, %d items). "
                "Some results may have been omitted.",
                MAX_PAGES,
                len(all_items),
            )

        return all_items

    def _get_json(
        self, url: str, params: Optional[Dict[str, str]] = None
    ) -> dict:
        """Perform an authenticated GET request with retry logic.

        Returns the parsed JSON body.  Raises ``RuntimeError`` on
        persistent failures.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                headers = self._auth.get_headers()
            except Exception as exc:
                logger.error(
                    "Failed to obtain auth headers: %s", exc
                )
                raise RuntimeError(
                    f"Authentication failed: {exc}"
                ) from exc

            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                delay = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    "Connection error on attempt %d/%d: %s. "
                    "Retrying in %ds...",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)
                continue
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                delay = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    "Request timed out on attempt %d/%d. "
                    "Retrying in %ds...",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue

            # Handle throttling (HTTP 429)
            if response.status_code == 429:
                retry_after = int(
                    response.headers.get("Retry-After", 5)
                )
                logger.warning(
                    "Throttled by Graph API (429). "
                    "Retrying after %ds (attempt %d/%d)...",
                    retry_after,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(retry_after)
                continue

            # Handle expired / invalid token (HTTP 401)
            if response.status_code == 401 and attempt < MAX_RETRIES - 1:
                logger.warning(
                    "401 Unauthorized on attempt %d/%d; token may be "
                    "expired. Re-authenticating...",
                    attempt + 1,
                    MAX_RETRIES,
                )
                continue

            # Raise on other client / server errors
            if response.status_code >= 400:
                error_body = response.text[:500]
                logger.error(
                    "Graph API error %d: %s",
                    response.status_code,
                    error_body,
                )
                raise RuntimeError(
                    f"Graph API returned HTTP {response.status_code}: "
                    f"{error_body}"
                )

            # Success
            return response.json() if response.content else {}

        # Exhausted retries
        raise RuntimeError(
            f"Graph API request failed after {MAX_RETRIES} retries: "
            f"{last_exc}"
        )

    # ------------------------------------------------------------------
    # Page content retrieval
    # ------------------------------------------------------------------

    def fetch_page_content(self, page_id: str) -> str:
        """Fetch the HTML content of a OneNote page and return plain text.

        Uses GET /me/onenote/pages/{id}/content to retrieve the page
        body as HTML, then strips tags to produce a plain-text version.

        Parameters
        ----------
        page_id:
            The Graph API page ID.

        Returns
        -------
        str
            Plain text content of the page.  Returns an empty string
            if fetching or parsing fails.
        """
        if not page_id:
            return ""

        url = f"{GRAPH_BASE_URL}/me/onenote/pages/{page_id}/content"
        logger.info("Fetching OneNote page content for page %s", page_id)

        try:
            headers = self._auth.get_headers()
        except Exception as exc:
            logger.error("Failed to get auth headers for page content: %s", exc)
            return ""

        try:
            response = requests.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT
            )
        except Exception as exc:
            logger.warning(
                "Failed to fetch page content for %s: %s", page_id, exc
            )
            return ""

        if response.status_code != 200:
            logger.warning(
                "Page content request returned HTTP %d for page %s",
                response.status_code,
                page_id,
            )
            return ""

        html_content = response.text
        return _strip_html_tags(html_content)

    # ------------------------------------------------------------------
    # Response normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_page(raw: Dict) -> Dict:
        """Transform a raw Graph API page object into the dict format
        expected by ``SummaryService._collect_notes``.

        The target shape is:

        .. code-block:: python

            {
                "id": str,
                "title": str,
                "lastModifiedDateTime": str,  # ISO-8601
                "parentSection": {
                    "displayName": str,
                },
            }
        """
        parent_section = raw.get("parentSection") or {}

        return {
            "id": raw.get("id", ""),
            "title": raw.get("title", "Untitled"),
            "lastModifiedDateTime": raw.get(
                "lastModifiedDateTime", ""
            ),
            "parentSection": {
                "displayName": parent_section.get(
                    "displayName", ""
                ),
            },
            "_source": "graph",
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _strip_html_tags(html: str) -> str:
    """Remove HTML tags from a string and return clean plain text.

    Performs basic whitespace normalisation (collapses runs of blank
    lines, strips leading/trailing whitespace).
    """
    if not html:
        return ""
    # Remove <style> and <script> blocks entirely
    text = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br>, <p>, <div>, <li> tags with newlines for readability
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|li|tr|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    # Collapse multiple blank lines into one
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _to_iso_utc(value: Union[datetime, date]) -> str:
    """Convert a ``datetime`` or ``date`` to an ISO-8601 UTC string
    suitable for OData ``$filter`` expressions.

    Graph API expects the format ``2026-02-10T00:00:00Z``.
    """
    if isinstance(value, datetime):
        # If the datetime is naive, assume UTC
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    # date object -- start of day in UTC
    return value.strftime("%Y-%m-%dT00:00:00Z")

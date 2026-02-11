"""
Microsoft Graph API Calendar Service.

Retrieves calendar events via the Microsoft Graph REST API and returns them
in the exact same normalized dict format as OutlookCalendarService, so that
SummaryService._store_meetings() can consume them without any changes.

This service is intended as a fallback when Outlook COM automation is not
available -- for example, when the user is running the New Outlook which
does not expose a COM interface.
"""

import logging
import re
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

GRAPH_CALENDAR_VIEW_URL = "https://graph.microsoft.com/v1.0/me/calendarView"

# Fields to request from the Graph API
_SELECT_FIELDS = (
    "subject,start,end,organizer,attendees,bodyPreview,"
    "location,isOnlineMeeting,onlineMeetingUrl,webLink,id"
)

# Regex to extract Teams meeting URLs from the body preview
TEAMS_URL_PATTERN = re.compile(
    r"https://teams\.microsoft\.com/l/meetup-join/[^\s<>\"')]+",
    re.IGNORECASE,
)

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 30


class GraphCalendarService:
    """
    Reads calendar events from Microsoft Graph API and returns them in the
    normalized dict format expected by SummaryService._store_meetings().

    The output format is identical to OutlookCalendarService.get_events_for_date().
    """

    def __init__(self, auth_service):
        """
        Args:
            auth_service: An instance of AuthService (or any object that
                          provides a get_access_token() method returning
                          a valid Bearer token string).
        """
        self._auth = auth_service

    def get_events_for_date(self, target_date=None):
        """
        Retrieve all calendar events for a given date from the Microsoft
        Graph calendarView endpoint.

        Args:
            target_date: A datetime.date or datetime.datetime for the day
                         to query.  Defaults to today if not provided.

        Returns:
            A list of dicts, each in the normalized format expected by
            SummaryService._store_meetings().  Returns an empty list if
            authentication fails or an API error occurs.
        """
        if target_date is None:
            target_date = datetime.now().date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()

        logger.info("Fetching Graph API calendar events for %s", target_date)

        # ------------------------------------------------------------------
        # Acquire an access token
        # ------------------------------------------------------------------
        try:
            token = self._auth.get_token()
        except Exception:
            logger.exception(
                "Failed to acquire access token. Returning empty event list."
            )
            return []

        if not token:
            logger.warning(
                "No access token available. Returning empty event list."
            )
            return []

        # ------------------------------------------------------------------
        # Build the request
        # ------------------------------------------------------------------
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # The calendarView endpoint requires startDateTime and endDateTime
        # in ISO 8601 / UTC format.
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)

        params = {
            "startDateTime": start_dt.isoformat() + "Z",
            "endDateTime": end_dt.isoformat() + "Z",
            "$select": _SELECT_FIELDS,
            "$orderby": "start/dateTime",
            "$top": 100,
        }

        # ------------------------------------------------------------------
        # Fetch events (with pagination)
        # ------------------------------------------------------------------
        raw_events = self._fetch_all_events(headers, params)

        # ------------------------------------------------------------------
        # Normalize each event to the shared dict format
        # ------------------------------------------------------------------
        events = []
        for raw in raw_events:
            try:
                normalized = self._normalize_event(raw)
                events.append(normalized)
            except Exception:
                subject = raw.get("subject", "<unknown>")
                logger.exception(
                    "Error normalizing Graph event '%s'. Skipping.", subject
                )

        logger.info(
            "Found %d event(s) on %s via Graph API.", len(events), target_date
        )
        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_all_events(self, headers, params):
        """
        Fetch all events from the calendarView endpoint, following
        @odata.nextLink pagination links until all pages are retrieved.

        Returns a list of raw event dicts from the Graph API.
        """
        all_events = []
        url = GRAPH_CALENDAR_VIEW_URL

        while url:
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                logger.exception(
                    "Graph API HTTP error (status %s) while fetching "
                    "calendar events.",
                    getattr(response, "status_code", "unknown"),
                )
                break
            except requests.exceptions.ConnectionError:
                logger.exception(
                    "Connection error while fetching calendar events "
                    "from Graph API."
                )
                break
            except requests.exceptions.Timeout:
                logger.exception(
                    "Timeout while fetching calendar events from Graph API."
                )
                break
            except requests.exceptions.RequestException:
                logger.exception(
                    "Unexpected request error while fetching calendar events."
                )
                break

            data = response.json()
            all_events.extend(data.get("value", []))

            # Follow pagination; clear params so they aren't re-appended
            # to the @odata.nextLink URL (which already contains them).
            url = data.get("@odata.nextLink")
            params = None

        return all_events

    def _normalize_event(self, raw_event):
        """
        Convert a single raw Graph API event dict into the normalized format
        that matches OutlookCalendarService._normalize_appointment().

        The output dict has exactly the same keys and value types so that
        SummaryService._store_meetings() works without changes.
        """
        # --- Basic fields ---------------------------------------------------
        graph_id = raw_event.get("id", "")
        subject = raw_event.get("subject", "") or ""
        body_preview = raw_event.get("bodyPreview", "") or ""
        web_link = raw_event.get("webLink", "") or ""

        # --- Times -----------------------------------------------------------
        start_obj = raw_event.get("start", {})
        end_obj = raw_event.get("end", {})
        start_time = start_obj.get("dateTime", "")
        end_time = end_obj.get("dateTime", "")
        timezone = start_obj.get("timeZone", "UTC")

        # --- Location --------------------------------------------------------
        location_obj = raw_event.get("location", {})
        location = location_obj.get("displayName", "") if location_obj else ""

        # --- Organizer -------------------------------------------------------
        organizer_obj = raw_event.get("organizer", {})
        organizer_email_obj = organizer_obj.get("emailAddress", {})
        organizer_name = organizer_email_obj.get("name", "") or ""
        organizer_email = organizer_email_obj.get("address", "") or ""

        # --- Attendees -------------------------------------------------------
        attendees = []
        for attendee in raw_event.get("attendees", []):
            email_address = attendee.get("emailAddress", {})
            status = attendee.get("status", {})
            attendees.append({
                "name": email_address.get("name", "") or "",
                "email": email_address.get("address", "") or "",
                "response": status.get("response", "none") or "none",
            })

        # --- Online meeting --------------------------------------------------
        is_online_meeting = raw_event.get("isOnlineMeeting", False) or False
        online_meeting_url = raw_event.get("onlineMeetingUrl", "") or ""

        # If no explicit online meeting URL, try to extract a Teams URL
        # from the body preview text.
        if not online_meeting_url:
            online_meeting_url = self._extract_teams_url(body_preview)

        return {
            "graph_id": graph_id,
            "subject": subject,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone,
            "organizer_name": organizer_name,
            "organizer_email": organizer_email,
            "attendees": attendees,
            "body_preview": body_preview,
            "location": location,
            "is_online_meeting": is_online_meeting,
            "online_meeting_url": online_meeting_url,
            "web_link": web_link,
        }

    @staticmethod
    def _extract_teams_url(text):
        """
        Extract the first Teams meeting URL from a text string.
        Returns the URL string or an empty string if none found.
        """
        if not text:
            return ""

        match = TEAMS_URL_PATTERN.search(text)
        if match:
            return match.group(0)
        return ""

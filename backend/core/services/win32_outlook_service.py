"""
Outlook Calendar Service via win32com COM automation.

Reads calendar events directly from the user's locally-running Outlook
desktop application. No Azure/Graph API authentication required.

Returns event data in the same normalized format as CalendarService._normalize_event()
so that SummaryService._store_meetings() continues to work without changes.
"""

import logging
import re
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Outlook OlResponseStatus enum mapping
# https://learn.microsoft.com/en-us/office/vba/api/outlook.olresponsestatus
OL_RESPONSE_STATUS_MAP = {
    0: "none",          # olResponseNone
    1: "organizer",     # olResponseOrganized
    2: "tentativelyAccepted",  # olResponseTentative
    3: "accepted",      # olResponseAccepted
    4: "declined",      # olResponseDeclined
    5: "notResponded",  # olResponseNotResponded
}

# Regex to extract Teams meeting URLs from the appointment body
TEAMS_URL_PATTERN = re.compile(
    r"https://teams\.microsoft\.com/l/meetup-join/[^\s<>\"')]+",
    re.IGNORECASE,
)


class OutlookCalendarService:
    """
    Reads calendar events from the local Outlook desktop client using
    win32com COM automation and returns them in the normalized dict format
    expected by SummaryService._store_meetings().
    """

    def get_events_for_date(self, target_date=None):
        """
        Retrieve all calendar events for a given date from the local Outlook
        calendar.

        All COM work runs in a single background thread because COM objects
        cannot cross thread boundaries. The background thread also provides
        timeout protection against New Outlook (which blocks COM indefinitely).

        Args:
            target_date: A datetime.date or datetime.datetime for the day to
                         query.  Defaults to today if not provided.

        Returns:
            A list of dicts, each in the normalized format expected by
            SummaryService._store_meetings().
        """
        if target_date is None:
            target_date = datetime.now().date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()

        logger.info("Fetching Outlook calendar events for %s", target_date)

        # Run ALL COM operations in one thread (COM objects can't cross threads)
        result = {"events": [], "error": None}
        normalize_fn = self._normalize_appointment
        safe_getattr_fn = self._safe_getattr

        def _fetch_in_thread():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                import win32com.client

                logger.info("Connecting to Outlook via COM automation...")
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                logger.info("Successfully connected to Outlook.")

                # 9 = olFolderCalendar
                calendar_folder = namespace.GetDefaultFolder(9)
                items = calendar_folder.Items

                items.IncludeRecurrences = True
                items.Sort("[Start]")

                day_start = datetime(target_date.year, target_date.month, target_date.day)
                day_end = day_start + timedelta(days=1)

                date_fmt = "%m/%d/%Y %I:%M %p"
                start_str = day_start.strftime(date_fmt)
                end_str = day_end.strftime(date_fmt)

                restriction = (
                    f"[End] > '{start_str}' AND [Start] < '{end_str}'"
                )
                logger.debug("Restrict filter: %s", restriction)

                restricted_items = items.Restrict(restriction)

                events = []
                item = restricted_items.GetFirst()
                while item is not None:
                    try:
                        normalized = normalize_fn(item)
                        if normalized is not None:
                            events.append(normalized)
                    except Exception:
                        subject = safe_getattr_fn(item, "Subject", "<unknown>")
                        logger.debug(
                            "Error normalizing appointment '%s'. Skipping.", subject
                        )
                    try:
                        item = restricted_items.GetNext()
                    except Exception:
                        break

                result["events"] = events
                logger.info("COM thread found %d event(s).", len(events))
            except Exception as e:
                result["error"] = e
                logger.error("COM calendar thread failed: %s", e)
            finally:
                # Release COM objects to avoid locking Outlook
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        t = threading.Thread(target=_fetch_in_thread, daemon=True)
        t.start()
        t.join(timeout=120)

        if t.is_alive():
            logger.error(
                "Outlook COM timed out (120s). "
                "New Outlook may not support COM automation."
            )
            raise ConnectionError("Outlook COM timed out")

        if result["error"] is not None:
            raise result["error"]

        events = result["events"]
        logger.info(
            "Found %d event(s) on %s in Outlook calendar.", len(events), target_date
        )
        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_appointment(self, appt):
        """
        Convert a single Outlook AppointmentItem COM object into the
        normalized dict format used by the rest of the application.
        """
        subject = self._safe_getattr(appt, "Subject", "") or ""
        location = self._safe_getattr(appt, "Location", "") or ""
        body = self._safe_getattr(appt, "Body", "") or ""
        entry_id = self._safe_getattr(appt, "EntryID", "") or ""
        organizer = self._safe_getattr(appt, "Organizer", "") or ""

        # --- Times -----------------------------------------------------------
        start_time = self._com_datetime_to_iso(self._safe_getattr(appt, "Start", None))
        end_time = self._com_datetime_to_iso(self._safe_getattr(appt, "End", None))

        # --- Body preview (clean Teams junk, first 200 chars) -----------------
        body_preview = self._clean_body_preview(body)

        # --- Attendees -------------------------------------------------------
        attendees = self._extract_attendees(appt)

        # Try to determine organizer email from attendees or recipients
        organizer_email = self._find_organizer_email(appt, organizer)

        # --- Online meeting detection ----------------------------------------
        is_online_meeting = self._detect_online_meeting(appt, body, location)
        online_meeting_url = self._extract_teams_url(body)

        return {
            "graph_id": entry_id,
            "subject": subject,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": "America/Chicago",
            "organizer_name": organizer,
            "organizer_email": organizer_email,
            "attendees": attendees,
            "body_preview": body_preview,
            "location": location,
            "is_online_meeting": is_online_meeting,
            "online_meeting_url": online_meeting_url or "",
            "web_link": "",
        }

    def _extract_attendees(self, appt):
        """
        Extract attendee information from the AppointmentItem.Recipients
        collection.  Each recipient yields a dict with name, email, and
        response status.
        """
        attendees = []
        try:
            recipients = appt.Recipients
            if recipients is None:
                return attendees

            for i in range(1, recipients.Count + 1):  # COM collections are 1-based
                try:
                    recipient = recipients.Item(i)
                    name = self._safe_getattr(recipient, "Name", "") or ""
                    email = self._resolve_recipient_email(recipient)
                    response_status = self._safe_getattr(
                        recipient, "MeetingResponseStatus", 0
                    )
                    response_str = OL_RESPONSE_STATUS_MAP.get(response_status, "none")

                    attendees.append(
                        {
                            "name": name,
                            "email": email,
                            "response": response_str,
                        }
                    )
                except Exception:
                    logger.debug(
                        "Could not read recipient at index %d. Skipping.", i
                    )
        except Exception:
            logger.debug("Could not access Recipients collection.")

        return attendees

    def _resolve_recipient_email(self, recipient):
        """
        Attempt to resolve a Recipient's SMTP email address.

        Outlook stores addresses in different formats depending on whether
        the contact is an Exchange user (``/o=ExchangeLabs/...``) or an
        external SMTP contact.  For Exchange users we try to resolve via
        the AddressEntry.GetExchangeUser() helper.
        """
        try:
            address = self._safe_getattr(recipient, "Address", "") or ""

            # If it already looks like an SMTP address, return it directly.
            if "@" in address:
                return address

            # Try to resolve through the AddressEntry
            address_entry = self._safe_getattr(recipient, "AddressEntry", None)
            if address_entry is not None:
                addr_type = self._safe_getattr(address_entry, "Type", "")
                if addr_type == "EX":
                    exchange_user = address_entry.GetExchangeUser()
                    if exchange_user is not None:
                        smtp = self._safe_getattr(
                            exchange_user, "PrimarySmtpAddress", ""
                        )
                        if smtp:
                            return smtp

            # Fallback: return whatever address we have
            return address
        except Exception:
            logger.debug(
                "Could not resolve email for recipient '%s'.",
                self._safe_getattr(recipient, "Name", "?"),
            )
            return ""

    def _find_organizer_email(self, appt, organizer_name):
        """
        Try to find the organizer's email address.  Outlook's
        AppointmentItem does not expose it directly, so we scan the
        Recipients collection for one whose MeetingResponseStatus is 1
        (olResponseOrganized).
        """
        try:
            recipients = appt.Recipients
            if recipients is None:
                return ""

            for i in range(1, recipients.Count + 1):
                try:
                    recipient = recipients.Item(i)
                    status = self._safe_getattr(
                        recipient, "MeetingResponseStatus", 0
                    )
                    if status == 1:  # olResponseOrganized
                        return self._resolve_recipient_email(recipient)
                except Exception:
                    continue
        except Exception:
            logger.debug("Could not determine organizer email.")

        return ""

    def _detect_online_meeting(self, appt, body, location):
        """
        Determine whether the appointment is an online (Teams) meeting.

        Checks:
        1. The COM property IsOnlineMeeting (may not exist in older Outlook).
        2. Whether the body or location contains a Teams URL.
        """
        # Try the native property first (Outlook 2016+ / M365)
        try:
            is_online = getattr(appt, "IsOnlineMeeting", None)
            if is_online is True:
                return True
        except Exception:
            pass

        # Fallback: look for Teams URLs in body or location text
        search_text = f"{body} {location}"
        if "teams.microsoft.com" in search_text.lower():
            return True

        return False

    @staticmethod
    def _extract_teams_url(body):
        """
        Extract the first Teams meeting URL from the appointment body text.
        Returns the URL string or an empty string if none found.
        """
        if not body:
            return ""

        match = TEAMS_URL_PATTERN.search(body)
        if match:
            return match.group(0)
        return ""

    @staticmethod
    def _com_datetime_to_iso(com_dt):
        """
        Convert a pywintypes.datetime (or regular datetime) returned by the
        Outlook COM object into an ISO 8601 formatted string with the
        correct local timezone.

        IMPORTANT: Outlook COM returns date/time values in the user's LOCAL
        timezone, not UTC.  However, pywintypes.datetime objects from pywin32
        are tagged with ``tzinfo=tzutc()``, which is INCORRECT -- the
        underlying values are still local time.  We must strip the bogus
        UTC tzinfo and replace it with the actual local timezone
        (America/Chicago / US Central) so that downstream consumers
        (Django ORM, the frontend, etc.) display the correct times.

        Returns an empty string if conversion fails.
        """
        if com_dt is None:
            return ""

        try:
            local_tz = ZoneInfo("America/Chicago")

            if hasattr(com_dt, "replace"):
                # Strip any existing tzinfo (pywintypes incorrectly sets
                # tzutc()) and re-interpret the naive datetime as local time.
                naive = com_dt.replace(tzinfo=None, microsecond=0)
                aware = naive.replace(tzinfo=local_tz)
                return aware.isoformat()

            # Fallback for unexpected types
            return str(com_dt)
        except Exception:
            logger.debug("Could not convert COM datetime: %s", com_dt)
            return ""

    @staticmethod
    def _clean_body_preview(body):
        """
        Extract meaningful agenda text from an appointment body,
        stripping Teams/Polycom meeting template boilerplate.

        Strategy: Meeting templates always appear AFTER any user-written
        agenda text. We find where the template starts and only keep
        what comes before it. If nothing meaningful remains, return empty.
        """
        if not body:
            return ""

        # Markers that indicate the start of meeting template boilerplate.
        # Everything from the first marker onward is discarded.
        template_markers = [
            'Microsoft Teams meeting',
            'Microsoft Teams',
            'teams.microsoft.com',
            'Join on your computer',
            'Join the meeting',
            '@t.plcm.vc',
            '________________',
            '----------------',
        ]

        clean = body
        # Find the earliest template marker and truncate there
        earliest_pos = len(clean)
        for marker in template_markers:
            pos = clean.find(marker)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos

        clean = clean[:earliest_pos]

        # Remove URLs and email addresses that might be in the agenda
        clean = re.sub(r'https?://\S+', '', clean)
        clean = re.sub(r'\S+@\S+\.\S+', '', clean)
        # Remove angle brackets
        clean = re.sub(r'<[^>]*>', '', clean)
        clean = re.sub(r'[<>]', '', clean)
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Must have meaningful text (enough alphabetic characters)
        alpha_chars = sum(1 for c in clean if c.isalpha())
        if len(clean) < 15 or alpha_chars < 10:
            return ""

        return clean[:200].strip()

    @staticmethod
    def _safe_getattr(obj, attr, default=None):
        """
        Safely get an attribute from a COM object, catching any COM
        errors that may arise from accessing unavailable properties.
        """
        try:
            return getattr(obj, attr, default)
        except Exception:
            return default

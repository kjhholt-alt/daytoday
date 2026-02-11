"""
Power Automate Calendar Service.

Reads calendar event JSON files exported by a Power Automate flow (via
OneDrive or direct HTTP POST) and returns them in the normalized dict
format expected by SummaryService._store_meetings().

This bypasses the Graph API authentication requirement entirely -- Power
Automate uses its own pre-approved Office 365 Outlook connector to fetch
calendar data and writes the results as a JSON file.
"""

import json
import logging
import os
import re as _re
import glob as _glob
from datetime import date, datetime

logger = logging.getLogger(__name__)


def _auto_detect_export_dir() -> str:
    """Try to find a DayToDay folder inside the user's OneDrive directory."""
    user_profile = os.environ.get("USERPROFILE", "")
    if not user_profile:
        return ""
    for onedrive in _glob.glob(os.path.join(user_profile, "OneDrive*")):
        candidate = os.path.join(onedrive, "DayToDay")
        if os.path.isdir(candidate):
            return candidate
    return ""


class PowerAutomateCalendarService:
    """
    Reads calendar events from JSON files produced by a Power Automate flow.

    The flow writes files to a known directory (typically OneDrive/DayToDay/).
    Files can be named:
      - ``calendar_events.json``   (current / most recent export)
      - ``calendar_YYYY-MM-DD.json`` (date-specific export)
    """

    def __init__(self, export_path: str = ""):
        self._export_path = export_path or _auto_detect_export_dir()

    @property
    def export_path(self) -> str:
        return self._export_path

    @property
    def available(self) -> bool:
        """True if the export directory exists."""
        return bool(self._export_path) and os.path.isdir(self._export_path)

    def get_events_for_date(self, target_date: date) -> list[dict]:
        """Read and return calendar events for *target_date*.

        Returns an empty list if no suitable file is found or the file is
        stale (not from today).
        """
        if not self.available:
            logger.debug("PA calendar: export path not available (%s)", self._export_path)
            return []

        raw_events = self._load_events_file(target_date)
        if not raw_events:
            return []

        return [self._normalize_event(e) for e in raw_events]

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _load_events_file(self, target_date: date) -> list[dict]:
        """Find and load the best matching JSON file for *target_date*."""
        date_str = target_date.isoformat()  # YYYY-MM-DD

        # 1. Try date-specific file first
        date_file = os.path.join(self._export_path, f"calendar_{date_str}.json")
        events = self._read_json_file(date_file)
        if events is not None:
            logger.info("PA calendar: loaded date-specific file %s", date_file)
            return events

        # 2. Fall back to generic file, but only if it's fresh
        generic_file = os.path.join(self._export_path, "calendar_events.json")
        if os.path.isfile(generic_file):
            mod_time = datetime.fromtimestamp(os.path.getmtime(generic_file))
            if mod_time.date() == target_date:
                events = self._read_json_file(generic_file)
                if events is not None:
                    logger.info("PA calendar: loaded generic file %s (modified today)", generic_file)
                    return events
            else:
                logger.debug(
                    "PA calendar: generic file is stale (modified %s, target %s)",
                    mod_time.date(), target_date,
                )

        return []

    @staticmethod
    def _read_json_file(path: str) -> list[dict] | None:
        """Read a JSON file and return a list of event dicts, or None on failure."""
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Accept either a bare list or {"events": [...]}
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "events" in data:
                return data["events"]
            if isinstance(data, dict) and "value" in data:
                # Power Automate sometimes wraps in {"value": [...]}
                return data["value"]
            logger.warning("PA calendar: unexpected JSON structure in %s", path)
            return None
        except (json.JSONDecodeError, OSError) as e:
            logger.error("PA calendar: failed to read %s: %s", path, e)
            return None

    # ------------------------------------------------------------------
    # Event normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_event(event: dict) -> dict:
        """Convert a Power Automate event dict to the normalized format.

        Power Automate's "Get calendar view" action returns events in the
        same structure as Graph API, so we handle both Graph-style and
        simplified key names.
        """
        # Handle Graph-style nested start/end objects
        start_raw = event.get("start_time") or event.get("start", "")
        end_raw = event.get("end_time") or event.get("end", "")

        if isinstance(start_raw, dict):
            start_time = start_raw.get("dateTime", "")
            timezone = start_raw.get("timeZone", "UTC")
        else:
            start_time = str(start_raw)
            timezone = event.get("timezone", "UTC")

        if isinstance(end_raw, dict):
            end_time = end_raw.get("dateTime", "")
        else:
            end_time = str(end_raw)

        # Handle Graph-style nested organizer
        organizer_raw = event.get("organizer", {})
        if isinstance(organizer_raw, dict) and "emailAddress" in organizer_raw:
            organizer_name = organizer_raw["emailAddress"].get("name", "")
            organizer_email = organizer_raw["emailAddress"].get("address", "")
        else:
            organizer_name = event.get("organizer_name", str(organizer_raw) if organizer_raw else "")
            organizer_email = event.get("organizer_email", "")

        # Handle attendees -- could be Graph-style or simplified
        attendees_raw = event.get("attendees", [])
        attendees = []
        for att in attendees_raw:
            if isinstance(att, dict):
                if "emailAddress" in att:
                    # Graph API format
                    attendees.append({
                        "name": att["emailAddress"].get("name", ""),
                        "email": att["emailAddress"].get("address", ""),
                        "response": att.get("status", {}).get("response", "none"),
                    })
                else:
                    # Simplified format
                    attendees.append({
                        "name": att.get("name", ""),
                        "email": att.get("email", ""),
                        "response": att.get("response", "none"),
                    })
            elif isinstance(att, str):
                attendees.append({"name": att, "email": att, "response": "none"})

        # Handle location
        location_raw = event.get("location", "")
        if isinstance(location_raw, dict):
            location = location_raw.get("displayName", "")
        else:
            location = str(location_raw)

        # Extract the full meeting body (agenda/description) when available.
        # PA / Graph returns body as {"contentType": "html", "content": "..."}
        # We prefer the full body over the truncated bodyPreview.
        body_raw = event.get("body", {})
        if isinstance(body_raw, dict) and body_raw.get("content"):
            # Strip HTML tags to get plain text
            body_text = _re.sub(r'<[^>]+>', ' ', body_raw["content"])
            body_text = _re.sub(r'\s+', ' ', body_text).strip()
        else:
            body_text = ""

        body_preview = (
            body_text
            or event.get("body_preview")
            or event.get("bodyPreview", "")
        )

        return {
            "graph_id": event.get("graph_id") or event.get("id", "pa-import"),
            "subject": event.get("subject", "Untitled"),
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone,
            "organizer_name": organizer_name,
            "organizer_email": organizer_email,
            "attendees": attendees,
            "body_preview": body_preview,
            "location": location,
            "is_online_meeting": event.get("is_online_meeting", False)
                or event.get("isOnlineMeeting", False),
            "online_meeting_url": event.get("online_meeting_url")
                or event.get("onlineMeetingUrl", ""),
            "web_link": event.get("web_link") or event.get("webLink", ""),
        }

    # ------------------------------------------------------------------
    # Write support (for the HTTP push endpoint)
    # ------------------------------------------------------------------

    def write_events(self, events: list[dict], target_date: date | None = None) -> str:
        """Write events to the export directory.

        Returns the path of the written file.
        """
        if not self._export_path:
            raise ValueError("No export path configured for Power Automate calendar")

        os.makedirs(self._export_path, exist_ok=True)

        if target_date:
            filename = f"calendar_{target_date.isoformat()}.json"
        else:
            filename = "calendar_events.json"

        filepath = os.path.join(self._export_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, default=str)

        logger.info("PA calendar: wrote %d event(s) to %s", len(events), filepath)
        return filepath

    def list_available_dates(self) -> list[date]:
        """Return all dates that have a ``calendar_YYYY-MM-DD.json`` file."""
        if not self.available:
            return []
        dates = []
        for filepath in _glob.glob(os.path.join(self._export_path, "calendar_*.json")):
            filename = os.path.basename(filepath)
            if filename == "calendar_events.json":
                continue
            # Expect calendar_YYYY-MM-DD.json
            date_part = filename[len("calendar_"):-len(".json")]
            try:
                dates.append(date.fromisoformat(date_part))
            except ValueError:
                continue
        dates.sort()
        return dates

    def get_status(self) -> dict:
        """Return status info for the Settings UI."""
        if not self.available:
            return {
                "available": False,
                "export_path": self._export_path,
                "file_found": False,
            }

        # Check for any calendar files
        generic = os.path.join(self._export_path, "calendar_events.json")
        today_file = os.path.join(
            self._export_path, f"calendar_{date.today().isoformat()}.json"
        )

        file_found = False
        file_path = ""
        file_age = ""
        event_count = 0

        for candidate in (today_file, generic):
            if os.path.isfile(candidate):
                file_found = True
                file_path = candidate
                mod_time = datetime.fromtimestamp(os.path.getmtime(candidate))
                file_age = mod_time.isoformat()
                events = self._read_json_file(candidate)
                event_count = len(events) if events else 0
                break

        return {
            "available": True,
            "export_path": self._export_path,
            "file_found": file_found,
            "file_path": file_path,
            "file_modified": file_age,
            "event_count": event_count,
        }

"""
OneNote Local Service - reads OneNote pages via win32com COM automation,
with a file-based fallback for the Windows Store / UWP version of OneNote.

Strategy
--------
1. **COM automation** (primary) -- works with OneNote Desktop 2013+.
   Uses the ``OneNote.Application`` COM ProgID to query the full
   Notebook -> Section -> Page hierarchy.

2. **File-system scan** (fallback) -- works with *any* edition of
   OneNote (UWP / Windows Store, Desktop, or notebooks synced via
   OneDrive).  Scans configurable directories for ``.one`` section
   files and ``.onetoc2`` table-of-contents files whose *modified
   time* is on or after the target date, then synthesises page-like
   dicts from the file metadata.

The public API (``list_recent_pages`` / ``get_page_content``) tries
COM first.  If that fails (e.g. UWP OneNote is installed instead of
the desktop edition) it falls back to the file scan automatically.

Requirements
------------
- pywin32 (`pip install pywin32`)  -- only for the COM path
- python-dateutil (`pip install python-dateutil`)
"""

import logging
import os
import re as _re
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Pattern to strip OneNote backup date suffixes like " (On 2-4-2026)"
_BACKUP_DATE_PATTERN = _re.compile(r"\s*\(On \d{1,2}-\d{1,2}-\d{4}\)$")

# Font names and metadata tokens to filter out of binary text extraction
_FONT_NAMES = frozenset({
    'Calibri', 'Calibri Light', 'Arial', 'Times New Roman', 'Segoe UI',
    'Consolas', 'Courier New', 'Verdana', 'Tahoma', 'Wingdings',
    'Microsoft Sans Serif', 'Symbol', 'Cambria', 'Georgia', 'Impact',
    'Lucida Console', 'Trebuchet MS', 'Comic Sans MS', 'Palatino Linotype',
})

# Pattern to match UTF-16LE printable strings (min 4 chars)
_UTF16LE_PATTERN = _re.compile(b'(?:[\x20-\x7e]\x00){4,}')

logger = logging.getLogger(__name__)

# OneNote HierarchyScope enum value used by GetHierarchy
HS_PAGES = 2

# Known OneNote XML namespaces (newest first)
_ONENOTE_NAMESPACES = [
    "http://schemas.microsoft.com/office/onenote/2013/onenote",
    "http://schemas.microsoft.com/office/onenote/2010/onenote",
]

# File extensions that represent OneNote content on disk
_ONENOTE_EXTENSIONS = {".one", ".onetoc2"}


class OneNoteLocalService:
    """Reads OneNote notebooks, sections, and pages through local COM
    automation with an automatic file-system fallback."""

    def __init__(self, onenote_paths: Optional[List[str]] = None):
        """
        Parameters
        ----------
        onenote_paths:
            Optional list of directory paths to scan when the file-based
            fallback is used.  When *None* (the default) the paths are
            read from ``ConfigService.onenote_paths`` at scan time.
        """
        self._app = None
        self._namespace = None
        self._com_available: Optional[bool] = None  # tri-state: None = unknown
        self._onenote_paths = onenote_paths

    # ------------------------------------------------------------------
    # COM bootstrap
    # ------------------------------------------------------------------

    def _get_app(self):
        """
        Lazily connect to the OneNote COM server.

        Tries OneNote.Application.15 (Office 2013+) first, then falls
        back to the version-independent ProgID.

        Raises ``RuntimeError`` if COM is not available at all.
        """
        if self._app is not None:
            return self._app

        try:
            import win32com.client.gencache as gencache
        except ImportError:
            logger.warning(
                "pywin32 is not installed -- COM automation unavailable. "
                "Will use file-based fallback."
            )
            raise RuntimeError("pywin32 is not installed")

        prog_ids = ["OneNote.Application.15", "OneNote.Application"]
        result = {"app": None, "error": None}

        def _try_connect():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                for prog_id in prog_ids:
                    try:
                        logger.info("Attempting to connect to OneNote via %s", prog_id)
                        app = gencache.EnsureDispatch(prog_id)
                        result["app"] = app
                        return
                    except Exception as exc:
                        logger.debug("Could not connect via %s: %s", prog_id, exc)
                        result["error"] = exc
                # Also try plain Dispatch as fallback
                try:
                    import win32com.client
                    app = win32com.client.Dispatch("OneNote.Application")
                    result["app"] = app
                except Exception as exc:
                    result["error"] = exc
            finally:
                # Release COM if we failed to connect
                if result["app"] is None:
                    try:
                        pythoncom.CoUninitialize()
                    except Exception:
                        pass

        t = threading.Thread(target=_try_connect, daemon=True)
        t.start()
        t.join(timeout=10)

        if t.is_alive():
            self._com_available = False
            logger.error("OneNote COM connection timed out (10s).")
            raise RuntimeError("OneNote COM timed out")

        if result["app"] is not None:
            self._app = result["app"]
            self._com_available = True
            logger.info("Connected to OneNote COM.")
            return self._app

        self._com_available = False
        logger.warning(
            "Failed to connect to OneNote COM. "
            "Is OneNote desktop (not UWP/Store) installed? "
            "Falling back to file-based notebook scanning."
        )
        raise RuntimeError(
            f"Unable to connect to OneNote COM object: {result['error']}"
        )

    # ------------------------------------------------------------------
    # XML helpers
    # ------------------------------------------------------------------

    def _detect_namespace(self, root: ET.Element) -> str:
        """
        Detect the XML namespace from the root element's tag.

        Falls back to the 2013 namespace if detection fails.
        """
        if self._namespace:
            return self._namespace

        tag = root.tag
        if tag.startswith("{"):
            ns = tag[1 : tag.index("}")]
            self._namespace = ns
            logger.debug("Detected OneNote XML namespace: %s", ns)
            return ns

        # Fallback
        self._namespace = _ONENOTE_NAMESPACES[0]
        logger.debug(
            "Could not detect namespace from tag '%s'; using default: %s",
            tag,
            self._namespace,
        )
        return self._namespace

    def _ns(self, tag: str) -> str:
        """Return a namespace-qualified tag string like ``{ns}tag``."""
        ns = self._namespace or _ONENOTE_NAMESPACES[0]
        return f"{{{ns}}}{tag}"

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """
        Parse an ISO-8601 datetime string from OneNote XML.

        Returns *None* if the value is empty or unparseable.
        """
        if not value:
            return None
        try:
            from dateutil.parser import parse as dateutil_parse
            return dateutil_parse(value)
        except Exception:
            pass
        # Fallback: try stdlib fromisoformat (handles most ISO strings in 3.11+)
        try:
            return datetime.fromisoformat(value)
        except Exception:
            logger.warning("Unable to parse datetime value: %s", value)
            return None

    def _format_datetime(self, value: Optional[str]) -> Optional[str]:
        """
        Return an ISO-formatted datetime string suitable for consumers.

        Parses then re-serialises so the output format is predictable.
        """
        dt = self._parse_datetime(value)
        if dt is None:
            return None
        return dt.isoformat()

    # ------------------------------------------------------------------
    # Hierarchy retrieval (COM path)
    # ------------------------------------------------------------------

    def _get_hierarchy_xml(self) -> ET.Element:
        """
        Fetch the full Notebook -> Section -> Page hierarchy from OneNote
        and return the parsed XML root element.
        """
        app = self._get_app()
        try:
            xml_str = app.GetHierarchy("", HS_PAGES)
        except Exception as exc:
            logger.error("GetHierarchy failed: %s", exc)
            raise RuntimeError(f"OneNote GetHierarchy call failed: {exc}")

        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as exc:
            logger.error("Failed to parse OneNote hierarchy XML: %s", exc)
            raise RuntimeError(f"Could not parse hierarchy XML: {exc}")

        self._detect_namespace(root)
        return root

    # ------------------------------------------------------------------
    # File-based fallback helpers
    # ------------------------------------------------------------------

    def _get_scan_directories(self) -> List[str]:
        """
        Return the list of directories to walk when scanning for OneNote
        files on disk.  Prefers explicitly-provided paths; otherwise
        reads from ConfigService.
        """
        if self._onenote_paths is not None:
            return list(self._onenote_paths)

        try:
            from .config_service import ConfigService
            cfg = ConfigService.get_instance()
            return cfg.onenote_paths
        except Exception as exc:
            logger.warning(
                "Could not read onenote_paths from config (%s). "
                "Using empty list.",
                exc,
            )
            return []

    def _scan_onenote_files(
        self, modified_since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Walk the configured directories looking for ``.one`` and
        ``.onetoc2`` files.  For each file whose *mtime* is on or after
        *modified_since*, emit a page-like dict compatible with the
        shape expected by ``SummaryService._collect_notes``.

        ``.onetoc2`` files are table-of-contents markers that sit at the
        notebook root.  ``.one`` files are individual section files.  We
        treat each ``.one`` file as a "page" reference (since we cannot
        read their internal page list without COM).
        """
        dirs = self._get_scan_directories()
        if not dirs:
            logger.warning(
                "No onenote_paths configured and none auto-detected. "
                "File-based OneNote fallback will return no results. "
                "Set 'onenote_paths' in config.json to point to your "
                "OneNote notebook folders."
            )
            return []

        logger.info(
            "File-based OneNote scan: searching %d director%s for .one/.onetoc2 files",
            len(dirs),
            "y" if len(dirs) == 1 else "ies",
        )

        # Convert modified_since to a naive timestamp for mtime comparison
        since_ts: Optional[float] = None
        if modified_since is not None:
            cmp = modified_since
            if cmp.tzinfo is not None:
                cmp = cmp.replace(tzinfo=None)
            since_ts = cmp.timestamp()

        pages: List[Dict] = []
        seen_paths: set = set()

        for base_dir in dirs:
            if not os.path.isdir(base_dir):
                logger.debug(
                    "Skipping non-existent onenote_path: %s", base_dir
                )
                continue

            for dirpath, _dirnames, filenames in os.walk(base_dir):
                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in _ONENOTE_EXTENSIONS:
                        continue

                    full_path = os.path.join(dirpath, fname)

                    # Skip recycle bin / deleted pages
                    if "RecycleBin" in dirpath or "DeletedPages" in fname:
                        continue

                    # Deduplicate (directories may overlap)
                    real = os.path.normcase(os.path.realpath(full_path))
                    if real in seen_paths:
                        continue
                    seen_paths.add(real)

                    try:
                        stat = os.stat(full_path)
                    except OSError as exc:
                        logger.debug(
                            "Could not stat %s: %s", full_path, exc
                        )
                        continue

                    # Filter by modification time
                    if since_ts is not None and stat.st_mtime < since_ts:
                        continue

                    mtime_dt = datetime.fromtimestamp(stat.st_mtime)

                    # Derive human-readable names from path structure.
                    # Typical layout:
                    #   .../NotebookName/SectionName.one
                    #   .../NotebookName/SectionGroup/SectionName.one
                    # Backup files have date suffixes: "MEETING NOTES (On 2-4-2026).one"
                    parent_dir = Path(dirpath)
                    section_name = Path(fname).stem  # e.g. "Meeting Notes"
                    # Strip backup date suffix if present
                    section_name = _BACKUP_DATE_PATTERN.sub("", section_name)
                    notebook_name = parent_dir.name   # immediate parent dir
                    # Also strip from notebook name
                    notebook_name = _BACKUP_DATE_PATTERN.sub("", notebook_name)

                    # For .onetoc2, the "section" is really the notebook TOC
                    if ext == ".onetoc2":
                        section_name = "(Table of Contents)"

                    pages.append(
                        {
                            "id": f"file://{full_path}",
                            "title": section_name,
                            "lastModifiedDateTime": mtime_dt.isoformat(),
                            "parentSection": {
                                "displayName": notebook_name,
                                "id": f"file://{dirpath}",
                            },
                            "notebookName": notebook_name,
                            "notebookId": f"file://{dirpath}",
                            "dateTime": mtime_dt.isoformat(),
                            "_source": "file_scan",
                            "_filePath": full_path,
                        }
                    )

        logger.info(
            "File-based scan found %d OneNote file(s) matching the filter "
            "(modified_since=%s)",
            len(pages),
            modified_since,
        )
        return pages

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_recent_pages(
        self, modified_since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Return a list of OneNote page dicts, optionally filtered to those
        modified on or after *modified_since*.

        Tries COM automation first.  If COM is unavailable (e.g. the
        user has UWP/Store OneNote instead of Office Desktop OneNote)
        it falls back to scanning the file system for ``.one`` files.

        Each dict has the shape expected by ``SummaryService._collect_notes``:

        .. code-block:: python

            {
                'id': '<page COM ID or file:// URI>',
                'title': 'Page Title',
                'lastModifiedDateTime': '2026-02-10T14:30:00',
                'parentSection': {
                    'displayName': 'Section Name',
                },
                'notebookName': 'Notebook Name',
            }
        """
        logger.info(
            "Listing recent OneNote pages (modified_since=%s)", modified_since
        )

        # -- Attempt 1: COM automation (Office Desktop OneNote) -----------
        if self._com_available is not False:
            try:
                pages = self._list_recent_pages_com(modified_since)
                logger.info(
                    "COM path returned %d page(s).", len(pages)
                )
                return pages
            except RuntimeError as exc:
                logger.warning(
                    "COM-based OneNote access failed (%s). "
                    "Falling back to file-based scanning.",
                    exc,
                )
                self._com_available = False

        # -- Attempt 2: file-system scan (UWP / OneDrive notebooks) -------
        return self._scan_onenote_files(modified_since)

    def get_page_content(self, page_id: str) -> str:
        """
        Retrieve the content of a single OneNote page as a plain-text
        string (HTML tags stripped).

        Parameters
        ----------
        page_id:
            The COM ID of the page (as returned by ``list_recent_pages``),
            or a ``file://`` URI for file-scan results.

        Returns
        -------
        str
            The concatenated text content of the page.  Returns an empty
            string if the page cannot be read.

        Notes
        -----
        For pages returned by the file-based fallback (``file://`` IDs)
        we cannot extract text content from the binary ``.one`` format,
        so an explanatory placeholder string is returned instead.
        """
        if not page_id:
            logger.warning("get_page_content called with empty page_id")
            return ""

        # File-scan pages -- extract text from .one binary
        if page_id.startswith("file://"):
            file_path = page_id[len("file://"):]
            return self._extract_text_from_one_file(file_path)

        # COM path
        logger.info("Fetching content for page ID: %s", page_id)
        try:
            app = self._get_app()
        except RuntimeError:
            return ""

        try:
            # piPageObjectsOut parameter: 0 = piBasic, 1 = piBinaryData, ...
            xml_str = app.GetPageContent(page_id, 0)
        except Exception as exc:
            logger.error(
                "GetPageContent failed for page %s: %s", page_id, exc
            )
            return ""

        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as exc:
            logger.error(
                "Failed to parse page content XML for %s: %s", page_id, exc
            )
            return ""

        self._detect_namespace(root)
        return self._extract_text_from_page(root)

    def get_page_hyperlink(self, page_id: str) -> str:
        """Return a ``onenote:`` protocol URL that opens the page in OneNote.

        Uses the COM ``GetHyperlinkToObject`` method.  Returns an empty
        string if the link cannot be generated (file-scan pages, COM
        unavailable, etc.).
        """
        if not page_id or page_id.startswith("file://"):
            return ""

        try:
            app = self._get_app()
        except RuntimeError:
            return ""

        try:
            link = app.GetHyperlinkToObject(page_id, "")
            return link or ""
        except Exception as exc:
            logger.debug("GetHyperlinkToObject failed for %s: %s", page_id, exc)
            return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _list_recent_pages_com(
        self, modified_since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        The original COM-based implementation of ``list_recent_pages``.

        Raises ``RuntimeError`` if COM is not usable.
        """
        root = self._get_hierarchy_xml()

        pages: List[Dict] = []

        for notebook in root.findall(self._ns("Notebook")):
            notebook_name = notebook.get("name", "Unknown Notebook")
            notebook_id = notebook.get("ID", "")

            # Sections may be nested inside SectionGroups as well
            for section in self._iter_sections(notebook):
                section_name = section.get("name", "Unknown Section")
                section_id = section.get("ID", "")

                for page in section.findall(self._ns("Page")):
                    page_id = page.get("ID", "")
                    page_title = page.get("name", "Untitled")
                    last_modified_raw = page.get("lastModifiedTime")
                    page_datetime_raw = page.get("dateTime")

                    last_modified_dt = self._parse_datetime(last_modified_raw)

                    # Apply the modified_since filter
                    if modified_since is not None and last_modified_dt is not None:
                        # Ensure both are naive or both are aware for comparison
                        cmp_modified = last_modified_dt
                        cmp_since = modified_since
                        if (
                            cmp_modified.tzinfo is not None
                            and cmp_since.tzinfo is None
                        ):
                            cmp_modified = cmp_modified.replace(tzinfo=None)
                        elif (
                            cmp_modified.tzinfo is None
                            and cmp_since.tzinfo is not None
                        ):
                            cmp_since = cmp_since.replace(tzinfo=None)

                        if cmp_modified < cmp_since:
                            continue

                    # If we couldn't parse the date and a filter is active,
                    # skip the page to avoid returning stale data.
                    if modified_since is not None and last_modified_dt is None:
                        logger.debug(
                            "Skipping page '%s' -- could not parse "
                            "lastModifiedTime '%s'",
                            page_title,
                            last_modified_raw,
                        )
                        continue

                    pages.append(
                        {
                            "id": page_id,
                            "title": page_title,
                            "lastModifiedDateTime": self._format_datetime(
                                last_modified_raw
                            ),
                            "parentSection": {
                                "displayName": section_name,
                                "id": section_id,
                            },
                            "notebookName": notebook_name,
                            "notebookId": notebook_id,
                            "dateTime": self._format_datetime(
                                page_datetime_raw
                            ),
                            "_source": "com",
                        }
                    )

        return pages

    def _iter_sections(self, parent: ET.Element):
        """
        Yield all ``<Section>`` elements under *parent*, recursing into
        any ``<SectionGroup>`` elements.
        """
        for child in parent:
            local_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local_tag == "Section":
                yield child
            elif local_tag == "SectionGroup":
                yield from self._iter_sections(child)

    @staticmethod
    def _extract_text_from_one_file(file_path: str) -> str:
        """Extract readable text from a binary ``.one`` section file.

        OneNote ``.one`` files store text as UTF-16LE strings interleaved
        with binary formatting data.  We scan the raw bytes for printable
        UTF-16LE runs and filter out font names, GUIDs, and other metadata
        to return meaningful note content.
        """
        if not os.path.isfile(file_path):
            return ""

        try:
            with open(file_path, 'rb') as f:
                data = f.read(5 * 1024 * 1024)  # cap at 5 MB
        except Exception as exc:
            logger.debug("Could not read .one file %s: %s", file_path, exc)
            return ""

        # Find all UTF-16LE printable string runs (min 4 chars)
        raw_parts = _UTF16LE_PATTERN.findall(data)
        decoded = [p.decode('utf-16-le', errors='ignore').strip()
                   for p in raw_parts]

        # Filter out noise
        seen: set = set()
        filtered: List[str] = []
        for text in decoded:
            if not text or len(text) < 3:
                continue
            if text in _FONT_NAMES:
                continue
            if text in seen:
                continue
            # Skip GUIDs
            if text.startswith('{') and text.endswith('}') and len(text) > 30:
                continue
            # Skip pure numbers
            if _re.match(r'^[\d.,]+$', text):
                continue
            # Skip XML/metadata fragments
            if text.startswith('<') and ('provider=' in text or 'localId' in text):
                continue
            # Skip known OneNote internal tokens
            if text in ('PageTitle', 'PageDateTime', 'Untitled picture.png',
                        'NotebookManagementEntityGuid'):
                continue
            seen.add(text)
            filtered.append(text)

        content = '\n'.join(filtered)
        logger.debug(
            "Extracted %d chars from .one binary: %s",
            len(content), os.path.basename(file_path),
        )
        return content

    def _extract_text_from_page(self, root: ET.Element) -> str:
        """
        Walk the page XML and concatenate all text content.

        OneNote page XML has a structure like::

            <Page ...>
              <Outline>
                <OEChildren>
                  <OE>
                    <T><![CDATA[some text]]></T>
                  </OE>
                </OEChildren>
              </Outline>
            </Page>

        We collect the text from every ``<T>`` element.
        """
        ns = self._namespace or _ONENOTE_NAMESPACES[0]
        text_parts: List[str] = []

        # Use a broad recursive search for all <T> elements
        for t_elem in root.iter(f"{{{ns}}}T"):
            if t_elem.text:
                text_parts.append(t_elem.text.strip())

        content = "\n".join(text_parts)
        logger.debug(
            "Extracted %d character(s) of text from page", len(content)
        )
        return content

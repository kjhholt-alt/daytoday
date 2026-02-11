import logging
import re
from datetime import datetime, date
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a'}
VIDEO_EXTENSIONS = {'.mp4', '.webm'}
TRANSCRIPT_EXTENSIONS = {'.vtt', '.srt', '.txt', '.docx'}

ALL_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | TRANSCRIPT_EXTENSIONS


def _classify_file_type(extension: str) -> str:
    ext = extension.lower()
    if ext in AUDIO_EXTENSIONS:
        return 'audio'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    if ext in TRANSCRIPT_EXTENSIONS:
        return 'transcript'
    return 'unknown'


class RecordingService:
    def __init__(self, directories: list):
        self._directories = [Path(d) for d in directories]

    def find_recordings(self, modified_since=None):
        """Scan configured directories for recording/transcript files.

        Args:
            modified_since: Optional date or datetime. Only return files
                modified on or after this date.

        Returns:
            List of dicts with file_name, file_path, modified_at,
            size_bytes, file_type.
        """
        recordings = []
        for directory in self._directories:
            if not directory.exists():
                logger.warning(f"Recordings directory not found: {directory}")
                continue
            if not directory.is_dir():
                logger.warning(f"Path is not a directory: {directory}")
                continue

            for file_path in directory.rglob('*'):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in ALL_EXTENSIONS:
                    continue
                if file_path.name.startswith('~$'):
                    continue

                try:
                    stat = file_path.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    size_bytes = stat.st_size
                except OSError as e:
                    logger.warning(f"Cannot stat {file_path}: {e}")
                    continue

                if modified_since:
                    compare_date = modified_since
                    if isinstance(compare_date, datetime):
                        compare_date = compare_date.date()
                    if isinstance(compare_date, date) and mod_time.date() < compare_date:
                        continue

                recordings.append({
                    'file_name': file_path.name,
                    'file_path': str(file_path),
                    'modified_at': mod_time.isoformat(),
                    'size_bytes': size_bytes,
                    'file_type': _classify_file_type(file_path.suffix),
                })

        logger.info(f"Found {len(recordings)} recording/transcript file(s).")
        return recordings

    def extract_transcript_text(self, file_path: str) -> str:
        """Extract plain text from a transcript file.

        Supports .vtt, .srt, .txt, and .docx files.

        Args:
            file_path: Absolute path to the transcript file.

        Returns:
            Plain text content of the transcript.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == '.vtt':
            return self._parse_vtt(path)
        elif ext == '.srt':
            return self._parse_srt(path)
        elif ext == '.txt':
            return self._read_text_file(path)
        elif ext == '.docx':
            return self._read_docx(path)
        else:
            logger.warning(
                f"Unsupported transcript format '{ext}' for {file_path}"
            )
            return ''

    def _parse_vtt(self, path: Path) -> str:
        """Parse a WebVTT file and return plain text lines."""
        try:
            raw = path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            logger.error(f"Cannot read VTT file {path}: {e}")
            return ''

        lines = raw.splitlines()
        text_lines = []
        # Skip the WEBVTT header and any blank lines / cue identifiers
        timestamp_re = re.compile(
            r'^\d{2}:\d{2}[:\.]'  # matches HH:MM: or HH:MM.
        )
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.upper().startswith('WEBVTT'):
                continue
            if stripped.upper().startswith('NOTE'):
                continue
            if timestamp_re.match(stripped):
                continue
            # Strip VTT formatting tags like <v Speaker>
            cleaned = re.sub(r'<[^>]+>', '', stripped)
            if cleaned:
                text_lines.append(cleaned)

        return '\n'.join(text_lines)

    def _parse_srt(self, path: Path) -> str:
        """Parse an SRT subtitle file and return plain text lines."""
        try:
            raw = path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            logger.error(f"Cannot read SRT file {path}: {e}")
            return ''

        lines = raw.splitlines()
        text_lines = []
        timestamp_re = re.compile(
            r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->'
        )
        sequence_re = re.compile(r'^\d+$')

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if sequence_re.match(stripped):
                continue
            if timestamp_re.match(stripped):
                continue
            # Strip SRT formatting tags
            cleaned = re.sub(r'<[^>]+>', '', stripped)
            if cleaned:
                text_lines.append(cleaned)

        return '\n'.join(text_lines)

    def _read_text_file(self, path: Path) -> str:
        """Read a plain text file."""
        try:
            return path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            logger.error(f"Cannot read text file {path}: {e}")
            return ''

    def _read_docx(self, path: Path) -> str:
        """Read text content from a .docx file."""
        try:
            doc = Document(str(path))
        except PackageNotFoundError:
            logger.error(f"Cannot open docx file: {path}")
            return ''
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            return ''

        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        return '\n'.join(paragraphs)

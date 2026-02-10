import logging
from datetime import datetime, date
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

logger = logging.getLogger(__name__)


class WordService:
    def __init__(self, directories: list):
        self._directories = [Path(d) for d in directories]

    def find_documents(self, modified_since=None):
        documents = []
        for directory in self._directories:
            if not directory.exists():
                logger.warning(f"Word doc directory not found: {directory}")
                continue
            if not directory.is_dir():
                logger.warning(f"Path is not a directory: {directory}")
                continue

            for docx_path in directory.rglob('*.docx'):
                if docx_path.name.startswith('~$'):
                    continue
                try:
                    mod_time = datetime.fromtimestamp(
                        docx_path.stat().st_mtime
                    )
                except OSError as e:
                    logger.warning(f"Cannot stat {docx_path}: {e}")
                    continue

                if modified_since:
                    compare_date = modified_since
                    if isinstance(compare_date, datetime):
                        compare_date = compare_date.date()
                    if mod_time.date() < compare_date:
                        continue

                documents.append({
                    'file_path': str(docx_path),
                    'file_name': docx_path.name,
                    'modified_at': mod_time.isoformat(),
                    'size_bytes': docx_path.stat().st_size,
                })

        logger.info(f"Found {len(documents)} Word document(s).")
        return documents

    def extract_text(self, file_path: str) -> dict:
        try:
            doc = Document(file_path)
        except PackageNotFoundError:
            logger.error(f"Cannot open docx file: {file_path}")
            return {'error': f'Cannot open: {file_path}', 'content': []}
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {'error': str(e), 'content': []}

        content_blocks = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                content_blocks.append({
                    'type': 'paragraph',
                    'text': text,
                })

        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(cells)
            if rows:
                content_blocks.append({
                    'type': 'table',
                    'rows': rows,
                })

        return {
            'file_name': Path(file_path).name,
            'file_path': file_path,
            'content': content_blocks,
        }

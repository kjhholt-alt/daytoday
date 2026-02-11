import json
import os
import glob as _glob
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# In frozen (PyInstaller) mode, use the writable user data directory for
# config so it persists between runs.  The template still lives inside the
# bundle.
_DATA_DIR = os.environ.get('DAYTODAY_DATA_DIR', '')
if _DATA_DIR:
    CONFIG_DIR = Path(_DATA_DIR) / 'config'
else:
    CONFIG_DIR = PROJECT_ROOT / 'config'
CONFIG_FILE = CONFIG_DIR / 'config.json'
TEMPLATE_FILE = PROJECT_ROOT / 'config' / 'config.template.json'

def _default_onenote_paths() -> list:
    """
    Build a list of default directories where OneNote notebooks are commonly
    stored.  The list is computed at call time so environment variables are
    resolved on the current Windows machine.
    """
    paths: list[str] = []

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        # 1. OneNote Desktop cache & backup (Office 365 / OneNote 2016+)
        #    This is where cloud-synced notebooks are cached locally.
        for subdir in ("Backup", "cache"):
            onenote_path = os.path.join(
                local_app, "Microsoft", "OneNote", "16.0", subdir,
            )
            if os.path.isdir(onenote_path):
                paths.append(onenote_path)

        # 2. OneNote UWP (Windows Store) local state
        uwp_path = os.path.join(
            local_app,
            "Packages",
            "Microsoft.Office.OneNote_8wekyb3d8bbwe",
            "LocalState",
        )
        if os.path.isdir(uwp_path):
            paths.append(uwp_path)

    # 3. OneDrive directories (may contain synced notebooks)
    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        for entry in _glob.glob(os.path.join(user_profile, "OneDrive*")):
            if os.path.isdir(entry):
                paths.append(entry)

    return paths


DEFAULT_CONFIG = {
    'word_doc_directories': [],
    'recordings_directories': [],
    'onenote_enabled': True,
    'onenote_paths': [],          # empty list means "use auto-detected defaults"
    'onenote_notebooks': [],      # empty list means "include all notebooks"
    'outlook_enabled': True,
    'graph_client_id': '',        # Azure AD app (public client) ID for MS Graph
}


class ConfigError(Exception):
    pass


class ConfigService:
    _instance = None
    _config = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        if not CONFIG_FILE.exists():
            if TEMPLATE_FILE.exists():
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy(TEMPLATE_FILE, CONFIG_FILE)
                logger.info(
                    "Config created from template at %s. "
                    "Please edit it with your Word doc directories.",
                    CONFIG_FILE,
                )
            else:
                logger.info(
                    "No config file found at %s. Using default configuration.",
                    CONFIG_FILE,
                )
            self._config = dict(DEFAULT_CONFIG)
            return

        try:
            with open(CONFIG_FILE, 'r') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}")

        # Merge defaults for any keys not present in the file
        for key, value in DEFAULT_CONFIG.items():
            self._config.setdefault(key, value)

        self._validate()
        logger.info("Configuration loaded successfully.")

    def _validate(self):
        dirs = self._config.get('word_doc_directories')
        if dirs is not None and not isinstance(dirs, list):
            raise ConfigError(
                "Config key 'word_doc_directories' must be a list."
            )

        rec_dirs = self._config.get('recordings_directories')
        if rec_dirs is not None and not isinstance(rec_dirs, list):
            raise ConfigError(
                "Config key 'recordings_directories' must be a list."
            )

        on_paths = self._config.get('onenote_paths')
        if on_paths is not None and not isinstance(on_paths, list):
            raise ConfigError(
                "Config key 'onenote_paths' must be a list of directory paths."
            )

        on_notebooks = self._config.get('onenote_notebooks')
        if on_notebooks is not None and not isinstance(on_notebooks, list):
            raise ConfigError(
                "Config key 'onenote_notebooks' must be a list of notebook names."
            )

    def get(self, key, default=None):
        return self._config.get(key, default)

    @property
    def word_doc_directories(self):
        return self._config.get('word_doc_directories', [])

    @property
    def onenote_enabled(self):
        return self._config.get('onenote_enabled', True)

    @property
    def recordings_directories(self):
        return self._config.get('recordings_directories', [])

    @property
    def onenote_paths(self) -> list:
        """
        Return the list of directories to scan for OneNote ``.one`` /
        ``.onetoc2`` files.

        If the user has not configured any paths (empty list or missing key),
        fall back to the auto-detected default locations.
        """
        configured = self._config.get('onenote_paths', [])
        if configured:
            return configured
        return _default_onenote_paths()

    @property
    def onenote_notebooks(self) -> list:
        """Return the list of notebook names to include.

        An empty list means 'include all notebooks' (no filtering).
        """
        return self._config.get('onenote_notebooks', [])

    @property
    def outlook_enabled(self):
        return self._config.get('outlook_enabled', True)



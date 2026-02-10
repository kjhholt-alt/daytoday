import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / 'config'
CONFIG_FILE = CONFIG_DIR / 'config.json'
TEMPLATE_FILE = CONFIG_DIR / 'config.template.json'

REQUIRED_KEYS = [
    'azure_client_id',
    'azure_authority',
    'graph_scopes',
]


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
                raise ConfigError(
                    f"Config created from template at {CONFIG_FILE}. "
                    "Please edit it with your Azure app details before running."
                )
            raise ConfigError(f"No config file found at {CONFIG_FILE}")

        try:
            with open(CONFIG_FILE, 'r') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}")

        self._validate()
        logger.info("Configuration loaded successfully.")

    def _validate(self):
        missing = [k for k in REQUIRED_KEYS if k not in self._config]
        if missing:
            raise ConfigError(f"Missing required config keys: {missing}")
        if self._config.get('azure_client_id') == 'YOUR_AZURE_APP_CLIENT_ID':
            raise ConfigError(
                "Please replace the placeholder azure_client_id in "
                f"{CONFIG_FILE} with your actual Azure App Client ID."
            )

    def get(self, key, default=None):
        return self._config.get(key, default)

    @property
    def client_id(self):
        return self._config['azure_client_id']

    @property
    def authority(self):
        return self._config['azure_authority']

    @property
    def scopes(self):
        return self._config['graph_scopes']

    @property
    def token_cache_path(self):
        path = self._config.get('token_cache_path', './config/token_cache.bin')
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / path
        return str(resolved)

    @property
    def word_doc_directories(self):
        return self._config.get('word_doc_directories', [])

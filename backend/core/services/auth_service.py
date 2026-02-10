import sys
import logging
from pathlib import Path

import msal
from msal_extensions import (
    PersistedTokenCache,
    FilePersistence,
)

logger = logging.getLogger(__name__)


def _build_persistence(cache_path):
    cache_path = str(Path(cache_path).resolve())
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        try:
            from msal_extensions import FilePersistenceWithDataProtection
            return FilePersistenceWithDataProtection(cache_path)
        except Exception:
            logger.warning(
                "DPAPI token encryption not available; "
                "falling back to plain file persistence."
            )
    return FilePersistence(cache_path)


class AuthError(Exception):
    pass


class AuthService:
    _instance = None

    def __init__(self, config_service):
        self._config = config_service
        self._app = None
        self._cache = None
        self._initialize()

    @classmethod
    def get_instance(cls, config_service=None):
        if cls._instance is None:
            if config_service is None:
                from .config_service import ConfigService
                config_service = ConfigService.get_instance()
            cls._instance = cls(config_service)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _initialize(self):
        persistence = _build_persistence(self._config.token_cache_path)
        self._cache = PersistedTokenCache(persistence)
        self._app = msal.PublicClientApplication(
            client_id=self._config.client_id,
            authority=self._config.authority,
            token_cache=self._cache,
        )
        logger.info("MSAL PublicClientApplication initialized.")

    def get_access_token(self):
        accounts = self._app.get_accounts()
        result = None

        if accounts:
            logger.debug("Attempting silent token acquisition...")
            result = self._app.acquire_token_silent(
                scopes=self._config.scopes,
                account=accounts[0],
            )

        if not result or 'access_token' not in result:
            logger.info("No cached token; launching interactive login...")
            try:
                result = self._app.acquire_token_interactive(
                    scopes=self._config.scopes,
                )
            except Exception as e:
                raise AuthError(f"Interactive authentication failed: {e}")

        if result and 'access_token' in result:
            logger.debug("Access token acquired successfully.")
            return result['access_token']

        error_desc = result.get('error_description', '') if result else ''
        error_code = result.get('error', 'unknown') if result else 'unknown'
        raise AuthError(
            f"Authentication failed [{error_code}]: {error_desc}"
        )

    def get_headers(self):
        token = self.get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def is_authenticated(self):
        accounts = self._app.get_accounts()
        return len(accounts) > 0

    def get_account_info(self):
        accounts = self._app.get_accounts()
        if accounts:
            return {
                'username': accounts[0].get('username', ''),
                'name': accounts[0].get('name', ''),
                'local_account_id': accounts[0].get('local_account_id', ''),
            }
        return None

    def logout(self):
        accounts = self._app.get_accounts()
        for account in accounts:
            self._app.remove_account(account)
        logger.info("All cached accounts removed.")

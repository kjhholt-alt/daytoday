"""
GraphAuthService -- MSAL-based authentication for Microsoft Graph API.

Provides zero-friction authentication: a browser window opens, the user
signs in with their Microsoft account, and the token is cached to disk
so subsequent calls silently refresh without any user interaction.

Auth priority:
    1. Silent acquisition from the persisted token cache (most common path).
    2. Interactive browser login when no cached token is available.

Uses a built-in public client ID so no Azure app registration is needed.
"""

import sys
import logging
from pathlib import Path

import msal
from msal_extensions import (
    PersistedTokenCache,
    FilePersistence,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTHORITY = 'https://login.microsoftonline.com/common'
SCOPES = ['Calendars.Read', 'Notes.Read', 'User.Read']

# Built-in public client ID -- no Azure app registration required.
# Microsoft Graph Command Line Tools -- specifically preauthorized for
# Graph API access with interactive login and dynamic consent.
BUILTIN_CLIENT_ID = '14d82eec-204b-4c2f-b7e8-296a70dab67e'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_persistence(cache_path: str):
    """
    Return the best available ``FilePersistence`` for the current platform.

    On Windows we attempt to use DPAPI-encrypted file persistence so the
    token cache is protected at rest.  If that is unavailable we fall back
    to a plain-text file (still useful for development).
    """
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


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Raised when an authentication operation fails."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class GraphAuthService:
    """
    Singleton service that manages MSAL authentication for Microsoft Graph.

    Usage::

        svc = GraphAuthService.get_instance()
        token = svc.get_token()          # silent or None
        if token is None:
            svc.login_interactive()      # opens browser for sign-in
    """

    _instance = None

    # -- construction / singleton -------------------------------------------

    def __init__(self, config_service=None):
        if config_service is None:
            from .config_service import ConfigService
            config_service = ConfigService.get_instance()

        self._config = config_service
        self._app = None
        self._cache = None
        self._login_error = None

        self._initialize()

    @classmethod
    def get_instance(cls, config_service=None):
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls(config_service)
        return cls._instance

    @classmethod
    def reset(cls):
        """Discard the singleton so a fresh instance is created next time."""
        cls._instance = None

    # -- initialisation -----------------------------------------------------

    @property
    def _client_id(self) -> str:
        """
        Return the Graph client ID to use.

        Uses the configured value from config.json if present, otherwise
        falls back to the built-in public client ID.
        """
        configured = self._config.get('graph_client_id', '')
        return configured or BUILTIN_CLIENT_ID

    @property
    def _cache_path(self) -> str:
        """Path where the serialised token cache is stored on disk."""
        from .config_service import CONFIG_DIR
        return str(CONFIG_DIR / 'graph_token_cache.bin')

    def _initialize(self):
        """Build the MSAL ``PublicClientApplication`` with a persisted cache."""
        client_id = self._client_id

        try:
            persistence = _build_persistence(self._cache_path)
            self._cache = PersistedTokenCache(persistence)
            self._app = msal.PublicClientApplication(
                client_id=client_id,
                authority=AUTHORITY,
                token_cache=self._cache,
            )
            logger.info("MSAL PublicClientApplication initialized (client: %s).", client_id[:8])
        except Exception:
            logger.exception("Failed to initialise MSAL application.")
            self._app = None
            self._cache = None

    # -- public API ---------------------------------------------------------

    def get_token(self) -> str | None:
        """
        Return a valid access token string, or ``None``.

        Tries silent acquisition from the cache.  If that fails it returns
        ``None`` rather than prompting -- call :meth:`login_interactive` to
        start an interactive browser login.
        """
        if self._app is None:
            return None

        accounts = self._app.get_accounts()
        if not accounts:
            logger.debug("No cached accounts; token unavailable.")
            return None

        try:
            result = self._app.acquire_token_silent(
                scopes=SCOPES,
                account=accounts[0],
            )
        except Exception:
            logger.exception("Silent token acquisition raised an exception.")
            return None

        if result and 'access_token' in result:
            logger.debug("Access token acquired silently.")
            return result['access_token']

        error = result.get('error', 'unknown') if result else 'unknown'
        desc = result.get('error_description', '') if result else ''
        logger.warning("Silent token acquisition failed [%s]: %s", error, desc)
        return None

    def get_headers(self) -> dict | None:
        """
        Return authorisation headers suitable for Graph API requests,
        or ``None`` if no token is available.
        """
        token = self.get_token()
        if token is None:
            return None
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    @property
    def graph_enabled(self) -> bool:
        """Always True -- the built-in client ID ensures Graph is available."""
        return self._app is not None

    def is_authenticated(self) -> bool:
        """Return ``True`` if at least one account is present in the cache."""
        if self._app is None:
            return False
        try:
            return len(self._app.get_accounts()) > 0
        except Exception:
            logger.exception("Error checking authentication status.")
            return False

    def get_accounts(self) -> list:
        """Return the list of cached MSAL accounts (may be empty)."""
        if self._app is None:
            return []
        try:
            return self._app.get_accounts()
        except Exception:
            logger.exception("Error retrieving cached accounts.")
            return []

    def get_account_info(self) -> dict | None:
        """Return a dict with username/name for the first cached account."""
        accounts = self.get_accounts()
        if accounts:
            return {
                'username': accounts[0].get('username', ''),
                'name': accounts[0].get('name', ''),
                'local_account_id': accounts[0].get('local_account_id', ''),
            }
        return None

    @property
    def login_error(self) -> str | None:
        """Return the last login error message, if any."""
        return self._login_error

    # -- login (interactive browser flow) -----------------------------------

    def login_interactive(self) -> dict | None:
        """
        Open a browser window for the user to sign in with their Microsoft
        account.  This call BLOCKS until the user completes (or cancels) the
        login in the browser.

        Returns the MSAL result dict on success (contains ``access_token``),
        or ``None`` on failure.
        """
        if self._app is None:
            logger.warning("Cannot login -- MSAL app not initialised.")
            self._login_error = "MSAL app not initialised."
            return None

        self._login_error = None

        try:
            logger.info("Starting interactive browser login...")
            result = self._app.acquire_token_interactive(
                scopes=SCOPES,
            )
        except Exception as e:
            logger.exception("Interactive login raised an exception.")
            self._login_error = str(e)
            return None

        if result and 'access_token' in result:
            logger.info("Interactive authentication successful.")
            self._login_error = None
            return result

        error = result.get('error', 'unknown') if result else 'unknown'
        desc = result.get('error_description', '') if result else ''
        logger.error("Interactive login failed [%s]: %s", error, desc)
        self._login_error = desc or error
        return None

    # -- logout -------------------------------------------------------------

    def logout(self):
        """Remove every cached account and clear the persisted token cache."""
        if self._app is None:
            logger.debug("Logout called but MSAL app is not initialised.")
            return

        try:
            accounts = self._app.get_accounts()
            for account in accounts:
                self._app.remove_account(account)
            logger.info(
                "Logged out -- %d cached account(s) removed.", len(accounts)
            )
        except Exception:
            logger.exception("Error during logout.")

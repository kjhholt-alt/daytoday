import logging
import time

import requests

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = 'https://graph.microsoft.com/v1.0'


class GraphClientError(Exception):
    def __init__(self, status_code, message, response=None):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"Graph API Error {status_code}: {message}")


class GraphClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    REQUEST_TIMEOUT = 30

    def __init__(self, auth_service):
        self._auth = auth_service

    def _request(self, method, url, params=None, json_data=None, raw=False):
        for attempt in range(self.MAX_RETRIES):
            try:
                headers = self._auth.get_headers()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    timeout=self.REQUEST_TIMEOUT,
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(
                        f"Throttled by Graph API. "
                        f"Retrying after {retry_after}s (attempt {attempt + 1})..."
                    )
                    time.sleep(retry_after)
                    continue

                if response.status_code == 401 and attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        "401 Unauthorized; token may be expired. "
                        "Re-authenticating..."
                    )
                    continue

                if response.status_code >= 400:
                    raise GraphClientError(
                        response.status_code,
                        response.text[:500],
                        response,
                    )

                if raw:
                    return response.text
                return response.json() if response.content else {}

            except requests.exceptions.ConnectionError as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (attempt + 1)
                    logger.warning(
                        f"Connection error: {e}. "
                        f"Retrying in {delay}s (attempt {attempt + 1})..."
                    )
                    time.sleep(delay)
                    continue
                raise GraphClientError(0, f"Connection failed after retries: {e}")

            except requests.exceptions.Timeout as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (attempt + 1)
                    logger.warning(
                        f"Request timed out. "
                        f"Retrying in {delay}s (attempt {attempt + 1})..."
                    )
                    time.sleep(delay)
                    continue
                raise GraphClientError(0, f"Request timed out after retries: {e}")

        raise GraphClientError(0, "Max retries exceeded")

    def get(self, endpoint, params=None):
        url = f"{GRAPH_BASE_URL}{endpoint}"
        return self._request('GET', url, params=params)

    def get_raw(self, endpoint, params=None):
        url = f"{GRAPH_BASE_URL}{endpoint}"
        return self._request('GET', url, params=params, raw=True)

    def get_paginated(self, endpoint, params=None):
        url = f"{GRAPH_BASE_URL}{endpoint}"
        all_items = []
        result = self._request('GET', url, params=params)
        all_items.extend(result.get('value', []))

        while '@odata.nextLink' in result:
            next_url = result['@odata.nextLink']
            result = self._request('GET', next_url)
            all_items.extend(result.get('value', []))

        return all_items

"""
github_client.py — GitHub API client with rate limit handling for the
Ghostline lead generation tool.
"""

import logging
import time
import requests
from shared.config import (
    GITHUB_HEADERS,
    GITHUB_API_BASE,
    RATE_LIMIT_SLEEP_SEARCH,
    RATE_LIMIT_SLEEP_CODE_SEARCH,
    RATE_LIMIT_SLEEP_CORE,
    CORE_BUDGET_ABORT_THRESHOLD,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self):
        """Initialize with headers from config. Verify auth via /rate_limit on first use."""
        self.headers = dict(GITHUB_HEADERS)
        self.api_call_count = 0

        if not self.headers.get("Authorization") or self.headers["Authorization"] == "Bearer ":
            raise RuntimeError(
                "GITHUB_TOKEN is not set. Add it to your .env file. "
                "Generate one at https://github.com/settings/tokens (no scopes needed)."
            )

        # Verify authentication on init
        rate_data = self.check_rate_limit()
        if not rate_data:
            raise RuntimeError(
                "Failed to authenticate with GitHub API. "
                "Check that GITHUB_TOKEN is set and valid."
            )

        core = rate_data.get("resources", {}).get("core", {})
        logger.info(
            "GitHub API authenticated. Core rate limit: %s/%s remaining.",
            core.get("remaining", "?"),
            core.get("limit", "?"),
        )

    def search_repos(self, query: str, page: int = 1) -> dict:
        """
        Search GitHub repositories.

        Endpoint: GET /search/repositories
        Rate pool: Search API (30 req/min)
        Sleep: RATE_LIMIT_SLEEP_SEARCH between calls

        Args:
            query: Search query string (without sort/order/per_page params)
            page: Page number (1-indexed)

        Returns:
            Parsed JSON response dict with 'items' and 'total_count' keys.
            Returns empty dict on error.
        """
        url = f"{GITHUB_API_BASE}/search/repositories"
        try:
            response = requests.get(url, headers=self.headers, timeout=30, params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 100,
                "page": page,
            })
            result = self._handle_response(response, "search")
        except requests.RequestException as exc:
            logger.warning("search_repos request failed: %s", exc)
            result = {}
        finally:
            time.sleep(RATE_LIMIT_SLEEP_SEARCH)

        return result if isinstance(result, dict) else {}

    def search_code(self, query: str) -> dict:
        """
        Search GitHub code.

        Endpoint: GET /search/code
        Rate pool: Code Search API (10 req/min)
        Sleep: RATE_LIMIT_SLEEP_CODE_SEARCH between calls

        Args:
            query: Code search query (e.g. '"from langchain" repo:owner/repo')

        Returns:
            Parsed JSON response dict with 'items' and 'total_count' keys.
            Returns empty dict on error.
        """
        url = f"{GITHUB_API_BASE}/search/code"
        try:
            response = requests.get(url, headers=self.headers, timeout=30, params={
                "q": query,
                "per_page": 1,
            })
            result = self._handle_response(response, "code_search")
        except requests.RequestException as exc:
            logger.warning("search_code request failed: %s", exc)
            result = {}
        finally:
            time.sleep(RATE_LIMIT_SLEEP_CODE_SEARCH)

        return result if isinstance(result, dict) else {}

    def get_user(self, username: str) -> dict:
        """
        Get a GitHub user's public profile.

        Endpoint: GET /users/{username}
        Rate pool: Core API (5000 req/hr)
        Sleep: RATE_LIMIT_SLEEP_CORE between calls

        Args:
            username: GitHub login handle

        Returns:
            Parsed JSON user profile dict. Returns empty dict if user not found.
        """
        url = f"{GITHUB_API_BASE}/users/{username}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            result = self._handle_response(response, "core")
        except requests.RequestException as exc:
            logger.warning("get_user request failed for %s: %s", username, exc)
            result = {}
        finally:
            time.sleep(RATE_LIMIT_SLEEP_CORE)

        return result if isinstance(result, dict) else {}

    def get_commits(self, owner: str, repo: str, author: str, per_page: int = 5) -> list:
        """
        Get recent commits by a specific author in a repo.

        Endpoint: GET /repos/{owner}/{repo}/commits?author={author}&per_page={per_page}
        Rate pool: Core API (5000 req/hr)
        Sleep: RATE_LIMIT_SLEEP_CORE between calls

        Args:
            owner: Repo owner login
            repo: Repo name
            author: GitHub username to filter commits by
            per_page: Number of commits to fetch (default 5 is enough for email extraction)

        Returns:
            List of commit dicts. Each has commit.author.email and commit.committer.email.
            Returns empty list on error.
        """
        url = (
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
            f"?author={author}&per_page={per_page}"
        )
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            result = self._handle_response(response, "core")
        except requests.RequestException as exc:
            logger.warning("get_commits request failed for %s/%s: %s", owner, repo, exc)
            result = []
        finally:
            time.sleep(RATE_LIMIT_SLEEP_CORE)

        return result if isinstance(result, list) else []

    def get_user_events(self, username: str, per_page: int = 100) -> list:
        """
        Get a user's public events (for commit email extraction fallback).

        Endpoint: GET /users/{username}/events/public?per_page={per_page}
        Rate pool: Core API (5000 req/hr)
        Sleep: RATE_LIMIT_SLEEP_CORE between calls

        Look for PushEvent types. Each has payload.commits[] with author.email.

        Args:
            username: GitHub login handle
            per_page: Max events to fetch (default 100)

        Returns:
            List of event dicts. Returns empty list on error.
        """
        url = (
            f"{GITHUB_API_BASE}/users/{username}/events/public"
            f"?per_page={per_page}"
        )
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            result = self._handle_response(response, "core")
        except requests.RequestException as exc:
            logger.warning("get_user_events request failed for %s: %s", username, exc)
            result = []
        finally:
            time.sleep(RATE_LIMIT_SLEEP_CORE)

        return result if isinstance(result, list) else []

    def get_readme(self, owner: str, repo: str, max_chars: int = 2000) -> str:
        """
        Fetch the raw README for a repository, truncated to max_chars.

        Endpoint: GET /repos/{owner}/{repo}/readme
        Accept: application/vnd.github.raw  (returns raw text, not base64 JSON)
        Rate pool: Core API (5000 req/hr)
        Sleep: RATE_LIMIT_SLEEP_CORE between calls

        Args:
            owner: Repository owner login
            repo: Repository name
            max_chars: Maximum characters to return (default 2000)

        Returns:
            Raw README text truncated to max_chars, or empty string if the
            repository has no README or the request fails.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
        raw_headers = dict(self.headers)
        raw_headers["Accept"] = "application/vnd.github.raw"
        try:
            response = requests.get(url, headers=raw_headers, timeout=30)
            if response.status_code == 404:
                logger.warning("No README found for %s/%s (HTTP 404).", owner, repo)
                result = ""
            elif response.status_code >= 400:
                # Delegate non-404 error handling through the standard handler.
                # _handle_response expects a dict|list return type, so we call it
                # here only for its side effects (logging, rate-limit sleeps).
                # The README text itself comes from response.text on success.
                self._handle_response(response, "core")
                result = ""
            else:
                # Successful response — call _handle_response for rate-limit side effects
                # but catch the JSONDecodeError it raises on raw text responses.
                try:
                    self._handle_response(response, "core")
                except ValueError:
                    self.api_call_count += 1
                result = response.text[:max_chars]
        except requests.RequestException as exc:
            logger.warning("get_readme request failed for %s/%s: %s", owner, repo, exc)
            result = ""
        finally:
            time.sleep(RATE_LIMIT_SLEEP_CORE)

        return result if isinstance(result, str) else ""

    def check_rate_limit(self) -> dict:
        """
        Check current rate limit status. Does NOT count against rate limits.

        Endpoint: GET /rate_limit

        Returns:
            Dict with 'resources' key containing 'core', 'search', 'code_search' sub-dicts,
            each with 'remaining', 'limit', 'reset' fields. Returns empty dict on error.
        """
        url = f"{GITHUB_API_BASE}/rate_limit"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            logger.warning(
                "check_rate_limit returned HTTP %s: %s",
                response.status_code,
                response.text[:200],
            )
            return {}
        except requests.RequestException as exc:
            logger.warning("check_rate_limit request failed: %s", exc)
            return {}

    def _handle_response(self, response: requests.Response, rate_pool: str) -> dict | list:
        """
        Internal: handle rate limit headers, 403/429 errors, and retries.

        Reads X-RateLimit-Remaining and X-RateLimit-Reset headers.
        On remaining <= 2: sleeps until reset + 1s.
        On HTTP 403: reads Retry-After header, sleeps, retries.
        On HTTP 429: sleeps 60s, retries.
        If core remaining < CORE_BUDGET_ABORT_THRESHOLD: raises RuntimeError to abort run.

        Args:
            response: The requests.Response object
            rate_pool: One of "search", "code_search", "core" — determines sleep behavior

        Returns:
            Parsed JSON (dict or list)
        """
        # Read rate limit headers
        remaining_str = response.headers.get("X-RateLimit-Remaining")
        reset_str = response.headers.get("X-RateLimit-Reset")

        remaining = int(remaining_str) if remaining_str else None
        reset_time = int(reset_str) if reset_str else None

        # Check if core budget is critically low — abort to protect remaining calls
        if rate_pool == "core" and remaining is not None:
            if remaining < CORE_BUDGET_ABORT_THRESHOLD:
                raise RuntimeError(
                    f"Core API budget critically low: {remaining} remaining "
                    f"(threshold: {CORE_BUDGET_ABORT_THRESHOLD}). Aborting run."
                )

        # Handle HTTP 403 — secondary rate limit or abuse detection
        if response.status_code == 403:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                sleep_seconds = int(retry_after)
                logger.warning(
                    "HTTP 403 with Retry-After: %ss. Sleeping and retrying.",
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
            else:
                # No Retry-After header; sleep until reset if available
                if reset_time:
                    sleep_seconds = max(reset_time - int(time.time()) + 1, 1)
                    logger.warning(
                        "HTTP 403 without Retry-After. Sleeping %ss until reset.",
                        sleep_seconds,
                    )
                    time.sleep(sleep_seconds)
                else:
                    logger.warning("HTTP 403 with no retry info. Sleeping 60s.")
                    time.sleep(60)

            # Retry once
            retry_response = requests.get(
                response.url, headers=self.headers, timeout=30
            )
            if retry_response.status_code >= 400:
                logger.warning(
                    "Retry after 403 still failed with HTTP %s.",
                    retry_response.status_code,
                )
                return {} if rate_pool in ("search", "code_search") else []
            self.api_call_count += 1
            return retry_response.json()

        # Handle HTTP 429 — too many requests
        if response.status_code == 429:
            logger.warning("HTTP 429 rate limited. Sleeping 60s and retrying.")
            time.sleep(60)

            retry_response = requests.get(
                response.url, headers=self.headers, timeout=30
            )
            if retry_response.status_code >= 400:
                logger.warning(
                    "Retry after 429 still failed with HTTP %s.",
                    retry_response.status_code,
                )
                return {} if rate_pool in ("search", "code_search") else []
            self.api_call_count += 1
            return retry_response.json()

        # Handle 404 and other client errors
        if response.status_code == 404:
            logger.warning("HTTP 404: %s", response.url)
            return {} if rate_pool in ("search", "code_search") else []

        if response.status_code >= 400:
            logger.warning(
                "HTTP %s error for %s: %s",
                response.status_code,
                response.url,
                response.text[:200],
            )
            return {} if rate_pool in ("search", "code_search") else []

        # Successful response — check if we are close to exhausting limits
        if remaining is not None and remaining <= 2 and reset_time is not None:
            sleep_seconds = max(reset_time - int(time.time()) + 1, 1)
            logger.info(
                "Rate limit nearly exhausted for %s (%s remaining). "
                "Sleeping %ss until reset.",
                rate_pool,
                remaining,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)

        self.api_call_count += 1
        return response.json()

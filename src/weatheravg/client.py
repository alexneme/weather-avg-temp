# OOP boundary for external i/o
# all http/keys/retries live here, so the rest of the code is pure and testable
# use a thread-local session per ThreadPoolExecutor worker for best practice

from __future__ import annotations
import os
import threading
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()  # in production, environment variables is injected by docker, kubernetes, cloud provider

class WeatherAPIError(RuntimeError):
    # single error type used to propagate clear messages from this layer
    pass

class WeatherAPIClient:
    # this class encapsulates provider details like base URL, params, auth, retries
    BASE_URL = "https://api.weatherapi.com/v1/forecast.json"
    DEFAULT_TIMEOUT = 10.0

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        user_agent: str = "weather-avg-temp/0.1 (+https://github.com/alexneme/weather-avg-temp)",
    ):
        self.api_key = api_key or os.getenv("WEATHERAPI_KEY")
        if not self.api_key:
            # fail when key is missing to avoid confusing downstream errors
            raise WeatherAPIError("WEATHERAPI_KEY not set")

        self.timeout = timeout
        self.user_agent = user_agent

        # each worker thread lazily obtains its own session through _session()
        self._local = threading.local()

        # retry policy for transient network, server or rate-limit issues
        self._retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,        # exponential backoff (0.5, 1.0, 2.0, ...)
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )

    def _build_session(self) -> requests.Session:
        # central place to configure http behavior like headers, adapters, retries
        s = requests.Session()
        s.headers.update({"User-Agent": self.user_agent})
        adapter = HTTPAdapter(max_retries=self._retry)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s

    def _session(self) -> requests.Session:
        # thread-local session creation
        sess = getattr(self._local, "session", None)
        if sess is None:
            sess = self._build_session()
            self._local.session = sess
        return sess

    def get_city_forecast(self, city_query: str, days: int = 6) -> Dict[str, Any]:
        # fetch forecast JSON and validate minimal shape as single responsibility
        # caller remains simple, it only handles dicts of known shape
        if not (1 <= days <= 10):  # WeatherAPI has a cap limit of 10 days
            raise WeatherAPIError(f"'days' must be between 1 and 10 (got {days})")

        params = {
            "key": self.api_key,
            "q": city_query,
            "days": days,
            "aqi": "no",
            "alerts": "no",
        }

        try:
            resp = self._session().get(self.BASE_URL, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            # wrap requests exceptions with context for easier debugging
            raise WeatherAPIError(f"Request error for {city_query!r}: {exc}") from exc

        if resp.status_code >= 400:
            # include a short response snippet to speed up triage
            snippet = (resp.text or "")[:300]
            raise WeatherAPIError(f"HTTP {resp.status_code} for {city_query!r} (days={days}). Body: {snippet}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise WeatherAPIError(f"Invalid JSON for {city_query!r}: {exc}") from exc

        # ensure the data meets the basic requirements expected by the service layer
        try:
            _ = data["forecast"]["forecastday"]
        except (KeyError, TypeError) as exc:
            raise WeatherAPIError("Unexpected API shape: missing forecast.forecastday") from exc

        return data

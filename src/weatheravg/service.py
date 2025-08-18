# orchestration and business rules.
# use ThreadPoolExecutor to run the 3 network calls concurrently
# provides pure functions (parse and average) and a compute_all coordinator that works with any dict of cities


from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
from .models import Forecast, CityResult, mean
from .client import WeatherAPIClient

# transform raw provider payload into our small, typed value objects and check shape
def parse_forecasts(data) -> List[Forecast]:
    # weatherAPI shape: data["forecast"]["forecastday"][i]["day"]["maxtemp_c"]
    if isinstance(data, dict):
        try:
            days = data["forecast"]["forecastday"]
            return [Forecast(max_temp=float(d["day"]["maxtemp_c"])) for d in days]
        except (KeyError, TypeError):
            pass  # fall through to legacy shape

        if "consolidated_weather" in data:
            return [Forecast(max_temp=float(item["max_temp"]))
                    for item in data["consolidated_weather"]]

    raise ValueError("Unsupported payload shape for parse_forecasts()")

# single city path: fetch -> parse -> average    
def average_max_temp_for_city(client: WeatherAPIClient, city: str, query: str, days: int = 6) -> CityResult:
    # keeping this small makes it ideal as the function we submit to the thread pool
    payload = client.get_city_forecast(query, days=days)
    forecasts = parse_forecasts(payload)
    avg = mean([f.max_temp for f in forecasts])
    return CityResult(city=city, average_max_temp=avg)

# reuse a single WeatherAPI client, but each worker has its own thread local http session
def compute_all(cities: Dict[str, str], days: int = 6, max_workers: int = 3) -> List[CityResult]:
    client = WeatherAPIClient()
    results: List[CityResult] = []

    # one worker per city is enough here, and its configurable if more are needed
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(average_max_temp_for_city, client, city, query, days): city
            for city, query in cities.items()
        }
        for fut in as_completed(futures):
            # allow exceptions to propagate (pytest/cli will display clear messages)
            results.append(fut.result())

    # ensure a stable ordering so cli output is deterministic and tests are easier to validate
    return sorted(results, key=lambda x: x.city.lower())

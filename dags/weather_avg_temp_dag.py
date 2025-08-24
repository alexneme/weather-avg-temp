# dags/weather_avg_temp_dag.py
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Dict, List
from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from weatheravg.client import WeatherAPIClient
from weatheravg.models import mean

ORDER = ["Salt Lake City", "Los Angeles", "Boise"]
CITIES: Dict[str, str] = {
    "Salt Lake City": "Salt Lake City, UT",
    "Los Angeles": "Los Angeles, CA",
    "Boise": "Boise, ID",
}

@dag(
    dag_id="weather_avg_temp",
    start_date=datetime(2025, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
    default_args={"owner": "alex-eng", "retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["weather", "max-avg-temp"],
)
def weather_avg_temp():
    @task(pool="weatherapi", execution_timeout=timedelta(seconds=30))
    def fetch_avg(city: str, query: str, days: int = 6) -> dict:
        api_key = os.getenv("WEATHERAPI_KEY")
        if not api_key:
            raise AirflowFailException("WEATHERAPI_KEY not set in task environment")

        # If your plan only allows 3-day forecast, force days=min(days, 3)
        days_req = min(days, 6)

        client = WeatherAPIClient(api_key=api_key)
        try:
            payload = client.get_city_forecast(query, days=days_req)
        except Exception as e:
            # Will include HTTP status/body snippets from our client
            raise AirflowFailException(f"fetch_avg({city}) client error: {e}")

        try:
            days_list = payload["forecast"]["forecastday"]
            if not days_list:
                raise AirflowFailException(f"fetch_avg({city}) got empty forecastday list")
            temps = [float(d["day"]["maxtemp_c"]) for d in days_list]
        except Exception as e:
            # Log top-level keys to help debug shape issues
            keys = list(payload.keys())
            raise AirflowFailException(
                f"fetch_avg({city}) parse error: {e}; top-level keys: {keys}"
            )

        return {"city": city, "avg": round(mean(temps), 2), "n_days": len(temps)}

    results = fetch_avg.expand(
        city=list(CITIES.keys()),
        query=list(CITIES.values()),
    )

    @task
    def publish(rows: List[dict]) -> None:
        by = {r["city"]: r for r in rows}
        for city in ORDER:
            r = by[city]
            print(f"{city} Average Max Temp: {r['avg']:.2f} (n={r['n_days']})")

    publish(results)

dag = weather_avg_temp()

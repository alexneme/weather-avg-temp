# connects input (city -> query) to the service and prints the result in the required format.

from __future__ import annotations
from .service import compute_all

# be explicit in queries to avoid provider geocoding ambiguity
CITIES = {
    "Salt Lake City": "Salt Lake City, UT",
    "Los Angeles": "Los Angeles, CA",
    "Boise": "Boise, ID",
}

def main() -> None:
    # uses threads under the hood (ThreadPoolExecutor in service.compute_all)
    results = compute_all(CITIES, days=6, max_workers=3)
    by_city = {r.city: r for r in results}
    for city in CITIES:
        # match the prompt's exact formatting and precision
        r = by_city[city]
        print(f"{r.city} Average Max Temp: {r.average_max_temp:.2f}")

if __name__ == "__main__":
    main()

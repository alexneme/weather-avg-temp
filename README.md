# weather-avg-temp

Compute the **6-day average max temperature** for **Salt Lake City**, **Los Angeles**, and **Boise** using the [WeatherAPI](https://www.weatherapi.com/) forecast endpoint, and print the results.

Example (Numbers will vary):
```
Salt Lake City Average Max Temp: 35.73
Los Angeles Average Max Temp: 29.84
Boise Average Max Temp: 32.63
```

---

## Requirements

- **Python** 3.10+
- **Dependencies** (installed via `pip install -e .`):
  - `requests` – HTTP client
  - `python-dotenv` – load `.env` in local dev
  - `pytest` for tests **Dev (optional)**

---

## Setup

```bash
git clone https://github.com/alexneme/weather-avg-temp.git
cd weather-avg-temp
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Configure the API key

Use an environment variable or a local `.env` file (not committed):

```ini
# .env file at project root
WEATHERAPI_KEY="your_api_key_here"
```

> A `.env.example` can be provided for convenience. `.env` is ignored by git.

---

## Run

```bash
python -m weatheravg.cli
```

**What it does**
- Calls WeatherAPI `/v1/forecast.json` with `days=6`
- Fetches the 3 cities **concurrently** (threads)
- Averages `forecast.forecastday[*].day.maxtemp_c` for each city in degrees Celsius (ºC)

---

## Test

```bash
pytest -q
```

- Tests are **fast and deterministic** (use a local JSON fixture; no live HTTP).
- Validate both the average helper and the forecast parser.

---

## Project Layout

```
src/weatheravg/
  ├─ __init__.py
  ├─ models.py        # dataclasses (Forecast, CityResult) + mean()
  ├─ client.py        # WeatherAPIClient (thread-safe session, retries, timeouts)
  ├─ service.py       # parse + average + threaded orchestration
  └─ cli.py           # fixed output order & printing
tests/
  ├─ test_service.py
  └─ data/
     └─ example_city.json
pyproject.toml
README.md
.editorconfig
.gitignore
```

---

## Design Notes (concise)

- **OOP boundary (`client.py`)**  
  Encapsulates all external I/O (base URL, params, env key, retries, timeouts).  
  Uses a **thread-local `requests.Session`** so workers don’t share a session.

- **Concurrency (I/O-bound)**  
  `ThreadPoolExecutor(max_workers=3)` issues the three HTTP requests in parallel.  
  Threads are ideal here because we’re waiting on network I/O.

- **Pure business logic (`service.py`)**  
  Separate parsing (`forecastday[*].day.maxtemp_c`) and averaging from I/O.  
  Easy to test and reuse; order is enforced at the CLI print stage.

- **Error handling**  
  Custom `WeatherAPIError` with informative messages.  
  Retries and exponential backoff for transient errors / HTTP 429.

- **Security & config**  
  API key via env (`WEATHERAPI_KEY`) / `.env`. Never hard-code secrets.

---

## Extending

- **Add cities:** update `CITIES` in `cli.py` (display name → query string accepted by WeatherAPI, e.g., `"Los Angeles, CA"`).  
- **Change forecast window:** pass `days` (1–10) to `compute_all`.  
- **Units:** currently uses degrees Celsius**°C** (`maxtemp_c`). Switch to `maxtemp_f` if needed.

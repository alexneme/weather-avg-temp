# Weather Average Temperature

Compute the **6-day average max temperature** for **Salt Lake City**, **Los Angeles**, and **Boise** using the [WeatherAPI](https://www.weatherapi.com/) forecast endpoint, and print the results.

Example of output:
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
- **Dev (optional):**
  - `pytest` – run tests

---

## Setup (Local / Non-Airflow)

```bash
git clone https://github.com/alexneme/weather-avg-temp.git
cd weather-avg-temp
python3 -m venv .venv && source .venv/bin/activate
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

## Run (Local CLI)

```bash
python3 -m weatheravg.cli
```

**What it does**
- Calls WeatherAPI `/v1/forecast.json` with `days=6`
- Fetches the 3 cities **concurrently** (threads)
- Averages `forecast.forecastday[*].day.maxtemp_c` for each city in degrees Celsius (°C)

---

## Test

```bash
pytest -q
```

- Tests are **fast and deterministic** (use a local JSON fixture; no live HTTP).
- Validate both the average helper and the forecast parser.

---

## Run with Docker Compose (Airflow)

This repo also includes a minimal Airflow stack (Postgres + Airflow 2.9) to orchestrate one task **per city** in parallel. The DAG is at `dags/weather_avg_temp_dag.py` and prints results in the required order.

### 1) Prerequisites
- Docker & Docker Compose v2
- Open ports: **8080** (Airflow UI) and **5433** (Postgres mapped)
- Valid **WeatherAPI** key

### 2) Create a `.env` next to `docker-compose.yml`
```env
AIRFLOW_UID=50000
AIRFLOW_GID=0
WEATHERAPI_KEY="your_api_key_here"
```

### 3) Start the stack
```bash
docker compose up -d
```
This will:
- Start Postgres
- Run **airflow-init**: migrate DB, create `admin/admin`, and create pool `weatherapi` (3 slots)
- Start **webserver** and **scheduler**

> If your Compose doesn’t support `condition: service_completed_successfully`, run:
> ```bash
> docker compose up -d postgres
> docker compose run --rm airflow-init
> docker compose up -d airflow-webserver airflow-scheduler
> ```

### 4) Open Airflow
- UI: http://localhost:8080  
- Login: **admin / admin**  
- Unpause **`weather_avg_temp`**, then **Trigger DAG**.  
- View logs in the **`publish`** task to see the three lines of output (includes `(n=...)` days returned).

**Notes**
- `PYTHONPATH=/opt/airflow/app/src` is set in Compose so the DAG can import `weatheravg` directly from `src/` (no in-container pip install needed).
- `WEATHERAPI_KEY` is injected into the scheduler/webserver environment via `.env`.

---

## Project Layout

```
src/weatheravg/
  ├─ __init__.py
  ├─ models.py        # dataclasses (Forecast, CityResult) + mean()
  ├─ client.py        # WeatherAPIClient (thread-safe session, retries, timeouts)
  ├─ service.py       # parse + average + threaded orchestration
  └─ cli.py           # fixed output order & printing
dags/
  └─ weather_avg_temp_dag.py  # Airflow DAG (one task per city, pool-guarded)
tests/
  ├─ test_service.py
  └─ data/
     └─ example_city.json
pyproject.toml
README.md
.editorconfig
.gitignore
docker-compose.yml
```

---

## Design Notes (concise)

- **OOP boundary (`client.py`)**  
  Encapsulates all external I/O (base URL, params, env key, retries, timeouts).  
  Uses a **thread-local `requests.Session`** so workers don’t share a session.

- **Concurrency (I/O-bound)**  
  Local CLI: `ThreadPoolExecutor(max_workers=3)` issues the three HTTP requests in parallel.  
  Airflow DAG: one task per city (parallel), guarded by pool `weatherapi` (3 slots).

- **Pure business logic (`service.py`)**  
  Separate parsing (`forecastday[*].day.maxtemp_c`) and averaging from I/O.  
  Easy to test and reuse; order is enforced at the CLI print stage (and in DAG `publish`).

- **Error handling**  
  Custom `WeatherAPIError` with informative messages.  
  Retries and exponential backoff for transient errors / HTTP 429.

- **Security & config**  
  API key via env (`WEATHERAPI_KEY`) / `.env`. Never hard-code secrets.

---

## Extending

- **Add cities:** update the map in `cli.py` (local) and `CITIES` in the DAG (Airflow).  
- **Change forecast window:** pass `days` (1–10) to the service/task; averages whatever WeatherAPI returns (free tiers often return 3).  
- **Units:** currently uses **°C** (`maxtemp_c`). Switch to `maxtemp_f` if needed.
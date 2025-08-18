# unit tests for pure logic and kept tests fast, deterministic, and independent of live http

import json
from pathlib import Path
from weatheravg.models import mean
from weatheravg.service import parse_forecasts


def test_mean():
    # mean() should compute the arithmetic average
    assert mean([1, 2, 3]) == 2
    # empty input returns NaN
    assert str(mean([])) == "nan"

# use a local fixture so tests never hit the network.
def test_parse_forecasts_example():
    # The fixture must mirror the payload shape that parse_forecasts expects
    data_path = Path(__file__).parent / "data" / "example_city.json"
    payload = json.loads(data_path.read_text())

    # transform provider payload into our internal forecast objects
    forecasts = parse_forecasts(payload)

    # today + next 5 days = 6 items
    assert len(forecasts) == 6

    # each forecast should carry a numeric max_temp (°C)
    assert isinstance(forecasts[0].max_temp, float)


import hashlib
import json
import os
import time

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://api.openf1.org/v1"
CACHE_DIR = "openf1_cache"

API = requests.Session()

os.makedirs(CACHE_DIR, exist_ok=True)

# Keep requests below the free-tier rate limit.
LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 0.5



def fetch_data(endpoint, params=None):
    global LAST_REQUEST_TIME

    params = params or {}

    # Create a unique cache filename for each API request.
    cache_key = json.dumps(
        {"endpoint": endpoint, "params": params},
        sort_keys=True
    )

    filename = hashlib.sha256(
        cache_key.encode("utf-8")
    ).hexdigest()

    cache_path = os.path.join(
        CACHE_DIR,
        f"{filename}.json"
    )

    # Return cached data if it is less than 24 hours old.
    cache_expiry = 24 * 60 * 60

    if os.path.exists(cache_path):
        cache_age = time.time() - os.path.getmtime(cache_path)

        if cache_age < cache_expiry:
            try:
                with open(cache_path, "r", encoding="utf-8") as file:
                    print(f"Using cached data: {endpoint}")
                    return json.load(file)

            except (json.JSONDecodeError, OSError):
                print(f"Invalid cache detected: {endpoint}")

    url = f"{BASE_URL}/{endpoint}"

    for attempt in range(5):
        elapsed = time.monotonic() - LAST_REQUEST_TIME

        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        try:
            response = API.get(
                url,
                params=params,
                timeout=30
            )

            LAST_REQUEST_TIME = time.monotonic()

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")

                try:
                    wait_time = float(retry_after)
                except (TypeError, ValueError):
                    wait_time = min(5 * (2 ** attempt), 60)

                if attempt == 4:
                    raise RuntimeError(
                        f"OpenF1 rate limit exceeded: {endpoint}"
                    )

                print(
                    f"Rate limit reached. "
                    f"Waiting {wait_time:.0f} seconds..."
                )

                time.sleep(wait_time)
                continue

            response.raise_for_status()

            data = response.json()

            # Save the response using a temporary file first.
            temp_path = f"{cache_path}.tmp"

            try:
                with open(
                    temp_path,
                    "w",
                    encoding="utf-8"
                ) as file:
                    json.dump(data, file)

                os.replace(temp_path, cache_path)

            except OSError as error:
                print(f"Could not save cache: {error}")

                if os.path.exists(temp_path):
                    os.remove(temp_path)

            return data

        except requests.RequestException as error:
            if attempt == 4:
                raise RuntimeError(
                    f"OpenF1 request failed ({endpoint}): {error}"
                ) from error

            wait_time = min(5 * (2 ** attempt), 60)

            print(
                f"Request failed. Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        f"Unable to retrieve data from OpenF1: {endpoint}"
    )




def get_session(year, event, session_type="Q"):
    session_names = {
        "FP1": "Practice 1",
        "FP2": "Practice 2",
        "FP3": "Practice 3",
        "Q": "Qualifying",
        "S": "Sprint",
        "R": "Race"
    }

    session_name = session_names.get(
        session_type.upper(), session_type
    )

    sessions = fetch_data(
        "sessions",
        {
            "year": year,
            "session_name": session_name
        }
    )

    event = event.strip().lower()

    if not event:
        raise ValueError("Event name cannot be empty.")

    matches = [
        session for session in sessions
        if event in " ".join([
            str(session.get("circuit_short_name", "")),
            str(session.get("location", "")),
            str(session.get("country_name", "")),
            str(session.get("meeting_name", ""))
        ]).lower()
    ]

    if not matches:
        raise ValueError(
            f"No {session_name} session found for {event} in {year}."
        )

    if len(matches) > 1:
        matched_events = [
            session.get("meeting_name", "Unknown event")
            for session in matches
        ]

        raise ValueError(
            f"Multiple events matched '{event}': "
            f"{', '.join(matched_events)}. "
            "Please provide a more specific event name."
        )

    return matches[0]


def get_driver(session_key, driver_code):
    drivers = fetch_data(
        "drivers",
        {"session_key": session_key}
    )

    for driver in drivers:
        if driver.get("name_acronym", "").upper() == driver_code.upper():
            return driver

    raise ValueError(f"Driver {driver_code} not found.")


def get_fastest_lap(session_key, driver_number):
    laps = fetch_data(
        "laps",
        {
            "session_key": session_key,
            "driver_number": driver_number
        }
    )

    valid_laps = [
        lap for lap in laps
        if lap.get("lap_duration") is not None
        and lap.get("date_start") is not None
        and not lap.get("is_pit_out_lap", False)
    ]

    if not valid_laps:
        raise ValueError(
            f"No valid laps found for car {driver_number}."
        )

    return min(
        valid_laps,
        key=lambda lap: lap["lap_duration"]
    )



def get_lap_telemetry(session_key, driver_number, lap):
    # OpenF1 lap start timestamps are approximate.
    # Fetch extra data around the lap to avoid cutting off its edges.
    start = pd.to_datetime(lap["date_start"], utc=True)
    end = start + pd.to_timedelta(
        lap["lap_duration"], unit="s"
    )

    buffer_seconds = 5

    query_start = start - pd.Timedelta(seconds=buffer_seconds)
    query_end = end + pd.Timedelta(seconds=buffer_seconds)

    records = fetch_data(
        "car_data",
        {
            "session_key": session_key,
            "driver_number": driver_number,
            "date>": query_start.isoformat(),
            "date<": query_end.isoformat()
        }
    )

    if not records:
        raise ValueError(
            f"No telemetry found for car {driver_number}."
        )

    telemetry = pd.DataFrame(records)

    

    telemetry = (
        telemetry.sort_values("date")
        .drop_duplicates(subset="date")
        .reset_index(drop=True)
    )

    if len(telemetry) < 2:
        raise ValueError("Not enough telemetry samples.")

    # Convert timestamps to seconds.
    times = (
       pd.to_datetime(
    telemetry["date"],
    utc=True
).astype("int64").to_numpy() / 1e9
)
    


    start_time = start.timestamp()
    end_time = end.timestamp()

    # Ensure the API returned samples covering both lap boundaries.
    if times[0] > start_time or times[-1] < end_time:
        raise ValueError(
            "Telemetry does not cover the complete lap boundaries. "
            "Try another lap or session."
        )

    # Convert speed from km/h to m/s.
    speed = telemetry["speed"].astype(float).to_numpy() / 3.6

    # Calculate distance using trapezoidal integration.
    time_diff = np.diff(times)

    average_speed = (
        speed[:-1] + speed[1:]
    ) / 2

    distance_steps = average_speed * time_diff

    cumulative_distance = np.concatenate([
        [0],
        np.cumsum(distance_steps)
    ])

    # Find cumulative distance at the exact lap boundaries.
    start_distance = np.interp(
        start_time, times, cumulative_distance
    )

    # Include the exact start and end boundaries.
    inside_lap = (
        (times > start_time) &
        (times < end_time)
    )

    lap_times = np.concatenate([
        [start_time],
        times[inside_lap],
        [end_time]
    ])

    lap_times = np.unique(lap_times)

    # Interpolate telemetry values at each sample time.
    lap_speed = np.interp(
        lap_times,
        times,
        speed
    ) * 3.6

    lap_throttle = np.interp(
        lap_times,
        times,
        telemetry["throttle"].astype(float).to_numpy()
    )

    lap_brake = np.interp(
        lap_times,
        times,
        telemetry["brake"].astype(float).to_numpy()
    )

    lap_gear = np.interp(
        lap_times,
        times,
        telemetry["n_gear"].astype(float).to_numpy()
    )

    # Calculate distance relative to the lap start.
    lap_distance = (
        np.interp(
            lap_times,
            times,
            cumulative_distance
        ) - start_distance
    )

    result = pd.DataFrame({
        "Distance": lap_distance,
        "Speed": lap_speed,
        "Throttle": lap_throttle,
        "Brake": lap_brake >= 50,
        "nGear": np.rint(lap_gear).astype(int)
    })

    return result



def get_driver_telemetry(session_key, driver_code):
    driver = get_driver(session_key, driver_code)

    lap = get_fastest_lap(
        session_key,
        driver["driver_number"]
    )

    telemetry = get_lap_telemetry(
        session_key,
        driver["driver_number"],
        lap
    )

    return {
        "driver": driver,
        "lap": lap,
        "telemetry": telemetry
    }

def get_circuit_corners(session):
    """Retrieve corner numbers and distances for the session's circuit."""

    circuit_key = session.get("circuit_key")
    year = session.get("year")

    if not circuit_key or not year:
        raise ValueError("Session is missing circuit_key or year.")

    url = (
        f"https://api.multiviewer.app/api/v1/"
        f"circuits/{circuit_key}/{year}"
    )

    try:
        response = requests.get(
    url,
    headers={"User-Agent": "FastF1/"},
    timeout=20
)
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        raise RuntimeError(
            f"Could not retrieve circuit information: {error}"
        ) from error

    corners = []

    for corner in data.get("corners", []):
        number = corner.get("number")
        letter = corner.get("letter", "")
        length = corner.get("length")

        if number is None or length is None:
            continue

        corners.append({
            "label": f"{number}{letter}",
            "distance": float(length) / 10
        })

    corners.sort(key=lambda item: item["distance"])

    if not corners:
        raise ValueError("No corner information was returned.")

    return corners
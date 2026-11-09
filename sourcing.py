from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import logger
import requests
import time


JSON_DIR = Path(__file__).resolve().parent / "json"


# ---------------------------------------------------------------------------
# Raw API shape (exactly what GetCountsByAccount returns, keys untouched)
# ---------------------------------------------------------------------------
class ApiLocation(TypedDict):
    LocationId: int
    TotalCapacity: int
    LocationName: str
    CountOfParticipants: int
    PercetageCapacity: int  # sic: the API misspells "Percentage"
    LastUpdatedDateAndTime: str
    LastCount: int
    MinColor: str | None
    MidColor: str | None
    MaxColor: str | None
    MinCapacityRange: int
    MaxCapacityRange: int
    CountCapacityColorEnabled: bool
    FacilityId: int
    FacilityName: str
    IsClosed: bool
    SubLocations: list[ApiLocation] | None


# ---------------------------------------------------------------------------
# Our normalized shape
# ---------------------------------------------------------------------------
class LocationData(TypedDict):
    location_id: int
    location_name: str
    total_capacity: int
    last_count: int
    count_of_participants: int
    percentage_capacity: int
    last_updated: datetime
    is_closed: bool
    min_color: str | None
    mid_color: str | None
    max_color: str | None
    min_capacity_range: int
    max_capacity_range: int
    count_capacity_color_enabled: bool
    sub_locations: list[LocationData] | None


class FacilityData(TypedDict):
    facility_id: int
    facility_name: str
    locations: list[LocationData]


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------
def to_location_data(raw: ApiLocation) -> LocationData:
    sub_locations = raw["SubLocations"]
    return {
        "location_id": raw["LocationId"],
        "location_name": raw["LocationName"],
        "total_capacity": raw["TotalCapacity"],
        "last_count": raw["LastCount"],
        "count_of_participants": raw["CountOfParticipants"],
        "percentage_capacity": raw["PercetageCapacity"],
        "last_updated": datetime.fromisoformat(raw["LastUpdatedDateAndTime"]),
        "is_closed": raw["IsClosed"],
        "min_color": raw["MinColor"],
        "mid_color": raw["MidColor"],
        "max_color": raw["MaxColor"],
        "min_capacity_range": raw["MinCapacityRange"],
        "max_capacity_range": raw["MaxCapacityRange"],
        "count_capacity_color_enabled": raw["CountCapacityColorEnabled"],
        "sub_locations": (
            [to_location_data(sub) for sub in sub_locations]
            if sub_locations is not None
            else None
        ),
    }


def parse_json_data(json_data: list[ApiLocation]) -> list[FacilityData]:
    """Group the flat API list into facility objects, each holding its locations."""
    facilities: dict[int, FacilityData] = {}
    for raw in json_data:
        facility = facilities.setdefault(
            raw["FacilityId"],
            {
                "facility_id": raw["FacilityId"],
                "facility_name": raw["FacilityName"],
                "locations": [],
            },
        )
        facility["locations"].append(to_location_data(raw))
    return list(facilities.values())


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
def get_json_data() -> list[ApiLocation] | None:
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
    params: dict[str, str] = {
        "AccountAPIKey": "965778f9-13b8-49e7-b9af-46d83702d026",
    }
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json;charset=utf-8",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    try:
        response: requests.Response = requests.get(
            url="https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount",
            params=params,
            headers=headers,
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"Error occurred while fetching data: {e}")
        return None

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return None

    json_data: list[ApiLocation] = response.json()
    if not json_data:
        print("No data received from the API.")
        return None

    save_json_snapshot(json_data)
    return json_data


def save_json_snapshot(json_data: list[ApiLocation]) -> Path:
    """Write the raw API response to json/<fetch time>.json and return the path."""
    JSON_DIR.mkdir(exist_ok=True)
    # No colons in the name so the files stay valid on Windows too.
    path = JSON_DIR / f"{datetime.now():%Y-%m-%dT%H-%M-%S}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"Saved snapshot to {path}")
    return path


if __name__ == "__main__":
    while True:
        json_data = get_json_data()
        time.sleep(1200)  # Sleep for 20 minutes

    # nah
    if json_data:
        for facility in parse_json_data(json_data):
            print(f"{facility['facility_name']} (id {facility['facility_id']})")
            for loc in facility["locations"]:
                status = "CLOSED" if loc["is_closed"] else "open"
                print(
                    f"  {loc['location_name']}: {loc['last_count']}/{loc['total_capacity']}"
                    f" [{status}] updated {loc['last_updated']:%Y-%m-%d %H:%M}"
                )

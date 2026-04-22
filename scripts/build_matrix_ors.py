import os
import json
import time
import requests
import pandas as pd

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"

def main():
    api_key = os.environ.get("ORS_API_KEY")
    if not api_key:
        raise SystemExit("Missing ORS_API_KEY")

    in_csv = os.environ.get("GEOCODED_CSV", "data/geocoded.csv")
    out_json = os.environ.get("MATRIX_JSON", "data/time_matrix.json")

    df = pd.read_csv(in_csv)

    # Ensure stable order by id
    df = df.sort_values("id")

    # Build locations list: [[lon, lat], ...]
    locations = df[["lon", "lat"]].values.tolist()

    payload = {
        "locations": locations,
        "metrics": ["duration"]
    }

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    r = requests.post(ORS_MATRIX_URL, headers=headers, json=payload, timeout=120)
    r.raise_for_status()

    matrix = r.json()

    # Minimal validation
    durations = matrix.get("durations", [])
    n = len(locations)
    if len(durations) != n or any(len(row) != n for row in durations):
        raise ValueError("Returned matrix dimensions do not match input")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    print(f"Saved {n}x{n} duration matrix to {out_json}")

if __name__ == "__main__":
    main()

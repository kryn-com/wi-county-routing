import os
import json
import time
import requests
import pandas as pd

ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"  # ORS Geocoder endpoint 【2-205be5】

def geocode_one(session, api_key, address, size=1):
    headers = {"Authorization": api_key}  # ORS supports Authorization header 【6-1cc688】
    params = {"text": address, "size": size}
    r = session.get(ORS_GEOCODE_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    features = data.get("features", [])
    if not features:
        return None, None, None

    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    label = features[0].get("properties", {}).get("label")
    return coords[0], coords[1], label

def main():
    api_key = os.environ.get("ORS_API_KEY")
    if not api_key:
        raise SystemExit("Missing ORS_API_KEY (set it as a GitHub Actions secret)")

    in_csv = os.environ.get("STOPS_CSV", "data/stops.csv")
    out_csv = os.environ.get("GEOCODED_CSV", "data/geocoded.csv")
    cache_path = os.environ.get("GEOCODE_CACHE", "data/geocode_cache.json")

    df = pd.read_csv(in_csv)

    # Cache avoids re-geocoding identical addresses on re-runs
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)

    lons, lats, labels, statuses = [], [], [], []

    with requests.Session() as session:
        for _, row in df.iterrows():
            addr = str(row["address"]).strip()
            key = addr.lower()

            if key in cache:
                hit = cache[key]
                lons.append(hit["lon"]); lats.append(hit["lat"])
                labels.append(hit.get("label")); statuses.append(hit.get("status", "CACHED"))
                continue

            try:
                lon, lat, label = geocode_one(session, api_key, addr, size=1)
                if lon is None:
                    lons.append(None); lats.append(None); labels.append(None); statuses.append("NO_MATCH")
                    cache[key] = {"lon": None, "lat": None, "label": None, "status": "NO_MATCH"}
                else:
                    lons.append(lon); lats.append(lat); labels.append(label); statuses.append("OK")
                    cache[key] = {"lon": lon, "lat": lat, "label": label, "status": "OK"}
            except requests.HTTPError as e:
                code = e.response.status_code if e.response is not None else "HTTP_ERROR"
                lons.append(None); lats.append(None); labels.append(None); statuses.append(f"HTTP_{code}")
                cache[key] = {"lon": None, "lat": None, "label": None, "status": f"HTTP_{code}"}
            except Exception as e:
                lons.append(None); lats.append(None); labels.append(None); statuses.append(f"ERROR_{type(e).__name__}")
                cache[key] = {"lon": None, "lat": None, "label": None, "status": f"ERROR_{type(e).__name__}"}

            time.sleep(0.2)  # gentle pacing (helps avoid burst throttling)

    df["lon"] = lons
    df["lat"] = lats
    df["ors_label"] = labels
    df["geocode_status"] = statuses

    df.to_csv(out_csv, index=False)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(df["geocode_status"].value_counts(dropna=False))
    print(f"Wrote {out_csv}")

if __name__ == "__main__":
    main()

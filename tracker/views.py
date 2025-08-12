from pathlib import Path
import os
import json
import requests

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from .models import Shelter

def index(request):
    shelters = Shelter.objects.all()
    return render(request, "index.html", {"shelters": shelters})


def shelter_list(request):
    shelters = Shelter.objects.all()
    data = [
        {
            "name": s.name,
            "address": s.address,
            "city": s.city,
            "county": s.county,
            "zip_code": s.zip_code,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "capacity": s.capacity,
            "is_pet_friendly": s.is_pet_friendly,
            "notes": s.notes,
            "shelter_type": s.shelter_type,
            "status": s.status,
        }
        for s in shelters
    ]
    return JsonResponse(data, safe=False)


def storms_api(request):
    """
    Legacy mapping: returns {storm_id: {cone: url, track: url, name: ..., advisory: ...}}
    from files under tracker/static/tracker/data. Kept for backward compatibility.
    """
    data_dir = os.path.join(settings.BASE_DIR, "tracker", "static", "tracker", "data")
    storms = {}

    # Local name mapping (optional)
    storm_name_file = os.path.join(data_dir, "storm_names.json")
    name_lookup = {}
    if os.path.exists(storm_name_file):
        try:
            with open(storm_name_file, "r", encoding="utf-8") as f:
                name_lookup = json.load(f)
        except Exception:
            pass

    # Supplement with live NHC data (best-effort)
    try:
        resp = requests.get("https://www.nhc.noaa.gov/CurrentStorms.json", timeout=6)
        resp.raise_for_status()
        nhc_data = resp.json()
        for storm in nhc_data:
            sid = storm.get("id")
            nm = storm.get("name")
            if sid and (sid not in name_lookup or not str(name_lookup[sid]).strip()):
                name_lookup[sid] = nm
    except Exception:
        pass

    # Build the legacy mapping from local files
    if os.path.isdir(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith(".geojson"):
                parts = filename.split("_")
                if len(parts) == 3:
                    storm_id, kind, advisory = parts
                    key = storm_id
                    storms.setdefault(key, {"advisory": advisory})
                    storms[key][kind] = f"/static/tracker/data/{filename}"

                    # Friendly name if available
                    name = name_lookup.get(storm_id)
                    if not name or not str(name).strip():
                        name = f"Unnamed Storm ({storm_id.upper()})"
                    storms[key]["name"] = name

    return JsonResponse(storms)


# Directory where your .geojson storm files are written
STORMS_DIR = Path(settings.BASE_DIR) / "tracker" / "static" / "tracker" / "data"


def storms_geojson(request):
    """
    Combine every *.geojson in STORMS_DIR and enrich with:
      - properties.stormName (friendly name)
      - properties.status   (e.g., "Tropical Storm", "Hurricane Cat 2")
      - properties.title    (e.g., "Tropical Storm Iova")
    """
    if not STORMS_DIR.exists():
        return JsonResponse({"type": "FeatureCollection", "features": []})

    # 1) Local names (optional)
    storm_name_file = STORMS_DIR / "storm_names.json"
    name_lookup = {}
    if storm_name_file.exists():
        try:
            with open(storm_name_file, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            for sid, val in raw.items():
                sid = sid.lower()
                if isinstance(val, dict):
                    name_lookup[sid] = {
                        "name": (val.get("name") or "").strip(),
                        "type": (val.get("type") or "").strip(),
                    }
                else:
                    name_lookup[sid] = {"name": str(val).strip(), "type": ""}
        except Exception:
            pass

    # 2) Live NHC supplement (adds stormType)
    nhc_types = {}  # sid -> stormType string
    try:
        resp = requests.get("https://www.nhc.noaa.gov/CurrentStorms.json", timeout=6)
        resp.raise_for_status()
        for s in resp.json():
            sid = (s.get("id") or "").lower()
            stype = (s.get("stormType") or "").strip()  # e.g., "Tropical Storm", "Hurricane"
            if sid:
                nhc_types[sid] = stype
                if sid not in name_lookup:
                    name_lookup[sid] = {"name": (s.get("name") or "").strip(), "type": stype}
                else:
                    if stype and not name_lookup[sid].get("type"):
                        name_lookup[sid]["type"] = stype
    except Exception:
        pass

    def classify_from_props(props):
        # direct text fields
        for k in ("status", "stormType", "type", "CLASS", "Class", "system", "SYSTEM"):
            v = str(props.get(k, "")).strip()
            if v:
                return v

        # code fields (TS/HU/TD etc.)
        code = str(props.get("INTENSITY") or props.get("TCtype") or "").upper().strip()
        cmap = {
            "TD": "Tropical Depression",
            "TS": "Tropical Storm",
            "HU": "Hurricane",
            "SS": "Subtropical Storm",
            "SD": "Subtropical Depression",
            "EX": "Extratropical",
            "PT": "Post-Tropical",
            "LO": "Low",
            "DB": "Disturbance",
        }
        if code in cmap:
            if code == "HU":
                cat = props.get("SS") or props.get("SAFFIR_SIMPSON") or props.get("Category") or props.get("category")
                if cat:
                    return f"Hurricane Cat {cat}"
            return cmap[code]

        # wind-based inference
        wind_keys = ("MAX_WIND_MPH", "MAX_WIND", "Vmax", "V_MAX", "VMAX", "MAX_WIND_KTS")
        vmax = None
        for k in wind_keys:
            if k in props and props[k] not in (None, "", "NA"):
                try:
                    n = float(props[k])
                    vmax = n * 1.15078 if ("KTS" in k or (k == "Vmax" and n < 120)) else n
                except Exception:
                    pass
                break
        if vmax is not None:
            if vmax < 39:
                return "Tropical Depression"
            if vmax < 74:
                return "Tropical Storm"
            cat = 5 if vmax >= 157 else 4 if vmax >= 130 else 3 if vmax >= 111 else 2 if vmax >= 96 else 1
            return f"Hurricane Cat {cat}"

        return ""

    features = []
    files = list(STORMS_DIR.rglob("*.geojson"))
    for p in files:
        try:
            gj = json.loads(p.read_text(encoding="utf-8"))
            storm_id = p.stem.split("_")[0].lower()  # e.g., al012025_cone_005 -> al012025
            info = name_lookup.get(storm_id, {})
            friendly_name = info.get("name") or f"Unnamed Storm ({storm_id.upper()})"
            nhc_type = info.get("type") or nhc_types.get(storm_id, "")

            def enrich(feat):
                props = feat.setdefault("properties", {})
                # ensure stormName
                if not props.get("stormName"):
                    props["stormName"] = props.get("name") or props.get("storm") or friendly_name
                # status: prefer NHC type, else classify from props
                status = nhc_type or classify_from_props(props)
                if status:
                    props["status"] = status
                    props["title"] = f"{status} {props['stormName']}"
                else:
                    props["title"] = props["stormName"]
                # also expose a likely ID so client can match if needed
                props.setdefault("stormId", storm_id)
                return feat

            if gj.get("type") == "FeatureCollection":
                features.extend(enrich(f) for f in gj.get("features", []))
            elif gj.get("type") == "Feature":
                features.append(enrich(gj))
        except Exception:
            continue

    print(f"[storms_geojson] files={len(files)} features={len(features)} dir={STORMS_DIR}")
    return JsonResponse({"type": "FeatureCollection", "features": features})


@require_GET
def nhc_current(request):
    """
    CORS-safe proxy for https://www.nhc.noaa.gov/CurrentStorms.json
    Returns {"byId": {...}, "byName": {...}}.
    """
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"

    def build_maps(obj):
        # Accept either {"activeStorms":[...]} or a raw list [...]
        if isinstance(obj, dict):
            arr = obj.get("activeStorms", [])
        elif isinstance(obj, list):
            arr = obj
        else:
            arr = []
        by_id, by_name = {}, {}
        for s in arr:
            if not isinstance(s, dict):
                continue
            sid = (s.get("id") or "").strip().lower()
            nm  = (s.get("name") or "").strip().lower()
            st  = (s.get("stormType") or "").strip()
            if sid and st:
                by_id[sid] = st
            if nm and st:
                by_name[nm] = st
        return by_id, by_name

    # Primary attempt (normal SSL)
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        obj = r.json()
        by_id, by_name = build_maps(obj)
        return JsonResponse({"byId": by_id, "byName": by_name}, status=200)
    except Exception as e1:
        print(f"[nhc_current] primary fetch failed: {e1}")

    # One retry for dev SSL hiccups
    try:
        r = requests.get(url, timeout=6, verify=False)
        r.raise_for_status()
        obj = r.json()
        by_id, by_name = build_maps(obj)
        print("[nhc_current] succeeded on retry with verify=False (dev-only).")
        return JsonResponse({"byId": by_id, "byName": by_name}, status=200)
    except Exception as e2:
        print(f"[nhc_current] retry failed: {e2}")
        # Don’t break the UI—return empty maps
        return JsonResponse({"byId": {}, "byName": {}, "error": "upstream_failed"}, status=200)

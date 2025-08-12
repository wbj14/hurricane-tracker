import os
import requests
import zipfile
import shutil
import geopandas as gpd
import json

NHC_API = "https://www.nhc.noaa.gov/CurrentStorms.json"
DATA_DIR = "tracker/static/tracker/data"
TMP_DIR = "tmp_download"
STORM_NAME_FILE = os.path.join(DATA_DIR, "storm_names.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

def extract_related_files(z, base_name, dest_dir):
    extracted = []
    for ext in [".shp", ".shx", ".dbf", ".prj"]:
        filename = f"{base_name}{ext}"
        if filename in z.namelist():
            extracted_path = z.extract(filename, dest_dir)
            extracted.append(extracted_path)
        else:
            print(f"⚠️ Missing {filename}")
    return extracted

def download_and_convert_zip(storm_id, advisory, url):
    zip_path = os.path.join(TMP_DIR, f"{storm_id}_{advisory}.zip")

    try:
        print(f"🔽 Downloading ZIP from: {url}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")
        return

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            cone_base = None
            track_base = None

            print(f"📦 Contents of ZIP for {storm_id}:")
            for name in z.namelist():
                print(" -", name)
                if name.endswith("_5day_pgn.shp"):
                    cone_base = name.replace(".shp", "")
                    print(f"✅ Found cone shapefile: {name}")
                elif name.endswith("_5day_lin.shp"):
                    track_base = name.replace(".shp", "")
                    print(f"✅ Found track shapefile: {name}")

            if cone_base:
                extract_related_files(z, cone_base, TMP_DIR)
                gdf_cone = gpd.read_file(os.path.join(TMP_DIR, f"{cone_base}.shp"))
                cone_out = os.path.join(DATA_DIR, f"{storm_id}_cone_{advisory}.geojson")
                gdf_cone.to_file(cone_out, driver="GeoJSON")
                print(f"✅ Saved cone GeoJSON: {cone_out}")

            if track_base:
                extract_related_files(z, track_base, TMP_DIR)
                gdf_track = gpd.read_file(os.path.join(TMP_DIR, f"{track_base}.shp"))
                track_out = os.path.join(DATA_DIR, f"{storm_id}_track_{advisory}.geojson")
                gdf_track.to_file(track_out, driver="GeoJSON")
                print(f"✅ Saved track GeoJSON: {track_out}")

            if not cone_base and not track_base:
                print(f"⚠️ No relevant shapefiles found in {storm_id} ZIP")

    except Exception as e:
        print(f"❌ Error extracting ZIP: {e}")

def main():
    print("🌐 Fetching active storms...")
    try:
        response = requests.get(NHC_API)
        response.raise_for_status()
        storm_data = response.json().get("activeStorms", [])
    except Exception as e:
        print(f"❌ Failed to fetch storm data: {e}")
        return

    if not storm_data:
        print("🌀 No active storms found.")
        return

    storm_names = {}
    active_ids = []

    for storm in storm_data:
        storm_id = storm.get("id")
        storm_name = storm.get("name", storm_id)
        advisory = storm.get("forecastTrack", {}).get("advNum")
        zip_url = storm.get("forecastTrack", {}).get("zipFile")

        if storm_id:
            active_ids.append(storm_id)

        if storm_id and advisory and zip_url:
            print(f"\n🌀 Processing {storm_id} ({storm_name}) - Advisory {advisory}...")
            storm_names[storm_id] = storm_name
            download_and_convert_zip(storm_id, advisory, zip_url)
        else:
            print(f"⚠️ Incomplete data for {storm_name}")

    # Save storm ID → name mapping
    with open(STORM_NAME_FILE, "w") as f:
        json.dump(storm_names, f, indent=2)
        print(f"\n✅ Saved storm names to {STORM_NAME_FILE}")
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".geojson"):
            parts = filename.split("_")
            if len(parts) == 3:
                storm_id = parts[0]
                if storm_id not in active_ids:
                    file_path = os.path.join(DATA_DIR, filename)
                    os.remove(file_path)
                    print(f"🗑️ Removed outdated file: {filename}")

    shutil.rmtree(TMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
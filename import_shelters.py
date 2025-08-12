import csv
import os
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hurricane_project.settings")
django.setup()

from tracker.models import Shelter

# Path to your CSV
csv_file = "risk_shelters.csv"

with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    print("Field names in CSV:", reader.fieldnames)
    first_row = next(reader)
    print("First row values:", first_row)
    f.seek(0)
    next(reader)  # Skip header again

    Shelter.objects.all().delete()  # Optional: clear old data

    count = 0
    for row in reader:
        try:
            Shelter.objects.create(
                name=row["Name"].strip(),
                address=row["Address"].strip(),
                city=row["City"].strip(),
                zip_code=row["Zip"].strip(),
                county=row["COUNTY"].strip(),
                latitude=float(row["Y"]),
                longitude=float(row["X"]),
                capacity=int(row["EHPA_Capac"]) if row["EHPA_Capac"].strip().isdigit() else None,
                is_pet_friendly=row["Pet_Friend"].strip().lower() in ("yes", "true", "y", "1"),
                notes=row.get("Notes", "").strip(),
                shelter_type=row.get("SHELTER_TY", "").strip(),
                status=row.get("General_Po", "").strip()
            )
            count += 1
        except Exception as e:
            print(f"❌ Error on row: {row.get('Name', '[Unnamed]')} → {e}")

print(f"✅ Imported {count} shelters into the database.")

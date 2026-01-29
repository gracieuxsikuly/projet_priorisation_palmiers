from src import extract_geojson
from src import compute_density, compute_distance, compute_priority
from src import display_console, generate_pdf, generate_priority_map
import os
from dotenv import load_dotenv
load_dotenv()
def main():
    # --- Extraction depuis PostgreSQL (ou autre source) ---
    palmiers, zones, routes = extract_geojson(source="postgresql")
    # --- Transformation ---
    zones = compute_density(zones, palmiers)
    zones = compute_distance(zones, routes)
    zones, zone_prioritaire = compute_priority(zones)

    # --- Chargement / Visualisation ---
    display_console(zones, zone_prioritaire)

    # --- Paramètres S3 ---
    s3_bucket = os.getenv("BUCKET_NAME")  
    generate_pdf(
        zones, 
        zone_prioritaire, 
        palmiers, 
        routes,
        s3_bucket=s3_bucket,     
    )
    generate_priority_map(
        zones,
        palmiers,
        routes,
        s3_bucket=s3_bucket,
    )

if __name__ == "__main__":
    main()

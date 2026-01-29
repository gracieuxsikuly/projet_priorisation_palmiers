from src import extract_geojson
from src import compute_density, compute_distance, compute_priority
from src import display_console, generate_pdf,generate_priority_map

def main():
    # --- Extraction local  ---
    palmiers, zones, routes = extract_geojson(source="postgresql")
    # extration s3 example---------
    # palmiers, zones, routes = extract_geojson(source="s3",s3_bucket="mon-bucket",s3_prefix="donnees_sig")
    # extration api example---------
    # palmiers, zones, routes = extract_geojson(
    # source="api",
    # api_urls={
    #     "palmiers": "https://api.exemple.com/palmiers.geojson",
    #     "zones": "https://api.exemple.com/zones.geojson",
    #     "routes": "https://api.exemple.com/routes.geojson",
    # })

    # --- Transformation ---
    zones = compute_density(zones, palmiers)
    zones = compute_distance(zones, routes)
    zones, zone_prioritaire = compute_priority(zones)
    # --- Chargement / Visualisation ---
    display_console(zones, zone_prioritaire)
    generate_pdf(zones, zone_prioritaire, palmiers, routes)  # PDF avec tableau, graphique et carte
    generate_priority_map(zones, palmiers, routes)

if __name__ == "__main__":
    main()


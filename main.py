from src.extract import extract_geojson
from src.transform import compute_density, compute_distance, compute_priority
from src.load import display_console, generate_pdf

def main():
    # --- Extraction ---
    palmiers, zones, routes = extract_geojson()
    # --- Transformation ---
    zones = compute_density(zones, palmiers)
    zones = compute_distance(zones, routes)
    zones, zone_prioritaire = compute_priority(zones)
    # --- Chargement / Visualisation ---
    display_console(zones, zone_prioritaire)
    # generate_map(zones, palmiers, routes, zone_prioritaire)
    generate_pdf(zones, zone_prioritaire, palmiers, routes)  # PDF avec tableau, graphique et carte

if __name__ == "__main__":
    main()


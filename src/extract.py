import geopandas as gpd
import os

def extract_geojson(data_dir="data/"):
    palmiers = gpd.read_file(os.path.join(data_dir, "palmiers.geojson"))
    zones = gpd.read_file(os.path.join(data_dir, "zones_cultures.geojson"))
    routes = gpd.read_file(os.path.join(data_dir, "highway.geojson"))

    # Forcer toutes les couches en UTM 35S
    target_crs = "EPSG:32735"
    palmiers = palmiers.to_crs(target_crs)
    zones = zones.to_crs(target_crs)
    routes = routes.to_crs(target_crs)

    return palmiers, zones, routes

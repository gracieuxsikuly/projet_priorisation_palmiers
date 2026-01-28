import geopandas as gpd
import os

def extract_geojson(data_dir="../data"):
    """Lecture des fichiers GeoJSON et retour des GeoDataFrames"""
    palmiers = gpd.read_file(os.path.join(data_dir, "palmiers.geojson"))
    zones = gpd.read_file(os.path.join(data_dir, "zones.geojson"))
    routes = gpd.read_file(os.path.join(data_dir, "routes.geojson"))
    return palmiers, zones, routes

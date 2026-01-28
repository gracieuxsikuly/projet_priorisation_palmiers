import geopandas as gpd
import os
import boto3
from io import BytesIO
import json


def _read_geojson(path_or_url):
    """Lecture GeoJSON depuis un chemin local ou une URL"""
    return gpd.read_file(path_or_url)


def extract_geojson(
    source="local",
    data_dir="data/",
    s3_bucket=None,
    s3_prefix=None,
    api_urls=None,
    target_crs="EPSG:32735"
):
    """Extraction des couches géographiques depuis plusieurs sources :
    - local
    - s3
    - api
    """

    if source == "local":
        palmiers = _read_geojson(os.path.join(data_dir, "palmiers.geojson"))
        zones = _read_geojson(os.path.join(data_dir, "zones_cultures.geojson"))
        routes = _read_geojson(os.path.join(data_dir, "highway.geojson"))

    elif source == "s3":
        if not s3_bucket or not s3_prefix:
            raise ValueError("s3_bucket et s3_prefix sont requis pour la source S3")
        palmiers = _read_geojson_from_s3(
            s3_bucket, f"{s3_prefix}/palmiers.geojson"
        )
        zones = _read_geojson_from_s3(
            s3_bucket, f"{s3_prefix}/zones_cultures.geojson"
        )
        routes = _read_geojson_from_s3(
            s3_bucket, f"{s3_prefix}/highway.geojson"
        )

    elif source == "api":
        if not api_urls:
            raise ValueError("api_urls est requis pour la source API")

        palmiers = _read_geojson(api_urls["palmiers"])
        zones = _read_geojson(api_urls["zones"])
        routes = _read_geojson(api_urls["routes"])

    else:
        raise ValueError("Source inconnue : local | s3 | api")

    # Harmonisation CRS
    palmiers = palmiers.to_crs(target_crs)
    zones = zones.to_crs(target_crs)
    routes = routes.to_crs(target_crs)

    return palmiers, zones, routes

def _read_geojson_from_s3(bucket, key):
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    geojson_bytes = response["Body"].read()
    return gpd.read_file(BytesIO(geojson_bytes))

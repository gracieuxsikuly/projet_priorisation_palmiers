import geopandas as gpd
import os
import boto3
from io import BytesIO
from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


def _read_geojson(path_or_url):
    """Lecture GeoJSON depuis un chemin local ou une URL"""
    return gpd.read_file(path_or_url)


def _read_geojson_from_s3(bucket, key):
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    geojson_bytes = response["Body"].read()
    return gpd.read_file(BytesIO(geojson_bytes))


# def _read_postgis(table_name, geom_col="geometry"):
#     """Lecture d'une table PostGIS"""
#     db_user = os.getenv("DB_USER")
#     db_password = os.getenv("DB_PASSWORD")
#     db_host = os.getenv("DB_HOST")
#     db_port = os.getenv("DB_PORT", 5432)
#     db_name = os.getenv("DB_NAME")
#     db_schema = os.getenv("DB_SCHEMA")

#     engine = create_engine(
#         f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
#     )

#     query = f"SELECT * FROM {db_schema}.{table_name}"
#     return gpd.read_postgis(query, engine, geom_col=geom_col)
def _read_postgis_chunked(
    table_name,
    geom_col="geometry",
    chunksize=50_000
):
    """Lecture PostGIS par chunks (simple, robuste)"""

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", 5432)
    db_name = os.getenv("DB_NAME")
    db_schema = os.getenv("DB_SCHEMA")

    engine = create_engine(
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

    query = f"SELECT * FROM {db_schema}.{table_name}"

    chunks = []

    for gdf_chunk in gpd.read_postgis(
        query,
        engine,
        geom_col=geom_col,
        chunksize=chunksize
    ):
        chunks.append(gdf_chunk)

    if not chunks:
        return gpd.GeoDataFrame()

    return gpd.GeoDataFrame(
        pd.concat(chunks, ignore_index=True),
        crs=chunks[0].crs
    )
def extract_geojson(
    source="postgresql",
    data_dir="data/",
    s3_bucket=None,
    s3_prefix=None,
    api_urls=None,
    target_crs="EPSG:32735"
):
    """Extraction des couches géographiques depuis plusieurs sources :
    - postgresql (par défaut)
    - local
    - s3
    - api
    """

    if source == "postgresql":
        palmiers = _read_postgis_chunked("palmiers_valid")
        zones = _read_postgis_chunked("zones_cultures_valid")
        routes = _read_postgis_chunked("highway_valid")

    elif source == "local":
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
        raise ValueError("Source inconnue : postgresql | local | s3 | api")

    # Harmonisation CRS
    palmiers = palmiers.to_crs(target_crs)
    zones = zones.to_crs(target_crs)
    routes = routes.to_crs(target_crs)

    return palmiers, zones, routes

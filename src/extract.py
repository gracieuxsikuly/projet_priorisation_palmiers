import geopandas as gpd
import os
import boto3
from io import BytesIO
from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
import logging
from tqdm import tqdm

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "extract.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
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
    """Lecture PostGIS par chunks avec logs et progress bar"""

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

    logging.info(
        "Début extraction PostGIS | table=%s | chunksize=%s",
        table_name,
        chunksize
    )

    chunks = []
    total_rows = 0

    for gdf_chunk in tqdm(
        gpd.read_postgis(
            query,
            engine,
            geom_col=geom_col,
            chunksize=chunksize
        ),
        desc=f"Lecture {table_name}",
        unit="chunk"
    ):
        chunk_size = len(gdf_chunk)
        total_rows += chunk_size

        logging.info(
            "Chunk lu | table=%s | lignes=%s | total=%s",
            table_name,
            chunk_size,
            total_rows
        )

        chunks.append(gdf_chunk)

    if not chunks:
        logging.warning("Aucune donnée trouvée | table=%s", table_name)
        return gpd.GeoDataFrame()

    logging.info(
        "Fin extraction | table=%s | lignes_totales=%s",
        table_name,
        total_rows
    )

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

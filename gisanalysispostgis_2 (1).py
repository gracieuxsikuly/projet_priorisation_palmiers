#!/usr/bin/env python
"""
Plantation Pipeline v5 — FULLY CHUNKED + FULL POSTGIS
→ Zones now streamed in chunks too (scalable if zones become huge)
"""

import boto3
import geopandas as gpd
import logging
import os
import tempfile
import sys
from io import BytesIO
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import fiona

# ========================= CONFIG =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

BUCKET_NAME = "s3-demos-bis"
METRIC_CRS = "EPSG:32735"
SCHEMA = "gistestbiscf"

# ========================= HELPERS =========================
def s3_to_gdf(key: str) -> gpd.GeoDataFrame:
    """For small files (e.g. roads)"""
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return gpd.read_file(BytesIO(obj["Body"].read()))

def stream_geojson_s3(key: str, chunk_size: int = 4000):
    """Memory-safe streaming for large GeoJSON files"""
    s3 = boto3.client("s3")
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        s3.download_fileobj(Bucket=BUCKET_NAME, Key=key, Fileobj=tmp)
        tmp_path = tmp.name

    try:
        with fiona.open(tmp_path) as src:
            chunk = []
            for i, feature in enumerate(src, 1):
                chunk.append(feature)
                if len(chunk) == chunk_size:
                    yield gpd.GeoDataFrame.from_features(chunk, crs=src.crs)
                    chunk = []
            if chunk:
                yield gpd.GeoDataFrame.from_features(chunk, crs=src.crs)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ========================= MAIN =========================
def main():
    logger.info("STARTING FULLY CHUNKED POSTGIS PIPELINE")

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA};"))

    # ====================== 1. ROADS (small) ======================
    logger.info("Loading ROADS...")
    roads = s3_to_gdf("raw/routes.geojson")
    roads = roads.to_crs(METRIC_CRS)
    roads.columns = roads.columns.str.lower()
    roads.to_postgis("routes", engine, schema=SCHEMA, if_exists="replace", index=False)
    logger.info(f"Roads loaded ({len(roads)} rows)")

    # ====================== 2. ZONES — Chunked ======================
    logger.info("Loading ZONES in chunks...")
    total_zones = 0
    first_zone = True

    for chunk in stream_geojson_s3("raw/zones.geojson", chunk_size=1000):   # Smaller chunk for zones
        chunk.columns = chunk.columns.str.lower()

        # Keep only needed columns
        if 'designation' in chunk.columns:
            chunk = chunk[["designation", "geometry"]]

        chunk = chunk.to_crs(METRIC_CRS)

        chunk.to_postgis(
            "zones",
            engine,
            schema=SCHEMA,
            if_exists="replace" if first_zone else "append",
            index=False
        )

        total_zones += len(chunk)
        first_zone = False
        logger.info(f"   → Zones chunk inserted | Total zones: {total_zones:,}")

    logger.info(f"All zones loaded ({total_zones:,} rows)")

    # ====================== 3. PLANTATIONS — Chunked ======================
    logger.info("Loading PLANTATIONS in chunks...")
    total_plants = 0
    first = True

    for chunk in stream_geojson_s3("raw/palmerains.geojson", chunk_size=4000):
        chunk.columns = chunk.columns.str.lower()
        chunk = chunk.drop_duplicates(subset=["id_contact_copie", "coordx_copie", "coordy_copie"])

        if 'geometry' not in chunk.columns:
            chunk['geometry'] = gpd.points_from_xy(chunk['coordx_copie'], chunk['coordy_copie'])
            chunk = gpd.GeoDataFrame(chunk, crs="EPSG:4326")

        chunk = chunk.to_crs(METRIC_CRS)
        chunk.to_postgis(
            "plantations",
            engine,
            schema=SCHEMA,
            if_exists="replace" if first else "append",
            index=False
        )

        total_plants += len(chunk)
        first = False
        logger.info(f"   → Plantations chunk inserted | Total: {total_plants:,}")

    # ====================== 4. Indexes + Vacuum ======================
    logger.info("Creating Spatial Indexes...")
    with engine.begin() as conn:
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_plant_geom  ON {SCHEMA}.plantations USING GIST (geometry);"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_routes_geom ON {SCHEMA}.routes USING GIST (geometry);"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_zones_geom  ON {SCHEMA}.zones USING GIST (geometry);"))

    logger.info("   → Running VACUUM ANALYZE...")
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text(f"VACUUM ANALYZE {SCHEMA}.plantations;"))
        conn.execute(text(f"VACUUM ANALYZE {SCHEMA}.routes;"))
        conn.execute(text(f"VACUUM ANALYZE {SCHEMA}.zones;"))
    logger.info("Database optimized")

    # ====================== 5. Distance Calculation (SQL) ======================

    logger.info("⚙️ Calculating distance_to_road_km using KNN...")
    with engine.begin() as conn:
        conn.execute(text(f"""
            ALTER TABLE {SCHEMA}.plantations 
                ADD COLUMN IF NOT EXISTS distance_to_road_km FLOAT;

            UPDATE {SCHEMA}.plantations p
            SET distance_to_road_km = (
                SELECT ST_Distance(p.geometry, r.geometry) / 1000.0
                FROM {SCHEMA}.routes r
                ORDER BY p.geometry <-> r.geometry
                LIMIT 1
            );
        """))
    logger.info("Distance calculation done")

    # 7. Zone Analysis
    logger.info("Running Zone Analysis...")
    query = text(f"""
        WITH stats AS (
            SELECT 
                z.designation,
                z.geometry,
                COUNT(p.fid) AS point_count,
                AVG(p.distance_to_road_km) AS mean_dist_road_km,
                ST_Area(z.geometry) / 1000000.0 AS area_km2
            FROM {SCHEMA}.zones z
            LEFT JOIN {SCHEMA}.plantations p ON ST_Intersects(z.geometry, p.geometry)
            GROUP BY z.designation, z.geometry
        )
        SELECT 
            designation,
            point_count,
            area_km2,
            (point_count / NULLIF(area_km2, 0)) AS density_km2,
            mean_dist_road_km,
            (point_count / NULLIF(area_km2, 0)) + (1.0 / NULLIF(mean_dist_road_km, 0)) AS priority_score,
            geometry
        FROM stats
        ORDER BY priority_score DESC;
    """)

    results = gpd.read_postgis(query, engine, geom_col="geometry")
    results.to_postgis("zones_analysis", engine, schema=SCHEMA, if_exists="replace", index=False)

    # Final Output
    print("\n" + "="*60)
    print("TOP 10 PRIORITY ZONES")
    print("="*60)
    print(results.head(10)[["designation","point_count","density_km2","mean_dist_road_km","priority_score"]].round(4).to_string(index=False))
    print("="*60)

    logger.info("PIPELINE FINISHED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python
"""
Plantation Pipeline v6 — SQL ONLY (PostGIS Driven)
→ No S3, no GeoJSON, no Python spatial processing
"""

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import geopandas as gpd

# ========================= CONFIG =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

SCHEMA = os.getenv("DB_SCHEMA")

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# ========================= MAIN =========================
def main():
    logger.info("STARTING SQL-ONLY POSTGIS PIPELINE")
    # ====================== 1. Spatial Indexes ======================
    logger.info("Ensuring spatial indexes...")
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_highway_valid_geom
                ON {SCHEMA}.highway_valid USING GIST (geometry);

            CREATE INDEX IF NOT EXISTS idx_zones_cultures_valid_geom
                ON {SCHEMA}.zones_cultures_valid USING GIST (geometry);

            CREATE INDEX IF NOT EXISTS idx_palmiers_valid_geom
                ON {SCHEMA}.palmiers_valid USING GIST (geometry);
        """))

    # ====================== 3. Distance to road (KNN) ======================
    logger.info("📏 Computing distance_to_road_km...")
    with engine.begin() as conn:
        conn.execute(text(f"""
            ALTER TABLE {SCHEMA}.palmiers_valid
                ADD COLUMN IF NOT EXISTS distance_to_road_km FLOAT;

            UPDATE {SCHEMA}.palmiers_valid p
            SET distance_to_road_km = (
                SELECT ST_Distance(p.geometry, r.geometry) / 1000.0
                FROM {SCHEMA}.highway_valid r
                ORDER BY p.geometry <-> r.geometry
                LIMIT 1
            );
        """))
    # ====================== 4. Zone analysis ======================
    logger.info("Running zone prioritization analysis...")
    zone_analysis_query = text(f"""
                DROP TABLE IF EXISTS {SCHEMA}.zoneculture_analysis;
                CREATE TABLE {SCHEMA}.zoneculture_analysis AS
                WITH stats AS (
                    SELECT
                    z.designation,
                    z.geometry,
                    -- 1️ Nombre de palmiers dans la zone
                    COUNT(p.*) AS nb_palmiers,
                    -- 2️ Distance minimale centroïde → route (KNN veut dire K-Nearest Neighbors (en français : les K plus proches voisins). propre)
                    (
                        SELECT
                            ST_Distance(
                                ST_Centroid(z.geometry),
                                r.geometry
                            )
                        FROM {SCHEMA}.highway_valid r
                        ORDER BY ST_Centroid(z.geometry) <-> r.geometry
                        LIMIT 1
                    ) AS dist_route_min
                FROM {SCHEMA}.zones_cultures_valid z
                LEFT JOIN {SCHEMA}.palmiers_valid p
                    ON ST_Within(p.geometry, z.geometry)
                GROUP BY
                    z.designation,
                    z.geometry
            )
            SELECT
                designation,
                nb_palmiers,
                dist_route_min,
                -- 3️ Score de priorité 
                nb_palmiers / (dist_route_min + 1e-6) AS priority_score,
                geometry
            FROM stats;
            """)
    with engine.begin() as conn:
        conn.execute(zone_analysis_query)

    # ====================== 5. Read Top 10 ======================
    results = gpd.read_postgis(
    f"""
    SELECT
        designation,
        nb_palmiers,
        dist_route_min,
        priority_score,
        geometry
    FROM {SCHEMA}.zoneculture_analysis
    ORDER BY
        CASE
            WHEN COALESCE(priority_score, 0) = 0 THEN 1
            ELSE 0
        END,
        priority_score DESC
    LIMIT 10;
    """,
    engine,
    geom_col="geometry"
)
    print("\n" + "=" * 60)
    print("🏆 TOP 10 PRIORITY ZONES")
    print("=" * 60)

    print(
        results[
            ["designation", "nb_palmiers", "dist_route_min", "priority_score"]
        ]
        .round(4)
        .to_string(index=False)
    )

    print("=" * 60)

    logger.info("🎉 SQL-ONLY PIPELINE FINISHED SUCCESSFULLY")

# ========================= RUN =========================
if __name__ == "__main__":
    main()

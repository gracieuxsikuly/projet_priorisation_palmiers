#!/usr/bin/env python
"""
Plantation Pipeline v8 — SQL ONLY + PDF Reporting Pro
"""

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Patch
from matplotlib import colors
import matplotlib.colors as mcolors
import contextily as ctx
import boto3

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

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)
PDF_PATH = os.path.join(REPORTS_DIR, "rapport_priorite_zones.pdf")
def upload_pdf_to_s3(pdf_path: str):
    """
    Upload un fichier PDF sur S3.
    
    - pdf_path: chemin local du PDF (ex: "rapport_priorite_zones.pdf")
    - BUCKET_NAME est récupéré depuis les variables d'environnement
    - S3_PREFIX est 'outputs/carte/'
    """
    s3_bucket = os.getenv("BUCKET_NAME")
    if not s3_bucket:
        raise ValueError("La variable d'environnement BUCKET_NAME n'est pas définie.")
    
    s3_prefix = "outputs/carte/"
    s3_key = f"{s3_prefix}{os.path.basename(pdf_path)}"

    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(pdf_path, s3_bucket, s3_key)
        logger.info(f" PDF uploaded to s3://{s3_bucket}/{s3_key}")
    except Exception as e:
        logger.error(f" Échec de l'upload PDF: {e}")
        raise
# ========================= PDF GENERATION =========================
def generate_pdf(top_zones: gpd.GeoDataFrame):
    logger.info("Generating PDF report...")

    # Fonction couleur
    max_score = top_zones["priority_score"].max()
    def score_color(val):
        norm = colors.Normalize(vmin=0, vmax=max_score)
        cmap = plt.cm.RdYlGn_r
        rgba = cmap(norm(val))
        return mcolors.to_hex(rgba)

    # Génération PDF
    with PdfPages(PDF_PATH) as pdf:
        # --- Page 1 ---
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        fig.subplots_adjust(top=0.95, bottom=0.05)
        ax.text(0.5, 0.92, "Rapport de Priorité des Zones de Plantation",
                ha="center", va="top", fontsize=16, weight="bold")
        explanation_text = (
            "Ce rapport présente l'analyse des zones de plantation de palmiers.\n"
            "La zone la plus prioritaire est sélectionnée sur la base du score de priorité, "
            "calculé comme le nombre de palmiers divisé par la distance minimale à la route.\n\n"
            "Le tableau ci-dessous montre les 10 zones les plus prioritaires."
        )
        ax.text(0.5, 0.85, explanation_text, ha="center", va="top", fontsize=10, wrap=True)
        table_data = top_zones[["designation","nb_palmiers","dist_route_min","priority_score"]].round(4)
        cell_colors = [[score_color(val)]*4 for val in table_data["priority_score"]]
        table = ax.table(cellText=table_data.values, colLabels=table_data.columns,
                         cellColours=cell_colors, loc="center", cellLoc="center", colLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        pdf.savefig(fig)
        plt.close()

        # --- Page 2 ---
        fig, axs = plt.subplots(1, 2, figsize=(8.27, 11.69))
        ax_bar = axs[0]
        top_zones.plot.bar(x="designation", y="priority_score", ax=ax_bar, color="forestgreen", legend=False)
        ax_bar.set_title("Scores de Priorité", fontsize=12)
        ax_bar.set_ylabel("Priority Score", fontsize=10)
        ax_bar.set_xlabel("Zone", fontsize=10)
        ax_bar.tick_params(axis='x', rotation=45, labelsize=9)
        ax_bar.tick_params(axis='y', labelsize=9)

        ax_map = axs[1]
        top_zones_3857 = top_zones.to_crs(epsg=3857)
        top_zones_3857.plot(ax=ax_map, color="green", alpha=0.3)
        top_zones_3857.boundary.plot(ax=ax_map, color="darkgreen", linewidth=1)
        ctx.add_basemap(ax_map, source=ctx.providers.OpenStreetMap.Mapnik)
        ax_map.set_title("Carte des Zones", fontsize=12)
        ax_map.axis("off")
        legend_elements = [
            Patch(facecolor="green", alpha=0.3, label="Zone prioritaire"),
            Patch(edgecolor="darkgreen", facecolor="none", linewidth=1, label="Limite zone")
        ]
        ax_map.legend(handles=legend_elements, loc="lower left", fontsize=8)
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close()
    upload_pdf_to_s3(PDF_PATH)
    logger.info(f"PDF report saved locally at {PDF_PATH} and uploaded to S3.")

# ========================= MAIN =========================
def main():
    logger.info("STARTING SQL-ONLY POSTGIS PIPELINE")

    # --- spatial indexes ---
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_highway_valid_geom
                ON {SCHEMA}.highway_valid USING GIST (geometry);
            CREATE INDEX IF NOT EXISTS idx_zones_cultures_valid_geom
                ON {SCHEMA}.zones_cultures_valid USING GIST (geometry);
            CREATE INDEX IF NOT EXISTS idx_palmiers_valid_geom
                ON {SCHEMA}.palmiers_valid USING GIST (geometry);
        """))

    # --- distance to road ---
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

    # --- zone analysis ---
    zone_analysis_query = text(f"""
        DROP TABLE IF EXISTS {SCHEMA}.zoneculture_analysis;
        CREATE TABLE {SCHEMA}.zoneculture_analysis AS
        WITH stats AS (
            SELECT
                z.designation,
                z.geometry,
                COUNT(p.*) AS nb_palmiers,
                (
                    SELECT ST_Distance(ST_Centroid(z.geometry), r.geometry)
                    FROM {SCHEMA}.highway_valid r
                    ORDER BY ST_Centroid(z.geometry) <-> r.geometry
                    LIMIT 1
                ) AS dist_route_min
            FROM {SCHEMA}.zones_cultures_valid z
            LEFT JOIN {SCHEMA}.palmiers_valid p
            ON ST_Within(p.geometry, z.geometry)
            GROUP BY z.designation, z.geometry
        )
        SELECT
            designation,
            nb_palmiers,
            dist_route_min,
            nb_palmiers / (dist_route_min + 1e-6) AS priority_score,
            geometry
        FROM stats;
    """)
    with engine.begin() as conn:
        conn.execute(zone_analysis_query)

    # --- read top 10 ---
    top_zones = gpd.read_postgis(
        f"""
        SELECT *
        FROM {SCHEMA}.zoneculture_analysis
        ORDER BY
            CASE WHEN COALESCE(priority_score,0)=0 THEN 1 ELSE 0 END,
            priority_score DESC
        LIMIT 10
        """,
        engine,
        geom_col="geometry"
    )

  
    # --- print console ---
    print("\n" + "="*60)
    print("TOP 10 PRIORITY ZONES")
    print("="*60)
    print(top_zones[["designation","nb_palmiers","dist_route_min","priority_score"]].round(4).to_string(index=False))
    print("="*60)

    # --- generate PDF ---
    generate_pdf(top_zones)

    logger.info("SQL + PDF Pipeline finished successfully")

# ========================= RUN =========================
if __name__ == "__main__":
    main()

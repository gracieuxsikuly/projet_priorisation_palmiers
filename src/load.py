import matplotlib.pyplot as plt
import geopandas as gpd
from tabulate import tabulate
import pdfkit
import os
import base64
from io import BytesIO
import seaborn as sns

def display_console(zones, zone_prioritaire):
    """Affichage des résultats dans la console"""
    print("\n=== Densité de palmiers par zone ===")
    print(tabulate(zones[["nb_palmiers", "dist_route_min", "score_priorite"]], headers="keys"))
    print("\n=== Zone prioritaire ===")
    print(zone_prioritaire[["nb_palmiers", "dist_route_min", "score_priorite"]])

def generate_map(zones, palmiers, routes, zone_prioritaire):
    """Affichage de la carte à l'écran"""
    fig, ax = plt.subplots(figsize=(12, 12))
    zones.plot(ax=ax, color="lightgrey", edgecolor="black")
    palmiers.plot(ax=ax, color="green", markersize=5, label="Palmiers")
    routes.plot(ax=ax, color="red", linewidth=2, label="Routes")
    gpd.GeoSeries([zone_prioritaire.geometry]).plot(ax=ax, color="yellow", alpha=0.5, label="Zone prioritaire")
    plt.legend()
    plt.title("Carte des zones avec palmiers et routes")
    plt.show()

def generate_density_chart(zones):
    """Création d'un graphique de densité des palmiers par zone et retour en base64"""
    plt.figure(figsize=(10,6))
    sns.barplot(x=zones.index, y=zones["nb_palmiers"], palette="viridis")
    plt.xlabel("Zone")
    plt.ylabel("Nombre de palmiers")
    plt.title("Densité de palmiers par zone")
    plt.xticks(rotation=45)
    
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return img_base64

def generate_map_pdf(zones, palmiers, routes, zone_prioritaire):
    """Création d'une carte pour le PDF et retour en base64"""
    fig, ax = plt.subplots(figsize=(12,12))
    zones.plot(ax=ax, color="lightgrey", edgecolor="black")
    palmiers.plot(ax=ax, color="green", markersize=5, label="Palmiers")
    routes.plot(ax=ax, color="red", linewidth=2, label="Routes")
    gpd.GeoSeries([zone_prioritaire.geometry]).plot(ax=ax, color="yellow", alpha=0.5, label="Zone prioritaire")
    plt.legend()
    plt.title("Carte des zones avec palmiers et routes")
    
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return img_base64

def generate_pdf(zones, zone_prioritaire, palmiers, routes, pdf_path="../reports/rapport_final.pdf"):
    """Création d'un PDF complet avec tableau, graphique, carte et explication"""
    # Tableau HTML
    tableau_html = zones[["nb_palmiers", "dist_route_min", "score_priorite"]].to_html(classes="table", border=1, float_format="%.2f")
    
    # Graphique densité
    chart_base64 = generate_density_chart(zones)

    # Carte intégrée
    map_base64 = generate_map_pdf(zones, palmiers, routes, zone_prioritaire)

    # Explication automatique
    explanation = (
        f"La zone prioritaire est la zone {zone_prioritaire.name} avec "
        f"{zone_prioritaire['nb_palmiers']:.0f} palmiers et une distance minimale à la route de "
        f"{zone_prioritaire['dist_route_min']:.2f} unités. "
        f"Elle présente le score de priorité le plus élevé ({zone_prioritaire['score_priorite']:.2f}), "
        f"ce qui en fait la zone la plus favorable pour la culture de palmiers."
    )

    # Contenu HTML complet
    html = f"""
    <html>
    <head>
        <style>
            h1 {{ text-align: center; }}
            .table {{ width: 100%; border-collapse: collapse; }}
            .table th, .table td {{ border: 1px solid black; padding: 5px; text-align: center; }}
            img {{ display: block; margin-left: auto; margin-right: auto; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h1>Rapport de priorisation des zones de culture de palmiers</h1>
        <h2>Zone prioritaire</h2>
        <p>{explanation}</p>
        <h2>Carte des zones avec palmiers et routes</h2>
        <img src="data:image/png;base64,{map_base64}" width="600">
        <h2>Tableau de synthèse des zones</h2>
        {tableau_html}
        <h2>Graphique de densité des palmiers</h2>
        <img src="data:image/png;base64,{chart_base64}" width="600">
    </body>
    </html>
    """

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    pdfkit.from_string(html, pdf_path)
    print(f"\nRapport PDF complet avec carte généré : {pdf_path}")

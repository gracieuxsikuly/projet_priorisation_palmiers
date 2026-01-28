import matplotlib.pyplot as plt
import geopandas as gpd
from tabulate import tabulate
import os
import base64
from io import BytesIO
import seaborn as sns
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


def display_console(zones, zone_prioritaire):
    """Affichage des résultats dans la console"""
    print("\n=== Densité de palmiers par zone ===")
    print("\n=== TOP 10 DES ZONES PRIORITAIRES ===")
    top_10 = (
        zones[["designation", "nb_palmiers", "dist_route_min", "score_priorite"]]
        .sort_values("score_priorite", ascending=False)
        .head(10)
    )
    print(
        tabulate(
            top_10,
            headers=["Zone", "Nb palmiers", "Distance route (m)", "Score priorité"],
            tablefmt="grid",
            floatfmt=".3f"
        )
    )
    print("\n===TOP 1 ZONE PRIORITAIRE ===")
    zone_prioritaire_df = (
        zones[["designation", "nb_palmiers", "dist_route_min", "score_priorite"]]
        .sort_values("score_priorite", ascending=False)
        .head(1)
    )
    print(
        tabulate(
            zone_prioritaire_df,
            headers=["Zone", "Nb palmiers", "Distance route (m)", "Score priorité"],
            tablefmt="grid",
            floatfmt=".3f"
        )
    )
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
    plt.figure(figsize=(12,6))
    
    # Barplot avec noms de zones en x
    sns.barplot(x="designation", y="nb_palmiers", data=zones.sort_values("score_priorite", ascending=False), palette="viridis")
    
    plt.xlabel("Zone")
    plt.ylabel("Nombre de palmiers")
    plt.title("Densité de palmiers par zone")
    plt.xticks(rotation=45, ha='right') 
    
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


def generate_pdf(zones, zone_prioritaire, palmiers, routes, pdf_path="reports/rapport_final.pdf"):
    """Création d'un PDF complet avec tableau, graphique, carte et explication avec reportlab"""
    # Génération des images base64
    chart_base64 = generate_density_chart(zones)    
    map_base64 = generate_map_pdf(zones, palmiers, routes, zone_prioritaire)  
    
    # Création du PDF
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titre
    elements.append(Paragraph("Rapport de priorisation des zones de culture de palmiers", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Explication zone prioritaire
    explanation = (
        f"La zone prioritaire est la zone <b>{zone_prioritaire['designation']}</b> avec "
        f"{zone_prioritaire['nb_palmiers']:.0f} palmiers et une distance minimale à la route de "
        f"{zone_prioritaire['dist_route_min']:.2f} m. "
        f"Elle présente le score de priorité le plus élevé ({zone_prioritaire['score_priorite']:.3f}), "
        f"ce qui en fait la zone la plus favorable pour la culture de palmiers."
    )
    elements.append(Paragraph(explanation, styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Carte
    map_bytes = BytesIO(base64.b64decode(map_base64))
    elements.append(Image(map_bytes, width=450, height=450))
    elements.append(Spacer(1, 12))
    
    # Tableau top 10 zones prioritaires
    top10 = zones.sort_values("score_priorite", ascending=False).head(10)
    table_data = [["Zone", "Nb palmiers", "Distance route (m)", "Score priorité"]]
    for _, row in top10.iterrows():
        table_data.append([
            row["designation"],
            f"{row['nb_palmiers']:.0f}",
            f"{row['dist_route_min']:.2f}",
            f"{row['score_priorite']:.3f}"
        ])
    
    t = Table(table_data, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#cccccc")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f2f2")])
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # Graphique densité des palmiers
    chart_bytes = BytesIO(base64.b64decode(chart_base64))
    elements.append(Image(chart_bytes, width=450, height=300))
    
    # Génération PDF
    doc.build(elements)
    print(f"\nRapport PDF complet généré : {pdf_path}")


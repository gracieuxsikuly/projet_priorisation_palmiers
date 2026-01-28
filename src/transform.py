import geopandas as gpd

def compute_density(zones, palmiers):
    """Calcul de la densité de palmiers par zone"""
    palmiers_in_zones = gpd.sjoin(palmiers, zones, how="inner", predicate="within")
    densite_par_zone = (
        palmiers_in_zones.groupby("index_right")
        .size()
        .reset_index(name="nb_palmiers")
    )
    zones["nb_palmiers"] = zones.index.map(
        dict(zip(densite_par_zone["index_right"], densite_par_zone["nb_palmiers"]))
    )
    zones["nb_palmiers"] = zones["nb_palmiers"].fillna(0)
    return zones
def compute_distance(zones, routes):
    """
    Calcul de la distance minimale entre le centroïde de chaque zone
    et les routes (en mètres, CRS UTM 35S).
    """
    zones["dist_route_min"] = zones.geometry.centroid.apply(
        lambda c: routes.distance(c).min()
    )
    return zones
def compute_priority(zones):
    """Calcul du score de priorité pour chaque zone et identification de la zone prioritaire.
    Logique :
    - Le score de priorité est défini comme : 
        score_priorite = nb_palmiers / dist_route_min
      Ce qui signifie que :
        • Plus une zone contient de palmiers (nb_palmiers élevé), plus son score augmente.
        • Plus une zone est proche des routes (dist_route_min faible), plus son score augmente.
      Ainsi, une zone dense en palmiers et proche des routes sera considérée comme prioritaire.
    - 1e-6 ajouté dans le dénominateur pour éviter la division par zéro :
        • Si une zone touche exactement une route, dist_route_min pourrait être 0.
        • Diviser par zéro provoquerait une erreur.
        • En ajoutant 1e-6 (0.000001), on garantit que le calcul ne plante pas,
          sans modifier significativement le score pour les distances non nulles.

    Retour :
    - zones : GeoDataFrame avec une nouvelle colonne 'score_priorite'.
    - zone_prioritaire : ligne (GeoSeries) correspondant à la zone avec le score le plus élevé.
    """
    zones["score_priorite"] = zones["nb_palmiers"] / (zones["dist_route_min"] + 1e-6)
    zone_prioritaire = zones.sort_values("score_priorite", ascending=False).iloc[0]

    return zones, zone_prioritaire


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
    """Calcul de la distance minimale de chaque zone à une route"""
    zones["dist_route_min"] = zones.geometry.apply(lambda z: routes.distance(z).min())
    return zones

def compute_priority(zones):
    """Calcul du score de priorité et identification de la zone prioritaire"""
    zones["score_priorite"] = zones["nb_palmiers"] / (zones["dist_route_min"] + 1e-6)
    zone_prioritaire = zones.sort_values("score_priorite", ascending=False).iloc[0]
    return zones, zone_prioritaire

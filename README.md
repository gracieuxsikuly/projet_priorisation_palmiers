# ETL SIG de Priorisation des Palmiers
## 📖 Description du projet
Ce projet est un **ETL (Extract, Transform, Load) géospatial** conçu pour **analyser et prioriser les zones contenant des palmiers**. Il utilise des couches spatiales (`palmiers`, `routes`, `zones`) pour générer un **score de priorité** pour chaque zone, afin de faciliter la planification et la gestion des interventions.
**Logique principale :**
* Les zones avec **plus de palmiers** et **proches des routes** sont considérées comme prioritaires.
* Le score de priorité est calculé comme suit :


$$
score\_priorite = \frac{nb\_palmiers}{dist\_route\_min + 10^{-6}}
$$



* `1e-6` est ajouté pour éviter une division par zéro si une zone touche une route.
---
## 🛠️ Technologies utilisées
* **Python 3**
* **Bibliothèques géospatiales et d’analyse :**
  * `geopandas`, `shapely`, `pyproj`, `geoalchemy2`
* **Analyse de données et visualisation :**
  * `pandas`, `matplotlib`, `seaborn`, `tabulate`
* **Base de données et API :**
  * `sqlalchemy`, `psycopg2-binary`, `requests`, `boto3`
* **Gestion des environnements :**
  * `python-dotenv`
* **Rapports :**
  * `jinja2`, `reportlab`
---
## 📂 Structure du projet
```
projet_priorisation_palmiers/
│
├─ src/                      # Code source ETL
│   ├─ extract.py             # Extraction des données
│   ├─ transform.py           # Transformation et calcul des scores
│   ├─ load.py                # Chargement des résultats et génération de rapports
│   └─ __init__.py
│
├─ data/                     # Couches géospatiales (palmiers, routes, zones)
├─ rapports/                 # Rapports générés
├─ main.py                   # Point d'entrée pour exécuter l'ETL
├─ requirements.txt          # Dépendances Python
└─ README.md                 # Documentation du projet
```
---
## ⚡ Installation
1. **Créer un environnement virtuel :**
```powershell
py -m venv env
```
2. **Définir la politique d’exécution (Windows PowerShell) :**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
3. **Activer l’environnement :**
```powershell
env\Scripts\activate.ps1
```
4. **Installer les dépendances :**
```powershell
pip install -r requirements.txt
```
---
## 🧩 Fonctionnement de l’ETL
1. **Extract**
   * Les fichiers des couches (`palmiers`, `routes`, `zones`) sont chargés depuis le dossier `data/`.
2. **Transform**
   * Les données sont transformées et enrichies :
     * Calcul du **nombre de palmiers par zone**
     * Calcul de la **distance minimale entre chaque zone et la route la plus proche**
     * Calcul du **score de priorité** avec la fonction :
```python
def compute_priority(zones):
    zones["score_priorite"] = zones["nb_palmiers"] / (zones["dist_route_min"] + 1e-6)
    zone_prioritaire = zones.sort_values("score_priorite", ascending=False).iloc[0]
    return zones, zone_prioritaire
```
3. **Load**
   * Les résultats sont exportés dans le dossier `rapports/` sous forme de fichiers Excel ou PDF.
   * Des visualisations et rapports cartographiques peuvent être générés.
---
## 🚀 Exécution
Pour lancer l’ETL, utiliser le script principal `main.py` :
```bash
python main.py
```
* Les rapports et résultats seront générés automatiquement dans le dossier `rapports/`.
---
## 🧪 Tests
Les tests unitaires et d’intégration peuvent être ajoutés dans un futur dossier `tests/`.
Ils permettront de vérifier :
* Le calcul correct des distances
* La bonne attribution du nombre de palmiers par zone
* La génération correcte du score de priorité
---
## 👤 Auteur

**Gracieux Sikuly|graciersikuly@gmail.com** – Développeur du projet ETL SIG de priorisation des palmiers

## 🤝 Contributions
Les contributions sont les bienvenues !
Merci de soumettre vos **issues** ou **pull requests** pour améliorer le projet.
---
## 📄 Licence
Ce projet est sous licence **MIT**.

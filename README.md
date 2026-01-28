# creation de la varibale d'environnement
py -m venv env
# ExecutionPolicy Bypass
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# activation de la variable d'environnement
env\Scripts\activate.ps1
# installation de dependendace
pip install -r requirements.txt
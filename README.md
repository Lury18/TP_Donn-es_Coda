# PMD — Jour 1 : Fondations (environnement & NumPy)

Projet du module **Préparation et Manipulation de Données** (M1), séance 1 :
mise en place d'un environnement Python reproductible et manipulation de
tableaux NumPy (slicing, masques booléens, statistiques par axe,
vectorisation). Le notebook `01_environnement_numpy.ipynb` contient le TP
complété (ateliers 1.1 à 1.3).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab
```

## Données

Le dossier `data/raw/` (exclu du dépôt via `.gitignore`) contient les données
brutes en lecture seule ; toute transformation est écrite dans
`data/processed/`, jamais dans `data/raw/`.

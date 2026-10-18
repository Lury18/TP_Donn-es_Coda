# PMD — Notebooks de séance (environnement, pandas, nettoyage, transformation)

Projets du module **Préparation et Manipulation de Données** (M1) :

- **Séance 1 — Fondations** (`01_environnement_numpy.ipynb`) : mise en place d'un
  environnement Python reproductible et manipulation de tableaux NumPy (slicing,
  masques booléens, statistiques par axe, vectorisation).
- **Séance 2 — Exploration pandas** (`02_pandas_exploration.ipynb`) : lecture de
  sources multiples (CSV/Excel/JSON), sélection et filtrage avec `loc`/`iloc`, et
  écriture de la fonction réutilisable `profile_dataframe` (`src/exploration.py`).
- **Séance 3 — Nettoyage et qualité** (`03_nettoyage_qualite.ipynb`) : typologie
  des valeurs manquantes, détection des valeurs aberrantes (IQR vs score z),
  normalisation de texte et écriture de la fonction idempotente `clean_sales`
  (`src/cleaning.py`).
- **Séance 4 — Transformation et encodage** (`04_transformation_encodage.ipynb`) :
  mise à l'échelle (min-max, z-score), fuite de données, encodage one-hot avec
  regroupement des modalités rares, variables dérivées, et fonction
  `prepare_features` (`src/transformation.py`).

## Structure du dépôt

- `src/` : code réutilisable (`exploration.py`, `cleaning.py`, `transformation.py`).
- `data/processed/` : jeux produits par les notebooks (`ventes_nettoyees.parquet`,
  `journal_nettoyage.json`, `ventes_transformees.parquet`).
- `requirements.txt` : dépendances figées.

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
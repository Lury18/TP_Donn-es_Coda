import pandas as pd


def parse_price(series):
    """Convertit une colonne de prix mixte (nombre ou texte '123,45 EUR') en float."""
    text = series.astype(str).str.replace(' EUR', '', regex=False)
    return pd.to_numeric(text.str.replace(',', '.', regex=False).str.strip(),
                         errors='coerce')


def normalize_text(series):
    """Casse, espaces et accents : trois sources de faux niveaux."""
    text = series.astype(str).str.strip().str.lower()
    text = text.str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('utf-8')
    return text.str.replace(r'\s+', ' ', regex=True)


TEXT_COLUMNS = ['canal', 'statut', 'ville_livraison']          # descriptives uniquement
KEY_COLUMNS = ['id_commande', 'id_client', 'id_produit', 'id_magasin']  # à préserver


def clean_sales(df, drop_negative_quantities=True, max_quantity=None, verbose=True):
    """Nettoie le jeu de ventes et renvoie (df_propre, log).

    Étapes attendues, dans cet ordre :
      1. copier le DataFrame reçu (ne jamais modifier l'entrée) ;
      2. convertir prix_unitaire en numérique ;
      3. normaliser les colonnes texte DESCRIPTIVES (jamais les identifiants) ;
      4. supprimer les doublons stricts ;
      5. convertir date_commande en datetime et supprimer les lignes sans date ;
      6. appliquer la stratégie retenue pour remise_pct ;
      7. traiter les quantités selon les paramètres ;
      8. calculer la colonne montant.

    Le log recense, pour chaque étape, le nombre de lignes ou de valeurs touchées.
    """
    log = {'lignes_initiales': len(df)}
    df = df.copy()

    df['prix_unitaire'] = parse_price(df['prix_unitaire'])

    for column in TEXT_COLUMNS:
        df[column] = normalize_text(df[column])

    n_before = len(df)
    df = df.drop_duplicates()
    log['doublons_stricts_supprimes'] = n_before - len(df)

    df['date_commande'] = pd.to_datetime(df['date_commande'], format='mixed', dayfirst=True, errors='coerce')
    n_before = len(df)
    df = df[df['date_commande'].notna()]
    log['lignes_sans_date_supprimees'] = n_before - len(df)

    n_filled = df['remise_pct'].isna().sum()
    df['remise_pct'] = df['remise_pct'].fillna(0)
    log['remise_pct_imputee_zero'] = int(n_filled)

    if drop_negative_quantities:
        n_before = len(df)
        df = df[df['quantite'] >= 0]
        log['quantites_negatives_supprimees'] = n_before - len(df)
    else:
        log['quantites_negatives_supprimees'] = 0

    if max_quantity is not None:
        n_before = len(df)
        df = df[df['quantite'] <= max_quantity]
        log['quantites_hors_plafond_supprimees'] = n_before - len(df)
    else:
        log['quantites_hors_plafond_supprimees'] = 0

    df['montant'] = df['quantite'] * df['prix_unitaire'] * (1 - df['remise_pct'] / 100)

    log['lignes_finales'] = len(df)
    if verbose:
        for key, value in log.items():
            print(f'  {key:<28} {value}')
    return df, log
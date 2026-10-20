import pandas as pd


def scale_minmax(series):
    """Ramène la série dans [0 ; 1] : (x - min) / (max - min)."""
    return (series - series.min()) / (series.max() - series.min())


def scale_zscore(series):
    """Centre sur la moyenne et réduit par l'écart type : (x - moyenne) / écart type."""
    return (series - series.mean()) / series.std()


def group_rare_categories(series, min_frequency=0.01, other_label='autre'):
    """Regroupe sous un même libellé les modalités dont la fréquence est trop faible."""
    frequencies = series.value_counts(normalize=True)
    rare_labels = frequencies[frequencies < min_frequency].index
    return series.where(~series.isin(rare_labels), other_label)


def prepare_features(df, products):
    """Jointure produits, variables dérivées, encodage one-hot, mise à l'échelle.

    Copie l'entrée et renvoie un nouveau DataFrame. Les paramètres de la mise à
    l'échelle sont calculés sur les données reçues : pour un modèle, les apprendre
    sur l'entraînement seulement et les réappliquer au test.
    """
    df = df.copy()

    df = df.merge(products, on='id_produit', how='left')

    df['montant_apres_remise'] = df['quantite'] * df['prix_unitaire'] * (1 - df['remise_pct'].fillna(0) / 100)
    df['panier_moyen_client'] = df.groupby('id_client')['montant_apres_remise'].transform('mean')
    df['commande_non_aboutie'] = df['statut'].isin(['annule', 'retourne']).astype(int)
    median_price = df.groupby('categorie')['prix_unitaire'].transform('median')
    df['ecart_prix_median_categorie'] = ((df['prix_unitaire'] - median_price) / median_price).round(4)

    df['sous_categorie'] = group_rare_categories(df['sous_categorie'], min_frequency=0.02)
    df = pd.get_dummies(df, columns=['canal', 'statut', 'categorie', 'sous_categorie'],
                        prefix_sep='=', dtype=int)

    df['montant_zscore'] = scale_zscore(df['montant'])

    return df

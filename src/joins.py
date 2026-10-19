import pandas as pd


def safe_merge(left, right, **kwargs):
    """Jointure contrôlée : vérifie le nombre de lignes et signale les clés non appariées.

    Lève une ValueError si un 'left join' modifie le nombre de lignes (clé non unique
    à droite).
    """
    how = kwargs.get('how', 'inner')
    merged = left.merge(right, indicator='_appariement', **kwargs)

    if how == 'left' and len(merged) != len(left):
        raise ValueError(f'left join : {len(left)} lignes en entrée, {len(merged)} en sortie '
                         '(clé non unique à droite ?)')

    unmatched_rate = (merged['_appariement'] == 'left_only').mean()
    print(f'safe_merge ({how}) : {len(left)} -> {len(merged)} lignes, '
          f'clés non appariées : {unmatched_rate:.2%}')
    return merged.drop(columns='_appariement')


def check_referential_integrity(fact_table, dimensions):
    """Vérifie que toute clé de la table de faits existe dans sa dimension.

    dimensions : dict {nom_colonne_cle: dataframe_dimension}. Lève une ValueError
    au moindre orphelin ou clé absente.
    """
    problems = {}
    for key, dimension in dimensions.items():
        orphan_keys = set(fact_table[key].dropna()) - set(dimension[key])
        n_orphan_rows = int(fact_table[key].isin(orphan_keys).sum())
        n_missing_keys = int(fact_table[key].isna().sum())
        print(f'{key:<11} clés orphelines : {len(orphan_keys):>3} '
              f'({n_orphan_rows} lignes) | clés absentes : {n_missing_keys}')
        if orphan_keys or n_missing_keys:
            problems[key] = sorted(orphan_keys)[:10]
    if problems:
        raise ValueError(f'Intégrité référentielle violée : {problems}')
    print('OK — intégrité référentielle respectée')

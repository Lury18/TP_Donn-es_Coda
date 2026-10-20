"""Nettoyage et modèle en étoile du projet garage (groupe 4).

Chaque fonction copie son entrée, renvoie (df_propre, log) et est idempotente :
la réappliquer à son propre résultat ne change plus rien.
"""

import pandas as pd

from cleaning import normalize_text, parse_price

TEXT_COLUMNS = ['origine', 'statut']                     # descriptives uniquement
KEY_COLUMNS = ['id_intervention', 'id_client', 'id_prestation', 'id_atelier']

KM_SENTINEL = 999_999        # valeur de remplissage : un compteur réel n'affiche pas 999 999
DURATION_SUSPECT = 24        # 24 h isolé au-delà d'une distribution 1-9 h : saisie « journée »
AGE_MIN, AGE_MAX = 18, 100   # titulaire d'un véhicule : majeur, et âge humain plausible
UNKNOWN = 'inconnu'


def _print_log(log):
    for key, value in log.items():
        print(f'  {key:<34} {value}')


def clean_interventions(df, verbose=True):
    """Nettoie la table de faits des interventions."""
    log = {'lignes_initiales': len(df)}
    df = df.copy()

    # 1. montant : '519,57 EUR' -> 519.57 ; 'nan EUR' est un manquant déguisé en texte
    raw_amount = df['montant_facture_eur'].astype('string')
    n_missing_before = int(df['montant_facture_eur'].isna().sum())
    disguised = raw_amount.str.strip().str.lower().eq('nan eur').fillna(False)
    textual = raw_amount.str.contains('EUR', na=False) & ~disguised
    df['montant_facture_eur'] = parse_price(df['montant_facture_eur'])
    log['montants_textuels_convertis'] = int(textual.sum())
    log['montants_nan_eur_deguises'] = int(disguised.sum())

    # 2. texte descriptif (jamais les identifiants)
    for column in TEXT_COLUMNS:
        df[column] = normalize_text(df[column])

    # 3. doublons stricts, APRÈS normalisation
    n_before = len(df)
    df = df.drop_duplicates()
    log['doublons_stricts_supprimes'] = n_before - len(df)

    # 4. dates : cinq formats ; une intervention sans date est inexploitable
    df['date_evenement'] = pd.to_datetime(df['date_evenement'], format='mixed',
                                          dayfirst=True, errors='coerce')
    n_before = len(df)
    df = df[df['date_evenement'].notna()].copy()
    log['lignes_sans_date_supprimees'] = n_before - len(df)

    # 5. durée négative : impossible -> valeur inconnue (la facture reste exploitable)
    negative = df['duree_heures'] < 0
    df.loc[negative, 'duree_heures'] = pd.NA
    df['duree_heures'] = df['duree_heures'].astype('Float64')
    log['durees_negatives_mises_a_vide'] = int(negative.sum())
    df['duree_suspecte'] = df['duree_heures'] == DURATION_SUSPECT
    df['duree_suspecte'] = df['duree_suspecte'].fillna(False).astype(bool)
    log['durees_24h_signalees'] = int(df['duree_suspecte'].sum())

    # 6. kilométrage sentinelle 999 999 -> valeur inconnue + indicateur
    df['km_inconnu'] = (df['km_vehicule'].isna() | (df['km_vehicule'] == KM_SENTINEL)).astype(bool)
    df['km_vehicule'] = df['km_vehicule'].astype('Float64').mask(df['km_vehicule'] == KM_SENTINEL)
    log['km_sentinelle_mis_a_vide'] = int(df['km_inconnu'].sum())

    # 7. montant manquant : PAS d'imputation d'une mesure financière, indicateur seulement
    df['montant_manquant'] = df['montant_facture_eur'].isna()
    log['montants_manquants_signales'] = int(df['montant_manquant'].sum())
    log['montants_manquants_dans_la_source'] = n_missing_before

    log['lignes_finales'] = len(df)
    if verbose:
        _print_log(log)
    return df.reset_index(drop=True), log


def clean_clients(df, verbose=True):
    """Nettoie le référentiel clients : ville, âges impossibles, imputation par segment."""
    log = {'lignes_initiales': len(df)}
    df = df.copy()

    df['ville'] = normalize_text(df['ville'])
    df['date_creation'] = pd.to_datetime(df['date_creation'], errors='coerce')

    impossible = (df['age'] < AGE_MIN) | (df['age'] > AGE_MAX)
    log['ages_impossibles_mis_a_vide'] = int(impossible.sum())
    df['age'] = df['age'].mask(impossible)

    previously_imputed = df['age_imputee'] if 'age_imputee' in df else False
    missing = df['age'].isna()
    log['ages_imputes_mediane_segment'] = int(missing.sum())
    df['age'] = df['age'].fillna(df.groupby('segment')['age'].transform('median'))
    df['age_imputee'] = (missing | previously_imputed).astype(bool)

    log['lignes_finales'] = len(df)
    if verbose:
        _print_log(log)
    return df, log


def clean_prestations(df, verbose=True):
    """Coût de référence manquant : médiane de la sous-famille, à défaut de la famille."""
    log = {'lignes_initiales': len(df)}
    df = df.copy()

    previously_imputed = df['cout_imputee'] if 'cout_imputee' in df else False
    missing = df['cout_reference_eur'].isna()
    log['couts_imputes'] = int(missing.sum())
    for group in ['sous_famille', 'famille']:
        median = df.groupby(group)['cout_reference_eur'].transform('median')
        df['cout_reference_eur'] = df['cout_reference_eur'].fillna(median)
    df['cout_imputee'] = (missing | previously_imputed).astype(bool)

    if verbose:
        _print_log(log)
    return df, log


def add_unknown_members(dimension, fact, key, labels):
    """Ajoute un membre « inconnu » pour chaque clé de la table de faits absente de la dimension."""
    missing_keys = sorted(set(fact[key].dropna()) - set(dimension[key]))
    if not missing_keys:
        return dimension
    unknown = pd.DataFrame({key: missing_keys, **{column: UNKNOWN for column in labels}})
    return pd.concat([dimension, unknown], ignore_index=True)


def build_star(interventions, clients, prestations, ateliers):
    """Construit le modèle en étoile : une table de faits et quatre dimensions."""
    fact = pd.DataFrame({
        'id_intervention': interventions['id_intervention'],
        'cle_date': interventions['date_evenement'].dt.strftime('%Y%m%d').astype(int),
        'id_client': interventions['id_client'],
        'id_prestation': interventions['id_prestation'],
        'id_atelier': interventions['id_atelier'],
        'duree_heures': interventions['duree_heures'],
        'km_vehicule': interventions['km_vehicule'],
        'montant_facture_eur': interventions['montant_facture_eur'],
        'origine': interventions['origine'],
        'statut': interventions['statut'],
        'duree_suspecte': interventions['duree_suspecte'],
        'km_inconnu': interventions['km_inconnu'],
        'montant_manquant': interventions['montant_manquant'],
    })

    dates = pd.date_range(interventions['date_evenement'].min().normalize(),
                          interventions['date_evenement'].max().normalize(), freq='D')
    dim_date = pd.DataFrame({'date': dates})
    dim_date['cle_date'] = dim_date['date'].dt.strftime('%Y%m%d').astype(int)
    dim_date['annee'] = dim_date['date'].dt.year
    dim_date['mois'] = dim_date['date'].dt.month
    dim_date['trimestre'] = dim_date['date'].dt.quarter
    dim_date['semaine_iso'] = dim_date['date'].dt.isocalendar().week.astype(int)
    dim_date['jour_semaine'] = dim_date['date'].dt.dayofweek
    dim_date['est_weekend'] = dim_date['jour_semaine'] >= 5

    dim_prestation = add_unknown_members(prestations.drop_duplicates('id_prestation'), fact,
                                         'id_prestation', ['libelle', 'famille', 'sous_famille'])
    return {
        'fact_interventions': fact,
        'dim_date': dim_date,
        'dim_client': clients.drop_duplicates('id_client'),
        'dim_prestation': dim_prestation,
        'dim_atelier': ateliers.drop_duplicates('id_atelier'),
    }

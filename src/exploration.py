import pandas as pd


def profile_dataframe(df, name='jeu de données', max_cardinality=25):
    """Affiche un rapport d'exploration standard.

    Doit produire, dans cet ordre :
      1. le nom, les dimensions et l'empreinte mémoire ;
      2. le nombre de lignes strictement dupliquées ;
      3. un tableau par colonne : type, nombre de valeurs manquantes, taux en %,
         nombre de valeurs distinctes ;
      4. les statistiques descriptives des colonnes numériques ;
      5. pour chaque colonne texte de cardinalité inférieure à max_cardinality,
         la répartition des modalités.

    Ne renvoie rien : la fonction affiche.
    """
    print(f'--- {name} ---')
    print('dimensions :', df.shape)
    print('mémoire    :', f'{df.memory_usage(deep=True).sum() / 1024:,.1f} Ko'.replace(',', ' '))

    duplicate_count = df.duplicated().sum()
    print('doublons   :', duplicate_count)

    summary = pd.DataFrame({
        'type': df.dtypes,
        'manquants': df.isna().sum(),
        'taux_manquants_%': (df.isna().mean() * 100).round(2),
        'valeurs_distinctes': df.nunique(),
    })
    print('\n--- colonnes ---')
    print(summary)

    numeric_columns = df.select_dtypes(include='number')
    if not numeric_columns.empty:
        print('\n--- statistiques numériques ---')
        print(numeric_columns.describe().round(2))

    text_columns = df.select_dtypes(include='object').columns
    for column in text_columns:
        if df[column].nunique() < max_cardinality:
            print(f'\n--- {column} ---')
            print(df[column].value_counts())
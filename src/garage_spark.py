"""Composant PySpark du projet garage (groupe 4).

Même nettoyage que garage.clean_interventions, écrit en PySpark, puis écriture
Parquet partitionnée par atelier.

    spark-submit src/garage_spark.py
    spark-submit src/garage_spark.py --input <interventions.csv> --output <dossier>
"""

import argparse
import sys
import time
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

ROOT = Path(__file__).resolve().parent.parent

INTERVENTIONS_SCHEMA = StructType([
    StructField('id_intervention', StringType(), True),
    StructField('date_evenement', StringType(), True),       # cinq formats : parsé ensuite
    StructField('id_client', StringType(), True),
    StructField('id_prestation', StringType(), True),
    StructField('id_atelier', StringType(), True),
    StructField('duree_heures', IntegerType(), True),
    StructField('km_vehicule', IntegerType(), True),
    StructField('montant_facture_eur', StringType(), True),  # '519,57 EUR' : parsé ensuite
    StructField('origine', StringType(), True),
    StructField('statut', StringType(), True),
])

DATE_FORMATS = ['yyyy/MM/dd HH:mm', 'yyyy-MM-dd', 'dd/MM/yyyy', 'dd-MM-yyyy', 'dd MMM yyyy']
TEXT_COLUMNS = ['origine', 'statut']
KM_SENTINEL = 999_999
DURATION_SUSPECT = 24


def build_session(app_name='PMD-garage', master=None):
    builder = (SparkSession.builder.appName(app_name)
               .config('spark.sql.shuffle.partitions', '8')
               .config('spark.sql.legacy.timeParserPolicy', 'CORRECTED'))
    if master:
        builder = builder.master(master)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel('ERROR')
    return spark


def read_interventions(spark, path):
    return spark.read.csv(str(path), header=True, schema=INTERVENTIONS_SCHEMA)


def clean_interventions_spark(df):
    """Équivalent PySpark de garage.clean_interventions, dans le même ordre."""
    # 1. montant : 'nan EUR' -> null, '519,57 EUR' -> 519.57
    amount = F.trim(F.col('montant_facture_eur'))
    amount = F.when(F.lower(amount) == 'nan eur', None).otherwise(amount)
    amount = F.regexp_replace(F.regexp_replace(amount, ' EUR', ''), ',', '.').cast('double')
    df = df.withColumn('montant_facture_eur', F.when(F.isnan(amount), None).otherwise(amount))
    # 2. texte descriptif
    for column in TEXT_COLUMNS:
        df = df.withColumn(column, F.regexp_replace(F.lower(F.trim(F.col(column))), r'\s+', ' '))
    # 3. doublons stricts
    df = df.dropDuplicates()
    # 4. dates
    df = (df.withColumn('date_evenement',
                        F.coalesce(*[F.to_timestamp('date_evenement', fmt) for fmt in DATE_FORMATS]))
            .na.drop(subset=['date_evenement']))
    # 5. durées
    df = (df.withColumn('duree_heures', F.when(F.col('duree_heures') < 0, None)
                                         .otherwise(F.col('duree_heures')))
            .withColumn('duree_suspecte', F.coalesce(F.col('duree_heures') == DURATION_SUSPECT,
                                                     F.lit(False))))
    # 6. kilométrage sentinelle
    df = (df.withColumn('km_inconnu', F.col('km_vehicule').isNull()
                        | (F.col('km_vehicule') == KM_SENTINEL))
            .withColumn('km_vehicule', F.when(F.col('km_inconnu'), None)
                                        .otherwise(F.col('km_vehicule'))))
    # 7. montant manquant signalé, non imputé
    return df.withColumn('montant_manquant', F.col('montant_facture_eur').isNull())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--input', default=str(ROOT / 'data' / 'projets' / 'groupe_04_garage'
                                               / 'interventions.csv'))
    parser.add_argument('--output', default=str(ROOT / 'data' / 'processed' / 'garage'
                                                / 'interventions_spark'))
    args = parser.parse_args(argv)

    start = time.perf_counter()
    spark = build_session()
    try:
        raw = read_interventions(spark, args.input)
        cleaned = clean_interventions_spark(raw)
        cleaned.write.mode('overwrite').partitionBy('id_atelier').parquet(args.output)

        written = spark.read.parquet(args.output)
        totals = written.agg(F.count('*').alias('n'),
                             F.round(F.sum('montant_facture_eur'), 2).alias('ca')).first()
        print(f"Entrée : {raw.count()} lignes | sortie : {totals['n']} lignes | CA : {totals['ca']}")
        print(f'Écrit dans {args.output} en {time.perf_counter() - start:.1f} s')
    finally:
        spark.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())

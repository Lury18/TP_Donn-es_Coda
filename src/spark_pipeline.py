"""Pipeline PySpark autonome — séance 7.

Lit le journal d'événements volumineux avec un schéma explicite, le nettoie et
l'écrit en Parquet partitionné par catégorie.

    spark-submit src/spark_pipeline.py
    spark-submit src/spark_pipeline.py --input data/raw/evenements_volumineux.csv \
        --output data/processed/evenements_spark --partition-by categorie

Le script fonctionne aussi avec `python src/spark_pipeline.py` si pyspark est installé.
"""

import argparse
import sys
import time
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (DoubleType, IntegerType, LongType, StringType,
                               StructField, StructType, TimestampType)

ROOT = Path(__file__).resolve().parent.parent

EVENTS_SCHEMA = StructType([
    StructField('id_evenement', LongType(), True),
    StructField('horodatage', TimestampType(), True),
    StructField('id_utilisateur', IntegerType(), True),
    StructField('categorie', StringType(), True),
    StructField('ville', StringType(), True),
    StructField('montant', DoubleType(), True),
    StructField('duree_s', IntegerType(), True),
])

OUTPUT_COLUMNS = ['id_evenement', 'jour', 'heure', 'est_weekend', 'id_utilisateur',
                  'ville', 'categorie', 'montant', 'tranche_montant', 'duree_s']


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--input', default=str(ROOT / 'data' / 'raw' / 'evenements_volumineux.csv'))
    parser.add_argument('--output', default=str(ROOT / 'data' / 'processed' / 'evenements_spark'))
    parser.add_argument('--partition-by', default='categorie')
    parser.add_argument('--shuffle-partitions', type=int, default=16)
    return parser.parse_args(argv)


def build_session(shuffle_partitions):
    # Pas de .master() ici : c'est spark-submit (--master) qui le décide. En exécution
    # directe avec python, Spark démarre en local par défaut.
    spark = (SparkSession.builder
             .appName('PMD-spark-pipeline')
             .config('spark.sql.shuffle.partitions', str(shuffle_partitions))
             .getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    return spark


def clean_events(events):
    """Même nettoyage que l'atelier 7.2 du notebook."""
    return (events
            .filter(F.col('montant') > 0)
            .filter(F.col('duree_s').between(1, 7200))
            .withColumn('ville', F.lower(F.trim(F.col('ville'))))
            .withColumn('jour', F.to_date('horodatage'))
            .withColumn('heure', F.hour('horodatage'))
            .withColumn('est_weekend', F.dayofweek('horodatage').isin([1, 7]))
            .withColumn('tranche_montant',
                        F.when(F.col('montant') < 30, 'faible')
                         .when(F.col('montant') < 100, 'moyen')
                         .otherwise('eleve'))
            .dropDuplicates(['id_evenement']))


def main(argv=None):
    args = parse_args(argv)
    if not Path(args.input).exists():
        print(f'Fichier introuvable : {args.input}\n'
              'Générez-le avec : python src/generate_data.py --big 5000000', file=sys.stderr)
        return 1

    start = time.perf_counter()
    spark = build_session(args.shuffle_partitions)
    try:
        events = spark.read.csv(args.input, header=True, schema=EVENTS_SCHEMA)
        cleaned = clean_events(events).select(*OUTPUT_COLUMNS)

        (cleaned.write.mode('overwrite')
         .partitionBy(args.partition_by)
         .parquet(args.output))

        # Contrôle : relecture du résultat écrit, comptage par partition
        written = spark.read.parquet(args.output)
        counts = written.groupBy(args.partition_by).count().orderBy(args.partition_by).collect()
        n_input, n_output = events.count(), sum(row['count'] for row in counts)

        print(f'Entrée  : {n_input:,} lignes  ({args.input})'.replace(',', ' '))
        print(f'Sortie  : {n_output:,} lignes  ({args.output})'.replace(',', ' '))
        print(f'Écartées par le nettoyage : {n_input - n_output:,}'.replace(',', ' '))
        for row in counts:
            print(f'  {args.partition_by}={row[args.partition_by]:<14} {row["count"]:>10,}'.replace(',', ' '))
        print(f'Durée totale : {time.perf_counter() - start:.1f} s')
    finally:
        spark.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())

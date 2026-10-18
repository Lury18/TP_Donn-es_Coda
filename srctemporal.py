import pandas as pd


def parse_dates(series, min_success_rate=0.95):
    """Convertit une série de dates hétérogènes et renvoie (dates, rapport).

    Lève une ValueError si le taux de réussite est inférieur au seuil.
    """
    converted = pd.to_datetime(series, format='mixed', dayfirst=True, errors='coerce')

    n_total = len(series)
    n_already_missing = int(series.isna().sum())
    n_failed = int(converted.isna().sum()) - n_already_missing
    n_to_parse = n_total - n_already_missing
    success_rate = (n_to_parse - n_failed) / n_to_parse if n_to_parse else 1.0

    report = {
        'n_total': n_total,
        'n_already_missing': n_already_missing,
        'n_failed': n_failed,
        'success_rate': round(success_rate, 4),
        'min_date': converted.min(),
        'max_date': converted.max(),
    }

    if success_rate < min_success_rate:
        raise ValueError(f'Taux de réussite {success_rate:.1%} inférieur au seuil {min_success_rate:.0%}')

    return converted, report


def detect_outages(sensors, sensor_id, min_hours=24, value_column='temperature_c'):
    """Renvoie les plages horaires sans mesure de plus de min_hours heures."""
    readings = sensors.loc[sensors['id_capteur'] == sensor_id].set_index('horodatage')[value_column].sort_index()
    hourly = readings.resample('h').mean()
    missing = hourly.isna()
    run_id = (missing != missing.shift(fill_value=False)).cumsum()
    times = pd.Series(hourly.index, index=hourly.index)
    gaps = times[missing].groupby(run_id[missing]).agg(debut='min', fin='max', heures='size')
    return gaps[gaps['heures'] > min_hours].reset_index(drop=True)


def detect_stuck_sensor(sensors, sensor_id, min_readings=24, value_column='temperature_c'):
    """Renvoie les périodes où le capteur renvoie une valeur strictement constante.

    Les relevés sans valeur sont ignorés : ils n'interrompent pas une période bloquée.
    """
    readings = (sensors.loc[sensors['id_capteur'] == sensor_id]
                .dropna(subset=[value_column])
                .sort_values('horodatage'))
    run_id = readings[value_column].ne(readings[value_column].shift()).cumsum()
    runs = readings.groupby(run_id).agg(debut=('horodatage', 'min'), fin=('horodatage', 'max'),
                                        valeur=(value_column, 'first'), nb_releves=(value_column, 'size'))
    return runs[runs['nb_releves'] > min_readings].reset_index(drop=True)
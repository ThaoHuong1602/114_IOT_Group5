import pandas as pd
from influxdb_client import InfluxDBClient
from config.config import (
    INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG,
    INFLUX_BUCKET, INFLUX_MEASUREMENT
)


def query_influx(device=None, start="-30d"):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    device_filter = f'r["device"] == "{device}"' if device else "true"

    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start})
      |> filter(fn: (r) => r["_measurement"] == "{INFLUX_MEASUREMENT}")
      |> filter(fn: (r) => {device_filter})
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time","brightness","temperature","power","needs_maintenance"])
      |> sort(columns: ["_time"])
    '''

    tables = query_api.query_data_frame(flux)
    df = pd.concat(tables) if isinstance(tables, list) else tables

    df["_time"] = pd.to_datetime(df["_time"])
    df = df.set_index("_time")

    df = df.loc[:, ~df.columns.str.contains("result|table")]

    client.close()
    return df

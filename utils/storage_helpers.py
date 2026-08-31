import json
from io import BytesIO
from typing import Dict, Tuple

import duckdb
import pandas as pd

from supabase_client import supabase


# =========================================================
# DOWNLOAD
# =========================================================

def download_file_from_supabase(path: str) -> bytes:

    return (
        supabase.storage
        .from_("facility-data")
        .download(path)
    )


# =========================================================
# LOAD DATAFRAME  (returns an in-memory DuckDB relation)
# =========================================================

def new_connection() -> duckdb.DuckDBPyConnection:
    """Returns a fresh ephemeral in-memory DuckDB connection."""
    return duckdb.connect()


def load_dataframe_from_storage(path: str) -> Tuple[duckdb.DuckDBPyConnection, duckdb.DuckDBPyRelation]:
    """
    Downloads a file from Supabase and returns ``(con, relation)``.

    Callers must hold a reference to *con* for the relation to stay alive:

    - .csv  → read directly by DuckDB (zero pandas touch)
    - .xlsx → read by pandas (DuckDB has no Excel reader), then registered
              as an in-memory DuckDB table so all downstream callers get a
              consistent DuckDBPyRelation regardless of source format.
    """
    file_bytes = download_file_from_supabase(path)
    con = duckdb.connect()  # ephemeral, in-memory connection

    if path.endswith(".csv"):
        rel = con.read_csv(BytesIO(file_bytes), encoding="UTF-8")
        return con, rel

    elif path.endswith(".xlsx"):
        df = pd.read_excel(BytesIO(file_bytes))
        con.register("_excel_tmp", df)
        return con, con.table("_excel_tmp")

    else:
        raise ValueError(f"Unsupported file format: {path}")


# =========================================================
# CARE LEVEL RATES
# =========================================================

def load_care_level_rates(
    facility: str
) -> Dict[str, float]:

    path = (
        f"{facility}/rates/"
        "care_level_rates.json"
    )

    try:

        file_bytes = download_file_from_supabase(
            path
        )

        data = json.loads(
            file_bytes.decode("utf-8")
        )

        return {
            str(x["care_level"]).strip():
            float(x["cost"])
            for x in data
        }

    except Exception:

        return {}


# =========================================================
# PAYER RATES
# =========================================================

def load_payer_rates(
    facility: str
) -> Dict[str, float]:

    path = (
        f"{facility}/payer_rates/"
        "payer_rates.json"
    )

    try:

        file_bytes = download_file_from_supabase(
            path
        )

        data = json.loads(
            file_bytes.decode("utf-8")
        )

        return {
            str(x["payer"]).strip().lower():
            float(x["adjustment_percent"])
            for x in data
        }

    except Exception:

        return {}
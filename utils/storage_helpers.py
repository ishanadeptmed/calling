import json
from io import BytesIO
from typing import Dict

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
# LOAD DATAFRAME
# =========================================================

def load_dataframe_from_storage(path: str) -> pd.DataFrame:

    file_bytes = download_file_from_supabase(path)

    if path.endswith(".csv"):

        return pd.read_csv(
            BytesIO(file_bytes),
            encoding="utf-8-sig"
        )

    elif path.endswith(".xlsx"):

        return pd.read_excel(
            BytesIO(file_bytes)
        )

    else:
        raise ValueError("Unsupported file")


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
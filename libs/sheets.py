
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from functools import lru_cache

SCOPE = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    # Expects service account JSON in st.secrets["gcp_service_account"]
    creds_info = st.secrets.get("gcp_service_account")
    if not creds_info:
        raise RuntimeError("Missing Google service account in st.secrets['gcp_service_account']")
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, SCOPE)
    client = gspread.authorize(credentials)
    return client

@st.cache_data(ttl=60)  # small cache
def load_sheet_as_df(sheet_id: str, worksheet_name: str):
    client = get_gspread_client()
    sh = client.open_by_key(sheet_id)
    ws = sh.worksheet(worksheet_name)
    rows = ws.get_all_records()
    df = pd.DataFrame(rows)
    return df

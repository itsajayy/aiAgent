# libs/metrics.py
import pandas as pd
import numpy as np
from datetime import datetime

def parse_dates(df, date_col="Date"):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    return df

def compute_email_metrics(email_history_df):
    df = parse_dates(email_history_df, "Date")
    now = pd.Timestamp.now()
    total = len(df)
    today = len(df[df["Date"].dt.date == now.date()])
    # assume Email History has Reply and output where output indicates automated/manual?
    automated = df['output'].apply(lambda x: 1 if str(x).lower().startswith('auto') else 0).sum()
    # average response time: assume email_history has a 'Reply' time column? If only Date and Reply exist,
    # we'll assume 'Reply' column is reply timestamp as string or NaN
    # fallback: if there's no reply timestamp, skip
    if 'Reply' in df.columns:
        df['Reply'] = pd.to_datetime(df['Reply'], errors='coerce')
        df['response_time_hours'] = (df['Reply'] - df['Date']).dt.total_seconds() / 3600
        avg_response = df['response_time_hours'].dropna().mean()
        hours_saved = automated * 0.5  # heuristic: each automated skeleton saves 0.5 hr — change as needed
    else:
        avg_response = None
        hours_saved = automated * 0.5
    return {
        "total_emails": total,
        "today_emails": today,
        "automated_count": int(automated),
        "avg_response_hours": float(avg_response) if avg_response is not None else None,
        "hours_saved": hours_saved
    }

def monthly_volume_by_topic(df, date_col="Date", topic_col="topic"):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df['month'] = df[date_col].dt.to_period('M').astype(str)
    pivot = pd.pivot_table(df, index='month', columns=topic_col, values='UID', aggfunc='count', fill_value=0)
    return pivot.reset_index()

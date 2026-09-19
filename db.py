"""PostgreSQL helpers for saving and loading past trips."""

import os

import psycopg2


def _get_database_url():
    try:
        import streamlit as st

        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return os.environ.get("DATABASE_URL")


def get_connection():
    database_url = _get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(database_url)


def run_query(query, params=None, fetch=False, commit=False):
    """Open a connection, run a parameterised query, and optionally fetch/commit."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            result = cur.fetchall() if fetch else None
        if commit:
            conn.commit()
        return result
    finally:
        conn.close()


def save_trip(destination, days, style, itinerary_json):
    run_query(
        """
        INSERT INTO trips (destination, days, style, itinerary)
        VALUES (%s, %s, %s, %s)
        """,
        (destination, days, style, itinerary_json),
        commit=True,
    )


def get_all_trips():
    rows = run_query(
        """
        SELECT id, destination, days, style, itinerary, created_at
        FROM trips
        ORDER BY created_at DESC
        """,
        fetch=True,
    )
    return rows or []


def delete_trip(trip_id):
    run_query("DELETE FROM trips WHERE id = %s", (trip_id,), commit=True)

"""AI Trip Planner - Streamlit app.

Generates a day-by-day itinerary using OpenAI, grounded with a RAG
knowledge base of local travel tips and live weather from an MCP tool.
Past trips are saved to and loaded from PostgreSQL.
"""

import json
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

import db
from rag import retrieve_tips
from weather_client import get_weather

load_dotenv()

st.set_page_config(page_title="AI Trip Planner", page_icon="\U0001f9f3", layout="wide")

MODEL = "gpt-4o-mini"

WEATHER_ICONS = {
    "rain": "☔",
    "drizzle": "\U0001f327️",
    "snow": "❄️",
    "thunderstorm": "⛈️",
    "fog": "\U0001f32b️",
    "cloud": "☁️",
    "overcast": "☁️",
    "clear": "☀️",
}


def weather_icon(summary: str) -> str:
    lowered = summary.lower()
    for keyword, icon in WEATHER_ICONS.items():
        if keyword in lowered:
            return icon
    return "\U0001f324️"


def get_openai_client():
    api_key = None
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


@st.cache_data(show_spinner=False, ttl=1800)
def cached_get_weather(destination: str):
    return get_weather(destination)


@st.cache_data(show_spinner=False, ttl=3600)
def cached_retrieve_tips(destination: str):
    return retrieve_tips(destination)


@st.cache_data(show_spinner=False, ttl=3600)
def cached_generate_itinerary(destination, days, style, weather_summary, tips_tuple, _api_key):
    client = get_openai_client()
    tips_text = "\n".join(f"- {tip}" for tip in tips_tuple) if tips_tuple else "None available."

    prompt = f"""Plan a {days}-day {style.lower()} trip to {destination}.

Today's weather in {destination}: {weather_summary}
Adjust the plan to suit this forecast (e.g. prefer indoor activities if it is rainy).

Use these local tips where relevant:
{tips_text}

Return ONLY valid JSON in this exact shape:
{{
  "days": [
    {{
      "day_number": 1,
      "theme": "short theme for the day",
      "morning": "activity description",
      "afternoon": "activity description",
      "evening": "activity description",
      "food_tip": "a specific food or restaurant recommendation"
    }}
  ]
}}
Produce exactly {days} entries in "days", numbered 1 through {days}."""

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are an expert travel planner who returns strict JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)


def render_itinerary(itinerary, weather_summary, tips, destination, days, style):
    if weather_summary:
        st.info(f"{weather_icon(weather_summary)} Current weather: {weather_summary}")

    st.subheader(f"\U0001f5fa️ {days}-day {style} trip to {destination}")

    if tips:
        with st.expander("\U0001f4cd Local insider tips", expanded=True):
            for tip in tips:
                st.markdown(f"- {tip}")

    for day in itinerary.get("days", []):
        with st.expander(f"Day {day.get('day_number')}: {day.get('theme', '')}"):
            st.markdown(f"\U0001f305 **Morning:** {day.get('morning', '')}")
            st.markdown(f"☀️ **Afternoon:** {day.get('afternoon', '')}")
            st.markdown(f"\U0001f306 **Evening:** {day.get('evening', '')}")
            st.markdown(f"\U0001f37d️ **Food tip:** {day.get('food_tip', '')}")

    itinerary_text = format_itinerary_text(itinerary, destination, days, style)
    st.download_button(
        "⬇️ Download itinerary",
        data=itinerary_text,
        file_name=f"{destination.replace(' ', '_').lower()}_itinerary.txt",
        mime="text/plain",
    )


def format_itinerary_text(itinerary, destination, days, style):
    lines = [f"{days}-day {style} trip to {destination}", ""]
    for day in itinerary.get("days", []):
        lines.append(f"Day {day.get('day_number')}: {day.get('theme', '')}")
        lines.append(f"  Morning: {day.get('morning', '')}")
        lines.append(f"  Afternoon: {day.get('afternoon', '')}")
        lines.append(f"  Evening: {day.get('evening', '')}")
        lines.append(f"  Food tip: {day.get('food_tip', '')}")
        lines.append("")
    return "\n".join(lines)


def db_available():
    return bool(os.environ.get("DATABASE_URL")) or "DATABASE_URL" in getattr(st, "secrets", {})


def render_past_trips_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.subheader("\U0001f4dc My past trips")

    if not db_available():
        st.sidebar.caption("Set DATABASE_URL to enable trip history.")
        return

    try:
        trips = db.get_all_trips()
    except Exception as exc:
        st.sidebar.warning(f"Trip history unavailable: {exc}")
        return

    if not trips:
        st.sidebar.caption("No saved trips yet.")
        return

    for trip_id, destination, days, style, itinerary_json, created_at in trips:
        label = f"{destination} ({created_at:%b %d, %Y})"
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(label, key=f"load-{trip_id}", use_container_width=True):
                st.session_state["itinerary"] = json.loads(itinerary_json)
                st.session_state["destination"] = destination
                st.session_state["days"] = days
                st.session_state["style"] = style
                st.session_state["weather_summary"] = None
                st.session_state["tips"] = []
        with col2:
            if st.button("\U0001f5d1️", key=f"delete-{trip_id}"):
                db.delete_trip(trip_id)
                st.rerun()


def main():
    st.title("\U0001f9f3 AI Trip Planner")
    st.caption("Day-by-day itineraries powered by OpenAI, your own travel notes, and live weather.")

    with st.sidebar:
        st.header("Plan your trip")
        destination = st.text_input("Destination", placeholder="e.g. Paris")
        days = st.number_input("Number of days", min_value=1, max_value=14, value=3)
        style = st.selectbox("Travel style", ["Budget", "Balanced", "Luxury"])
        plan_clicked = st.button("✈️ Plan my trip", type="primary")

    render_past_trips_sidebar()

    if plan_clicked:
        api_key = None
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            st.error("OPENAI_API_KEY is not set. Add it to your .env file or Streamlit secrets.")
            st.stop()

        if not destination.strip():
            st.warning("Please enter a destination.")
            st.stop()

        with st.spinner(f"Planning your trip to {destination}..."):
            try:
                weather_summary = cached_get_weather(destination)
            except Exception as exc:
                weather_summary = None
                st.warning(f"Could not fetch live weather: {exc}")

            tips = cached_retrieve_tips(destination)

            try:
                itinerary = cached_generate_itinerary(
                    destination, days, style, weather_summary or "unknown", tuple(tips), api_key
                )
            except Exception as exc:
                st.error(f"Could not generate itinerary: {exc}")
                st.stop()

        st.session_state["itinerary"] = itinerary
        st.session_state["destination"] = destination
        st.session_state["days"] = days
        st.session_state["style"] = style
        st.session_state["weather_summary"] = weather_summary
        st.session_state["tips"] = tips

        if db_available():
            try:
                db.save_trip(destination, days, style, json.dumps(itinerary))
            except Exception as exc:
                st.warning(f"Trip generated, but could not save to database: {exc}")

    if "itinerary" in st.session_state:
        render_itinerary(
            st.session_state["itinerary"],
            st.session_state.get("weather_summary"),
            st.session_state.get("tips"),
            st.session_state["destination"],
            st.session_state["days"],
            st.session_state["style"],
        )
    else:
        st.markdown(
            """
            <div style="padding: 3rem; text-align: center; border: 2px dashed #ccc;
                        border-radius: 12px; color: #888;">
                <h3>\U0001f30d Your itinerary will appear here</h3>
                <p>Fill in your destination and trip details in the sidebar, then click
                "Plan my trip".</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()

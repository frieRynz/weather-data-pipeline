from pathlib import Path
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from components.map import render_thailand_map  # noqa: E402

st.set_page_config(page_title="Weather Forecast Dashboard", page_icon="⛅", layout="wide")

# ---------- custom polish on top of the existing dark theme ----------
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.2rem; }
        .city-card {
            background: rgba(38, 39, 48, 0.6);
            border: 1px solid rgba(250, 250, 250, 0.12);
            border-radius: 12px;
            padding: 0.8rem 1rem;
        }
        div[data-testid="stDataFrame"] { border-radius: 10px; }
        div[data-testid="stRadio"] label {
            font-size: 1.05rem;
            padding: 0.25rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

CITY_EMOJI = {
    "Bangkok": "🏙️",
    "Chiang Mai": "🛕",
    "Phuket": "🏝️",
    "Khon Kaen": "🏛️",
    "Hat Yai": "🌆",
}

# ---------- data ----------
conn = st.connection("postgresql", type="sql")

df = conn.query(
    """SELECT c.city_name as city,
              c.latitude,
              c.longitude,
              date(f.forecast_time) as day,
              round(avg(f.temperature),2) as average_temperature,
              max(f.temperature) as maximum_temperature,
              min(f.temperature) as minimum_temperature
       from forecast f
       INNER JOIN city c on f.city_id = c.city_id
       group by c.city_name, c.latitude, c.longitude, day
       ORDER BY c.city_name, day""",
    ttl="10m",
)

# ---------- header ----------
st.title("⛅ Weather Forecast Dashboard")
st.caption("7-day temperature forecast per city")

cities = df["city"].unique().tolist()
if not cities:
    st.warning("No forecast data available yet — run the pipeline first.")
    st.stop()

# ---------- city selection: dropdown synced with the clickable city list ----------
if "city_radio" not in st.session_state:
    st.session_state["city_radio"] = cities[0]


def _sync_radio():
    st.session_state["city_radio"] = st.session_state["city_sb"]


st.selectbox(
    "Select a City",
    cities,
    key="city_sb",
    index=cities.index(st.session_state["city_radio"]),
    on_change=_sync_radio,
)
city = st.session_state["city_radio"]

# ---------- top row: city list | map | 7-day average card ----------
left, center, right = st.columns([3, 4, 2], gap="medium")

with left:
    per_city = (
        df.groupby("city", as_index=False)["average_temperature"].mean().round(1)
    )
    selected = st.radio(
        "Cities",
        cities,
        key="city_radio",
        format_func=lambda c: f"{CITY_EMOJI.get(c, '📍')}  {c}  —  "
        f"{per_city.loc[per_city['city'] == c, 'average_temperature'].iloc[0]:.1f} °C",
        label_visibility="collapsed",
    )
    city = selected

subset = df[df["city"] == city].copy()
subset["day"] = subset["day"].astype(str)
cities_geo = (
    df[["city", "latitude", "longitude"]]
    .drop_duplicates(subset="city")
    .reset_index(drop=True)
)

with center:
    st.markdown("**🗺️ Thailand — selected city view**")
    render_thailand_map(cities_geo, city)

with right:
    avg_7d = subset["average_temperature"].mean()
    st.markdown(
        f"""
        <div class="city-card" style="text-align:center; padding:1.5rem 1rem">
            <div style="font-size:1.1rem">🌡️ <b>7-days Average Temperature</b></div>
            <div style="font-size:3rem; font-weight:800; margin:0.6rem 0">
                {avg_7d:.1f} °C
            </div>
            <div style="font-size:1.4rem; margin-bottom:0.4rem">
                {CITY_EMOJI.get(city, '📍')} {city}
            </div>
            <small>Average of daily average temperature for the next 7 days</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- line chart ----------
st.subheader(f"📈 Daily temperatures — {city}")

subset = subset.rename(
    columns={
        "average_temperature": "Avg_Temp",
        "maximum_temperature": "Max_Temp",
        "minimum_temperature": "Min_Temp",
    }
)

chart_df = subset.melt(
    id_vars="day",
    value_vars=["Avg_Temp", "Max_Temp", "Min_Temp"],
    var_name="series",
    value_name="temperature",
)
chart_df["day"] = chart_df["day"].astype(str)

series_colors = alt.Scale(
    domain=["Max_Temp", "Avg_Temp", "Min_Temp"],
    range=["#ff4d4d", "#4da6ff", "#2ecc71"],
)

line = (
    alt.Chart(chart_df)
    .mark_line()
    .encode(
        x=alt.X("day:N", title="Day", sort=None),
        y=alt.Y("temperature:Q", title="Temperature (°C)"),
        color=alt.Color("series:N", title="Metric", scale=series_colors),
    )
)
points = (
    alt.Chart(chart_df)
    .mark_circle(size=80)
    .encode(
        x="day:N",
        y="temperature:Q",
        color=alt.Color("series:N", title="Metric", scale=series_colors),
        tooltip=["day:N", "series:N", alt.Tooltip("temperature:Q", format=".2f")],
    )
)

chart = (
    (line + points)
    .interactive()
    .configure(background="transparent")
    .configure_axis(
        gridColor="rgba(250,250,250,0.10)", labelColor="#d0d0d8", titleColor="#d0d0d8"
    )
    .configure_legend(labelColor="#d0d0d8", titleColor="#d0d0d8")
)

st.altair_chart(chart, use_container_width=True)

# ---------- breakdown table with colored metric values ----------
st.subheader("🗓️ Daily temperature breakdown")


def _color_metric(series: pd.Series, color: str) -> list:
    return [f"color: {color}"] * len(series)


styled = (
    subset.style.format(
        {
            "Avg_Temp": "{:.2f}",
            "Max_Temp": "{:.2f}",
            "Min_Temp": "{:.2f}",
            "latitude": "{:.4f}",
            "longitude": "{:.4f}",
        }
    )
    .apply(_color_metric, color="#4da6ff", subset=["Avg_Temp"])
    .apply(_color_metric, color="#ff4d4d", subset=["Max_Temp"])
    .apply(_color_metric, color="#2ecc71", subset=["Min_Temp"])
)

st.dataframe(styled, hide_index=True, use_container_width=True)

st.caption("🕒 All times are local time for each city")



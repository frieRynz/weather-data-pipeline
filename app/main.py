import streamlit as st
import altair as alt
import pandas as pd

# showing temperatures per city, reading from the DB
# st.write(st.secrets) 

# Initialized connection
conn = st.connection("postgresql", type="sql")

df = conn.query("""SELECT c.city_name as city,
                    date(f.forecast_time) as day,
                    round(avg(f.temperature),2) as average_temperature,
                    max(f.temperature) as maximum_temperature,
                    min(f.temperature) as minimum_temperature
                    from forecast f
                    INNER JOIN city c
                    on f.city_id = c.city_id
                    group by c.city_name, day
                    ORDER BY c.city_name, day""", ttl="10m")
st.title("⛅Weather Forecast Dashboard")

city = st.selectbox("Select a City", df["city"].unique())

subset = df[df["city"] == city].copy()
subset["day"] = subset["day"].astype(str)

st.metric("7-days Average Temperature", f"{subset['average_temperature'].mean():.1f} °C")

st.subheader(f"📈Daily temperatures — {city}")

subset = subset.rename(columns={"average_temperature": "Avg_Temp",
                                "maximum_temperature": "Max_Temp",
                                "minimum_temperature":"Min_Temp"})
chart_df = subset.melt(
    id_vars = "day",
    value_vars = ["Avg_Temp", "Max_Temp", "Min_Temp"],
    var_name = "series",
    value_name = "temperature",
)

chart_df["day"] = chart_df["day"].astype(str)

line = alt.Chart(chart_df).mark_line().encode(
    x=alt.X("day:N", title="Day", sort=None),
    y=alt.Y("temperature:Q", title="Temperature (°C)"),
    color=alt.Color("series:N", title="Metric",
                    scale=alt.Scale(scheme="set1"))
)

points = alt.Chart(chart_df).mark_circle(size=70).encode(
    x="day:N", y="temperature:Q", color="series:N"
)

st.altair_chart((line+points).interactive(), use_container_width=True)

st.subheader("🗓️Daily temperature breakdown")
st.dataframe(subset, hide_index=True)

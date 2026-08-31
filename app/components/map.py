from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

# Colors tuned for the existing dark Streamlit theme
_LAND_FILL = [30, 38, 58]
_LAND_LINE = [90, 110, 160]
_POINT_COLOR = [90, 170, 255]
_SELECTED_COLOR = [0, 220, 180]
_TEXT_COLOR = [200, 215, 240]


def _city_points(df: pd.DataFrame, selected_city: str) -> pd.DataFrame:
    """Build the point layer dataframe with highlight flags for the selected city."""
    points = df.copy()
    points["is_selected"] = points["city"] == selected_city
    points["color"] = points["is_selected"].map(
        {True: _SELECTED_COLOR, False: _POINT_COLOR}
    )
    points["radius"] = points["is_selected"].map({True: 22000, False: 12000})
    return points


def render_thailand_map(cities_df: pd.DataFrame, selected_city: str, height: int = 430):
    """Render the Thailand map, zoomed into the selected city with a highlighted anchor.

    Each time the selection changes, the view state re-centers on the city's
    latitude/longitude so the map zooms in instead of showing the whole country.
    """
    selected = cities_df.loc[cities_df["city"] == selected_city].iloc[0]
    points = _city_points(cities_df, selected_city)

    view_state = pdk.ViewState(
        latitude=float(selected["latitude"]),
        longitude=float(selected["longitude"]),
        zoom=6.4,
        pitch=0,
    )

    # Soft glowing halo under the selected city
    selected_halo = pdk.Layer(
        "ScatterplotLayer",
        points[points["is_selected"]],
        get_position="[longitude, latitude]",
        get_radius=42000,
        radius_min_pixels=18,
        get_fill_color=_SELECTED_COLOR + [60],
        pickable=False,
    )

    city_dots = pdk.Layer(
        "ScatterplotLayer",
        points,
        get_position="[longitude, latitude]",
        get_radius="radius",
        radius_min_pixels=6,
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )

    city_labels = pdk.Layer(
        "TextLayer",
        points,
        get_position="[longitude, latitude]",
        get_text="city",
        get_color=_TEXT_COLOR,
        get_size=14,
        get_pixel_offset=[12, 0],
        get_alignment_baseline="center",
        pickable=False,
    )

    deck = pdk.Deck(
        layers=[selected_halo, city_dots, city_labels],
        initial_view_state=view_state,
        map_style=None,  # no basemap tiles; dark page background shows through
        views=[pdk.View(type="MapView", controller=True)],
    )
    st.pydeck_chart(deck, use_container_width=True, height=height)
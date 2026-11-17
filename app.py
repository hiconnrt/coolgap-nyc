"""CoolGap NYC: the Streamlit app.

Run from the coolgap folder:
    streamlit run app.py

This file only sets up the menu. Each page lives in the views/ folder.
"""
import streamlit as st

from views import block_heat, explorer, finder, gap_map, methods, simulator_page

st.set_page_config(page_title="CoolGap NYC", layout="wide")

pages = [
    st.Page(gap_map.render, title="Heat Gap Map", url_path="map", default=True),
    st.Page(explorer.render, title="Neighborhood Explorer", url_path="explorer"),
    st.Page(finder.render, title="Cooling Resource Finder", url_path="finder"),
    st.Page(simulator_page.render, title="Simulator", url_path="simulator"),
    st.Page(block_heat.render, title="Block-Level Heat", url_path="heat"),
    st.Page(methods.render, title="Methods and Limitations", url_path="methods"),
]
page = st.navigation(pages)

with st.sidebar:
    st.markdown("### CoolGap NYC")
    st.caption(
        "A student research project on heat risk and cooling access in "
        "Southern Brooklyn. Not an official city tool. No personal data is "
        "collected. Cooling center data is historical. In an emergency, call 911."
    )

page.run()

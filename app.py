"""Main Streamlit application for the Pickleball Financial Model."""

import streamlit as st
from config.default_params import TSD_SIMPLE_DEFAULTS, VEROS_DEFAULTS
from components.validation_tab import render_validation_tab
from components.projections_tab import render_projections_tab

# Page configuration
st.set_page_config(
    page_title="Pickleball Financial Model",
    page_icon="🎾",
    layout="wide"
)

st.title("🎾 Pickleball Financial Model")

# Initialize session state
if 'tsd_simple' not in st.session_state:
    st.session_state.tsd_simple = TSD_SIMPLE_DEFAULTS.copy()

if 'veros_params' not in st.session_state:
    st.session_state.veros_params = VEROS_DEFAULTS.copy()

# Create tabs
tab1, tab2 = st.tabs(["Facility Model Validation", "Veros Projections"])

# Render tabs
with tab1:
    render_validation_tab()

with tab2:
    render_projections_tab()
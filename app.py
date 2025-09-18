import streamlit as st
from workflows.trip_planner_flow import run_trip_pipeline
from dotenv import load_dotenv
load_dotenv()

st.title("🧠 Meguru AI Travel Companion")

destination = st.text_input("Destination", "Kyoto")
dates = st.text_input("Dates", "Nov 5–9")
preferences = st.text_area("Vibe", "Peaceful, beautiful, tea, nature, slow mornings")

if st.button("Plan My Trip"):
    plan = run_trip_pipeline(destination, dates, preferences)
    st.markdown(plan)

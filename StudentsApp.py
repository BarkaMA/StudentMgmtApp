import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials
import os
from streamlit_option_menu import option_menu

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Student Management App",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- GOOGLE SHEETS SETUP ---
# ... (the rest of your Python code)

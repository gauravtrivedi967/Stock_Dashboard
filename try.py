import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
load_dotenv()

# Retrieve credentials
VALID_USERNAME = os.getenv("USERNAME", "gaurav")  # Default for testing
VALID_PASSWORD = os.getenv("PASSWORD", "password123")  # Default for testing

# Configuration for Streamlit app
st.set_page_config(layout="wide")
st.sidebar.title("Login")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.sidebar.form("Login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        # Debug the retrieved credentials (remove in production)
        st.sidebar.write(f"DEBUG: VALID_USERNAME={VALID_USERNAME}, VALID_PASSWORD={VALID_PASSWORD}")

        if login_button:
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                st.session_state["authenticated"] = True
                st.success("Login successful! Reload the page if needed.")
            else:
                st.error("Invalid username or password.")
else:
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.experimental_rerun()

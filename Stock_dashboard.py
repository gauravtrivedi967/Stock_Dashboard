import os
import creds
import base64
import ollama
import tempfile
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from stocknews import StockNews
from alpha_vantage.fundamentaldata import FundamentalData
import streamlit_authenticator as stauth

# Configuration for Streamlit app
st.set_page_config(layout="wide")
st.title("AI-Powered Technical Stock Analysis Dashboard")

# Set up authentication
st.sidebar.title("Login")
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.sidebar.form("Login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        # Hardcoded credentials (for demonstration; replace with secure storage)
        VALID_USERNAME = os.getenv("USERNAME","gaurav")
        VALID_PASSWORD = os.getenv("PASSWORD","password123")

        if login_button:
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                st.session_state["authenticated"] = True
                st.success("Login successful! Reload the page if needed.")
            else:
                st.error("Invalid username or password.")
else:
    # Logout option
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.experimental_rerun()

# Main dashboard (only visible after login)
if st.session_state["authenticated"]:
    st.sidebar.header("Configuration")

    st.sidebar.header("Configuration")
    ticker = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL):", "AAPL")
    start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
    end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2024-12-14"))

    # Initialize session state
if "stock_data" not in st.session_state:
    st.session_state["stock_data"] = None

# Fetch stock data
if st.sidebar.button("Fetch Data"):
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        if not stock_data.empty:
            # Clean stock data
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = ["_".join(col) for col in stock_data.columns]
            stock_data = stock_data.dropna().reset_index()
            st.session_state["stock_data"] = stock_data
            st.success("Stock data loaded successfully!")
        else:
            st.error("No data available for the specified ticker and date range.")
    except Exception as e:
        st.error(f"Error fetching data: {e}")

# Main dashboard
if st.session_state["stock_data"] is not None:
    data = st.session_state["stock_data"].copy()

    # Define column names dynamically
    open_col = [col for col in data.columns if "Open" in col][0]
    high_col = [col for col in data.columns if "High" in col][0]
    low_col = [col for col in data.columns if "Low" in col][0]
    close_col = [col for col in data.columns if "Close" in col][0]
    date_col = data.columns[0]  # Date column
    adj_close_column = [col for col in data.columns if "Adj Close" in col][0]
    volume_col = [col for col in data.columns if "Volume" in col][0]

    # Display stock data
    st.subheader("Cleaned Stock Data")
    st.dataframe(data)

    # Plot candlestick chart
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=data[date_col],
                open=data[open_col],
                high=data[high_col],
                low=data[low_col],
                close=data[close_col],
                name="Candlestick",
            )
        ]
    )

    # Sidebar for technical indicators
    st.sidebar.subheader("Technical Indicators")
    indicators = st.sidebar.multiselect(
        "Select Indicators:",
        ["20-Day SMA", "20-Day EMA", "20-Day Bollinger Bands", "VWAP"],
        default=["20-Day SMA"],
    )

    # Add indicators to the chart
    def add_indicator(indicator, data):
        if indicator == "20-Day SMA":
            sma = data[close_col].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=data[date_col], y=sma, mode="lines", name="SMA (20)"))
        elif indicator == "20-Day EMA":
            ema = data[close_col].ewm(span=20).mean()
            fig.add_trace(go.Scatter(x=data[date_col], y=ema, mode="lines", name="EMA (20)"))
        elif indicator == "20-Day Bollinger Bands":
            sma = data[close_col].rolling(window=20).mean()
            std = data[close_col].rolling(window=20).std()
            bb_upper = sma + 2 * std
            bb_lower = sma - 2 * std
            fig.add_trace(go.Scatter(x=data[date_col], y=bb_upper, mode="lines", name="BB Upper"))
            fig.add_trace(go.Scatter(x=data[date_col], y=bb_lower, mode="lines", name="BB Lower"))
        elif indicator == "VWAP":
            vwap = (data[close_col] * data[volume_col]).cumsum() / data[volume_col].cumsum()
            fig.add_trace(go.Scatter(x=data[date_col], y=vwap, mode="lines", name="VWAP"))

    for indicator in indicators:
        add_indicator(indicator, data)

    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

    # AI Analysis
    st.subheader("AI-Powered Analysis")
    if st.button("Run AI Analysis"):
        try:
            with st.spinner("Analyzing the chart, please wait..."):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                    fig.write_image(tmpfile.name)
                    tmpfile_path = tmpfile.name

                with open(tmpfile_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode("utf-8")

                messages = [
                    {
                        "role": "user",
                        "content": """You are a Stock Trader specializing in Technical Analysis.
                                Analyze the stock chart's indicators and provide a buy/hold/sell recommendation.""",
                        "images": [image_data],
                    }
                ]
                response = ollama.chat(model="llama3.2-vision", messages=messages)
                st.write("**AI Analysis Results:**")
                st.write(response["message"]["content"])
        except Exception as e:
            st.error(f"Error during AI analysis: {e}")
        finally:
            if os.path.exists(tmpfile_path):
                os.remove(tmpfile_path)

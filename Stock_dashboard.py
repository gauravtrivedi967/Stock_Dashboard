import os
import creds
import base64
import ollama
import tempfile
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from stocknews import StockNews
from alpha_vantage.fundamentaldata import FundamentalData


st.set_page_config(layout="wide")
st.title("AI-Powered Technical Stock Analysis Dashboard")
st.sidebar.header("Configuration")

# Sidebar inputs
ticker = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL):", "AAPL")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2024-12-14"))

# Fetch data
if st.sidebar.button("Fetch Data"):
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        if not stock_data.empty:
            # Drop rows with missing or None values
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = ['_'.join(col) for col in stock_data.columns]
            stock_data = stock_data.dropna().reset_index()
            st.session_state["stock_data"] = stock_data
            st.success("Stock data loaded successfully!")
        else:
            st.error("No data available for the specified ticker and date range.")
    except Exception as e:
        st.error(f"Error fetching data: {e}")

# Check if data is available
if st.session_state["stock_data"] is not None:
    data = st.session_state["stock_data"].copy()

    # Dynamically find the relevant columns for candlestick plotting
    open_col = [col for col in data.columns if 'Open' in col][0]
    high_col = [col for col in data.columns if 'High' in col][0]
    low_col = [col for col in data.columns if 'Low' in col][0]
    close_col = [col for col in data.columns if 'Close' in col][0]
    date_col = data.columns[0]  # Usually, the 'Date' or 'Datetime' column
    adj_close_column = [col for col in data.columns if 'Adj Close' in col][0]
    volume_col = [col for col in data.columns if 'Volume' in col][0]

    # Display the cleaned stock data
    st.subheader("Cleaned Stock Data")
    st.dataframe(data)

    # Plot candlestick chart dynamically
    fig = go.Figure(data=[
        go.Candlestick(
            x=data[date_col],
            open=data[open_col],
            high=data[high_col],
            low=data[low_col],
            close=data[close_col],
            name="Candlestick"
        )
    ])

    # Sidebar: Select technical indicators
    st.sidebar.subheader("Technical Indicators")
    indicators = st.sidebar.multiselect(
        "Select Indicators:",
        ["20-Day SMA", "20-Day EMA", "20-Day Bollinger Bands", "VWAP"],
        default=["20-Day SMA"]
    )

    # Helper function to add indicators to the chart
    def add_indicator(indicator, data):
        if indicator == "20-Day SMA":
            sma = data[close_col].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=data[date_col], y=sma, mode='lines', name='SMA (20)'))
        elif indicator == "20-Day EMA":
            ema = data[close_col].ewm(span=20).mean()
            fig.add_trace(go.Scatter(x=data[date_col], y=ema, mode='lines', name='EMA (20)'))
        elif indicator == "20-Day Bollinger Bands":
            sma = data[close_col].rolling(window=20).mean()
            std = data[close_col].rolling(window=20).std()
            bb_upper = sma + 2 * std
            bb_lower = sma - 2 * std
            fig.add_trace(go.Scatter(x=data[date_col], y=bb_upper, mode='lines', name='BB Upper'))
            fig.add_trace(go.Scatter(x=data[date_col], y=bb_lower, mode='lines', name='BB Lower'))
        elif indicator == "VWAP":
            vwap = (data[close_col] * data[volume_col]).cumsum() / data[volume_col].cumsum()
            fig.add_trace(go.Scatter(x=data[date_col], y=vwap, mode='lines', name='VWAP'))

    # Add selected indicators to the chart
    for indicator in indicators:
        add_indicator(indicator, data)

    # Update layout and display the chart
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

# Tabs for additional data
pricing_data, fundamental_data, news, ai_analysis = st.tabs(["Pricing Data", "Fundamental Data", "Top 10 News","AI-Powered Analysis"])

# Pricing Data Tab
with pricing_data:
    st.header("Price Movement")
    if not data.empty:
        data2 = data.copy()
        data2['% change'] = data[adj_close_column]/data[adj_close_column].shift(1)-1
        data2.dropna(inplace=True)

        # Annual Return
        annual_return = data2['% change'].mean() * 252 * 100
        st.write(f'### Annual Return: {annual_return:.2f}%')

        # Annual Volatility
        annual_volatility = np.std(data2['% change']) * np.sqrt(252) * 100
        st.write(f'### Annual Volatility: {annual_volatility:.2f}%')
    else:
        st.warning("No price data available.")

# Fundamental Data Tab
with fundamental_data:
    st.header("Fundamental Data")
    try:
        key = creds.api_key  # Assuming your `creds` file contains `api_key`
        fd = FundamentalData(key, output_format='pandas')

        st.subheader("Balance Sheet")
        balance_sheet = fd.get_balance_sheet_annual(ticker)[0]
        bs = balance_sheet.T[2:]
        bs.columns = list(balance_sheet.T.iloc[0])
        st.write(bs)

        st.subheader("Income Statement")
        income_statement = fd.get_income_statement_annual(ticker)[0]
        is1 = income_statement.T[2:]
        is1.columns = list(income_statement.T.iloc[0])
        st.write(is1)

        st.subheader("Cash Flow Statement")
        cash_flow = fd.get_cash_flow_annual(ticker)[0]
        cf = cash_flow.T[2:]
        cf.columns = list(cash_flow.T.iloc[0])
        st.write(cf)
    except Exception as e:
        st.error(f"An error occurred while fetching fundamental data: {e}")

# News Tab
with news:
    st.header(f'Top 10 News for {ticker}')
    try:
        sn = StockNews(ticker, save_news=False)
        df_news = sn.read_rss()

        # Display Top 10 News Articles
        for i in range(min(10, len(df_news))):  # Limit to top 10
            st.subheader(f'News {i+1}')
            st.write(f"**Published:** {df_news['published'][i]}")
            st.write(f"**Title:** {df_news['title'][i]}")
            st.write(f"**Summary:** {df_news['summary'][i]}")
            st.write(f"**Title Sentiment:** {df_news['sentiment_title'][i]}")
            st.write(f"**News Sentiment:** {df_news['sentiment_summary'][i]}")

            # Placeholder Image for News (Optional: Replace with custom logic)
            placeholder_image = "https://via.placeholder.com/150"  # Generic image
            st.image(placeholder_image, caption="News Image", use_column_width=True)

            # Add link to read full article if available
            try:
                st.write(f"[Read more...]({df_news['link'][i]})")
            except KeyError:
                st.warning("Link not available for this news article.")

    except Exception as e:
        st.error(f"An error occurred while fetching news: {e}")

#AI analysis tab 
with ai_analysis:
    st.subheader("AI-Powered Analysis")
    if st.button("Run AI Analysis"):
        try:
            with st.spinner("Analyzing the chart, please wait..."):
                # Save chart as a temporary image
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                    fig.write_image(tmpfile.name)
                    tmpfile_path = tmpfile.name

                # Read image and encode to Base64
                with open(tmpfile_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')

                # Prepare AI analysis request
                messages = [{
                    'role': 'user',
                    'content': """You are a Stock Trader specializing in Technical Analysis at a top financial institution.
                                Analyze the stock chart's technical indicators and provide a buy/hold/sell recommendation.
                                Base your recommendation only on the candlestick chart and the displayed technical indicators.
                                First, provide the recommendation, then, provide your detailed reasoning.
                    """,
                    'images': [image_data]
                }]
                response = ollama.chat(model='llama3.2-vision', messages=messages)

                # Display AI analysis result
                st.write("**AI Analysis Results:**")
                st.write(response["message"]["content"])
        except Exception as e:
            st.error(f"Error during AI analysis: {e}")
        finally:
            if os.path.exists(tmpfile_path):
                os.remove(tmpfile_path)


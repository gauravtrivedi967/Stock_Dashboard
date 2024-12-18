import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import creds
import plotly.express as px
from alpha_vantage.fundamentaldata import FundamentalData
from stocknews import StockNews

st.title('Stock Dashboard')

# Sidebar inputs
ticker = st.sidebar.text_input('Enter Stock Ticker')
start_date = st.sidebar.date_input('Start Date')
end_date = st.sidebar.date_input('End Date')

# Fetch data
if ticker:
    data = yf.download(ticker, start=start_date, end=end_date)

    # Flatten MultiIndex columns if needed
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = ['_'.join(col) for col in data.columns]

    if data.empty:
        st.error("No data available for the given inputs. Please check the ticker or date range.")
    else:
        st.write("### Stock Data", data)
        adj_close_column = [col for col in data.columns if 'Adj Close' in col][0]
        fig = px.line(data, x=data.index, y=adj_close_column,
                      title=f'{ticker} Adjusted Close Prices',
                      labels={'x': 'Date', adj_close_column: 'Adjusted Close Price'})
        st.plotly_chart(fig)
else:
    st.info("Please enter a stock ticker to fetch data.")

# Tabs for additional data
pricing_data, fundamental_data, news = st.tabs(["Pricing Data", "Fundamental Data", "Top 10 News"])

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

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px

st.title('Stock Dashboard')

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

pricing_data,fundamental_data,news=st.tabs(["Pricing Data","Fundamental Data","Top 10 news"])

with pricing_data:
    st.header("Price Movement")
    data2=data
    data2['% change'] = data[adj_close_column]/data[adj_close_column].shift(1)-1
    data2.dropna(inplace=True)
    annual_retrun=data2['% change'].mean()*252*100
    st.write(f'Annual Return: {annual_retrun:.2f}%')
    stdev=np.std(data2['% change'])*np.sqrt(252)
    st.write(f'Annual Volatility:',stdev*100,'%')

with fundamental_data:
    st.write("Fundamental Data")

with news:
    st.write("Top 10 News")


import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date
import ta
import io

# --- Page config ---
st.set_page_config(layout="wide", page_title="Stock Dashboard", initial_sidebar_state="expanded")

# --- Sidebar ---
st.sidebar.title("📊 Dashboard Settings")
tickers = st.sidebar.text_input("Enter up to 10 tickers (comma-separated)", "RELIANCE.NS, INFY.NS")
period = st.sidebar.selectbox("Select Period", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=1)
interval = st.sidebar.selectbox("Select Interval", ['1d', '1h', '30m', '15m'], index=0)
show_volume = st.sidebar.toggle("Show Volume", value=True)
indicators = st.sidebar.multiselect("Technical Indicators", ['MACD', 'RSI', 'SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'BBANDS', 'VWAP'], ['MACD', 'RSI'])

# --- Fetching Data ---
def fetch_data(ticker):
    try:
        data = yf.download(ticker.strip(), period=period, interval=interval)
        data.dropna(inplace=True)
        return data
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

# --- Indicator Calculation ---
def add_indicators(data):
    df = data.copy()
    if 'RSI' in indicators:
        df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    if 'MACD' in indicators:
        macd = ta.trend.MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
    if 'SMA_20' in indicators:
        df['SMA_20'] = df['Close'].rolling(20).mean()
    if 'SMA_50' in indicators:
        df['SMA_50'] = df['Close'].rolling(50).mean()
    if 'EMA_20' in indicators:
        df['EMA_20'] = df['Close'].ewm(span=20).mean()
    if 'EMA_50' in indicators:
        df['EMA_50'] = df['Close'].ewm(span=50).mean()
    if 'BBANDS' in indicators:
        bb = ta.volatility.BollingerBands(df['Close'])
        df['BB_H'] = bb.bollinger_hband()
        df['BB_L'] = bb.bollinger_lband()
    if 'VWAP' in indicators:
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# --- Chart Drawing ---
def draw_chart(all_data):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.02,
                        subplot_titles=("Price", "MACD", "RSI"))

    colors = ['cyan', 'orange', 'green', 'magenta', 'yellow', 'red']

    for idx, (ticker, data) in enumerate(all_data.items()):
        c = colors[idx % len(colors)]

        # Candlestick
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'],
                                     close=data['Close'], name=f"{ticker} Candles"), row=1, col=1)

        if show_volume:
            fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name=f"{ticker} Volume", marker_color=c, opacity=0.3), row=1, col=1)

        if 'SMA_20' in data:
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'], name=f"{ticker} SMA 20", line=dict(color='blue')), row=1, col=1)
        if 'EMA_20' in data:
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_20'], name=f"{ticker} EMA 20", line=dict(color='red')), row=1, col=1)
        if 'BB_H' in data:
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_H'], name=f"{ticker} BB Upper", line=dict(color='gray')), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_L'], name=f"{ticker} BB Lower", line=dict(color='gray')), row=1, col=1)
        if 'VWAP' in data:
            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name=f"{ticker} VWAP", line=dict(color='white', dash='dot')), row=1, col=1)

        if 'MACD' in data:
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name=f"{ticker} MACD", line=dict(color=c)), row=2, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD_Signal'], name=f"{ticker} MACD Signal", line=dict(color='white', dash='dot')), row=2, col=1)

        if 'RSI' in data:
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name=f"{ticker} RSI", line=dict(color=c)), row=3, col=1)

        # 52 Week High/Low
        high_52w = data['High'].max()
        low_52w = data['Low'].min()
        fig.add_hline(y=high_52w, line=dict(color='green', dash='dot'), row=1, col=1)
        fig.add_hline(y=low_52w, line=dict(color='red', dash='dot'), row=1, col=1)

    fig.update_layout(template='plotly_dark', height=900, title="Stock Analysis")
    st.plotly_chart(fig, use_container_width=True)

# --- Performance Summary ---
def show_summary(data, ticker):
    perf = (data['Close'][-1] - data['Close'][0]) / data['Close'][0] * 100
    st.metric(label=f"{ticker} Performance ({period})", value=f"{perf:.2f}%")

# --- Download Buttons ---
def download_section(all_data):
    csv_data = []
    for ticker, df in all_data.items():
        df['Ticker'] = ticker
        csv_data.append(df)
    merged = pd.concat(csv_data)
    csv = merged.to_csv().encode('utf-8')
    st.download_button("📥 Download Data (CSV)", data=csv, file_name="stocks_data.csv", mime='text/csv')

# --- Main Section ---
ticker_list = [t.strip() for t in tickers.split(',')][:10]
all_data = {}
for ticker in ticker_list:
    data = fetch_data(ticker)
    if not data.empty:
        data = add_indicators(data)
        all_data[ticker] = data

if all_data:
    draw_chart(all_data)
    st.divider()
    st.subheader("Performance Summary")
    cols = st.columns(len(all_data))
    for idx, (ticker, df) in enumerate(all_data.items()):
        with cols[idx]:
            show_summary(df, ticker)

    st.divider()
    download_section(all_data)

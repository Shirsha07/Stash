import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date
import ta

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="📈 Stock Market Dashboard", initial_sidebar_state="expanded")

# --- Optional Logo & Title ---
st.markdown("<h1 style='text-align: center;'>📈 Stock Market Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# --- Sidebar Settings ---
st.sidebar.title("Settings")
tickers_input = st.sidebar.text_input("Enter up to 10 tickers (comma-separated)", "RELIANCE.NS, INFY.NS")
period = st.sidebar.selectbox("Select Period", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=1)
interval = st.sidebar.selectbox("Select Interval", ['1d', '1h', '30m', '15m'], index=0)
indicators = st.sidebar.multiselect("Technical Indicators", ['MACD', 'RSI', 'SMA', 'EMA', 'BBANDS', 'VWAP'], default=['MACD', 'RSI'])
show_volume = st.sidebar.toggle("Show Volume", value=True)

# --- Helper Functions ---
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period=period, interval=interval)
        return df.dropna()
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def add_indicators(df, selected):
    if 'RSI' in selected:
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close']).rsi()
    if 'MACD' in selected:
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
    if 'SMA' in selected:
        df['SMA'] = df['Close'].rolling(window=20).mean()
    if 'EMA' in selected:
        df['EMA'] = df['Close'].ewm(span=20).mean()
    if 'BBANDS' in selected:
        bb = ta.volatility.BollingerBands(close=df['Close'])
        df['BB_H'] = bb.bollinger_hband()
        df['BB_L'] = bb.bollinger_lband()
    if 'VWAP' in selected and 'Volume' in df.columns:
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

def draw_chart(df, ticker):
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.02,
        subplot_titles=[f"{ticker} Price", "MACD", "RSI"]
    )

    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name="Candlestick"), row=1, col=1)

    # Volume
    if show_volume:
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", opacity=0.3), row=1, col=1)

    # Indicators on main price chart
    if 'SMA' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA'], name="SMA", line=dict(color='blue')), row=1, col=1)
    if 'EMA' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA'], name="EMA", line=dict(color='red')), row=1, col=1)
    if 'BB_H' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_H'], name="BB Upper", line=dict(color='gray')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_L'], name="BB Lower", line=dict(color='gray')), row=1, col=1)
    if 'VWAP' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name="VWAP", line=dict(color='orange', dash='dot')), row=1, col=1)

    # MACD
    if 'MACD' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD", line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name="MACD Signal", line=dict(color='white', dash='dot')), row=2, col=1)

    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='violet')), row=3, col=1)

    fig.update_layout(template='plotly_dark', height=900, margin=dict(t=30, b=30))
    st.plotly_chart(fig, use_container_width=True)

# --- Main App Logic ---
ticker_list = [t.strip().upper() for t in tickers_input.split(",")][:10]
data_dict = {}

for ticker in ticker_list:
    df = fetch_data(ticker)
    if not df.empty:
        df = add_indicators(df, indicators)
        data_dict[ticker] = df
        st.markdown(f"### {ticker}")
        draw_chart(df, ticker)

# --- Download Section ---
if data_dict:
    st.subheader("📥 Download Combined Data")
    full_data = pd.concat([df.assign(Ticker=ticker) for ticker, df in data_dict.items()])
    csv = full_data.to_csv().encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="stock_data.csv", mime='text/csv')

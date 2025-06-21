# 🧠 Prediction Market Arbitrage Dashboard (Kalshi vs Polymarket)
# 📊 Auto-matches markets, checks prices, and shows arbitrage in a friendly web UI

import requests
import time
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Prediction Market Arbitrage Bot", layout="wide")

# --- Fetch all markets from both APIs ---
def fetch_kalshi_markets():
    try:
        r = requests.get("https://trading-api.kalshi.com/trade-api/v2/markets")
        return r.json()['markets']
    except:
        return []

def fetch_polymarket_markets():
    try:
        r = requests.get("https://api.polymarket.com/v3/markets")
        return r.json()['markets']
    except:
        return []

# --- Normalize market titles for matching ---
def normalize_title(title):
    return title.lower().replace("?", "").replace(",", "").replace(" ", "").strip()

# --- Auto-match markets by normalized title ---
def match_markets(kalshi, polymarkets):
    matches = []
    kalshi_lookup = {normalize_title(m['title']): m for m in kalshi}
    for pm in polymarkets:
        norm_title = normalize_title(pm['title'])
        if norm_title in kalshi_lookup:
            matches.append({
                'name': pm['title'],
                'kalshi': kalshi_lookup[norm_title],
                'polymarket': pm
            })
    return matches

# --- Extract best bid price for Kalshi YES ---
def get_kalshi_yes_bid(market):
    try:
        return float(market['order_books']['yes']['bids'][0]['price'])
    except:
        return None

# --- Extract Polymarket NO price ---
def get_polymarket_no_price(market):
    try:
        outcomes = market['outcomes']
        for o in outcomes:
            if o['name'].lower() == 'no':
                return float(o['price'])
    except:
        return None

# --- Calculate profit from arbitrage opportunity ---
def calculate_profit(total_cost, stake=100):
    payout = stake
    profit = payout - (total_cost * stake)
    return round(profit, 2)

# --- Streamlit App ---
st.title("📈 Prediction Market Arbitrage Dashboard")
st.write("This dashboard auto-matches Kalshi and Polymarket markets and finds arbitrage opportunities.")

stake_amount = st.sidebar.number_input("Enter stake amount ($)", min_value=1, value=100)

placeholder = st.empty()

while True:
    kalshi_data = fetch_kalshi_markets()
    poly_data = fetch_polymarket_markets()
    matches = match_markets(kalshi_data, poly_data)

    rows = []
    for pair in matches:
        k_price = get_kalshi_yes_bid(pair['kalshi'])
        p_price = get_polymarket_no_price(pair['polymarket'])
        if k_price is None or p_price is None:
            continue
        total = k_price + p_price
        is_arb = total < 1.0
        profit = calculate_profit(total, stake=stake_amount) if is_arb else None
        rows.append({
            'Market': pair['name'],
            'Kalshi YES ($)': round(k_price, 3),
            'Polymarket NO ($)': round(p_price, 3),
            'Total Cost': round(total, 3),
            'Arbitrage?': '✅' if is_arb else '',
            'Profit ($)': profit if is_arb else ''
        })

    df = None
    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values(by='Total Cost')

    with placeholder.container():
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.write("No matched markets or arbitrage detected.")

    time.sleep(30)

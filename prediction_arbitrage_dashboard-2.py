# 🧠 Prediction Market Arbitrage Dashboard (Kalshi vs Polymarket)
# 📊 Auto-matches markets using AI, checks prices, and shows arbitrage in a friendly web UI

import requests
import streamlit as st
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import openai

st.set_page_config(page_title="Prediction Market Arbitrage Bot", layout="wide")

# --- Use OpenAI API for real text embeddings ---
openai.api_key = st.secrets["OPENAI_API_KEY"]

def get_embedding(text):
    try:
        response = openai.Embedding.create(
            input=[text],
            model="text-embedding-3-small"
        )
        st.info(f"✅ Embedded: {text[:40]}...")
        return response["data"][0]["embedding"]
    except Exception as e:
        st.error(f"❌ Embedding error: {e}")
        return np.zeros(1536)

# --- Fetch all markets from Kalshi (requires auth) ---
def fetch_kalshi_markets():
    try:
        headers = {"Authorization": f"Bearer {st.secrets['KALSHI_API_KEY']}"}
        r = requests.get("https://trading-api.kalshi.com/trade-api/v2/markets", headers=headers)
        markets = r.json().get('markets', [])
        st.write(f"🟢 Kalshi markets fetched: {len(markets)}")
        return markets
    except Exception as e:
        st.error(f"Kalshi API error: {e}")
        return []

# --- Fetch all markets from Polymarket (may fail on Streamlit Cloud) ---
def fetch_polymarket_markets():
    try:
        r = requests.get("https://api.polymarket.com/v3/markets")
        markets = r.json().get('markets', [])
        st.write(f"🟣 Polymarket markets fetched: {len(markets)}")
        return markets
    except Exception as e:
        st.error(f"Polymarket API error: {e}")
        return []

# --- Extract polymarket title from various possible fields ---
def extract_polymarket_title(market):
    return market.get('question') or market.get('title') or market.get('slug') or 'unknown'

# --- Match markets by embedding similarity ---
def match_markets_ai(kalshi, polymarkets):
    matches = []
    for k in kalshi:
        k_title = k['title']
        k_embed = get_embedding(k_title)
        for p in polymarkets:
            p_title = extract_polymarket_title(p)
            p_embed = get_embedding(p_title)
            sim = cosine_similarity([k_embed], [p_embed])[0][0]
            st.text(f"Comparing: {k_title[:30]} ⇄ {p_title[:30]} | sim={sim:.2f}")
            if sim > 0.90:
                matches.append({
                    'name': k_title,
                    'kalshi': k,
                    'polymarket': p,
                    'similarity': round(sim, 3)
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
st.write("This dashboard uses OpenAI to match Kalshi and Polymarket markets and finds arbitrage opportunities.")

stake_amount = st.sidebar.number_input("Enter stake amount ($)", min_value=1, value=100)

# Always run logic without refresh button
kalshi_data = fetch_kalshi_markets()
poly_data = fetch_polymarket_markets()
matches = match_markets_ai(kalshi_data, poly_data)

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
        'Similarity': pair['similarity'],
        'Kalshi YES ($)': round(k_price, 3),
        'Polymarket NO ($)': round(p_price, 3),
        'Total Cost': round(total, 3),
        'Arbitrage?': '✅' if is_arb else '',
        'Profit ($)': profit if is_arb else ''
    })

if rows:
    df = pd.DataFrame(rows)
    df = df.sort_values(by='Total Cost')
    st.dataframe(df, use_container_width=True)
else:
    st.write("No matched markets or arbitrage detected.")

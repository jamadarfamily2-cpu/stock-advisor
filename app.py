import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import requests
import json

st.set_page_config(page_title="Shreya Stock Advisor", page_icon="📈", layout="wide")

GROQ_API_KEY = "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"

# ── STOCK UNIVERSE ──
SCAN_STOCKS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS",
    "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
    "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS",
    "TITAN.NS","WIPRO.NS","ULTRACEMCO.NS","BAJFINANCE.NS","NESTLEIND.NS",
    "POWERGRID.NS","NTPC.NS","ONGC.NS","TECHM.NS","HCLTECH.NS",
    "JSWSTEEL.NS","TATAMOTORS.NS","TATASTEEL.NS","ADANIENT.NS","ADANIPORTS.NS",
    "BAJAJFINSV.NS","BPCL.NS","BRITANNIA.NS","CIPLA.NS","COALINDIA.NS",
    "DIVISLAB.NS","DRREDDY.NS","EICHERMOT.NS","GRASIM.NS","HDFCLIFE.NS",
    "HEROMOTOCO.NS","HINDALCO.NS","INDUSINDBK.NS","SBILIFE.NS","SHRIRAMFIN.NS",
    "TATACONSUM.NS","VEDL.NS","BAJAJ-AUTO.NS","M&M.NS",
    "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
    "INDUSINDBK.NS","BANKBARODA.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","AUBANK.NS",
    "COLPAL.NS","PIDILITIND.NS","HAVELLS.NS","VOLTAS.NS","TRENT.NS",
    "ZOMATO.NS","IRCTC.NS","APOLLOHOSP.NS","LICI.NS","RVNL.NS",
    "IRFC.NS","PFC.NS","RECLTD.NS","POLYCAB.NS","DMART.NS",
]

STOCK_MAP = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS", "INFY": "INFY.NS", "SBIN": "SBIN.NS",
    "NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "KOTAKBANK": "KOTAKBANK.NS",
    "AXISBANK": "AXISBANK.NS", "LT": "LT.NS", "TITAN": "TITAN.NS",
    "WIPRO": "WIPRO.NS", "BAJFINANCE": "BAJFINANCE.NS", "MARUTI": "MARUTI.NS",
    "TATAMOTORS": "TATAMOTORS.NS", "ONGC": "ONGC.NS", "NTPC": "NTPC.NS",
    "SHRIRAMFIN": "SHRIRAMFIN.NS", "HINDALCO": "HINDALCO.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS", "INDUSINDBK": "INDUSINDBK.NS",
    "HCLTECH": "HCLTECH.NS", "SUNPHARMA": "SUNPHARMA.NS",
    "BHARTIARTL": "BHARTIARTL.NS", "ITC": "ITC.NS", "M&M": "M&M.NS",
    "ADANIENT": "ADANIENT.NS", "TATASTEEL": "TATASTEEL.NS",
    "COLPAL": "COLPAL.NS", "COLGATE": "COLPAL.NS",
    "NESTLEIND": "NESTLEIND.NS", "NESTLE": "NESTLEIND.NS",
    "PIDILITIND": "PIDILITIND.NS", "PIDILITE": "PIDILITIND.NS",
    "HAVELLS": "HAVELLS.NS", "VOLTAS": "VOLTAS.NS",
    "ZOMATO": "ZOMATO.NS", "IRCTC": "IRCTC.NS",
    "DMART": "DMART.NS", "TRENT": "TRENT.NS",
    "APOLLOHOSP": "APOLLOHOSP.NS", "APOLLO": "APOLLOHOSP.NS",
    "LICI": "LICI.NS", "LIC": "LICI.NS",
    "RVNL": "RVNL.NS", "IRFC": "IRFC.NS",
    "PFC": "PFC.NS", "RECLTD": "RECLTD.NS", "REC": "RECLTD.NS",
    "COALINDIA": "COALINDIA.NS", "COAL": "COALINDIA.NS",
    "BRITANNIA": "BRITANNIA.NS", "CIPLA": "CIPLA.NS",
    "DRREDDY": "DRREDDY.NS", "DIVISLAB": "DIVISLAB.NS",
    "BANDHANBNK": "BANDHANBNK.NS", "YESBANK": "YESBANK.NS",
    "POLYCAB": "POLYCAB.NS", "PFC": "PFC.NS",
}

# ── HELPERS ──
def ist_now():
    return datetime.now(pytz.timezone("Asia/Kolkata"))

def is_market_open():
    now = ist_now()
    return (now.weekday() < 5 and time(9,15) <= now.time() <= time(15,30)), now

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def compute_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def compute_bollinger(series, period=20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    return sma + 2*std, sma, sma - 2*std

def get_live_price(symbol):
    """Get current live price for any stock"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return round(data["Close"].iloc[-1], 2)
        data = ticker.history(period="2d", interval="5m")
        if not data.empty:
            return round(data["Close"].iloc[-1], 2)
    except Exception:
        pass
    return None

def analyze_stock(symbol):
    try:
        df = yf.Ticker(symbol).history(period="5d", interval="15m")
        if df.empty or len(df) < 20:
            return None
        close = df["Close"]
        volume = df["Volume"]
        rsi = compute_rsi(close).iloc[-1]
        macd, signal = compute_macd(close)
        upper_bb, mid_bb, lower_bb = compute_bollinger(close)
        current_price = close.iloc[-1]
        prev_close = close.iloc[-2]
        change_pct = ((current_price - prev_close) / prev_close) * 100
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1] if len(close) >= 50 else ema20
        avg_vol = volume.rolling(20).mean().iloc[-1]
        vol_surge = (volume.iloc[-1] / avg_vol) if avg_vol > 0 else 1.0

        score = 0
        signals = []
        if rsi < 35:
            score += 3; signals.append(f"RSI oversold {rsi:.1f}")
        elif rsi < 45:
            score += 1; signals.append(f"RSI low {rsi:.1f}")
        elif rsi > 70:
            score -= 2; signals.append(f"RSI overbought {rsi:.1f}")
        if macd.iloc[-1] > signal.iloc[-1]:
            score += 2; signals.append("MACD bullish")
        else:
            score -= 1
        if current_price <= lower_bb.iloc[-1] * 1.01:
            score += 2; signals.append("Bollinger support")
        elif current_price >= upper_bb.iloc[-1] * 0.99:
            score -= 2; signals.append("Bollinger resistance")
        if ema20 > ema50:
            score += 1; signals.append("Uptrend EMA")
        if vol_surge > 1.5:
            score += 2; signals.append(f"Volume {vol_surge:.1f}x")
        if change_pct > 0:
            score += 1

        return {
            "symbol": symbol, "price": round(current_price, 2),
            "change_pct": round(change_pct, 2), "rsi": round(rsi, 1),
            "macd": round(macd.iloc[-1], 4), "macd_signal": round(signal.iloc[-1], 4),
            "upper_bb": round(upper_bb.iloc[-1], 2), "lower_bb": round(lower_bb.iloc[-1], 2),
            "ema20": round(ema20, 2), "ema50": round(ema50, 2),
            "vol_surge": round(vol_surge, 2), "score": score, "signals": signals,
        }
    except Exception:
        return None

def get_nifty_data():
    try:
        hist = yf.Ticker("^NSEI").history(period="2d", interval="1d")
        if len(hist) >= 2:
            prev, curr = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
            return round(curr, 2), round(((curr-prev)/prev)*100, 2)
    except Exception:
        pass
    return None, None

def call_groq(messages):
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 800,
                "temperature": 0.2,
                "stop": ["---", "Note:", "Disclaimer:"]
            },
            timeout=60
        )
        result = response.json()
        if "choices" in result:
            text = result["choices"][0]["message"]["content"]
            # Remove repetitive lines
            lines = text.split("\n")
            seen = set()
            clean_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and stripped not in seen:
                    seen.add(stripped)
                    clean_lines.append(line)
            return "\n".join(clean_lines)
        return f"Error: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_market_time_context():
    now = ist_now()
    h = now.hour
    m = now.minute
    if h < 9 or (h == 9 and m < 15):
        return "बाजार उघडण्यापूर्वी (Pre-market)", "आज कोणते trade घ्यायचे ते plan करा"
    elif h == 9 and m < 30:
        return "बाजार नुकताच उघडला (Opening)", "opening volatility आहे — 9:30 नंतर trade घ्या"
    elif h < 11:
        return "सकाळचे trading (Morning)", "momentum trades साठी चांगला वेळ"
    elif h < 13:
        return "दुपारचे trading (Midday)", "trend follow करा"
    elif h < 14:
        return "दुपार नंतर (Afternoon)", "existing positions manage करा"
    elif h < 15:
        return "बाजार बंद होण्यापूर्वी (Pre-close)", "intraday positions close करा — 3:20 पर्यंत exit करा"
    else:
        return "बाजार बंद (After market)", "उद्यासाठी plan करा"

def get_main_recommendation(investment_amount, top_stocks, nifty_price, nifty_change, instrument_pref, risk_level):
    stocks_text = ""
    for s in top_stocks[:5]:
        stocks_text += f"- {s['symbol'].replace('.NS','')}: ₹{s['price']}, बदल {s['change_pct']}%, RSI {s['rsi']}, Score {s['score']}, Signals: {', '.join(s['signals'][:3])}\n"

    trend = "तेजी" if nifty_change and nifty_change > 0.3 else "मंदी" if nifty_change and nifty_change < -0.3 else "तटस्थ"
    today = ist_now().strftime("%d %B %Y")
    weekday = ist_now().strftime("%A")
    market_time, time_advice = get_market_time_context()

    if "F&O" in instrument_pref:
        format_text = f"""आजचे market analysis करून F&O strategy सांगा:

📊 बाजार विश्लेषण:
[आज market कुठे जाणार — bullish/bearish/sideways आणि का]

🎯 F&O Strategy:
- कोणता stock/index निवडावा आणि का
- Call घ्यावा की Put आणि का
- Strike: ITM/ATM/OTM कोणते योग्य आणि का
- ₹{investment_amount:,} मध्ये किती lots घेता येतील (lot size सांगा)
- Entry zone: premium range
- Target premium (₹500 नफ्यासाठी)
- Stop Loss premium
- Weekly की monthly expiry योग्य आणि का"""
    elif "ETF" in instrument_pref:
        format_text = f"""आजचे market analysis करून ETF strategy सांगा:

📊 बाजार विश्लेषण:
[आज market कुठे जाणार आणि का]

🎯 ETF Strategy:
- कोणता ETF निवडावा आणि का
- ₹{investment_amount:,} मध्ये किती units
- Entry price zone
- Target (₹500 नफ्यासाठी)
- Stop Loss"""
    else:
        format_text = f"""आजचे market analysis करून Stock strategy सांगा:

📊 बाजार विश्लेषण:
[आज market कुठे जाणार आणि का]

🎯 Stock Strategy:
- कोणता stock निवडावा आणि का
- ₹{investment_amount:,} मध्ये किती shares
- Entry price zone
- Target 1 आणि Target 2
- Stop Loss
- ₹500 नफा कसा मिळेल"""

    prompt = f"""तुम्ही तज्ञ भारतीय शेअर बाजार विश्लेषक आहात. फक्त मराठीत उत्तर द्या.
कोणतीही section किंवा line repeat करू नका. प्रत्येक section एकदाच लिहा.

आजची तारीख: {today} ({weekday})
बाजार वेळ: {market_time} — {time_advice}
Nifty 50: ₹{nifty_price} ({nifty_change}%), कल = {trend}
उपलब्ध रक्कम: फक्त ₹{investment_amount:,}
लक्ष्य: ₹500 नफा
जोखीम: {risk_level}

Top Stocks (live scan):
{stocks_text}

{format_text}

📈 तांत्रिक कारणे (प्रत्येक एकदाच):
• RSI: [explain]
• MACD: [explain]
• Volume: [explain]
• Support/Resistance: [explain]

⏰ वेळ:
- प्रवेश: [best entry time]
- Exit: [3:15 पूर्वी]

⚠️ सावधगिरी: [1 line]"""

    return call_groq([
        {"role": "system", "content": "Expert Indian stock market analyst. Always respond in Marathi only. Give exact numbers. Today's goal: ₹500 profit from given investment amount. For F&O expiry dates: DO NOT guess specific dates. Write 'nearest Thursday expiry' or 'current week expiry'. Never write a specific date unless you are 100% sure."},
        {"role": "user", "content": prompt}
    ])

def get_chat_response(user_question, investment_amount, nifty_price, nifty_change, chat_history):
    stock_data_text = ""
    question_upper = user_question.upper()

    # Detect stocks mentioned and get live prices
    detected_stocks = []
    for stock_name, symbol in STOCK_MAP.items():
        if stock_name in question_upper:
            price = get_live_price(symbol)
            data = analyze_stock(symbol)
            if price or data:
                actual_price = price or (data['price'] if data else 'N/A')
                stock_data_text += f"\n{stock_name} live data:\n"
                stock_data_text += f"- Current Price: ₹{actual_price}\n"
                if data:
                    stock_data_text += f"- RSI: {data['rsi']}\n"
                    stock_data_text += f"- MACD: {'Bullish' if data['macd'] > data['macd_signal'] else 'Bearish'}\n"
                    stock_data_text += f"- Volume: {data['vol_surge']}x average\n"
                    stock_data_text += f"- Bollinger: Upper ₹{data['upper_bb']}, Lower ₹{data['lower_bb']}\n"
                    stock_data_text += f"- Score: {data['score']}/10\n"
                detected_stocks.append(stock_name)

    today = ist_now().strftime("%d %B %Y")
    market_time, time_advice = get_market_time_context()

    messages = [
        {"role": "system", "content": f"""तुम्ही तज्ञ भारतीय शेअर बाजार विश्लेषक आहात.
फक्त मराठीत उत्तर द्या. Concise आणि specific उत्तर द्या.
आजची तारीख: {today}
बाजार वेळ: {market_time}
गुंतवणूक: ₹{investment_amount:,}
Nifty: ₹{nifty_price} ({nifty_change}%)
{stock_data_text}
Exact numbers द्या. Hold/Exit decisions साठी current price वापरा."""}
    ]

    for msg in chat_history[-4:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_question})

    return call_groq(messages)

# ── MAIN UI ──
st.title("📈 Shreya's AI Stock Advisor")
st.caption("रोज ₹2,000 → ₹500 नफा | Nifty 50 + F&O + Bank Nifty स्कॅन | मराठीत सल्ला")

market_open, now_ist = is_market_open()
market_time_label, time_advice = get_market_time_context()

if market_open:
    st.success(f"🟢 बाजार उघडा | {now_ist.strftime('%d %b %Y, %I:%M %p')} IST | {market_time_label}")
else:
    st.warning(f"🔴 {market_time_label} | {now_ist.strftime('%d %b %Y, %I:%M %p')} IST")
    st.info(f"💡 {time_advice}")

st.divider()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "nifty_price" not in st.session_state:
    st.session_state.nifty_price = 24000
if "nifty_change" not in st.session_state:
    st.session_state.nifty_change = 0

with st.sidebar:
    st.header("⚙️ तुमची माहिती")
    investment_amount = st.number_input("💰 आजची रक्कम (₹)", min_value=1000, max_value=500000, value=2000, step=500)
    instrument_pref = st.selectbox("📊 कोणत्या प्रकारात?", ["AI ठरवू दे (Best opportunity)", "Stock (Intraday)", "ETF", "F&O (Options)"])
    risk_level = st.select_slider("⚡ जोखीम", options=["कमी", "मध्यम", "जास्त"], value="मध्यम")
    st.divider()
    st.success(f"**रक्कम:** ₹{investment_amount:,}\n\n**लक्ष्य नफा:** ₹500")
    analyze_btn = st.button("🔍 आजचे विश्लेषण सुरू करा", type="primary", use_container_width=True)
    if st.button("🗑️ Chat साफ करा", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ── SCAN SECTION ──
if analyze_btn:
    st.subheader("📊 बाजार स्थिती...")
    nifty_price, nifty_change = get_nifty_data()
    st.session_state.nifty_price = nifty_price or 24000
    st.session_state.nifty_change = nifty_change or 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nifty 50", f"₹{nifty_price:,}" if nifty_price else "N/A", f"{nifty_change}%" if nifty_change else "")
    with col2:
        sentiment = "🟢 तेजी" if (nifty_change and nifty_change > 0.3) else "🔴 मंदी" if (nifty_change and nifty_change < -0.3) else "🟡 तटस्थ"
        st.metric("बाजार कल", sentiment)
    with col3:
        st.metric("तुमची रक्कम", f"₹{investment_amount:,}")
    with col4:
        st.metric("लक्ष्य नफा", "₹500")

    st.subheader("🔍 Stocks स्कॅन होत आहे...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    all_symbols = list(set(SCAN_STOCKS))
    results = []
    for i, sym in enumerate(all_symbols):
        status_text.text(f"Scanning {sym.replace('.NS','')}...")
        progress_bar.progress((i + 1) / len(all_symbols) * 0.8)
        data = analyze_stock(sym)
        if data:
            results.append(data)

    top_stocks = sorted(results, key=lambda x: x["score"], reverse=True)

    st.subheader("🏆 Top 5 आजचे Best Stocks")
    top5 = top_stocks[:5]
    if top5:
        cols = st.columns(5)
        for i, stock in enumerate(top5):
            with cols[i]:
                st.metric(label=stock["symbol"].replace(".NS",""), value=f"₹{stock['price']}", delta=f"{stock['change_pct']}%")
                st.caption(f"RSI: {stock['rsi']} | Score: {stock['score']}")

    st.subheader("🤖 AI सल्ला तयार होत आहे...")
    progress_bar.progress(0.9)

    with st.spinner("AI विश्लेषण करत आहे..."):
        recommendation = get_main_recommendation(
            investment_amount, top_stocks,
            nifty_price, nifty_change, instrument_pref, risk_level
        )

    progress_bar.progress(1.0)
    status_text.text("✅ पूर्ण!")

    st.divider()
    st.subheader("🎯 आजचा Trade Plan")
    st.markdown(
        f'<div style="background:#f0f8f0;padding:24px;border-radius:12px;border-left:5px solid #28a745;font-size:16px;line-height:2.2;">{recommendation.replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True
    )
    st.warning("⚠️ हा AI सल्ला माहितीसाठी आहे. SEBI registered advisor चा सल्ला घ्या.")
    st.caption(f"वेळ: {ist_now().strftime('%d %B %Y, %I:%M %p IST')}")

else:
    st.info("👈 रक्कम टाका → **'आजचे विश्लेषण सुरू करा'** दाबा → AI exact trade plan देईल!")

# ── CHAT SECTION ──
st.divider()
st.subheader("💬 कोणताही प्रश्न विचारा")
st.caption("उदा: 'COLPAL 2300 CALL HOLD करू का?' | 'RELIANCE आज कसा आहे?' | 'माझा trade profit मध्ये आहे का?'")

for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(msg["content"])

user_input = st.chat_input("तुमचा प्रश्न इथे लिहा...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Live data बघत आहे..."):
            response = get_chat_response(
                user_input, investment_amount,
                st.session_state.nifty_price,
                st.session_state.nifty_change,
                st.session_state.chat_history[:-1]
            )
        st.markdown(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import requests
import json

# CONFIG
st.set_page_config(page_title="Shreya Stock Advisor", page_icon="📈", layout="wide")

OPENROUTER_API_KEY = "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"

# STOCK UNIVERSE
NIFTY50 = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS",
    "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
    "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS",
    "TITAN.NS","WIPRO.NS","ULTRACEMCO.NS","BAJFINANCE.NS","NESTLEIND.NS",
    "POWERGRID.NS","NTPC.NS","ONGC.NS","TECHM.NS","HCLTECH.NS",
    "JSWSTEEL.NS","TATAMOTORS.NS","TATASTEEL.NS","ADANIENT.NS","ADANIPORTS.NS",
    "BAJAJFINSV.NS","BPCL.NS","BRITANNIA.NS","CIPLA.NS","COALINDIA.NS",
    "DIVISLAB.NS","DRREDDY.NS","EICHERMOT.NS","GRASIM.NS","HDFCLIFE.NS",
    "HEROMOTOCO.NS","HINDALCO.NS","INDUSINDBK.NS","SBILIFE.NS","SHRIRAMFIN.NS",
    "TATACONSUM.NS","UPL.NS","VEDL.NS","BAJAJ-AUTO.NS","M&M.NS"
]

BANK_NIFTY = [
    "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
    "INDUSINDBK.NS","BANKBARODA.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","AUBANK.NS"
]

ETFS = {
    "Nifty BeES": "NIFTYBEES.NS",
    "Bank BeES": "BANKBEES.NS",
    "Gold BeES": "GOLDBEES.NS",
    "IT BeES": "ITBEES.NS",
}

# HELPERS
def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    market_open = time(9, 15)
    market_close = time(15, 30)
    return (now.weekday() < 5 and market_open <= now.time() <= market_close), now

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

def call_openrouter(prompt, model):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://shreya-stock-advisor.streamlit.app",
                "X-Title": "Shreya Stock Advisor",
            },
            data=json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are an expert Indian stock market analyst. Always respond in Marathi language only. Give specific actionable trade recommendations with exact numbers."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.3,
            }),
            timeout=60
        )
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0]["message"]["content"]
            if text and len(text) > 50:
                return text
        return None
    except Exception:
        return None

def get_ai_recommendation(investment_amount, top_stocks, etf_data, nifty_price, nifty_change, instrument_pref, risk_level):
    stocks_text = ""
    for s in top_stocks[:5]:
        stocks_text += f"- {s['symbol'].replace('.NS','')}: किंमत ₹{s['price']}, बदल {s['change_pct']}%, RSI {s['rsi']}, Score {s['score']}, Signals: {', '.join(s['signals'][:3])}\n"

    etf_text = ""
    for name, data in etf_data.items():
        if data:
            etf_text += f"- {name}: ₹{data['price']}, बदल {data['change_pct']}%, RSI {data['rsi']}\n"

    trend = "तेजी (Bullish)" if nifty_change and nifty_change > 0.3 else "मंदी (Bearish)" if nifty_change and nifty_change < -0.3 else "तटस्थ (Sideways)"

    prompt = f"""तुम्ही एक तज्ञ भारतीय शेअर बाजार विश्लेषक आहात. खालील data वापरून आजचा एकच सर्वोत्तम intraday trade सुचवा.

बाजार माहिती:
- Nifty 50: ₹{nifty_price} ({nifty_change}% आज)
- बाजार कल: {trend}

गुंतवणूकदार:
- रक्कम: ₹{investment_amount:,}
- जोखीम: {risk_level}
- प्राधान्य: {instrument_pref}

आजचे Top Stocks (Nifty 50 + Bank Nifty स्कॅन):
{stocks_text}

ETF data:
{etf_text}

खालील format मध्ये मराठीत उत्तर द्या:

📊 आजचे बाजाराचे विश्लेषण:
[आज बाजार कसा आहे आणि का - 2-3 वाक्ये]

🎯 आजची सर्वोत्तम संधी: [STOCK NAME]
प्रकार: [Stock Intraday]

💰 गुंतवणूक योजना (₹{investment_amount:,} साठी):
- खरेदी किंमत: ₹[exact number]
- प्रमाण (Quantity): [exact number] shares
- एकूण गुंतवणूक: ₹[total]
- लक्ष्य किंमत 1: ₹[target1]
- लक्ष्य किंमत 2: ₹[target2]
- स्टॉप लॉस: ₹[stoploss]
- अपेक्षित नफा: ₹[profit at T1]
- जास्तीत जास्त तोटा: ₹[max loss]

📈 तांत्रिक कारणे:
• RSI: [मराठीत explain]
• MACD: [मराठीत explain]
• Volume: [मराठीत explain]
• Support: [मराठीत explain]

⏰ वेळ:
- प्रवेश वेळ: [best entry time]
- बाहेर पडण्याची वेळ: [exit time]

⚠️ सावधगिरी: [risk warning मराठीत]"""

    models = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-3-4b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free",
    ]

    for model in models:
        result = call_openrouter(prompt, model)
        if result:
            return result, model

    return "सर्व AI models अनुपलब्ध आहेत. OpenRouter account मध्ये credits check करा.", "none"

# MAIN UI
st.title("📈 Shreya's AI Stock Advisor")
st.caption("Nifty 50 + Bank Nifty संपूर्ण स्कॅन → आजची सर्वोत्तम संधी → मराठीत सल्ला")

market_open, now_ist = is_market_open()
if market_open:
    st.success(f"🟢 बाजार उघडा आहे | {now_ist.strftime('%d %b %Y, %I:%M %p')} IST")
else:
    st.warning(f"🔴 बाजार बंद आहे | {now_ist.strftime('%d %b %Y, %I:%M %p')} IST")

st.divider()

with st.sidebar:
    st.header("⚙️ तुमची माहिती")
    investment_amount = st.number_input("💰 आजची गुंतवणूक रक्कम (₹)", min_value=1000, max_value=1000000, value=10000, step=1000)
    instrument_pref = st.selectbox("📊 कोणत्या प्रकारात?", ["AI ठरवू दे (Best opportunity)", "Stock (Intraday)", "ETF", "F&O (Options)"])
    risk_level = st.select_slider("⚡ जोखीम पातळी", options=["कमी (Conservative)", "मध्यम (Moderate)", "जास्त (Aggressive)"], value="मध्यम (Moderate)")
    st.divider()
    st.info(f"**Investment:** ₹{investment_amount:,}\n\n**Type:** {instrument_pref}\n\n**Risk:** {risk_level}")
    analyze_btn = st.button("🔍 आजचे विश्लेषण सुरू करा", type="primary", use_container_width=True)

if analyze_btn:
    st.subheader("📊 Step 1: बाजार स्थिती तपासत आहे...")
    nifty_price, nifty_change = get_nifty_data()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nifty 50", f"₹{nifty_price:,}" if nifty_price else "N/A", f"{nifty_change}%" if nifty_change else "")
    with col2:
        sentiment = "🟢 तेजी" if (nifty_change and nifty_change > 0.3) else "🔴 मंदी" if (nifty_change and nifty_change < -0.3) else "🟡 तटस्थ"
        st.metric("बाजार कल", sentiment)
    with col3:
        st.metric("गुंतवणूक", f"₹{investment_amount:,}")

    st.subheader("🔍 Step 2: Nifty 50 + Bank Nifty स्कॅन होत आहे...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    all_symbols = list(set(NIFTY50 + BANK_NIFTY))
    results = []
    for i, sym in enumerate(all_symbols):
        status_text.text(f"Scanning {sym.replace('.NS','')}...")
        progress_bar.progress((i + 1) / len(all_symbols) * 0.75)
        data = analyze_stock(sym)
        if data:
            results.append(data)

    top_stocks = sorted(results, key=lambda x: x["score"], reverse=True)

    status_text.text("ETFs तपासत आहे...")
    etf_data = {}
    for i, (name, symbol) in enumerate(ETFS.items()):
        progress_bar.progress(0.75 + 0.1 * (i+1) / len(ETFS))
        etf_data[name] = analyze_stock(symbol)

    st.subheader("🏆 Top 5 सर्वोत्तम Stocks")
    top5 = top_stocks[:5]
    if top5:
        cols = st.columns(5)
        for i, stock in enumerate(top5):
            with cols[i]:
                name = stock["symbol"].replace(".NS", "")
                st.metric(label=name, value=f"₹{stock['price']}", delta=f"{stock['change_pct']}%")
                st.caption(f"RSI: {stock['rsi']} | Score: {stock['score']}")

    st.subheader("🤖 Step 3: AI सल्ला तयार होत आहे...")
    progress_bar.progress(0.9)
    status_text.text("AI विश्लेषण करत आहे... थोडं wait करा...")

    with st.spinner("AI विश्लेषण करत आहे... (30-60 seconds)"):
        recommendation, model_used = get_ai_recommendation(
            investment_amount, top_stocks, etf_data,
            nifty_price, nifty_change, instrument_pref, risk_level
        )

    progress_bar.progress(1.0)
    status_text.text("✅ विश्लेषण पूर्ण!")

    st.divider()
    st.subheader("🎯 AI चा आजचा सल्ला")
    st.caption(f"Model: {model_used}")
    st.markdown(
        f'<div style="background:#f0f8f0;padding:24px;border-radius:12px;border-left:5px solid #28a745;font-size:16px;line-height:2.2;">{recommendation.replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True
    )

    st.divider()
    st.warning("⚠️ हा AI सल्ला फक्त माहितीसाठी आहे. गुंतवणूक करताना स्वतःचा विवेक वापरा. SEBI registered advisor चा सल्ला घ्या.")
    st.caption(f"विश्लेषण वेळ: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y, %I:%M %p IST')}")

else:
    st.info("👈 डाव्या बाजूला रक्कम टाका आणि **'आजचे विश्लेषण सुरू करा'** दाबा!\n\nAI Nifty 50 + Bank Nifty स्कॅन करून आजची एकच सर्वोत्तम संधी सांगेल — exact buy, target, stop loss सह!")
    st.markdown("""
    | | वैशिष्ट्य |
    |---|---|
    | 🔍 | Nifty 50 + Bank Nifty संपूर्ण स्कॅन |
    | 📊 | RSI, MACD, Bollinger, Volume analysis |
    | 🏆 | Score-based best opportunity |
    | 💰 | तुमच्या रकमेनुसार exact trade plan |
    | 🗣️ | मराठीत संपूर्ण सल्ला |
    """)

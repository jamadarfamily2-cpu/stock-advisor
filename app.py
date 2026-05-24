import streamlit as st
import yfinance as yf
import requests

st.set_page_config(page_title="AI Stock Advisor", page_icon="📈")

OPENROUTER_API_KEY = "इथे तुझी OpenRouter key paste कर"

def get_stock_data(symbol):
    try:
        stock = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True)
        delta = stock['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        stock['RSI'] = 100 - (100 / (1 + rs))
        price = round(stock['Close'].iloc[-1].item(), 2)
        rsi = round(stock['RSI'].iloc[-1].item(), 2)
        return price, rsi
    except:
        return None, None

def get_ai_suggestion(amt, stock_info, trade_type):
    if trade_type == "Stocks":
        prompt = "You are Indian stock market advisor. Reply in Marathi only. I have Rs " + str(amt) + " to invest today in stocks. Market data:\n" + stock_info + "\nGive specific stock buy suggestion with exact amount allocation and reason based on RSI value. Be specific."
    elif trade_type == "F&O (Paper Trade)":
        prompt = "You are Indian stock market advisor. Reply in Marathi only. I have Rs " + str(amt) + " and want to learn F&O paper trading today. Market data:\n" + stock_info + "\nSuggest: 1) Nifty or BankNifty Call or Put option 2) Strike price 3) Why based on market trend 4) Risk warning. This is for learning only."
    else:
        prompt = "You are Indian stock market advisor. Reply in Marathi only. I have Rs " + str(amt) + " to invest today. Market data:\n" + stock_info + "\nGive: 1) Stock suggestion with amount 2) F&O paper trade suggestion for learning 3) Risk level for each. Be specific."

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer " + OPENROUTER_API_KEY},
        json={"model": "nvidia/nemotron-3-super-120b-a12b:free", "messages": [{"role": "user", "content": prompt}]}
    )
    data = response.json()
    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    return "Error आला — परत try करा"

st.title("AI Stock Advisor")
st.caption("रोज सकाळी market analyze करा")

amt = st.number_input("आज किती invest करायचे? (Rs)", min_value=100, max_value=100000, value=2000, step=500)

trade_type = st.radio("काय बघायचे आहे?", ["Stocks", "F&O (Paper Trade)", "दोन्ही"])

if st.button("Market Analyze करा"):
    stocks = {"RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC Bank": "HDFCBANK.NS", "Infosys": "INFY.NS", "Nifty": "^NSEI", "BankNifty": "^NSEBANK"}
    stock_info = ""
    st.subheader("Market Status")
    cols = st.columns(2)
    i = 0
    for name, symbol in stocks.items():
        price, rsi = get_stock_data(symbol)
        if price:
            signal = "BUY" if rsi < 40 else ("SELL" if rsi > 70 else "HOLD")
            with cols[i % 2]:
                st.metric(label=name, value="Rs " + str(price), delta="RSI: " + str(rsi) + " - " + signal)
            stock_info += name + ": Rs" + str(price) + " RSI=" + str(rsi) + "\n"
            i += 1

    st.subheader("AI Suggestion")
    with st.spinner("AI विचार करतोय..."):
        suggestion = get_ai_suggestion(amt, stock_info, trade_type)
    st.write(suggestion)
    
    if "F&O" in trade_type:
        st.error("⚠️ F&O खूप risky आहे! हे फक्त paper trade साठी — real पैसे लावू नका!")
    st.warning("हे educational आहे. Real investment साठी SEBI advisor चा सल्ला घ्या.")

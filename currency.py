import asyncio
import csv, os, streamlit as st
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import requests

def send_to_telegram(photo_path, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, "rb") as photo:
        response = requests.post(url, data={"chat_id": chat_id}, files={"photo": photo})
    return response.json()


def scrape_value(country):
    url = f"https://www.klmoneychanger.com/compare-rates?n={country}"  
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # First attempt: find <td style="font-size: 22px;color:red">
    value_td = soup.select_one('td[style*="font-size: 22px;color:red"]')
    value = value_td.get_text(strip=True) if value_td else None

    # If not found or <= 0, fall back to the 6th <tr>
    try:
        if value is None or float(value) <= 0:
            fallback_td = soup.select_one("table tr:nth-of-type(6) td[style*='font-size: 22px;color:red']")
            if fallback_td:
                value = fallback_td.get_text(strip=True)
    except ValueError:
        pass  # in case conversion to float fails

    print(value)
    return value


def save_to_csv(value):
    filename="data.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["datetime"] + list(value.keys()))
        writer.writerow([datetime.now().isoformat()] + list(value.values()))


def update_graph(selected, filename="data.csv", graph="graph.png"):
    df = pd.read_csv(filename)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    if len(df) >= 28:
        df["date"] = df["datetime"].dt.date
        df = df.groupby("date").mean(numeric_only=True)
        df.set_index("date", inplace=True)
    plot_df=df.copy()
    if selected == "monthly":
        plot_df = df.resample("ME").mean()
        plot_df.index= plot_df.index.strftime("%b").last("12ME")
        st.subheader("Monthly Trend (Average)")
    else:
        days=0
        if selected == "28days":
            days=28
            st.subheader("Last 28 Days (Daily)")
        elif selected == "90days":
            days=90
            st.subheader("3-Month Trend (Daily)")
        end = df.index.max()             
        start = end - timedelta(days) 
        plot_df = df.loc[start:end]

    # --- Plot ---
    fig, axes = plt.subplots(len(plot_df.columns), 1, figsize=(10, 2*len(plot_df.columns)), sharex=True)
    if len(plot_df.columns) == 1:
        axes = [axes]

    for ax, col in zip(axes, plot_df.columns):
        ax.plot(plot_df.index, plot_df[col], marker="o", label=col)
        ax.set_ylabel(col)
        x = plot_df.index[-1]
        y = plot_df[col].iloc[-1]
        ax.text(x, y, f"{y:.2f}", ha="left", va="bottom")
        ax.grid(True)
    plt.xlabel("Date")
    plt.savefig(graph)
    st.pyplot(fig)
    result = send_to_telegram(graph_file, BOT_TOKEN, CHAT_ID)
   
if __name__ == "__main__":
    value={}
    currency=['JPY','TWD','THB','CNY','USD']
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  
    graph_file='graph.png'
    for country in currency:
        value[country] = scrape_value(country)
    save_to_csv(value)
    st.title("Currency Trend Dashboard")
    col1, col2, col3 = st.columns(3)
    
    selected = None
    update_graph(selected)
    if col1.button("28 Days"):
        selected = "28days"
    if col2.button("90 Days"):
        selected = "90days"
    if col3.button("Monthly Trend"):
        selected = "monthly"
    
    

# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 07:59:41 2025

@author: admin
"""

import asyncio
import csv, os
from datetime import datetime
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


def update_graph(filename="data.csv", graph="graph.png"):
    df = pd.read_csv(filename)
    df["datetime"] = pd.to_datetime(df["datetime"])
    if len(df) >= 28:
        df["date"] = df["datetime"].dt.date
        df = df.groupby("date").mean(numeric_only=True)
        df.set_index("date", inplace=True)
        
    df.set_index("datetime", inplace=True)
    axes = df.plot(subplots=True, figsize=(10,8), marker="o", grid=True, legend=True)

    for i, col in enumerate(df.columns):
        ax = axes[i]
        x = df.index[-1]
        y = df[col].iloc[-1]
        ax.text(x, y, f"{y:.2f}", fontsize=9, ha="left", va="bottom")
    
    plt.suptitle("Currencies over Time", fontsize=14)
    plt.tight_layout()
    plt.savefig(graph)
    plt.close()
    
if __name__ == "__main__":
    value={}
    currency=['JPY','TWD','THB','CNY','USD']
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  
    graph_file='graph.png'
    for country in currency:
        value[country] = scrape_value(country)
    save_to_csv(value)
    update_graph()
    print(f"[{datetime.now()}] Saved value: {value}")
    result = send_to_telegram(graph_file, BOT_TOKEN, CHAT_ID)
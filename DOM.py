import pandas as pd
import requests

# Fetch Binance Order Book Data
url = "https://api.binance.com/api/v3/depth"
params = {"symbol": "BTCUSDT", "limit": 5000}
response = requests.get(url, params=params)
order_book = response.json()

# Create DataFrame
df = pd.DataFrame(
    {
        "Bid Price": [float(bid[0]) for bid in order_book["bids"]],
        "Bid Quantity": [float(bid[1]) for bid in order_book["bids"]],
        "Ask Price": [float(ask[0]) for ask in order_book["asks"]],
        "Ask Quantity": [float(ask[1]) for ask in order_book["asks"]],
    }
)

print(df)

# Calculate Total Liquidity
total_bid_volume = df["Bid Quantity"].sum()
total_ask_volume = df["Ask Quantity"].sum()

# Determine Order Book Imbalance
imbalance = total_bid_volume - total_ask_volume
dominance = "Buyers (Bullish)" if imbalance > 0 else "Sellers (Bearish)"

# Display Results
print(f"Total Bid Volume: {total_bid_volume:.2f}")
print(f"Total Ask Volume: {total_ask_volume:.2f}")
print(f"Order Book Imbalance: {imbalance:.2f}")
print(f"Dominating Side: {dominance}")

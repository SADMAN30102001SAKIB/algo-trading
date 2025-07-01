import os
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the API token and account ID from environment variables
auth_token = os.getenv("METAAPI_TOKEN")  # Your authorization token
account_id = os.getenv("METAAPI_ACCOUNT_ID")  # Your MetaTrader account ID

# Check if the environment variables are loaded properly
if not auth_token or not account_id:
    print("Error: Missing METAAPI_TOKEN or METAAPI_ACCOUNT_ID in .env file")
    exit()

# Set the time range for retrieving trade history (from 1970-01-01 to current time)
start_time = "2025-01-01T00:00:00.000Z"  # Start time
end_time = datetime.utcnow().strftime(
    "%Y-%m-%dT%H:%M:%S.000Z"
)  # Current time in UTC format

# API endpoint for getting trade history
# url = f"https://mt-client-api-v1.london.agiliumtrade.ai/users/current/accounts/{account_id}/history-deals/time/{start_time}/{end_time}"
url = f"https://mt-client-api-v1.london.agiliumtrade.ai/users/current/accounts/{account_id}/positions"

# Set headers with the authorization token
headers = {
    "Accept": "application/json",
    "auth-token": auth_token,
}

# Send GET request to fetch the trade history
response = requests.get(url, headers=headers)

# Check the response status
if response.status_code == 200:
    trade_history = response.json()

    print(trade_history)

    # Print each trade details
    for trade in trade_history:
        if (
            trade["type"] == "DEAL_TYPE_BUY" or trade["type"] == "DEAL_TYPE_SELL"
        ) and trade["entryType"] == "DEAL_ENTRY_OUT":
            commission = 0
            for related_trade in trade_history:
                if (
                    (
                        related_trade["type"] == "DEAL_TYPE_BUY"
                        or related_trade["type"] == "DEAL_TYPE_SELL"
                    )
                    and related_trade["positionId"] == trade["positionId"]
                    and related_trade["entryType"] == "DEAL_ENTRY_IN"
                ):
                    commission = related_trade["commission"]
                    break

            print(f"Position ID: {trade['positionId']}")
            print(f"Type: {trade['type']}")
            print(f"Volume: {trade['volume']}")
            print(f"Price: {trade['price']}")
            print(f"Profit: {trade['profit']}")
            print(f"Broker Time: {trade['brokerTime']}")
            print(f"Commission: {commission}")
            print("-" * 50)

else:
    print(f"Error: {response.status_code} - {response.text}")

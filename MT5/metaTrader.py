import logging
import sys

import MetaTrader5 as mt5

logging.basicConfig(
    filename="trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

ACCOUNT = {
    "server": "Exness-MT5Trial8",
    "login": 79555324,
    "password": "TapSs@14023010",
}

open_trades = {}
pending_orders = {}


def connect_to_account():
    retries = 3
    for attempt in range(1, retries + 1):
        if mt5.initialize(
            login=ACCOUNT["login"],
            password=ACCOUNT["password"],
            server=ACCOUNT["server"],
        ):
            logging.info(
                f"Connected to account {ACCOUNT['login']} on server {ACCOUNT['server']}."
            )
            return True
        logging.error(
            f"Failed to connect to account {ACCOUNT['login']}. Attempt {attempt}/{retries}. Error: {mt5.last_error()}"
        )
    logging.critical("All connection attempts failed. Exiting.")
    sys.exit(1)


def validate_input(
    prompt, input_type=float, min_value=None, max_value=None, optional=False, values=[]
):
    while True:
        user_input = input(prompt).strip()
        if optional and not user_input:
            return None
        try:
            if not user_input:
                continue
            value = input_type(user_input)
            if min_value is not None and value < min_value:
                print(f"Value must be greater than {min_value}")
                continue
            if (min_value is not None and value < min_value) and (
                max_value is not None and value > max_value
            ):
                print(" & ")
            if max_value is not None and value > max_value:
                print(f"Value must be less than {max_value}.")
                continue
            if values and value not in values:
                print(f"Invalid input. Please enter one of {values}.")
                continue
            return value
        except ValueError:
            print(f"Invalid input. Please enter a valid {input_type.__name__}.")


def initialize_trade_tracking():
    global open_trades, pending_orders
    open_trades = {}
    pending_orders = {}

    positions = mt5.positions_get()
    orders = mt5.orders_get()

    if positions:
        for pos in positions:
            open_trades[pos.ticket] = {
                "symbol": pos.symbol,
                "direction": "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell",
                "lot_size": pos.volume,
                "tp": pos.tp,
                "sl": pos.sl,
                "type": pos.type,
            }
    if orders:
        for order in orders:
            pending_orders[order.ticket] = {
                "symbol": order.symbol,
                "lot_size": order.volume_current,
                "price": order.price_open,
                "tp": order.tp,
                "sl": order.sl,
                "type": order.type,
            }

    logging.info(
        f"Initialized trades: {len(open_trades)} open, {len(pending_orders)} pending."
    )


def place_order():
    symbol = "BTCUSD"
    if not mt5.symbol_select(symbol, True):
        logging.error(f"Failed to select symbol {symbol}.")
        return

    direction = validate_input("Enter direction (buy/sell): ", str).lower()
    if direction not in ["buy", "sell"]:
        print("Invalid direction. Please enter 'buy' or 'sell'.")
        return

    lot_size = validate_input("Enter lot size (e.g., 0.01): ", float, min_value=0.01)
    tp = validate_input(
        "Enter Take Profit (optional, press Enter to skip): ", float, optional=True
    )
    sl = validate_input(
        "Enter Stop Loss (optional, press Enter to skip): ", float, optional=True
    )

    price = (
        mt5.symbol_info_tick(symbol).ask
        if direction == "buy"
        else mt5.symbol_info_tick(symbol).bid
    )
    action_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": action_type,
        "price": price,
        "deviation": 20,
        "tp": tp or 0.0,
        "sl": sl or 0.0,
        "magic": 0,  # Custom identifier
        "comment": "Trade placed via script",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Trade placed successfully. Ticket: {result.order}")
        open_trades[result.order] = {
            "symbol": symbol,
            "direction": direction,
            "lot_size": lot_size,
            "tp": tp,
            "sl": sl,
        }
    else:
        logging.error(f"Trade failed. Error: {result.comment}.")


def update_order():
    if not open_trades:
        print("No open trades to update.")
        return

    ticket = validate_input("Enter the ticket ID of the trade to update: ", int)
    if ticket not in open_trades:
        print("Invalid ticket ID.")
        return

    tp = validate_input(
        "Enter New Take Profit (optional, press Enter to skip): ", float, optional=True
    )
    sl = validate_input(
        "Enter New Stop Loss (optional, press Enter to skip): ", float, optional=True
    )

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl": sl or 0.0,
        "tp": tp or 0.0,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Order updated successfully. Ticket: {ticket}")
        open_trades[ticket]["tp"] = tp
        open_trades[ticket]["sl"] = sl
    else:
        logging.error(f"Failed to update order. Error: {result.comment}")


def close_order():
    if not open_trades:
        print("No open trades to close.")
        return

    ticket = validate_input("Enter the ticket ID of the trade to close: ", int)
    if ticket not in open_trades:
        print("Invalid ticket ID.")
        return

    trade = open_trades[ticket]
    symbol = trade["symbol"]
    price = (
        mt5.symbol_info_tick(symbol).bid
        if trade["direction"] == "buy"
        else mt5.symbol_info_tick(symbol).ask
    )
    action_type = (
        mt5.ORDER_TYPE_SELL if trade["direction"] == "buy" else mt5.ORDER_TYPE_BUY
    )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": symbol,
        "volume": trade["lot_size"],
        "type": action_type,
        "price": price,
        "deviation": 20,
        "magic": 0,
        "comment": "Close trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Trade closed successfully. Ticket: {ticket}")
        del open_trades[ticket]
    else:
        logging.error(f"Failed to close trade. Error: {result.comment}")


def close_partial_position():
    if not open_trades:
        print("No open trades to close partially.")
        return

    ticket = validate_input(
        "Enter the ticket ID of the trade to partially close: ", int
    )
    if ticket not in open_trades:
        print("Invalid ticket ID.")
        return

    perc_close = validate_input(
        "Enter the percentage to close (e.g., 0.5 for 50%): ",
        float,
        values=[
            0.05,
            0.1,
            0.15,
            0.2,
            0.25,
            0.3,
            0.35,
            0.4,
            0.45,
            0.5,
            0.55,
            0.6,
            0.65,
            0.7,
            0.75,
            0.8,
            0.85,
            0.9,
            0.95,
        ],
    )

    trade = open_trades[ticket]
    symbol = trade["symbol"]
    price = (
        mt5.symbol_info_tick(symbol).bid
        if trade["direction"] == "buy"
        else mt5.symbol_info_tick(symbol).ask
    )
    action_type = (
        mt5.ORDER_TYPE_SELL if trade["direction"] == "buy" else mt5.ORDER_TYPE_BUY
    )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": symbol,
        "volume": round(trade["lot_size"] * perc_close, 2),
        "type": action_type,
        "price": price,
        "deviation": 20,
        "magic": 0,
        "comment": "Partial close via script",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Partial close successful. Ticket: {ticket}")
        open_trades[ticket]["lot_size"] -= request["volume"]
        if open_trades[ticket]["lot_size"] <= 0:
            del open_trades[ticket]
    else:
        logging.error(f"Failed to partially close position. Error: {result.comment}")


def show_all_open_trades():
    if not open_trades:
        print("No open trades.")
    else:
        print("\n--- Open Trades ---")
        for ticket, trade in open_trades.items():
            print(
                f"Ticket: {ticket}, Symbol: {trade['symbol']}, Lot Size: {trade['lot_size']}, TP: {trade['tp']}, SL: {trade['sl']}, , Type: {trade['type']}"
            )


def place_pending_order():
    symbol = "BTCUSD"
    if not mt5.symbol_select(symbol, True):
        logging.error(f"Failed to select symbol {symbol}.")
        return

    order_type = validate_input(
        "Enter order type (buy_limit/sell_limit/buy_stop/sell_stop): ",
        str,
        values=["bl", "sl", "bs", "ss"],
    ).lower()

    lot_size = validate_input("Enter lot size (e.g., 0.01): ", float, min_value=0.01)
    price = validate_input("Enter price for the pending order: ", float)
    tp = validate_input(
        "Enter Take Profit (optional, press Enter to skip): ", float, optional=True
    )
    sl = validate_input(
        "Enter Stop Loss (optional, press Enter to skip): ", float, optional=True
    )

    action_type = {
        "bl": mt5.ORDER_TYPE_BUY_LIMIT,
        "sl": mt5.ORDER_TYPE_SELL_LIMIT,
        "bs": mt5.ORDER_TYPE_BUY_STOP,
        "ss": mt5.ORDER_TYPE_SELL_STOP,
    }[order_type]

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot_size,
        "type": action_type,
        "price": price,
        "deviation": 20,
        "tp": float(tp) if tp else 0.0,
        "sl": float(sl) if sl else 0.0,
        "magic": 0,
        "comment": "Pending order via script",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Pending order placed successfully. Ticket: {result.order}")
        pending_orders[result.order] = {
            "symbol": symbol,
            "type": action_type,
            "lot_size": lot_size,
            "price": price,
            "tp": tp,
            "sl": sl,
        }
    else:
        logging.error(f"Failed to place pending order. Error: {result.comment}")


def show_all_pending_trades():
    if not pending_orders:
        print("No pending orders.")
    else:
        print("\n--- Pending Orders ---")
        for ticket, order in pending_orders.items():
            print(
                f"Ticket: {ticket}, Symbol: {order['symbol']}, Lot Size: {order['lot_size']}, Price: {order['price']}, Type: {order['type']}, TP: {order['tp']}, SL: {order['sl']}"
            )


def remove_pending_order():
    if not pending_orders:
        print("No open trades to close.")
        return

    ticket = validate_input("Enter the ticket ID of the pending order to remove: ", int)
    if ticket not in pending_orders:
        print("Invalid ticket ID.")
        return

    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": ticket,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Pending order removed successfully. Ticket: {ticket}")
        del pending_orders[ticket]
    else:
        logging.error(f"Failed to remove pending order. Error: {result.comment}")


def update_pending_order():
    ticket = validate_input("Enter the ticket ID of the pending order to update: ", int)
    if ticket not in pending_orders:
        print("Invalid ticket ID.")
        return

    price = validate_input("Enter new price: ", float)
    tp = validate_input(
        "Enter new Take Profit (optional, press Enter to skip): ", float, optional=True
    )
    sl = validate_input(
        "Enter new Stop Loss (optional, press Enter to skip): ", float, optional=True
    )

    request = {
        "action": mt5.TRADE_ACTION_MODIFY,
        "order": ticket,
        "price": price,
        "sl": sl or 0.0,
        "tp": tp or 0.0,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Pending order updated successfully. Ticket: {ticket}")
        pending_orders[ticket]["price"] = price
        pending_orders[ticket]["tp"] = tp
        pending_orders[ticket]["sl"] = sl
    else:
        logging.error(f"Failed to update pending order. Error: {result.comment}")


def main():
    connect_to_account()
    initialize_trade_tracking()

    terminal_info = mt5.terminal_info()
    if terminal_info.trade_allowed:
        print("✅ Algo Trading is already enabled.")
    else:
        print("⚠️ Algo Trading is DISABLED. Please enable it manually in MT5 settings.")

    while True:
        print("\n--- MT5 Trading Tool Menu ---")
        print("1. Place Market Order")
        print("2. Update an Order")
        print("3. Close Order")
        print("4. Close Partial Position")
        print("5. Show All Open Trades")
        print("6. Place Pending Order")
        print("7. Update Pending Order")
        print("8. Remove Pending Order")
        print("9. Show All Pending Orders")
        print("0. Exit")

        choice = validate_input(
            "Enter your choice: ",
            str,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        )

        if choice == "1":
            initialize_trade_tracking()
            place_order()
        elif choice == "2":
            initialize_trade_tracking()
            update_order()
        elif choice == "3":
            initialize_trade_tracking()
            close_order()
        elif choice == "4":
            initialize_trade_tracking()
            close_partial_position()
        elif choice == "5":
            initialize_trade_tracking()
            show_all_open_trades()
        elif choice == "6":
            initialize_trade_tracking()
            place_pending_order()
        elif choice == "7":
            initialize_trade_tracking()
            update_pending_order()
        elif choice == "8":
            initialize_trade_tracking()
            remove_pending_order()
        elif choice == "9":
            initialize_trade_tracking()
            show_all_pending_trades()
        elif choice == "0":
            print("Exiting the program. Goodbye!")
            mt5.shutdown()
            sys.exit(0)
        else:
            print("Invalid choice. Please select a valid option.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        mt5.shutdown()

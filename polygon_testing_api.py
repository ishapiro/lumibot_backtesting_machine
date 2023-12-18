from polygon import RESTClient
from credentials import POLYGON_CONFIG
from datetime import datetime, timedelta

client = RESTClient(api_key=POLYGON_CONFIG["API_KEY"])

# Test Listing Historical Values
trades = client.get_daily_open_close_agg("AAPL", "2023-04-04")
print ()
print(trades)

# Test Listing Historical Options Contracts
start_date = datetime(2022, 1, 4)
end_date = datetime(2022, 1, 12)

# Iterate through the dates
current_date = start_date
while current_date <= end_date:
    print(current_date.date())  # Print the date portion only
    current_date += timedelta(days=1)
    last_date = current_date + timedelta(days=60)
    contracts = client.list_options_contracts(underlying_ticker="AAPL",
                        expiration_date_gte=current_date.date(),
                        expiration_date_lt=last_date.date(),
                        strike_price_lt=200,
                        strike_price_gt=190,
                        expired=True,
                        limit=5)
    print ()
    for next_contract in contracts:
        print(next_contract.expiration_date, ":", next_contract.strike_price)

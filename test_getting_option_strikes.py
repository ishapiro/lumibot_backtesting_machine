import requests
from datetime import datetime, timedelta

from credentials import POLYGON_CONFIG
api_key = POLYGON_CONFIG['API_KEY']

def get_option_strikes(symbol, expiration_date, maximum_strikes, current_price, api_key):

# Get the options chain
    options = []
    page = 1
    options_url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={symbol}&limit=500&expired=true&expiration_date={expiration_date}&apiKey={api_key}"
    while True:
        response = requests.get(options_url)
        data = response.json()
        options += data['results']
        if data.get('next_url'):
            options_cursor = data['next_url']
            options_url = f"{options_cursor}&apiKey={api_key}"
        else:
            break

    # Separate the options into puts and calls just in case the strikes are not the same for both
    put_strikes = [option['strike_price'] for option in options if option['contract_type'] == 'put']
    call_strikes = [option['strike_price'] for option in options if option['contract_type'] == 'call']

    # Sort the strikes so we can find the middle X strikes
    call_strikes.sort()

    # Find the index of the current_price in the put_strikes and call_strikes
    put_index = min(range(len(put_strikes)), key=lambda i: abs(put_strikes[i]-current_price))
    call_index = min(range(len(call_strikes)), key=lambda i: abs(call_strikes[i]-current_price))

    middle_strike = maximum_strikes // 2

    # Only return maximum_strikes number of put_strikes and call_strikes
    put_strikes = put_strikes[max(0, put_index-middle_strike):put_index+middle_strike]
    call_strikes = call_strikes[max(0, call_index-middle_strike):call_index+middle_strike]  

    return put_strikes, call_strikes

def get_historical_price(symbol, date, api_key):
    # Get the historical price data for the stock on the specified date
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{date}/{date}?apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    if data['resultsCount'] > 0:
        return data['results'][0]['c']  # return the closing price
    else:
        return None  # no data for the specified date

# Usage:
symbol = 'SPY'
# The expired flag has to be changed depending on the option date 
# See API above  
#option_expiration_date = '2024-05-17'
option_expiration_date = '2023-05-19'
#option_expiration_date = '2024-06-21'
maximum_strikes = 50
# Get the current stock price
# Use yesterday since our API key does not have real time data access
yesterday = datetime.now() - timedelta(days=1)
yesterday_str = yesterday.strftime('%Y-%m-%d')
# Testing
yesterday_str = '2023-02-01'
current_price = get_historical_price(symbol, yesterday_str, api_key)

put_strikes, call_strikes = get_option_strikes(symbol, option_expiration_date, maximum_strikes, current_price, api_key)

print(f"Current Price: {current_price}")
print(f"Put Strikes: {put_strikes}")
print(f"Call Strikes: {call_strikes}")
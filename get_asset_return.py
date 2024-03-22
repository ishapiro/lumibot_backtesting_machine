# get_return_from_yahoo
#
# Description: This script is used to get the return of a ticker from Yahoo Finance.
# The get_return_from_yahoo function takes in a ticker, start_date, and end_date as input and returns the cumulative return of the ticker from the start_date to the end_date.

import pandas as pd
from pandas_datareader import data as web
import yfinance as yf
yf.pdr_override()

def get_asset_return(ticker, start_date, end_date):
    pd = web.get_data_yahoo(ticker, start=start_date, end=end_date)
    pd_daily_returns = pd['Adj Close'].pct_change()
    pd_cum_returns = (pd_daily_returns + 1).cumprod()
    return (pd_cum_returns.iloc[-1]-1)

if __name__ == "__main__":
    ticker = "SPY"
    start_date = "2020-01-01"
    end_date = "2020-12-31"
    ticker_return = get_asset_return(ticker, start_date, end_date)
    print(f"{ticker} {ticker_return}")
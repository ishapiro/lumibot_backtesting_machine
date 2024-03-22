# get_return_from_yahoo
#
# Description: This script is used to get the return of a ticker from Yahoo Finance.
# The get_return_from_yahoo function takes in a ticker, start_date, and end_date as input and returns the cumulative return of the ticker from the start_date to the end_date.

import pandas as pd
from pandas_datareader import data as web
import yfinance as yf
yf.pdr_override()

def get_strategy_return(stats_file):
    df = pd.read_csv(stats_file,  parse_dates=True)
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    df = df.set_index('datetime')
    df_daily_returns = df['portfolio_value'].pct_change()
    total_return = (df_daily_returns + 1).cumprod() - 1
    return (total_return.iloc[-1])

if __name__ == "__main__":
    strategy_stats_file = "logs/mwt-IBM-bull-put-spread_2024-03-21_13-55-24_stats.csv"
    strategy_return = get_strategy_return(strategy_stats_file)
    print(f"{strategy_stats_file} {strategy_return}")
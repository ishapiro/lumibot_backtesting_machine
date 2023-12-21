from datetime import datetime, timedelta
import datetime as dtime

from lumibot.entities import Asset, TradingFee
from lumibot.strategies.strategy import Strategy

# IMS moved all module includes to the top of the code
from credentials import POLYGON_CONFIG
from lumibot.backtesting import PolygonDataBacktesting

'''
This strategy will list all the option data for a given underlying X days from the current day.
'''

class ListOptionData(Strategy):

    def initialize(self):
        # The time to sleep between each trading iteration
        self.sleeptime = "1D"  # 1 minute = 1M, 1 hour = 1H,  1 day = 1D

    def on_trading_iteration(self):

        # Get the current price of the underlying
        underlying_price = self.get_last_price("SPY")

        # Round the price to the nearest dollar
        rounded_underlying_price = round(underlying_price)

        dt = self.get_datetime()
        expiry = self.get_option_expiration_after_date(dt + timedelta(days=10))

        for i in range(0, 100):
            put_strike = rounded_underlying_price - i

            put_sell_asset = Asset(
                'SPY',
                asset_type="option",
                expiration=expiry,
                strike=put_strike,
                right="put",
            )

            # Get the current price of the option
            put_sell_price = self.get_last_price(put_sell_asset)

            greeks = self.get_greeks(put_sell_asset)

            print (f"Put: {put_sell_asset} Price: {put_sell_price} Delta: {greeks['delta']} Gamma: {greeks['gamma']} Theta: {greeks['theta']} Vega: {greeks['vega']}")


if __name__ == "__main__":
    # Backtest this strategy
    backtesting_start = datetime(2022, 4, 1)
    backtesting_end = datetime(2022, 4, 20)

    # polygon_has_paid_subscription is set to true to api calls are not thottled
    ListOptionData.backtest(
        PolygonDataBacktesting,
        backtesting_start,
        backtesting_end,
        benchmark_asset="SPY",
        polygon_api_key=POLYGON_CONFIG["API_KEY"],
        polygon_has_paid_subscription=True
    )

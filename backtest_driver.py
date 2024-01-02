# IMS moved all module includes to the top of the code
from credentials import POLYGON_CONFIG
from datetime import datetime, timedelta
from lumibot.backtesting import PolygonDataBacktesting
from options_iron_condor_backtest_mwt import OptionsIronCondorMWT
from lumibot.entities import TradingFee

'''
The Plan ---

This module reads parameters from a configuration file and the runs a backtest.

At the conclusion of the run it creates a directory for the test run and moves the log
files from the "log" directory to this new directory.  It also creates a file called
"backtest_results.csv" in the new directory that contains the summary of the results.
'''

distance_of_wings = 15 # reference in multiple parameters below, in dollars not strikes
quantity_to_trade = 10 # reference in multiple parameters below, number of contracts
strategy_parameters = {
    "symbol": "SPY",
    "option_duration": 40,  # How many days until the call option expires when we sell it
    "strike_step_size": 1,  # IMS Is this the strike spacing of the specific asset, can we get this from Poloygon?
    "delta_required": 0.15,  # The delta of the option we want to sell
    "roll_delta_required": 0.15,  # The delta of the option we want to sell when we do a roll
    "maximum_rolls": 2,  # The maximum number of rolls we will do
    "days_before_expiry_to_buy_back": 7,  # How many days before expiry to buy back the call
    "quantity_to_trade": quantity_to_trade,  # The number of contracts to trade
    "minimum_hold_period": 5,  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
    "distance_of_wings" : distance_of_wings, # Distance of the longs from the shorts in dollars -- the wings
    "budget" : (distance_of_wings * 100 * quantity_to_trade * 1.25), # Need to add logic to limit trade size based on margin requirements.  Added 20% for safety since I am likely to only allocate 80% of the account.
    "strike_roll_distance" : (0.10 * distance_of_wings) # How close to the short do we allow the price to move before rolling.
}

# Read parameters from a TOML file
import toml
strategy_parameters = toml.load("strategy_parameters.toml")


# Override the parameters set in the OptionsIronCondorMWT class
OptionsIronCondorMWT.set_parameters(strategy_parameters)

strategy_name = f'ic-{strategy_parameters["symbol"]}-{strategy_parameters["delta_required"]}delta-{strategy_parameters["option_duration"]}duration-{strategy_parameters["days_before_expiry_to_buy_back"]}exit-{strategy_parameters["minimum_hold_period"]}hold'

if __name__ == "__main__":
        # Backtest this strategy
        backtesting_start = datetime(2020, 2, 3)
        backtesting_end = datetime(2023, 12, 15)

        trading_fee = TradingFee(percent_fee=0.007)  # IMS account for trading fees and slipage

        # polygon_has_paid_subscription is set to true to api calls are not thottled
        OptionsIronCondorMWT.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset=strategy_parameters["symbol"],
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
            polygon_api_key=POLYGON_CONFIG["API_KEY"],
            polygon_has_paid_subscription=True,
            name=strategy_name,
            budget = strategy_parameters["budget"],
        )
 

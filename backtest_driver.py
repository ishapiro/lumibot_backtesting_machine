# IMS moved all module includes to the top of the codels 
from credentials import POLYGON_CONFIG
from datetime import datetime, timedelta
from lumibot.backtesting import PolygonDataBacktesting
from options_iron_condor_backtest_mwt import OptionsIronCondorMWT
from lumibot.entities import TradingFee
import os
import time
import shutil
import toml
import pprint
pp = pprint.PrettyPrinter(indent=4)

"""
Author:  Irv Shapiro
License: MIT License

The Plan --- This is a work in process ...

This module reads parameters from a TOML configuration located in the strategy_configurations
directory, runs the strategy and moves the logs in the strategy_logs directory with the same
name as the configuration file.  The TOML file can have any name but should end with .toml

"""

"""
Disclaimer: The options strategies presented within this content are intended for educational purposes only. They are not meant to be used for trading live stocks or any other financial instruments. The information provided is based on historical data and hypothetical scenarios, and it does not guarantee future results or profits.

Trading stocks and options involve substantial risks and may result in the loss of your invested capital. It is essential to conduct thorough research, seek advice from a qualified financial professional, and carefully consider your risk tolerance before engaging in any trading activities.

By accessing and utilizing the information presented, you acknowledge that you are solely responsible for any trading decisions you make. Neither the author nor any associated parties shall be held liable for any losses, damages, or consequences arising from the use of the strategies discussed in this content.
"""

# These are just defining defaults that are overriden by the TOML file
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
    "budget" : (distance_of_wings * 100 * quantity_to_trade * 1.25), # Need to add logic to limit trade size based on margin requirements.
    "strike_roll_distance" : (0.10 * distance_of_wings), # How close to the short do we allow the price to move before rolling.
    "trading_fee_percent" : 0.007 # The percent fee charged by the broker for each trade
}

# Get a list of all files in the current directory
files = os.listdir("iron_condor_lumibot_example/strategy_configurations/")

# Loop through all of the configurations files in the strategy configuration directory
# Then load the parameters and run the strategy backtest

for toml_file in files:
    # Check if the file is a TOML file
    if toml_file.endswith('.toml'):
        strategy_file = toml_file
        print(f"Strategy file found: {strategy_file}")

        # Read parameters from a TOML file
        strategy_parameters = toml.load(f"iron_condor_lumibot_example/strategy_configurations/{strategy_file}")
        print()
        print("**************************************************")
        print("Strategy Parameters read from TOML file")
        pp.pprint(strategy_parameters)
        print("**************************************************")
        print()

        capital_budget =  (strategy_parameters["distance_of_wings"] * 100 * strategy_parameters["quantity_to_trade"] * 1.5)

        backtesting_start = datetime.combine(strategy_parameters["starting_date"], datetime.min.time())
        backtesting_end = datetime.combine(strategy_parameters["ending_date"], datetime.min.time())

        # Override the parameters set in the OptionsIronCondorMWT class
        OptionsIronCondorMWT.set_parameters(strategy_parameters)

        strategy_name = f'ic-{strategy_parameters["symbol"]}-{strategy_parameters["delta_required"]}delta-{strategy_parameters["option_duration"]}dur-{strategy_parameters["days_before_expiry_to_buy_back"]}ex-{strategy_parameters["minimum_hold_period"]}hd'

        trading_fee = TradingFee(flat_fee=strategy_parameters["trading_fee"])  # Account for trading fees and slipage

        # Clean out the log direcectory from the privious run.  We do this since at the end of each run
        # we copy the log files to the strategy log directory.
        if os.path.exists("logs/"):
            files = os.listdir("logs/")
            # Delete each file in the log directory
            for file in files:
                os.remove(os.path.join("logs/", file))

        # Execute the strategy with the parameters from the TOML file
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
            budget = capital_budget,
        )

        # Copy the log files to the strategy log directory
        source_dir = "logs/"
        strategy_directory = strategy_file.split(".")[0]    
        target_dir = f"strategy_logs/{strategy_directory}/"

        # Create the target directory if it does not exist
        os.makedirs(target_dir, exist_ok=True)

        # Get a list of all files in Lumibot log directory
        files = os.listdir(source_dir)

        # Copy each file to the strategy log directory
        # Leave in the original log directory so the browser can display it
        for file in files:
            shutil.copy(os.path.join(source_dir, file), target_dir)

        # Wait 10 seconds so lumibot can finish writing the log files before starting the next iteration
        print("Waiting 10 seconds for Lumibot to finish writing log files")
        time.sleep(10)


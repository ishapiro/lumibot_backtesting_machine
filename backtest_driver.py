"""
Author:  Irv Shapiro
License: MIT License

The Plan --- This is a work in process ...

This module reads parameters from a TOML configuration located in the strategy_configurations
directory, runs the strategy and moves the logs in the strategy_logs directory with the same
name as the configuration file.  The TOML file can have any name but should end with .toml

Results from the backtest are stored in the database.  The database is used to track the results
of the backtest and to determine if the backtest has already been run.  If the backtest has already
been run, the backtest is skipped.  The backtest is rerun if any of the parameters in the TOML file
are changed.

"""

"""
Disclaimer: The options strategies presented within this content are intended for educational purposes only. They are not meant to be used for trading live stocks or any other financial instruments. The information provided is based on historical data and hypothetical scenarios, and it does not guarantee future results or profits.

Trading stocks and options involve substantial risks and may result in the loss of your invested capital. It is essential to conduct thorough research, seek advice from a qualified financial professional, and carefully consider your risk tolerance before engaging in any trading activities.

By accessing and utilizing the information presented, you acknowledge that you are solely responsible for any trading decisions you make. Neither the author nor any associated parties shall be held liable for any losses, damages, or consequences arising from the use of the strategies discussed in this content.
"""

# The following parameter determines if we use the pip install Lumibot or the local copy
use_local_lumibot = True

################################################################################
# Must Be Imported First If Run Locally
if use_local_lumibot:
    import os
    import sys

    myPath = os.path.dirname(os.path.abspath(__file__))
    myPath = myPath.replace("lumibot_backtesting_machine", "")
    myPath = myPath + "/lumibot/"
    sys.path.insert(0, myPath)
################################################################################


# IMS moved all module includes to the top of the codels 
from credentials import POLYGON_CONFIG
from datetime import datetime, timedelta
from lumibot.backtesting import PolygonDataBacktesting
from options_backtesting_machine import OptionsStrategyEngine
from lumibot.entities import TradingFee
import os
import sys
import time
import shutil
import toml
import pprint
pp = pprint.PrettyPrinter(indent=4)

from get_asset_return import get_asset_return
from get_strategy_return import get_strategy_return
from add_benchmark_to_db import add_benchmark_run_to_db
from check_for_previous_run import check_for_previous_run

class BacktestDriver():

    def BacktestRunner():

        # These are just defining defaults that are overriden by the TOML file
        distance_of_wings = 15 # reference in multiple parameters below, in dollars not strikes
        quantity_to_trade = 10 # reference in multiple parameters below, number of contracts
        strategy_parameters = {
                "symbol": "SPY",
                "trade_strategy" : "iron-condor",  # iron-condor, bull-put-spread, bear-call-spread, hybrid
                "option_duration": 40,  # How many days until the call option expires when we sell it
                "strike_step_size": 5,  # IMS Is this the strike spacing of the specific asset, can we get this from Polygon?
                "max_strikes" : 25,  # This needs to be appropriate for the name and the strike size
                "call_delta_required": 0.16, # The delta values are different if we are skewing the condor
                "put_delta_required": 0.16,
                "maximum_rolls": 2,  # The maximum number of rolls we will do
                "days_before_expiry_to_buy_back": 7,  # How many days before expiry to buy back the call
                "quantity_to_trade": quantity_to_trade,  # The number of contracts to trade
                "minimum_hold_period": 7,  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
                "distance_of_wings" : distance_of_wings, # Distance of the longs from the shorts in dollars -- the wings
                "budget" : (distance_of_wings * 100 * quantity_to_trade * 1.5), # 
                "strike_roll_distance" : 1.0, # How close to the short do we allow the price to move before rolling.
                "max_loss_multiplier" : .75, # The maximum loss is the initial credit * max_loss_multiplier, set to 0 to disable
                "roll_strategy" : "short", # short, delta, none # IMS not fully implemented
                "skip_on_max_rolls" : True, # If true, skip the trade days to skip after the maximum number of rolls is reached
                "delta_threshold" : 0.32, # If roll_strategy is delta this is the delta threshold for rolling
                "maximum_portfolio_allocation" : 0.75, # The maximum amount of the portfolio to allocate to this strategy for new condors
                "max_loss_trade_days_to_skip" : 5.0, # The number of days to skip after a max loss, rolls exceeded or undelying price move
                "max_volitility_days_to_skip" : 10.0, # The number of days to skip after a max move
                "max_symbol_volitility" : 0.05, # Percent of max move to stay out of the market as a decimal
                "starting_date" : "2022-01-01",
                "ending_date" : "2022-03-31",
                "trading_fee" : 0.65,  # The trading fee in dollars per contract
            }

        # Get a list of all files in the current directory
        files = os.listdir("/Users/irvshapiro/drvax-code-local/AAA Lumibot/lumibot_backtesting_machine/strategy_configurations/")

        # Loop through all of the configurations files in the strategy configuration directory
        # Then load the parameters and run the strategy backtest

        for toml_file in files:
            # Check if the file is a TOML file
            if toml_file.endswith('.toml'):
                strategy_file = toml_file
                print(f"Strategy file found: {strategy_file}")

                # Read parameters from a TOML file
                strategy_parameters = toml.load(f"/Users/irvshapiro/drvax-code-local/AAA Lumibot/lumibot_backtesting_machine/strategy_configurations/{strategy_file}")
                # print()
                # print("**************************************************")
                # print("Strategy Parameters read from TOML file")
                # pp.pprint(strategy_parameters)
                # print("**************************************************")
                # print()

                capital_budget =  (strategy_parameters["distance_of_wings"] * 100 * strategy_parameters["quantity_to_trade"] * 1.5)

                backtesting_start = datetime.combine(strategy_parameters["starting_date"], datetime.min.time())
                backtesting_end = datetime.combine(strategy_parameters["ending_date"], datetime.min.time())

                # Override the parameters set in the OptionsStrategyEngine class
                OptionsStrategyEngine.set_parameters(strategy_parameters)

                strategy_name = f'mwt-{strategy_parameters["symbol"]}-{strategy_parameters["trade_strategy"]}'
                print(f">>>>> Running strategy: {strategy_name}")

                # Check if the data already exists in the database and skip this run if it does
                if check_for_previous_run(strategy_parameters):
                    print ("------ Data already exists in the database.  Skipping benchmark run.  Change at least one value to rerun the benchmark.")
                    print()
                    continue

                trading_fee = TradingFee(flat_fee=strategy_parameters["trading_fee"])  # Account for trading fees and slipage

                # Clean out the log direcectory from the privious run.  We do this since at the end of each run
                # we copy the log files to the strategy log directory.
                if os.path.exists("/Users/irvshapiro/drvax-code-local/AAA Lumibot/logs/"):
                    stats_file = ""
                    files = os.listdir("/Users/irvshapiro/drvax-code-local/AAA Lumibot/logs/")
                    # Delete each file in the log directory
                    for file in files:
                        os.remove(os.path.join("/Users/irvshapiro/drvax-code-local/AAA Lumibot/logs/", file))

                # Execute the strategy with the parameters from the TOML file
                OptionsStrategyEngine.backtest(
                    PolygonDataBacktesting,
                    backtesting_start,
                    backtesting_end,
                    benchmark_asset=strategy_parameters["symbol"],
                    buy_trading_fees=[trading_fee],
                    sell_trading_fees=[trading_fee],
                    polygon_api_key=POLYGON_CONFIG["API_KEY"],
                    polygon_has_paid_subscription=True,
                    name=strategy_name,
                    budget=capital_budget,
                    show_plot=False,
                    show_indicators=False,
                    show_tearsheet=False,
                    save_tearsheet=True,
                )

                # Copy the log files to the strategy log directory
                source_dir = "/Users/irvshapiro/drvax-code-local/AAA Lumibot/logs/"
                strategy_directory = strategy_file.split(".")[0]    
                target_dir = f"strategy_logs/{strategy_directory}/"

                # Create the target directory if it does not exist
                os.makedirs(target_dir, exist_ok=True)

                # Get a list of all files in Lumibot log directory
                files = os.listdir(source_dir)
                stats_file = ""
                tearsheet_file = ""
                for file in files:
                    if "_stats.csv" in file:
                        stats_file = file
                    if "_tearsheet.html" in file:
                        tearsheet_file = file

                # Copy each file to the strategy log directory
                # Leave in the original log directory so the browser can display it
                for file in files:
                    shutil.copy(os.path.join(source_dir, file), target_dir)

                # Wait 3 seconds so lumibot can finish writing the log files before starting the next iteration
                print("Waiting 3 seconds for Lumibot to finish writing log files")
                time.sleep(3)

                print("\033c", end='')  # clear the screen

                print(f"Stats file {stats_file}")
                strategy_return = get_strategy_return("/Users/irvshapiro/drvax-code-local/AAA Lumibot/logs/" + stats_file)
                print(f"Strategy Return: {strategy_return}")

                benchmark_return = get_asset_return(strategy_parameters["symbol"], strategy_parameters["starting_date"], strategy_parameters["ending_date"])
                print(f"{strategy_parameters['symbol']} Return: {benchmark_return}")

                tearsheet_path = ""
                if tearsheet_file != "":
                    tearsheet_path = f"strategy_logs/{strategy_directory}/{tearsheet_file}"
                # Add the benchmark return to the database
                add_benchmark_run_to_db(stats_file, strategy_return, benchmark_return, strategy_parameters, tearsheet_path)


if __name__ == "__main__":
    backtest_reselts = BacktestDriver.BacktestRunner()


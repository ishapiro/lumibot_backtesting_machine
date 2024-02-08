Lumibot Iron Condor Benchmarking Experiment

**THIS FRAMEWORK IS AN EDUCATIONAL EXERCISE**

**DO NOT TRADE BASED ON THE RESULTS OF THIS FRAMEWORK**

# Iron Condor Backtesting Strategy

Disclaimer: The options strategies presented within this content are intended for educational purposes only. They are not meant to be used for trading live stocks or any other financial instruments. The information provided is based on historical data and hypothetical scenarios, and it does not guarantee future results or profits.

Trading stocks and options involve substantial risks and may result in the loss of your invested capital. It is essential to conduct thorough research, seek advice from a qualified financial professional, and carefully consider your risk tolerance before engaging in any trading activities.

By accessing and utilizing the information presented, you acknowledge that you are solely responsible for any trading decisions you make. Neither the author nor any associated parties shall be held liable for any losses, damages, or consequences arising from the use of the strategies discussed in this content.

License: MIT License:

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Background

This Lumibot strategy employs a parameter-driven back tester for Iron Condors. Iron Condors are option trades that involve two spreads centered on the current market price. Each spread consists of a short and a long position (the wing) on both the put and call sides, which limit risks and define the maximum profit. This exercise aims to determine if a universal set of rules can be applied to most market conditions to maximize returns while minimizing risks.

The parameters at the top of the strategy or loaded from TOML files control the condor's initial structure and the adjustments made as the market changes.  The adjustments available include rolling spreads and closing the condor based on time, delta, asset price, and underlying asset volatility.

Here is the structure of an Iron Condor:

    Iron Condor Structure
    
    call log position
    call short position
    call short_strike_boundary
    
    Initial Stock Position
    
    put short_strike_boundary
    put short position
    put long posittion


## Files

options_iron_condor_backtest_mwt.py -- this is the strategy
option_testing.py -- this is a mini strategy used to test retreiving option pricing
polygon_test_api.py -- this is a simple test of the polygon API


Before running the strategy, you need to create a file credentials.py containing your Poloycom API key. This
file is at the same level in the directory structure as your strategy file.

```
POLYGON_CONFIG = {
    # Put your own Polygon key here:
    "API_KEY": "hjkhkjhjkhkjhkjhkjhkjhhk",
}
```

## Strategy Configuration Files

Strategies parameters are defined toml files located in the strategy_configurations directory. The log files
from each strategy run are located in the strategy_logs directory with the same name as the 
configuration file that produced the log.

**The strategy_configuration directory is not included in the github distribution.   You will need to
create this manually.**

Check options_iron_condor_backtest_mwt.py for a current up to date list of parameters.

```
symbol = "SPY"
option_duration = 40  # How many days until the call option expires when we sell it
strike_step_size = 1  # IMS Is this the strike spacing of the specific asset can we get this from Poloygon?
delta_required = 0.16  # The delta of the option we want to sell
roll_delta_required = 0.16  # The delta of the option we want to sell when we do a roll
maximum_rolls = 2  # The maximum number of rolls we will do
days_before_expiry_to_buy_back = 7  # How many days before expiry to buy back the call
quantity_to_trade = 10  # The number of contracts to trade
minimum_hold_period = 5  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
distance_of_wings = 15  # Distance of the longs from the shorts in dollars -- the wings
strike_roll_distance = 5 # How close to the short do we allow the price to move before rolling.
trading_fee = 0.60 # Commmision and slipage
max_loss_multiplier = 2.0 # The maximum loss as a multiple of initial credit, set to 0 to disable
maximum_portfolio_allocation = 0.75 # The maximum amount of the portfolio to allocate to this strategy for new condors
max_loss_trade_days_to_skip =  3 # The number of days to skip after a max loss trade
roll_strategy = "short" # short, delta, none # IMS not fully implemented
delta_threshold = 0.20 # The delta threshold for rolling
starting_date = 2020-02-01
ending_date = 2020-04-30
```

## See the code for additional information

The code is extensively commented.  I recommend reviewing the code before attempting to run it.

## Development

I have used MacOS for development with the following setup:

```
brew install python@3.11
```

Then open up VS Code, and from the VS Code terminal, create a Python environment and install lumibot.

```
Shift-command-P
Python Create Environment
```

From the VS Code terminal:

```
pip install lumibot
```

If you want to work on the lumibot framewort you need to clone it from github at the same level as the directory 
holding "options_iron_condor_backtest_mwt.py".  For example you directory structure will look like this:

```
.venv
iron_condor_lumibot_example
lumibot
```

The following code at the top of the iron condor strategy will force the import of the module from the
local file vs the pip installed file.

```
use_local_lumibot = True

# Must Be Imported First If Run Locally
if use_local_lumibot:
    import os
    import sys

    myPath = os.path.dirname(os.path.abspath(__file__))
    myPath = myPath.replace("iron_condor_lumibot_example", "")
    myPath = myPath + "/lumibot/"
    sys.path.insert(0, myPath)
```



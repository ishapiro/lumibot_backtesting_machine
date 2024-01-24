Lumibot Iron Condor Benchmarking Experiment

**THIS FRAMEWORK IS NOT READY FOR USE AND SHOULD BE CONSIDERED AN ALPHA RELEASE**

**DO NOT TRADE BASED ON THE RESULTS OF THIS FRAMEWORK**

# Iron Condor Backtesting Strategy

Disclaimer: The options strategies presented within this content are intended for educational purposes only. They are not meant to be used for trading live stocks or any other financial instruments. The information provided is based on historical data and hypothetical scenarios, and it does not guarantee future results or profits.

Trading stocks and options involve substantial risks and may result in the loss of your invested capital. It is essential to conduct thorough research, seek advice from a qualified financial professional, and carefully consider your risk tolerance before engaging in any trading activities.

By accessing and utilizing the information presented, you acknowledge that you are solely responsible for any trading decisions you make. Neither the author nor any associated parties shall be held liable for any losses, damages, or consequences arising from the use of the strategies discussed in this content.

License: MIT License:

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Files

options_iron_condor_backtest_mwt.py -- this is the strategy
option_testing.py -- this is a mini strategy used to test retreiving option pricing
polygon_test_api.py -- this is a simple test of the polygon API

## Strategy Configuration Files

Strategies parameters are defined toml files located in the strategy_configurations directory. The log files
from each strategy run are located in the strategy_logs directory with the same name as the 
configuration file that produced the log.

**The strategy_configuration directory is not included in the github distribution.   You will need to
create this manually.**

```
symbol = "SPY"
option_duration = 40  # How many days until the call option expires when we sell it
strike_step_size = 1  # IMS Is this the strike spacing of the specific asset can we get this from Poloygon?
delta_required = 0.15  # The delta of the option we want to sell
roll_delta_required = 0.15  # The delta of the option we want to sell when we do a roll
maximum_rolls = 2  # The maximum number of rolls we will do
days_before_expiry_to_buy_back = 7  # How many days before expiry to buy back the call
quantity_to_trade = 10  # The number of contracts to trade
minimum_hold_period = 5  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
distance_of_wings = 20  # Distance of the longs from the shorts in dollars -- the wings
margin_call_factor = 1.25  # How much above the margin requirement do we set the budget
strike_roll_distance = 5 # How close to the short do we allow the price to move before rolling.
starting_date = 2020-02-01
ending_date = 2020-04-30
trading_fee_percent = 0.07 # Commmision and slipage
```

## See the code for additional information

The code is extensively commented.  I recommend reviewing the code before attempting to run it.

## Background

    Iron Condor Structure
    
    call log position
    call short position
    call short_strike_boundary
    
    Initial Stock Position
    
    put short_strike_boundary
    put short position
    put long posittion


The goal of the effort is to create a flexible Iron Condor backtesting solution easily modified by updating
parameters.   In future efforts these parameters will be exposed via web front end.

## Development

I have used MacOS for development with the following setup:

```
brew install python@3.11
```

Then open up vscode, and from the terminal, create an environment for your development.

```
python3 -m venv lumibot-env
source lumibot-env/bin/activate
```

Create a new directory at the next level down.  You do not want the env at the same level as the code because this will cause an issue with git.

If you are inside of the code directory, activate the env with:

```
../lumibot-env/bin/activate
```

Open the new directory in a terminal and run vscode as follows:

```
code .   
```

In VSCode, invoke the command prompt with cmd/shift/p and then type Python: Select Interpreter.  Make sure the Python interpreter is set
to the lumibot env.

The code is extensively commented.

To run, you need to create a file credentials.py containing your Poloycom API key:

```
POLYGON_CONFIG = {
    # Put your own Polygon key here:
    "API_KEY": "hjkhkjhjkhkjhkjhkjhkjhhk",
}
```




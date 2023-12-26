Lumibot Iron Condor Benchmarking Experiment

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




"""
Lumibot Backtesting Machine

Disclaimer: The options strategies presented within this content are intended for educational purposes only. They are not meant to be used for trading live stocks or any other financial instruments. The information provided is based on historical data and hypothetical scenarios, and it does not guarantee future results or profits.

Trading stocks and options involve substantial risks and may result in the loss of your invested capital. It is essential to conduct thorough research, seek advice from a qualified financial professional, and carefully consider your risk tolerance before engaging in any trading activities.

By accessing and utilizing the information presented, you acknowledge that you are solely responsible for any trading decisions you make. Neither the author nor any associated parties shall be held liable for any losses, damages, or consequences arising from the use of the strategies discussed in this content.
"""

"""
Strategy Description

Author: Irv Shapiro (ishapiro@cogitations.com)
YouTube: MakeWithTech
Websites: https://www.makewithtech.com, https://cogitations.com

Based on: Loosly based on the Lumibot Condor Example, modified to incorporate concepts discuss in the SMB Capital
Options Trading Course.  

NOTE: The current version assumes only one trade is open at a time!!!

The bull put spread is a bullish strategy that profits when the underlying asset stays above the short strike.  The bear
call spread is a bearish strategy that profits when the underlying asset stays below the short strike.  The iron condor
combines these two strategies to create a market neutral strategy that profits when the underlying asset stays within a
range.

The Iron Condor is a market neutral strategy that profits when the underlying asset stays within a range.  The strategy
is constructed by selling a call spread and a put spread.  The call spread is constructed by selling a call option and
buying a call option with a higher strike price.  The put spread is constructed by selling a put option and buying a put
option with a lower strike price.  The distance between the short and long strikes is the "wings" of the condor.

When selling premimum it is often safest to use ETFs as the underlying asset.  ETFs are less volatile than individual
stocks and have a lower margin requirement.  The following are the ETFs with the highest volume options: SPY, QQQ, IWM,
 EEM, XLF, FXI, XLE, GLD, GDX, EFA, EWZ, TLT, EWC, KWEB, ARKK, TQQQ, LQD, BKLN.


This parameterized trade testing application is designed to evaluate a range of parameters for a trade stragegy over a range 
of parmeters.  The parameters include the delta of the shorts, the distance of the wings, the days before expiration to exit
the trade, and the days before expiration to roll one of the spreads.  The application also supports setting an option maximum
loss.  The maximum loss is the initial credit * max_loss_multiplier.  If the maximum loss is exceeded the trade is closed.

The roll logic can be based on delta or distance to the short strike.  The delta threshold is the delta of the
short strike that will trigger a roll.  The distance to the short strike is the distance in dollars that the
underlying price must be from the short strike to trigger a roll.
    
"""

"""
License: MIT License:

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# The following parameter determines if we use the pip install Lumibot or the local copy
use_local_lumibot = False

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
    
# See debug_print function below
mwt_debug = False

from datetime import datetime, timedelta
import datetime as dtime
from decimal import Decimal
import time
import inspect
import sys

# IMS functions used for debugging
import pprint
pp = pprint.PrettyPrinter(indent=4)
from pprint import pformat  
import requests

from inspect import currentframe, getframeinfo

from lumibot.entities import Asset, TradingFee
from lumibot.strategies.strategy import Strategy

#######################################################################
# You must manually define a credentials.py file with the following:
#
# POLYGON_CONFIG = {
#     # Put your own Polygon key here:
#     "API_KEY": "hjkhkjhjkhkjhkjhkjhkjhhk",
# }
#######################################################################

# IMS moved all module includes to the top of the code
from credentials import POLYGON_CONFIG
from lumibot.backtesting import PolygonDataBacktesting

class OptionsStrategyEngine(Strategy):

    # IMS Replaced with parameters from the driver program. See set_parameters method below
    # Symbols testing: GLD, SPY, QQQ, IWM, ARKK, EEM  -- check the strike step size depending on the ETF
    # HYG did not work --- need to investage
    
    distance_of_wings = 10 # reference in multiple parameters below, in dollars not strikes
    quantity_to_trade = 10 # reference in multiple parameters below, number of contracts

    
    parameters = {
        "symbol": "SPY" , # The symbol to trade
        "trade_strategy" : "iron-condor",  # iron-condor, bull-put-spread, bear-call-spread, hybrid
        "option_duration": 40,  # How many days until the call option expires when we sell it
        "strike_step_size": 1,  # IMS Is this the strike spacing of the specific asset, can we get this from Polygon?
        "max_strikes" : 100,  # This needs to be appropriate for the name and the strike size
        "call_delta_required": 0.16, # The delta values are different if we are skewing the condor
        "put_delta_required": 0.16,
        "maximum_rolls": 2,  # The maximum number of rolls we will do
        "days_before_expiry_to_buy_back": 7,  # How many days before expiry to buy back the call
        "quantity_to_trade": quantity_to_trade,  # The number of contracts to trade
        "minimum_hold_period": 7,  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
        "distance_of_wings" : distance_of_wings, # Distance of the longs from the shorts in dollars -- the wings
        "budget" : (distance_of_wings * 100 * quantity_to_trade * 1.5), # 
        "strike_roll_distance" : 1.0, # How close to the short do we allow the price to move before rolling.
        "max_loss_multiplier" : 2.0, # The maximum loss is the initial credit * max_loss_multiplier, set to 0 to disable
        "roll_strategy" : "short", # short, delta, none # IMS not fully implemented
        "skip_on_max_rolls" : True, # If true, skip the trade days to skip after the maximum number of rolls is reached
        "delta_threshold" : 0.32, # If roll_strategy is delta this is the delta threshold for rolling
        "maximum_portfolio_allocation" : 0.75, # The maximum amount of the portfolio to allocate to this strategy for new condors
        "max_loss_trade_days_to_skip" : 5.0, # The number of days to skip after a max loss, rolls exceeded or undelying price move
        "max_volitility_days_to_skip" : 10.0, # The number of days to skip after a max move
        "max_symbol_volitility" : 0.05, # Percent of max move to stay out of the market as a decimal
        "starting_date" : "2023-01-01",
        "ending_date" : "2023-12-31",
    }

    # Default values if run directly instead of from backtest_driver program
    parameters_for_debug = pformat(parameters).replace("\n", "<br>")  

    # The Lumibot framework does not current track margin requirements.  For this strategy
    # we will track margin manually using the following approximation in an instance variable.
    #
    # margin reserve = distance of wings - condor credit
    #
    margin_reserve = 0

    strategy_name = f'mwt-{parameters["symbol"]}-{parameters["trade_strategy"]}-{parameters["starting_date"]}-{parameters["ending_date"]}'   

    @classmethod
    def set_parameters(cls, parameters):
        cls.parameters = parameters
        cls.parameters_for_debug = pformat(cls.parameters).replace("\n", "<br>")  
    
    def initialize(self):
        # The time to sleep between each trading iteration
        self.sleeptime = "1D"  # 1 minute = 1M, 1 hour = 1H,  1 day = 1D

        # Initialize the wait counter
        self.hold_length = 0

        # Roll counter -- used to track the number of rolls
        self.roll_count = 0

        # Used to speed up date checks
        self.non_existing_expiry_dates = []

        # Current Condor Maximum Profit
        self.purchase_credit = 0

        # Saved rolled data for debugging
        self.roll_current_delta = 0

        # Saved last trade size -- set in condor creation code
        self.last_trade_size = 0

        # Skipped day counter after a max loss
        self.skipped_days_counter = 0

        # Flag to indicate if we hit a max loss
        self.stay_out_of_market = False

        # Keep track of historical system price so we can use to track momentum
        self.historical_price = []

        # Keep track of selecive greeks for the current option
        self.call_vega = []
        self.put_vega = []

        # Flag to indicate if we hit a max move
        self.max_move_hit_flag = False

        # Flag to indicate if the portfolio has gone negative
        self.portfolio_blew_up = False

    def on_trading_iteration(self):
        # Used for debugging
        frameinfo = getframeinfo(currentframe())

        ############################################################################################
        # The following code is executed at the beginning of each trading iteration
        ############################################################################################        
        # Get the parameters
        symbol = self.parameters["symbol"]
        option_duration = self.parameters["option_duration"]
        strike_step_size = self.parameters["strike_step_size"]
        call_delta_required = self.parameters["call_delta_required"]
        put_delta_required = self.parameters["put_delta_required"]
        days_before_expiry_to_buy_back = self.parameters["days_before_expiry_to_buy_back"]
        distance_of_wings = self.parameters["distance_of_wings"]
        quantity_to_trade = self.parameters["quantity_to_trade"]
        minimum_hold_period  = self.parameters["minimum_hold_period"]
        strike_roll_distance = self.parameters["strike_roll_distance"]
        maximum_rolls = self.parameters["maximum_rolls"]
        max_loss_multiplier = self.parameters["max_loss_multiplier"]
        roll_strategy = self.parameters["roll_strategy"]
        delta_threshold = self.parameters["delta_threshold"]
        maximum_portfolio_allocation = self.parameters["maximum_portfolio_allocation"]
        days_to_stay_out_of_market = self.parameters["max_loss_trade_days_to_skip"]
        skip_on_max_rolls = self.parameters["skip_on_max_rolls"]
        max_symbol_volitility  = self.parameters["max_symbol_volitility"]
        max_volitility_days_to_skip = self.parameters["max_volitility_days_to_skip"]
        max_strikes = self.parameters["max_strikes"]
        trade_strategy = self.parameters["trade_strategy"]

        # Used to track delta found when walking options
        last_call_delta = 0
        last_put_delta = 0

        # Make sure we have a valid strategy selected
        if trade_strategy not in ["iron-condor", "bull-put-spread", "bear-call-spread", "hybrid"]:
            print ("********************** Invalid trade strategy ************")
            sys.exit(1)

        # Days to skip is different for max move and max loss
        # Days to skip for max rolls uses the max loss days to skip
        # This value is update when a skip condition is hit
        days_to_skip = days_to_stay_out_of_market
        
        # Get the price of the underlying asset
        underlying_price = self.get_last_price(symbol)
        rounded_underlying_price = round(underlying_price, 0)

        # Add lines to the indicator chart
        self.add_line(f"{symbol}_price", underlying_price)

        # IMS this only works because the strategy only holds one condor at a time
        self.hold_length += 1

        # Get the current datetime
        dt = self.get_datetime()

        self.debug_print (f"************************* Iteration Date: {dt} Underlying rounded price: {rounded_underlying_price} *************************")

        self.historical_price.append({"price": rounded_underlying_price, "date": dt})

        # If we have a move in the asset of more than x% we need to stay out of the market
        # So stay out of the market for a few days
        # Each time this is hit we will roll the days to stay out of the market forward
        if len(self.historical_price) > 2:
            if (self.historical_price[-1]["price"] * (1+max_symbol_volitility) < self.historical_price[-2]["price"]) or (self.historical_price[-1]["price"] * (1-max_symbol_volitility) > self.historical_price[-2]["price"]):
                self.max_move_hit_flag = True
                # Resetting the days counter will extend the time out of the market
                # This apply to any reason we are out of the market
                self.skipped_days_counter = 0
                days_to_skip = max_volitility_days_to_skip
            else:
                self.max_move_hit_flag = False
                days_to_skip = days_to_stay_out_of_market

        # Check if we need to skip days after a max loss
        self.skipped_days_counter += 1
        if self.stay_out_of_market and self.skipped_days_counter < days_to_skip:
            return
        else:
            # Reset the flags and days counter
            self.stay_out_of_market = False
            # Reset to general case in the event it was set to the max move value
            days_to_skip = days_to_stay_out_of_market
            self.skipped_days_counter = 0
        
        ##############################################################################
        # Collect the option positions and see if we have a condor.  If we only
        # have one position it will be the cash position.  If we have more than one
        # position, we have a condor.  If we have a condor we need to check if we
        # need to roll or close the condor.
        ##############################################################################

        # Get all the open positions
        no_active_condor = False
        positions = self.get_positions()
        if len(positions) < 2:
            no_active_condor = True

        # This strategy keeps one condor active at a time.  If this is the first trading
        # day or we have no condor active create one and exit.
            
        if (self.first_iteration or no_active_condor) and not self.portfolio_blew_up:
            ############################################################################################
            # Initialize values we track for each condor
            ############################################################################################
            self.call_vega = []
            self.put_vega = []

            ############################################################################################
            # If the cash available is less then the spread wings we do not haev the money to trade
            ############################################################################################
            self.portfolio_blew_up = self.check_if_portfolio_blew_up(distance_of_wings, self.get_cash())
            if self.portfolio_blew_up:
                return

            ############################################################################################
            # Output the parameters of the strategy to the indicator file
            ############################################################################################
            self.add_marker(
                    f"Parameters used in this model",
                    value=underlying_price+30,
                    color="pink",
                    symbol="square-dot", 
                    detail_text=self.parameters_for_debug
                )
            # Get next 3rd Friday expiry after the date
            expiry = self.get_next_expiration_date(option_duration, symbol, rounded_underlying_price)

            # IMS used for debugging.  Create a criteria and then put a break on the print statement
            # break_date = dtime.date(2022, 3, 18)
            # if expiry == break_date:
            #     print("break")

            sides = self.select_sides(trade_strategy)
            roll = False
            # Create the initial condor
            condor_status, call_strike, put_strike, purchase_credit, last_trade_size, last_call_delta, last_put_delta = self.create_legs(
                symbol, expiry, strike_step_size, call_delta_required, put_delta_required, quantity_to_trade, distance_of_wings, sides, maximum_portfolio_allocation, self.last_trade_size, max_strikes, roll
            )

            # Used when calculating and placing rolls
            self.purchase_credit = purchase_credit
            self.last_trade_size = last_trade_size

            if "Success" in condor_status:
                self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit
                # Add marker to the chart
                self.add_trade_marker(trade_strategy, dt, expiry, underlying_price, call_strike, put_strike, last_call_delta, last_put_delta, purchase_credit, roll)
            else:
                # Add marker to the chart
                self.add_marker(
                    f"Create Trade Failed: {condor_status}",
                    value=underlying_price,
                    color="blue",
                    symbol="asterisk",
                    detail_text=f"Date: {dt}<br>Strategy: {trade_strategy}<br>Expiration: {expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}<br>credit: {purchase_credit}"
                ) 

        else:
            #######################################################################
            # End of first iteration or no active condor
            #######################################################################

            roll_call_short = False
            roll_put_short = False
            sell_the_condor = False
            option_expiry = None
            call_strike = None
            put_strike = None
            original_expiration_date = None
            close_reason = "Closing, unknown reason"

            ###################################################################################
            # Loop through all of the open positions
            # This code assumes only one condor is open at a time
            # Check for the following conditions:
            # 1.   Days before expiration to buy back
            # 2a.  Roll if: Delta of the option is above the delta required or
            # 2b.  The underlying price is within the strike roll distance of the short strike
            # 3.   The maximum loss has been exceeded
            # 4.   The maximum number of rolls has been exceeded
            ###################################################################################

            for position in positions:
                # Reset sell/roll indicator before exit positions
                roll_call_short = False
                roll_put_short = False
                sell_the_condor = False
                position_strike = position.asset.strike

                # If the position is an option
                if position.asset.asset_type == "option":

                    # Get the expiry of the option
                    option_expiry = position.asset.expiration

                    # Saved for a potential roll
                    original_expiration_date = option_expiry

                    # Check how close to expiry the option is
                    days_to_expiry = (option_expiry - dt.date()).days

                    # If the option is within the days before expiry to buy back
                    if days_to_expiry <= days_before_expiry_to_buy_back:
                        # We need to buy back the option
                        sell_the_condor = True
                        cost_to_close = self.cost_to_close_position()
                        close_reason = f"Closing for days: credit {self.purchase_credit}, close {cost_to_close}"
                        break

                    # Base on the value of roll_strategy, determine if we need to roll on delta or on how close
                    # the underlying price is to the short strike.
                    call_short_strike_boundary = None
                    put_short_strike_boundary = None
                    roll_reason = "Rolling, unknown reason"
                    delta_message = ""

                    # Currently all adjustments are made on the short side of the condor
                    if position.quantity < 0:
                        greeks = self.get_greeks(position.asset)
                        self.debug_print(f"Delta: {greeks['delta']}, Theta: {greeks['theta']}, Gamma: {greeks['gamma']}, Vega: {greeks['vega']}")

                        # # Track the vega for the call and put options
                        # if position.asset.right == "CALL":
                        #     self.call_vega.append(greeks["vega"])
                        #     self.add_line(f"call_vega", greeks.vega)   
                        # elif position.asset.right == "PUT":
                        #     self.put_vega.append(greeks["vega"])
                        #     self.add_line(f"put_vega", greeks.vega)  

                        # Check the delta of the option if the strategy is delta based
                        if roll_strategy == "delta":
                            self.roll_current_delta = greeks["delta"]

                        # Check if the option is a call
                        if position.asset.right == "CALL":

                            if roll_strategy == "delta":
                                # Check if the delta is above the delta required
                                if abs(greeks["delta"]) > abs(delta_threshold):
                                    roll_call_short = True
                                    roll_reason = f"Rolling for CALL short delta: {greeks['delta']}"
                                    break
                            
                            if roll_strategy == "short":
                                call_short_strike_boundary = position.asset.strike - strike_roll_distance
                                call_strike = position.asset.strike
                                if underlying_price >= call_short_strike_boundary:
                                    # If it is, we need to roll the option
                                    roll_call_short = True
                                    roll_reason = f"Rolling for distance to CALL short"
                                    break

                        # Check if the option is a put
                        elif position.asset.right == "PUT":

                            if roll_strategy == "delta":
                                # Check if the delta is above the delta required
                                if abs(greeks["delta"]) > abs(delta_threshold):
                                    roll_put_short = True
                                    roll_reason = f"Rolling for PUT short delta: {greeks['delta']}"
                                    break
                            
                            if roll_strategy == "short":
                                put_short_strike_boundary = position.asset.strike + strike_roll_distance
                                put_strike = position.asset.strike
                                if underlying_price <= put_short_strike_boundary:
                                    # If it is, we need to roll the option
                                    roll_put_short = True
                                    roll_reason = f"Rolling for distance to PUT short"
                                    break
            
            #######################################################################
            # Check if we need to sell the condor completely or roll one spread
            #######################################################################
                            
            if roll_call_short or roll_put_short:
                self.roll_count += 1
                if self.roll_count > maximum_rolls:
                    sell_the_condor = True
                    roll_call_short = False
                    roll_put_short = False
                    cost_to_close = self.cost_to_close_position()
                    close_reason = f"{roll_reason}, rolls ({self.roll_count}), credit {self.purchase_credit}, close {cost_to_close} "
                    if skip_on_max_rolls:
                        self.stay_out_of_market = True
                        self.skipped_days_counter = 0

            ########################################################################
            # Check for max move exit condition are met
            # These conditions are check at the beginning of the day
            ########################################################################
            if self.max_move_hit_flag:
                # If we have a condor active sell it
                if len(positions) > 1:
                    sell_the_condor = True
                    roll_call_short = False
                    roll_put_short = False
                    self.stay_out_of_market = True
                    self.skipped_days_counter = 0
                    cost_to_close = self.cost_to_close_position()
                    close_reason = f"Max move hit: credit {self.purchase_credit}, cost to close {cost_to_close}"

 
            ########################################################################
            # Check for maximum loss over if do not have a max move exit condition
            ########################################################################
            if max_loss_multiplier != 0 and self.maximum_loss_exceeded(self.purchase_credit, max_loss_multiplier):
                # If we have a condor active sell it
                if len(positions) > 1:
                    sell_the_condor = True
                    roll_call_short = False
                    roll_put_short = False
                    self.stay_out_of_market = True
                    self.skipped_days_counter = 0
                    cost_to_close = self.cost_to_close_position()
                    close_reason = f"Maximum loss: credit {self.purchase_credit}, cost to close {cost_to_close}"

            ########################################################################
            # Now execute the close and roll conditions
            ########################################################################

            # First check if we need to sell the condor completely and create a new one
            if sell_the_condor:
                
                # The prior condor was closed because we approach the expiration date.  It is generally dangerous
                # to leave condors active since the gamma of the options accelerate as we approach the 
                # expiration date. Another way of saying the above is the pricing of options become more volatile
                # as we approach the expiration date.  

                self.sell_all()

                # Reset the roll count since we are creating a new condor with both legs
                self.roll_count = 0

                # Reset the minimum time to hold a condor
                self.hold_length = 0

                close_color = "red"
                if "max" in close_reason:
                    close_color = "purple"

                self.add_marker(
                    f"{close_reason}",
                    value=underlying_price,
                    color=close_color,
                    symbol="triangle-down",
                    detail_text=f"day_to_expiry: {days_to_expiry}<br>underlying_price: {underlying_price}<br>position_strike: {position_strike}"
                )

                # Sleep for 5 seconds to make sure the order goes through
                # IMS Only sleep when live, this sleep function will no-opt in a backtest
                self.sleep(5)

                # Check to see if the close was due to max loss, max move and if it was just return
                # If the max loss delay is hit, the code at the start of each day will open
                # a new condor.
                if self.stay_out_of_market:
                    self.purchase_credit = 0
                    return
                
                # Get closest 3rd Friday expiry
                new_expiry = self.get_next_expiration_date(option_duration, symbol, rounded_underlying_price)

                # Since we close the prior condor and we can open another one with a new expiration date
                # and strike based on the original parameters.
                sides = self.select_sides(trade_strategy)
                roll = False
                condor_status, call_strike, put_strike, purchase_credit, last_trade_size, last_call_delta, last_put_delta = self.create_legs(
                    symbol, new_expiry, strike_step_size, call_delta_required, put_delta_required, quantity_to_trade, distance_of_wings, sides, maximum_portfolio_allocation, self.last_trade_size, max_strikes, roll
                )

                # These values are used for calculating and placing rolls
                self.purchase_credit = purchase_credit
                self.last_trade_size = last_trade_size

                # IMS This is just a place holder.  This need to be rethought.
                self.margin_reserve = distance_of_wings * 100 * quantity_to_trade

                if "Success" in condor_status: 
                    self.margin_reserve = distance_of_wings * 100 * quantity_to_trade  # IMS need to update to reduce by credit
                    # Add marker to the chart
                    self.add_trade_marker(trade_strategy, dt, new_expiry, underlying_price, call_strike, put_strike, last_call_delta, last_put_delta,     purchase_credit, roll)
                else:
                    # Add marker to the chart
                    self.add_marker(
                        f"New trade creation failed: {condor_status}",
                        value=underlying_price,
                        color="blue",
                        symbol="cross-open-dot",
                        detail_text=f"Date: {dt}<br>Expiration: {new_expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}"
                    ) 

            #################################################################################################
            # The following section will roll one side of the condor if the underlying price approaches the
            # short strike on that side.  The new short strike will be selected based on the rolled delta
            # parameter.  We can make this delta smaller to give us more room.  The tradeoff is that we will
            # get less credit for the condor.  
            #################################################################################################
                    
            elif (roll_call_short or roll_put_short):
                if (int(self.hold_length) < int(minimum_hold_period)) and (not self.max_move_hit_flag):
                    self.add_marker(
                        f"Short hold period was not exceeded: {self.hold_length}<{minimum_hold_period}",
                        value=underlying_price,
                        color="yellow",
                        symbol="hexagon-open",
                        detail_text=f"Date: {dt}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}"
                    )
                    return
                
                roll_message = ""
                roll_close_status = ""
                roll = False
                if roll_call_short:
                    roll_message = f"{roll_reason}, {delta_message} "
                    side = "call"
                    roll = True
                    roll_close_status = self.close_spread(side)
                if roll_put_short:
                    roll_message = f"{roll_reason}, {delta_message} "
                    side = "put"
                    roll = True
                    roll_close_status = self.close_spread(side)
                
                # Reset the hold period counter
                self.hold_length = 0

                # IMS margin requirement needs to be update to reflect the change in the credit
                # The basic margin requirement remains the same.  The margin reserve is reduced by the cost of the roll
                self.margin_reserve = distance_of_wings * 100 * quantity_to_trade  # IMS need to update to reduce by credit

                # Sleep for 5 seconds to make sure the order goes through
                # IMS This is a noop in backtest mode
                self.sleep(5)

                cost_to_close = self.cost_to_close_position(side=side)

                # Add marker to the chart
                self.add_marker(
                    f"{roll_message}, cost {cost_to_close}",
                    value=underlying_price,
                    color="yellow",
                    symbol="triangle-down",
                    detail_text=f"day_to_expiry: {days_to_expiry}<br>\
                        underlying_price: {underlying_price}<br>\
                        position_strike: {position_strike}<br>\
                        {roll_close_status}"
                )

                # Use the original option expiration date when we only roll one side
                # However, we do use a different delta for the new short strike
                # By lowering the delta we reduce the risk it will be hit again
                roll_expiry = original_expiration_date

                # IMS This is an example of how to set a breakpoint for a specific date.
                # Set the breakpoint on the print statement.
                # break_date = dtime.date(2022, 3, 18)
                # if roll_expiry.year == 2024:
                #     print("break")

                condor_status, call_strike, put_strike, purchase_credit, last_trade_size, last_call_delta, last_put_delta = self.create_legs(
                    symbol, roll_expiry, strike_step_size, call_delta_required, put_delta_required, quantity_to_trade, distance_of_wings, side, maximum_portfolio_allocation, self.last_trade_size, max_strikes, roll
                )

                # The maximum_credit is only used when we initiate a new condor, not when we roll

                if "Success" in condor_status:
                    self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit
                    # Add marker to the chart
                    self.add_trade_marker(trade_strategy, dt, roll_expiry, underlying_price, call_strike, put_strike, last_call_delta, last_put_delta, purchase_credit,roll)       

                else:
                    # Add marker to the chart
                    self.add_marker(
                        f"Roll Failed: {condor_status}",
                        value=underlying_price,
                        color="blue",
                        symbol="asterisk",
                        detail_text=f"Date: {dt}<br>Expiration: {roll_expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}"
                    )  
    
        return

    ##############################################################################################
    # The following function creates an iron condor or a single spread when rolling an iron condor
    # The side parameters determines if we create a full condor, "both", or roll the "call"
    ##############################################################################################

    def create_legs(
        self, symbol, expiry, strike_step_size, call_delta_required, put_delta_required, quantity_to_trade, distance_of_wings, side, maximum_portfolio_allocation, last_trade_size, max_strikes, roll
    ):

        self.debug_print (f"************************* Creating Legs *************************")
        self.debug_print (f"Symbol: {symbol}, Expiry: {expiry}, Strike Step Size: {strike_step_size}, Call Delta Required: {call_delta_required}, Put Delta Required: {put_delta_required}, Quantity to Trade: {quantity_to_trade}, Distance of Wings: {distance_of_wings}, Side: {side}, Maximum Portfolio Allocation: {maximum_portfolio_allocation}, Last Trade Size: {last_trade_size}, Max Strikes: {max_strikes}, Roll: {roll}")
        status = "no condor created"
        # break_date = dtime.date(2022, 3, 18)
        # if expiry == break_date:
        #     print("break")

        # Maximum credit is only calculated when we create a new condor, i.e. side == "both"
        maximum_credit = 0
        
        # Get the current price of the underlying asset
        underlying_price = self.get_last_price(symbol)

        # Round the underlying price to the nearest strike step size
        rounded_underlying_price = (
            round(underlying_price / strike_step_size) * strike_step_size
        )

        revised_quantity_to_trade = quantity_to_trade
        if roll:
            revised_quantity_to_trade = last_trade_size  # Always use the same size when rolling


        ################################################################
        # Check the cash available in the account and set the trade size
        # Only do this for new condors not for rolls
        ################################################################

        # IMS we need to revise this to consider both cash and margin

        if not roll:
            portfolio_value = self.get_portfolio_value()
            if portfolio_value < 0:
                print ("****** invalid portfolio value")

            cash_required = distance_of_wings * 100 * quantity_to_trade
            if cash_required > portfolio_value * maximum_portfolio_allocation:
                # Reduce the size of the trade
                revised_quantity_to_trade = int((portfolio_value * maximum_portfolio_allocation) / (distance_of_wings * 100))
            else:
                revised_quantity_to_trade = quantity_to_trade

        if revised_quantity_to_trade <= 0:
            print ("****** invalid trade size")
            sys.exit(1)

        ################################################
        # Find the strikes for both the shorts and longs
        ################################################

        # IMS The following code is not very efficient and should be refactored

        # strikes = [
        #     rounded_underlying_price + strike_step_size * i for i in range(0, max_strikes)
        # ] + [rounded_underlying_price - strike_step_size * i for i in range(1, max_strikes)]
        # strikes.sort()  # Sort the strikes

        self.debug_print ("Retrieving strikes")
        api_key = POLYGON_CONFIG["API_KEY"]
        put_strikes, call_strikes = self.get_option_strikes(symbol, expiry, max_strikes, rounded_underlying_price, api_key)

        self.debug_print(f"Current Price: {rounded_underlying_price}")
        self.debug_print(f"Put Strikes: {put_strikes}")
        self.debug_print(f"Call Strikes: {call_strikes}")

        # IMS Eliminate negative numbers from strikes
        # strikes = [strike for strike in strikes if strike > 0]
    
        # Only keep the strikes above the underlying price for calls
        call_strikes = [call_strike for call_strike in call_strikes if call_strike > underlying_price]
        # Sort the strikes in ascending order
        call_strikes.sort()
        call_strike_deltas = self.get_strike_deltas(
            symbol, expiry, call_strikes, "call", stop_less_than=call_delta_required
        )

        # Find the call option with an appropriate delta and the expiry
        # IMS Optimization -- start searching from the back, this should be the last entry
        call_strike = None
        for strike, delta in call_strike_deltas.items():
            if delta is not None and delta <= call_delta_required:
                call_strike = strike
                last_call_delta = delta
                break

        # If we didn't find a call strike set an error message
        if call_strike is None and (side == "call" or side =="both"):
            status = "no call strike found"
            print ("********************** No Call Strike Found ************")
            return status, 0, 0, 0, 0, 0, 0

        # Only keep the strikes below the underlying price for puts
        put_strikes = [put_strike for put_strike in put_strikes if put_strike < underlying_price]
        # Sort the strikes in descending order
        put_strikes.sort(reverse=True)
        put_strike_deltas = self.get_strike_deltas(
            symbol, expiry, put_strikes, "put", stop_greater_than=-put_delta_required
        )

        # Find the put option with a the correct delta and the expiry
        put_strike = None
        for strike, delta in put_strike_deltas.items():
            if delta is not None and delta >= -put_delta_required:
                put_strike = strike
                last_put_delta = delta
                break

        # If we didn't find a  put strike set an error message
        if put_strike is None and (side == "put" or side =="both"):
            status = "no put strike found"
            print ("********************** No Put Strike Found ************")
            return status, 0, 0, 0, 0, 0, 0

        ###################################################################################
        # Attempt to find the orders (combination of strike, and expiration)
        ###################################################################################

        # Make 5 attempts to create the call side of the condor
        # We use 5 attempts because as we move out of the money, the distance between strikes
        # may increase from 1 to 5

        # IMS only try up to the number of strikes we have in the list
        # Change to 3 for now in the range(5) was 5

        call_strike_adjustment = 0
        put_sell_order, put_buy_order, call_sell_order, call_buy_order = None, None, None, None
        if side == "call" or side == "both":
            for i in range(5):
                call_sell_order, call_buy_order = self.get_call_orders(
                    symbol,
                    expiry,
                    strike_step_size,
                    call_strike + call_strike_adjustment,
                    revised_quantity_to_trade,
                    distance_of_wings,
                )

                # Check if we got both orders
                if call_sell_order is not None and call_buy_order is not None:
                    break

                # If we didn't get both orders, then move the call strike up
                else:
                    call_strike_adjustment -= strike_step_size

        if side=="put" or side == "both":
            # Make 5 attempts to create the put side of the condor
            put_strike_adjustment = -call_strike_adjustment
            for i in range(5):
                put_sell_order, put_buy_order = self.get_put_orders(
                    symbol,
                    expiry,
                    strike_step_size,
                    put_strike + put_strike_adjustment,
                    revised_quantity_to_trade,
                    distance_of_wings
                )

                # Check if we got both orders
                if put_sell_order is not None and put_buy_order is not None:
                    break

                # If we didn't get both orders, then move the put strike down
                else:
                    # put_strike_adjustment += strike_step_size
                    put_strike_adjustment += 1

        ############################################
        # Submit all of the orders
        ############################################

        if (
            call_sell_order is not None
            and call_buy_order is not None
        ):
            # Submit the orders
            self.submit_order(call_sell_order)
            self.submit_order(call_buy_order)

        if (
            put_sell_order is not None
            and put_buy_order is not None
        ):
            # Submit the orders
            self.submit_order(put_sell_order)
            self.submit_order(put_buy_order)

        ############################################
        # Calculate the maximum credit of the condor
        ############################################
        
        call_sell_price, call_buy_price, put_sell_price, put_buy_price = 0, 0, 0, 0
        # These will be estimates since we do not have the actual fill prices at this time
        # We cannot use the get_current_credit method since the order is not live yet
        if (call_sell_order):
            self.debug_print (f"get_last_price {call_sell_order.asset.strike}")
            call_sell_price = self.get_last_price(call_sell_order.asset)
        if (call_buy_order):
            self.debug_print (f"get_last_price {call_buy_order.asset.strike}")
            call_buy_price = self.get_last_price(call_buy_order.asset)
        if (put_sell_order):
            self.debug_print (f"get_last_price {put_sell_order.asset.strike}")
            put_sell_price = self.get_last_price(put_sell_order.asset)
        if (put_buy_order):
            self.debug_print (f"get_last_price {put_buy_order.asset.strike}")
            put_buy_price = self.get_last_price(put_buy_order.asset)
        maximum_credit = round(call_sell_price - call_buy_price + put_sell_price - put_buy_price,2)

      
        ############################################
        # Return an appropriate status
        ############################################
            
        # IMS This code should be refactored.  It is generally considered bad practice
        # to have multiple return statements in a function.  It is also bad practice
        # to mix return data types.
        
        if side == "both" and \
            (call_sell_order is None or \
             call_buy_order is None or \
             put_sell_order is None or \
             put_buy_order is None):
            print ("********************** Failed to place condor ************")
            return "failed to place condor", call_strike, put_strike, 0, 0, 0 ,0
        elif side == "call" and (call_sell_order is None or call_buy_order is None):
            print ("********************** Failed to place call side ************")
            return "failed to roll call side", call_strike, put_strike, 0, 0, 0 ,0
        elif side == "put" and (put_sell_order is None or put_buy_order is None):
            print ("********************** Failed to place put side ************")
            return "failed to roll put side", call_strike, put_strike, 0, 0, 0, 0
        else:
            status_messages = {
                "call": "Success: rolled the call side",
                "put": "Success: rolled the put side",
                "both": "Success the Condor" }

        last_trade_size = revised_quantity_to_trade
        return status_messages[side], call_strike, put_strike, maximum_credit, last_trade_size, last_call_delta, last_put_delta 
    
    ############################################
    # Utility functions
    ############################################

    def debug_print(self, msg):
        if not mwt_debug:
            return
        
        print (f"MWT DEBUG: LINE NUMBER: {inspect.currentframe().f_back.f_lineno} - {msg}")
        return
    
    def select_sides(self, trade_strategy):
        if trade_strategy == "iron-condor":
            return "both"
        if trade_strategy == "bull-put-spread":
            return "put"
        if trade_strategy == "bear-call-spread":
            return "call"
        if trade_strategy == "hybrid":
            return "both"
        return "both"
    
    def add_trade_marker(self, trade_strategy, dt, expiry, underlying_price, call_strike, put_strike, last_call_delta, last_put_delta, purchase_credit, roll):
        if roll:
            verb = "Rolled"
        else:
            verb = "Created"

        if trade_strategy == "iron-condor":
            self.add_marker(
                f"{verb} Iron Condor, credit {purchase_credit}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",    
                detail_text=f"Date: {dt}<br>Expiration: {expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}<br>credit: {purchase_credit}, <br>call delta: {last_call_delta}, <br>put delta: {last_put_delta}"
            )
        elif trade_strategy == "bull-put-spread":
            self.add_marker(
                f"{verb} Bull Put Spread, credit {purchase_credit}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",    
                detail_text=f"Date: {dt}<br>Expiration: {expiry}<br>Last price: {underlying_price}<br>put short: {put_strike}<br>credit: {purchase_credit}, <br>put delta: {last_put_delta}"
            )
        elif trade_strategy == "bear-call-spread":
            self.add_marker(
                f"{verb} Bear Call Spread, credit {purchase_credit}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",    
                detail_text=f"Date: {dt}<br>Expiration: {expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>credit: {purchase_credit}, <br>call delta: {last_call_delta}"
            )
        elif trade_strategy == "hybrid":
            self.add_marker(
                f"{verb} Trade, credit {purchase_credit}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",    
                detail_text=f"Date: {dt}<br>Expiration: {expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}<br>credit: {purchase_credit}, <br>call delta: {last_call_delta}, <br>put delta: {last_put_delta}"
            )
        else:
            self.add_marker(
                f"{verb} Trade, credit {purchase_credit}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",    
                detail_text=f"Date: {dt}<br>Expiration: {expiry}<br>Last price: {underlying_price}<br>call short: {call_strike}<br>put short: {put_strike}<br>credit: {purchase_credit}, <br>call delta: {last_call_delta}, <br>put delta: {last_put_delta}"
            )

        return

    def check_if_portfolio_blew_up(self, distance_of_wings, cash):
        if cash < distance_of_wings * 100:
            self.add_marker(
                f"Portfolio Blew Up",
                value=0,
                color="red",
                symbol="square",
                detail_text=f"Date: {self.get_datetime()}<br>Cash available: {cash}"
            )
            return True
        return False

    def get_put_orders(
        self, symbol, expiry, strike_step_size, put_strike, quantity_to_trade, distance_of_wings
    ):
        # Sell the put option at the put strike
        put_sell_asset = Asset(
            symbol,
            asset_type="option",
            expiration=expiry,
            strike=put_strike,
            right="put",
        )

        # Get the price of the put option
        put_sell_price = self.get_last_price(put_sell_asset)

        # Create the order
        put_sell_order = self.create_order(put_sell_asset, quantity_to_trade, "sell")

        # Buy the put option below the put strike
        put_buy_asset = Asset(
            symbol,
            asset_type="option",
            expiration=expiry,
            strike=put_strike - distance_of_wings,  # IMS was strike_step_size
            right="put",
        )

        # Get the price of the put option
        self.debug_print (f"get_last_price {put_buy_asset.strike}")
        put_buy_price = self.get_last_price(put_buy_asset)

        # Create the order
        put_buy_order = self.create_order(put_buy_asset, quantity_to_trade, "buy")

        if put_sell_price is None or put_buy_price is None:
            return None, None

        return put_sell_order, put_buy_order

    def get_call_orders(
        self, symbol, expiry, strike_step_size, call_strike, quantity_to_trade, distance_of_wings
    ):
        # Sell the call option at the call strike
        call_sell_asset = Asset(
            symbol,
            asset_type="option",
            expiration=expiry,
            strike=call_strike,
            right="call",
        )

        # Get the price of the call option
        self.debug_print (f"get_last_price {call_sell_asset.strike}")
        call_sell_price = self.get_last_price(call_sell_asset)

        if quantity_to_trade <= 0:
            print(f"invalid quality to trade: {quantity_to_trade}\n")

        call_sell_order = self.create_order(call_sell_asset, quantity_to_trade, "sell")

        # Buy the call option above the call strike
        call_buy_asset = Asset(
            symbol,
            asset_type="option",
            expiration=expiry,
            strike=call_strike + distance_of_wings, # strike_step_size
            right="call",
        )

        # Get the price of the call option
        call_buy_price = self.get_last_price(call_buy_asset)
        self.debug_print (f"call buy price is {call_buy_price}, strike {call_strike + distance_of_wings}, expiration {expiry}")

        # Create the order
        call_buy_order = self.create_order(call_buy_asset, quantity_to_trade, "buy")

        if call_sell_price is None or call_buy_price is None:
            return None, None

        return call_sell_order, call_buy_order

    def get_strike_deltas(
        self,
        symbol,
        expiry,
        strikes,
        right,
        stop_greater_than=None,
        stop_less_than=None,
    ):
        # Get the greeks for each strike
        strike_deltas = {}
        for strike in strikes:
            # Create the asset
            asset = Asset(
                symbol,
                asset_type="option",
                expiration=expiry,
                strike=strike,
                right=right,
            )

            # Use the price to verify the strike is valid
            # IMS we may be able to drop this now that we use polygon to retrieve the strikes
            # IMS Potential optimization
            # valid_strike = self.get_last_price(asset)
            valid_strike = 1

            if valid_strike is not None and valid_strike > 0:
                # Get the greeks for the asset if it is a valid strike
                # Invalid strikes will have a price of zero
                # Invoking get_geeks with an invalid strike will generate an error
                greeks = self.get_greeks(asset)

                if greeks is not None:
                    strike_deltas[strike] = greeks["delta"]
                    if (
                        stop_greater_than
                        and greeks["delta"]
                        and greeks["delta"] >= stop_greater_than
                    ):
                        break

                    if (
                        stop_less_than
                        and greeks["delta"] 
                        and greeks["delta"] <= stop_less_than
                    ):
                        break
                else: 
                    # IMS The calling code will check for None and skip these strikes
                    strike_deltas[strike] = None
            else:   
                strike_deltas[strike] = None

        return strike_deltas
    
    # IMS The code to close a side does not do any retries.  This will be a problem in live trading.
    # This code assumes we only have one condor open at a time.  It loops through and closes
    # all the options.  This is not a good assumption for a more sophisticated strategy.

    def cost_to_close_position(self, side="both"):
        cost_to_close = 0
        positions = self.get_positions()
        # Loop through and close all of the puts
        for position in positions:
            # If the position is an option
            if position.asset.asset_type == "option":
                if side == "both":
                    self.debug_print (f"Cost to close position both: {position.asset.strike}")
                    last_price = self.get_asset_price(position.asset.symbol,position.asset.expiration,position.asset.strike, position.asset.right)
                    if position.quantity >= 0:
                        cost_to_close += -last_price
                    else:
                        cost_to_close += last_price

                if side == "put" and position.asset.right == "put":
                    self.debug_print (f"Cost to close position put: {position.asset.strike}")
                    last_price = self.get_asset_price(position.asset.symbol,position.asset.expiration,position.asset.strike, position.asset.right)
                    if position.quantity >= 0:
                        cost_to_close += -last_price
                    else:
                        cost_to_close += last_price

                if side == "call" and position.asset.right == "call":
                    self.debug_print (f"Cost to close position call: {position.asset.strike}")
                    last_price = self.get_asset_price(position.asset.symbol,position.asset.expiration,position.asset.strike, position.asset.right)
                    if position.quantity >= 0:
                        cost_to_close += -last_price
                    else:
                        cost_to_close += last_price

        return round(cost_to_close,2)
    
    def get_asset_price(self, symbol, expiration, strike, right):
        asset = Asset(
            symbol,
            asset_type="option",
            expiration=expiration,
            strike=strike,
            right=right,
        )
        return self.get_last_price(asset)

    def close_spread(self, right):
        # Make sure the right is in upper case because the asset.right is upper case
        right = right.upper()
        # Get all the open positions
        positions = self.get_positions()

        close_status = "no side to close"

        # Loop through and close all of the calls
        for position in positions:
            # If the position is an option
            if position.asset.asset_type == "option":
                if position.asset.right == right:
                    # call_sell_order = self.get_selling_order(position)
                    asset = Asset(
                        position.asset.symbol,
                        asset_type="option",
                        expiration=position.asset.expiration,
                        strike=position.asset.strike,
                        right=position.asset.right,
                    )
                     # If this is a short we buy to close if it is long we sell to close                   
                    if position.quantity < 0:
                        action = "buy"
                    else:
                        action = "sell"

                    call_close_order = self.create_order(asset, abs(position.quantity), action)

                    self.submit_order(call_close_order)
                        
        return 

    # IMS This code assumes we only have one condor open at a time.  It loops through and calculates
    # the current credit of the condor.  This is not a good assumption for a more sophisticated strategy.
    
    def maximum_loss_exceeded(self, purchase_credit, max_loss_multiplier):

        cost_to_close = self.cost_to_close_position()
        max_loss_allowed = purchase_credit * max_loss_multiplier
    
        if cost_to_close > max_loss_allowed:
            return True
        else:
            return False
    
    
    def search_next_market_date( self, expiry, symbol, rounded_underlying_price):

        # Check if there is an option with this expiry (in case it's a holiday or weekend)
        while True:
            original_expiry = expiry
            # Check if we already know that this expiry doesn't exist
            if expiry in self.non_existing_expiry_dates:
                # Increase the expiry by one day
                expiry += timedelta(days=1)
                if expiry > (original_expiry + timedelta(days=5)):
                    return original_expiry
                else:
                    continue

            # Create the asset
            # IMS This was causing a polygon error when trying to get an option on a non-option strike
            # asset = Asset(
            #     symbol,
            #     asset_type="option",
            #     expiration=expiry,
            #     strike=rounded_underlying_price,
            #     right="call",
            # )

            # Get the price of the option
            self.debug_print (f"search_next_market_date: expiry {expiry}, price {rounded_underlying_price}")
            price = self.get_last_price(symbol)

            # If we got the price, then break because this expiry is valid
            if price is not None:
                break

            # Add the expiry to the list of non existing expiry dates
            self.non_existing_expiry_dates.append(expiry)

            # If we didn't get the price, then move the expiry forward by one day and try again
            expiry += timedelta(days=1)
            if expiry > (original_expiry + timedelta(days=5)):
                # If we have increased the expiry by 5 days and still haven't found an expiry date
                # then return the original date.  This may cause a non-fatal error but this is better
                # than an infinite loop.
                return original_expiry 

        return expiry
        
    def get_next_expiration_date(self, option_duration, symbol, strike_price):
        dt = self.get_datetime()
        suggested_date = self.get_option_expiration_after_date(dt + timedelta(days=option_duration))
        return self.search_next_market_date(suggested_date, symbol, strike_price)
    
    def get_option_strikes(self, symbol, expiration_date, maximum_strikes, current_price, api_key):
        options = []
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
            
################################################################################################
# If this module is run as a script it will invoke the backtest method in the Lumibot framework.
################################################################################################
    
# Make sure that the dates selected are supported by you Polygon.io subscription

if __name__ == "__main__":
        
        trading_fee = TradingFee(flat_fee=0.60)  # IMS account for trading fees and slippage

        # convert strategy_parmeters["starting_date"] to a datetime object
        backtesting_start = datetime.strptime(OptionsStrategyEngine.parameters["starting_date"], "%Y-%m-%d") 
        backtesting_end = datetime.strptime(OptionsStrategyEngine.parameters["ending_date"], "%Y-%m-%d")

        # polygon_has_paid_subscription is set to true to api calls are not throttled
        backtest_results = OptionsStrategyEngine.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset=OptionsStrategyEngine.parameters["symbol"],
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
            show_indicators=False,  
            save_tearsheet=True,
            show_plot=False,
            show_tearsheet=False,
            polygon_api_key=POLYGON_CONFIG["API_KEY"],
            polygon_has_paid_subscription=True,
            name=OptionsStrategyEngine.strategy_name,
            budget = OptionsStrategyEngine.parameters["budget"],
        )

        print("********** Backtest Results **********")
        pprint.pprint(backtest_results)
 
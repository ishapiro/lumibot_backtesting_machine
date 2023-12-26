from datetime import datetime, timedelta
import datetime as dtime
from decimal import Decimal

from lumibot.entities import Asset, TradingFee
from lumibot.strategies.strategy import Strategy

# IMS moved all module includes to the top of the code
from credentials import POLYGON_CONFIG
from lumibot.backtesting import PolygonDataBacktesting

"""
Disclaimer: The options strategies presented within this content are intended for educational purposes only. They are not meant to be used for trading live stocks or any other financial instruments. The information provided is based on historical data and hypothetical scenarios, and it does not guarantee future results or profits.

Trading stocks and options involve substantial risks and may result in the loss of your invested capital. It is essential to conduct thorough research, seek advice from a qualified financial professional, and carefully consider your risk tolerance before engaging in any trading activities.

The strategies discussed in this content should not be regarded as recommendations or endorsements. The market conditions, regulations, and individual circumstances can significantly impact the outcome of any trading strategy. Therefore, it is crucial to understand that every investment decision carries its own risks, and you should exercise caution and diligence when applying any information provided herein.

By accessing and utilizing the information presented, you acknowledge that you are solely responsible for any trading decisions you make. Neither the author nor any associated parties shall be held liable for any losses, damages, or consequences arising from the use of the strategies discussed in this content.

Always remember that trading in the financial markets involves inherent risks, and it is recommended to seek professional advice and conduct thorough analysis before making any investment decisions.
"""


"""
Strategy Description

Author: Irv Shapiro (ishapiro@cogitations.com)
YouTube: MakeWithTech

Based on: Lumibot Condor Example, modified to incorportate concepts discuss in the SMB Capital
Options Trading Course.

NOTE: The current version assumes only one condor is open at a time!!!
NOTE: Maximum margin is not enforced!!!

This parameterized Iron Condor Test is desgined to facilitate testing condors across a range of names,
deltas and expiration dates.

An iron condor is a market neutral strategy that profits when the underlying asset stays within a range.

Key user defined parameters:

Days to expiration
Delta of the shorts
Spacing of wings -- wings are equally spaced based on dollars not delta
Days before expiration to exit the trade
When to roll one of the spreads

Explaination of Iron Condor Parameters:

    Condor Example
    
    call log position
    call short position
    call short_strike_boundary
    
    Initial Stock Position
    
    put short_strike_boundary
    put short position
    put long posittion

When the price of the underlying asset gets within a certain distance of the short strike, the strategy
will roll the short strike to a new strike.  The distance of the short strike is defined by the
parameter strike_roll_distance.  The roll will be in the direction of the underlying price movement.
    
"""


class OptionsIronCondorMWT(Strategy):

    distance_of_wings = 15 # reference in multiple parameters below, in dollars not strikes
    parameters = {
        "symbol": "SPY",
        "option_duration": 40,  # How many days until the call option expires when we sell it
        "strike_step_size": 1,  # IMS Is this the strike spacing of the specific asset, can we get this from Poloygon?
        "delta_required": 0.15,  # The delta of the option we want to sell
        "days_before_expiry_to_buy_back": 7,  # How many days before expiry to buy back the call
        "quantity_to_trade": 10,  # The number of contracts to trade
        "minimum_hold_period": 7,  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
        "distance_of_wings" : distance_of_wings, # Distance of the longs from the shorts in dollars -- the wings
        "budget" : 100000, # Maximum portfolio size
        "strike_roll_distance" : (0.10 * distance_of_wings) # How close to the short do we allow the price to move before rolling.
    }

    # The Lumibot framework does not current track margin requirements.  For this strategy
    # we will track margin manually using the following approximation in an instance variable.
    #
    # margin reserve = distance of wings - condor credit
    #
    margin_reserve = 0

    strategy_name = f'ic_{parameters["delta_required"]}delta-{parameters["option_duration"]}duration-{parameters["days_before_expiry_to_buy_back"]}exit-{parameters["minimum_hold_period"]}hold'

    def initialize(self):
        # The time to sleep between each trading iteration
        self.sleeptime = "1D"  # 1 minute = 1M, 1 hour = 1H,  1 day = 1D

        # Initialize the wait counter
        self.hold_length = 0

        self.non_existing_expiry_dates = []

    def on_trading_iteration(self):
        # Get the parameters
        symbol = self.parameters["symbol"]
        option_duration = self.parameters["option_duration"]
        strike_step_size = self.parameters["strike_step_size"]
        delta_required = self.parameters["delta_required"]
        days_before_expiry_to_buy_back = self.parameters[
            "days_before_expiry_to_buy_back"
        ]
        distance_of_wings = self.parameters["distance_of_wings"]
        quantity_to_trade = self.parameters["quantity_to_trade"]
        minimum_hold_period  = self.parameters[
            "minimum_hold_period"
        ]
        strike_roll_distance = self.parameters["strike_roll_distance"]

        # Get the price of the underlying asset
        underlying_price = self.get_last_price(symbol)
        rounded_underlying_price = round(underlying_price, 0)

        # Add lines to the chart
        self.add_line(f"{symbol}_price", underlying_price)

        # IMS this only works because the strategy only holds one condor at a time
        self.hold_length += 1

        # Get the current datetime
        dt = self.get_datetime()

        # On first trading iteration, create the initial condor
        # IMS Once again this only works because we only hold one condor
        # a more sophisticated strategy using multiple condors will have to 
        # carfully track the margin reserve
        if self.first_iteration:
            # Get next 3rd Friday expiry after the date
            expiry = self.get_next_expiration_date(option_duration, symbol, rounded_underlying_price)

            # IMS used for debugging.  Create a criteria and then put a break on the print statement
            # break_date = dtime.date(2022, 3, 18)
            # if expiry == break_date:
            #     print("break")

            # Create the intial condor
            condor_status, call_strike, put_strike = self.create_condor(
                symbol, expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings, "both"
            )

            if "Success" in condor_status:
                self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit
                # Add marker to the chart
                self.add_marker(
                    f"Created 1st Condor: margin reserve {self.margin_reserve}",
                    value=underlying_price,
                    color="green",
                    symbol="triangle-up",    
                    detail_text=f"Date: {dt}\nExpiration: {expiry}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                )
            else:
                # Add marker to the chart
                self.add_marker(
                    f"Create Condor Failed: {condor_status}",
                    value=underlying_price,
                    color="blue",
                    symbol="asterisk",
                    detail_text=f"Date: {dt}\nExpiration: {expiry}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                ) 
            return

        # Get all the open positions
        positions = self.get_positions()

        roll_call_short = False
        roll_put_short = False
        should_sell_for_expiry = False
        option_expiry = None
        call_strike = None
        put_strike = None

        # Loop through all the positions
        for position in positions:
            # Reset sell/roll indicator before exit postions
            roll_call_short = False
            roll_put_short = False
            should_sell_for_expiry = False
            position_strike = position.asset.strike

            # If the position is an option
            if position.asset.asset_type == "option":

                # Get the expiry of the option
                option_expiry = position.asset.expiration

                # Check how close to expiry the option is
                days_to_expiry = (option_expiry - dt.date()).days

                # If the option is within the days before expiry to buy back
                if days_to_expiry <= days_before_expiry_to_buy_back:
                    # We need to buy back the option
                    should_sell_for_expiry = True
                    break

                # IMS roll when we are within a range of the short strikes
                call_short_strike_boundary = None
                put_short_strike_boundary = None

                # Check if it's a short position
                if position.quantity < 0:
                    # Check the delta of the option
                    # IMS NO longer used -- greeks = self.get_greeks(position.asset)

                    # Check if the option is a call
                    if position.asset.right == "CALL":
                        # Check if the delta is above the delta required
                        # IMS switch to check short cross over  -- if greeks["delta"] > delta_threshold:
                        call_short_strike_boundary = position.asset.strike - strike_roll_distance
                        call_strike = position.asset.strike
                        if underlying_price >= call_short_strike_boundary:
                            # If it is, we need to roll the option
                            roll_call_short = True
                            break

                    # Check if the option is a put
                    elif position.asset.right == "PUT":
                        # Check if the delta is below the delta required
                        # IMS switch to crossing strike -- if greeks["delta"] < -delta_threshold:
                        put_short_strike_boundary = position.asset.strike + strike_roll_distance
                        put_strike = position.asset.strike
                        if underlying_price <= put_short_strike_boundary:
                            # If it is, we need to roll the option
                            roll_put_short = True
                            break

        # If we need to sell for expiry
        if (should_sell_for_expiry):
            # Sell all of our positions
            self.sell_all()

            # Reset the minimum time to hold a condor
            self.hold_length = 0

            self.margin_reserve = self.margin_reserve - (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            self.add_marker(
                f"Close Condor for Days to Expiry: margin reserve {self.margin_reserve}",
                value=underlying_price,
                color="red",
                symbol="triangle-down",
                detail_text=f"day_to_expiry: {days_to_expiry}\nunderlying_price: {underlying_price}\nposition_strike: {position_strike}"
            )

            # Sleep for 5 seconds to make sure the order goes through
            # IMS Only sleep when live, this sleep function will no-opt in a backtest
            self.sleep(5)

            # Get closest 3rd Friday expiry
            new_expiry = self.get_next_expiration_date(option_duration, symbol, rounded_underlying_price)

            # break_date = dtime.date(2022, 3, 18)
            # if new_expiry.year == 2024:
            #     print("break")

            # Create a new condor
            condor_status, call_strike, put_strike = self.create_condor(
                symbol, new_expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings, "both"
            )

            if "Success" in condor_status:
                self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit
                # Add marker to the chart
                self.add_marker(
                    f"New Condor: margin reserve {self.margin_reserve}",
                    value=underlying_price,
                    color="green",
                    symbol="triangle-up",    
                    detail_text=f"Date: {dt}\nExpiration: {new_expiry}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                )
            else:
                # Add marker to the chart
                self.add_marker(
                    f"New condor creation failed: {condor_status}",
                    value=underlying_price,
                    color="blue",
                    symbol="asterisk",
                    detail_text=f"Date: {dt}\nExpiration: {new_expiry}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                ) 

        # Roll the option if it is over the minimum hold period and the underlying price is close to the short strike
        elif (roll_call_short or roll_put_short):
            if int(self.hold_length) < int(minimum_hold_period):
                self.add_marker(
                    f"Short exceeded hold was not exceeded: {self.hold_length}<{minimum_hold_period}",
                    value=underlying_price,
                    color="yellow",
                    symbol="circle-dot",
                    detail_text=f"Date: {dt}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                )
                return
            

            roll_message = ""
            if roll_call_short:
                roll_message = "Roll for approaching short strike: "
                side = "call"
                self.close_call_side()
            if roll_put_short:
                roll_message = "Roll for approaching put strike: "
                side = "put"
                self.close_put_side()

            # Reset the hold period counter
            self.hold_length = 0

            self.margin_reserve = self.margin_reserve - (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            # Sleep for 5 seconds to make sure the order goes through
            # IMS This is a noop in backtest mode
            self.sleep(5)

            # Add marker to the chart
            self.add_marker(
                f"Close for Roll, {roll_message} Margin reserve: {self.margin_reserve}",
                value=underlying_price,
                color="yellow",
                symbol="triangle-down",
                detail_text=f"day_to_expiry: {days_to_expiry}\n\
                    underlying_price: {underlying_price}\n\
                    position_strike: {position_strike}"
            )

            # Get closest 3rd Friday expiry
            roll_expiry = self.get_next_expiration_date(option_duration, symbol, rounded_underlying_price)

            # break_date = dtime.date(2022, 3, 18)
            # if roll_expiry.year == 2024:
            #     print("break")

            # Create a new condor
            condor_status, call_strike, put_strike = self.create_condor(
                symbol, roll_expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings, side
            )

            if "Success" in condor_status:
                self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit
                # Add marker to the chart
                self.add_marker(
                    f"Rolled Condor: {condor_status}, margin reserve {self.margin_reserve}",
                    value=underlying_price,
                    color="purple",
                    symbol="triangle-up",    
                    detail_text=f"Date: {dt}\nExpiration: {roll_expiry}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                )
            else:
                # Add marker to the chart
                self.add_marker(
                    f"Roll Failed: {condor_status}",
                    value=underlying_price,
                    color="blue",
                    symbol="asterisk",
                    detail_text=f"Date: {dt}\nExpiration: {roll_expiry}\nLast price: {underlying_price}\ncall short: {call_strike}\nput short: {put_strike}"
                )   

    def create_condor(
        self, symbol, expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings, side
    ):

        status = "no condor created"
        # break_date = dtime.date(2022, 3, 18)
        # if expiry == break_date:
        #     print("break")

        print(f"Creating condor for {symbol}, side is {side}, with expiry {expiry}")
        
        # Get the current price of the underlying asset
        underlying_price = self.get_last_price(symbol)

        # Round the underlying price to the nearest strike step size
        rounded_underlying_price = (
            round(underlying_price / strike_step_size) * strike_step_size
        )

        ################################################
        # Find the strikes for both the shorts and longs
        ################################################
        strikes = [
            rounded_underlying_price + strike_step_size * i for i in range(0, 100)
        ] + [rounded_underlying_price - strike_step_size * i for i in range(1, 100)]
        strikes.sort()  # Sort the strikes

        # Only keep the strikes above the underlying price for calls
        call_strikes = [strike for strike in strikes if strike > underlying_price]
        # Sort the strikes in ascending order
        call_strikes.sort()
        call_strike_deltas = self.get_strike_deltas(
            symbol, expiry, call_strikes, "call", stop_less_than=delta_required
        )

        # Find the call option with an appropriate delta and the expiry
        call_strike = None
        for strike, delta in call_strike_deltas.items():
            if delta and delta <= delta_required:
                call_strike = strike
                break

        # If we didn't find a call strike set an error message
        if call_strike is None and (side == "call" or side =="both"):
            status = "no call strike found"
            return status, call_strike, put_strike

        # Only keep the strikes below the underlying price for puts
        put_strikes = [strike for strike in strikes if strike < underlying_price]
        # Sort the strikes in descending order
        put_strikes.sort(reverse=True)
        put_strike_deltas = self.get_strike_deltas(
            symbol, expiry, put_strikes, "put", stop_greater_than=-delta_required
        )

        # Find the put option with a the correct delta and the expiry
        put_strike = None
        for strike, delta in put_strike_deltas.items():
            if delta and delta >= -delta_required:
                put_strike = strike
                break

        # If we didn't find a  put strike set an error message
        if put_strike is None and (side == "put" or side =="both"):
            status = "no put strike found"
            return status, call_strike, put_strike

        ###################################################################################
        # Attempt to find the orders (combination of strike, delta, and expiration) we need
        ###################################################################################
        # Make 3 attempts to create the call side of the condor
        call_strike_adjustment = 0
        for i in range(3):
            call_sell_order, call_buy_order = self.get_call_orders(
                symbol,
                expiry,
                strike_step_size,
                call_strike + call_strike_adjustment,
                quantity_to_trade,
                distance_of_wings,
            )

            # Check if we got both orders
            if call_sell_order is not None and call_buy_order is not None:
                break

            # If we didn't get both orders, then move the call strike up
            else:
                call_strike_adjustment -= strike_step_size

        # Make 3 attempts to create the put side of the condor
        put_strike_adjustment = -call_strike_adjustment
        for i in range(3):
            put_sell_order, put_buy_order = self.get_put_orders(
                symbol,
                expiry,
                strike_step_size,
                put_strike + put_strike_adjustment,
                quantity_to_trade,
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
        # Return an appropriate status
        ############################################
        
        if side == "both" and \
            (call_sell_order is None or \
             call_buy_order is None or \
             put_sell_order is None or \
             put_buy_order is None):
            return "failed to place condor", call_strike, put_strike
        elif side == "call" and (call_sell_order is None or call_buy_order is None):
            return "failed to roll call side", call_strike, put_strike
        elif side == "put" and (put_sell_order is None or put_buy_order is None):
            return "failed to roll put side", call_strike, put_strike
        else:
            status_messages = {
                "call": "Success: rolled the call side",
                "put": "Success: rolled the put side",
                "both": "Success the Condor" }

        return status_messages[side], call_strike, put_strike


    ############################################
    # Utility functions
    ############################################

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
        call_sell_price = self.get_last_price(call_sell_asset)

        # Create the order
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

            # Get the last price for this asset
            price = self.get_last_price(asset)

            if price is not None and price > 0:
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
                    # IMS This will force the delta out of range for the trade
                    # Do not set to 0 as this will create divide by zero errors in lumibot
                    strike_deltas[strike] = 0.001
            else:   
                # IMS This will force the delta out of range for the trade  
                strike_deltas[strike] = 0.001

        return strike_deltas
    
    # IMS The code to close a side does not do any retries.  This will be a problem in live trading.
    # This code assumes we only have one condor open at a time.  It loops through and closes
    # all the options.  This is not a good assumption for a more sophisticated strategy.

    def close_call_side(self):
        # Get all the open positions
        positions = self.get_positions()

        # Loop through and close all of the calls
        for position in positions:
            # If the position is an option
            if position.asset.asset_type == "option":
                if position.asset.right == "CALL":
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

                    close_status = self.submit_order(call_close_order)
        return
    
    def close_put_side(self):
        positions = self.get_positions()

        # Loop through and close all of the puts
        for position in positions:
            # If the position is an option
            if position.asset.asset_type == "option":
                if position.asset.right == "PUT":
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

                    close_status = self.submit_order(call_close_order)
        return
    
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
            asset = Asset(
                symbol,
                asset_type="option",
                expiration=expiry,
                strike=rounded_underlying_price,
                right="call",
            )

            # Get the price of the option
            price = self.get_last_price(asset)

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
            

if __name__ == "__main__":
        # Backtest this strategy
        backtesting_start = datetime(2023, 1, 1)
        backtesting_end = datetime(2023, 3, 31)

        trading_fee = TradingFee(percent_fee=0.005)  # IMS account for trading fees and slipage
        # polygon_has_paid_subscription is set to true to api calls are not thottled
        OptionsIronCondorMWT.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset=OptionsIronCondorMWT.parameters["symbol"],
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
            polygon_api_key=POLYGON_CONFIG["API_KEY"],
            polygon_has_paid_subscription=True,
            name=OptionsIronCondorMWT.strategy_name,
            budget = OptionsIronCondorMWT.parameters["budget"],
        )
 
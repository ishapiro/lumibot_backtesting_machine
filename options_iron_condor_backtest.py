from datetime import datetime, timedelta
import datetime as dtime

from lumibot.entities import Asset, TradingFee
from lumibot.strategies.strategy import Strategy

# IMS moved all module includes to the top of the code
from credentials import POLYGON_CONFIG
from lumibot.backtesting import PolygonDataBacktesting

"""
Strategy Description

Author: Irv Shapiro (ishapiro@cogitations.com)

Based on: Lumibot Condor Example

NOTE: The current version assumes only one condor is open at a time!!!
NOTE: Maximum margin is not enforced!!!

This parameterized Iron Condor Test is desgined to facilitate testing condors across a range of names,
deltas and expiration dates.

Future version:  In the future this will be undated so it can be invoked from a Flask web
framework with the input parameters available via an html form and the out files available
via a browser.

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
    
"""


class OptionsIronCondor(Strategy):

    distance_of_wings = 15 # reference in multiple parameters below, in dollars not strikes
    parameters = {
        "symbol": "SPY",
        "days_to_expiry": 40,  # How many days until the call option expires when we sell it
        "strike_step_size": 1,  # IMS Is this the strike spacing of the specific asset, can we get this from Poloygon?
        "delta_required": 0.15,  # The delta of the option we want to sell
        "delta_threshold": 1,  # The delta of the option when we need to buy it back
        "days_before_expiry_to_buy_back": 7,  # How many days before expiry to buy back the call
        "quantity_to_trade": 10,  # The number of contracts to trade
        "wait_cycles_after_threshold_cross": 10,  # The number minium number days to wait before exiting a strategy -- this strategy only trades once a day
        "distance_of_wings" : distance_of_wings, # Distance of the longs from the shorts in dollars -- the wings
        "budget" : 100000, # Maximum portfolio size
        "strike_roll_distance" : (0.20 * distance_of_wings) # How close to the short do we allow the price to move before rolling.
    }

    # The Lumibot framework does not current track margin requirements.  For this strategy
    # we will track margin manually using the following approximation in an instance variable.
    #
    # margin reserve = distance of wings - condor credit
    #
    margin_reserve = 0

    strategy_name = f'iron_condor_{parameters["delta_required"]}delta-{parameters["days_to_expiry"]}expiry-{parameters["days_before_expiry_to_buy_back"]}exit'

    def initialize(self):
        # The time to sleep between each trading iteration
        self.sleeptime = "1D"  # 1 minute = 1M, 1 hour = 1H,  1 day = 1D

        # Initialize the wait counter
        self.cycles_waited = 0

        self.non_existing_expiry_dates = []

    def on_trading_iteration(self):
        # Get the parameters
        symbol = self.parameters["symbol"]
        days_to_expiry = self.parameters["days_to_expiry"]
        strike_step_size = self.parameters["strike_step_size"]
        delta_required = self.parameters["delta_required"]
        delta_threshold = self.parameters["delta_threshold"]
        days_before_expiry_to_buy_back = self.parameters[
            "days_before_expiry_to_buy_back"
        ]
        distance_of_wings = self.parameters["distance_of_wings"]
        quantity_to_trade = self.parameters["quantity_to_trade"]
        wait_cycles_after_threshold_cross = self.parameters[
            "wait_cycles_after_threshold_cross"
        ]
        strike_roll_distance = self.parameters["strike_roll_distance"]

        # Get the price of the underlying asset
        underlying_price = self.get_last_price(symbol)
        rounded_underlying_price = round(underlying_price, 0)

        # Add lines to the chart
        self.add_line(f"{symbol}_price", underlying_price)

        # Add 1 to the wait counter
        self.cycles_waited += 1

        # Get the current datetime
        dt = self.get_datetime()

        # On first trading iteration, create the initial condor
        # IMS We do not really need this is we set a capital available and always add a condor
        # if we are below the capital threshold
        if self.first_iteration:
            # Get next 3rd Friday expiry after the date
            expiry = self.get_next_expiration_date(days_to_expiry, symbol, rounded_underlying_price)

            break_date = dtime.date(2022, 3, 18)
            if expiry == break_date:
                print("break")

            # Create the condor
            call_strike, put_strike = self.create_condor(
                symbol, expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings
            )

            # Reserve the margin

            self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            # Add marker to the chart
            self.add_marker(
                f"Create 1st New Condor, current margin: {self.margin_reserve}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",
                detail_text=f"Expiry: {expiry}\nUnderlying price: {underlying_price}\ncall strike: {call_strike}\nput_strike: {put_strike}"
            )
            return

        # Get all the open positions
        positions = self.get_positions()

        roll_call_short = False
        roll_put_short = False
        should_sell_for_expiry = False
        option_expiry = None
        days_to_expiry = None

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
                        if underlying_price >= call_short_strike_boundary:
                            # If it is, we need to roll the option
                            roll_call_short = True
                            break

                    # Check if the option is a put
                    elif position.asset.right == "PUT":
                        # Check if the delta is below the delta required
                        # IMS switch to crossing strike -- if greeks["delta"] < -delta_threshold:
                        put_short_strike_boundary = position.asset.strike + strike_roll_distance
                        if underlying_price <= put_short_strike_boundary:
                            # If it is, we need to roll the option
                            roll_put_short = True
                            break

        # If we need to sell for expiry
        if (should_sell_for_expiry):
            # Sell all of our positions
            self.sell_all()

            self.margin_reserve = self.margin_reserve - (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            self.add_marker(
                f"Close Condor for Days to Expiry: margin reserve {self.margin_reserve}",
                value=underlying_price,
                color="orange",
                symbol="triangle-down",
                detail_text=f"day_to_expiry: {days_to_expiry}\nunderlying_price: {underlying_price}\nposition_strike: {position_strike}"
            )

            # Sleep for 5 seconds to make sure the order goes through
            # IMS Only sleep when live, this sleep function will no-opt in a backtest
            self.sleep(5)

            # Get closest 3rd Friday expiry
            new_expiry = self.get_next_expiration_date(days_to_expiry, symbol, rounded_underlying_price)

            break_date = dtime.date(2022, 3, 18)
            if new_expiry == break_date:
                print("break")

            # Create a new condor
            call_strike, put_strike = self.create_condor(
                symbol, new_expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings
            )

            self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            # Add marker to the chart
            self.add_marker(
                f"Create New Condor: margin reserve {self.margin_reserve}",
                value=underlying_price,
                color="green",
                symbol="triangle-up",
                detail_text=f"New Expiry: {new_expiry}\nUnderlying price: {underlying_price}\ncall strike: {call_strike}\nput_strike: {put_strike}"
            )

        # If we need to roll the option
        elif roll_call_short or roll_put_short:
            # Create roll message
            roll_message = ""
            if roll_call_short:
                roll_message = "Roll for approaching short strike: "
            if roll_put_short:
                roll_message = "Roll for approaching put strike: "

            # Sell all of our positions
            # IMS this need to be changed to only roll one of the spreads and not create a new condor
            # IMS sell all will close ALL postions, we need to upgrade to only close the current position
            #   to handle multiple open condors at one time
            self.sell_all()

            self.margin_reserve = self.margin_reserve - (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            # Sleep for 5 seconds to make sure the order goes through
            # IMS do we need this in a backtest?
            self.sleep(1)

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
            roll_expiry = self.get_next_expiration_date(days_to_expiry, symbol, rounded_underlying_price)

            break_date = dtime.date(2022, 3, 18)
            if roll_expiry == break_date:
                print("break")

            # Create a new condor
            call_strike, put_strike = self.create_condor(
                symbol, roll_expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings
            )

            self.margin_reserve = self.margin_reserve + (distance_of_wings * 100 * quantity_to_trade)  # IMS need to update to reduce by credit

            # Add marker to the chart
            self.add_marker(
                f"Rolled Condor: margin reserve {self.margin_reserve}",
                value=underlying_price,
                color="purple",
                symbol="triangle-up",    
                detail_text=f"New Expiry: {roll_expiry}\nUnderlying price: {underlying_price}\ncall strike: {call_strike}\nput_strike: {put_strike}"
            )

    def create_condor(
        self, symbol, expiry, strike_step_size, delta_required, quantity_to_trade, distance_of_wings
    ):

        break_date = dtime.date(2022, 3, 18)
        if expiry == break_date:
            print("break")

        print(f"Creating condor for {symbol} with expiry {expiry}")
        
        # Get the current price of the underlying asset
        underlying_price = self.get_last_price(symbol)

        # Round the underlying price to the nearest strike step size
        rounded_underlying_price = (
            round(underlying_price / strike_step_size) * strike_step_size
        )

        # Make a list of all the strikes around the underlying price
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

        # If we didn't find a call strike or a put strike, return
        if call_strike is None or put_strike is None:
            return

        # Make 3 attempts to create the call side of the condor
        call_strike_adjustment = 0
        for i in range(8):
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
        for i in range(8):
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

        # Check if all the orders are valid
        if (
            call_sell_order is None
            or call_buy_order is None
            or put_sell_order is None
            or put_buy_order is None
        ):
            return

        # Submit the orders
        self.submit_order(call_sell_order)
        self.submit_order(call_buy_order)
        self.submit_order(put_sell_order)
        self.submit_order(put_buy_order)

        return call_strike, put_strike

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

            if price > 0 and price is not None:
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
                    strike_deltas[strike] = 0
            else:   
                # IMS This will force the delta out of range for the trade  
                strike_deltas[strike] = 0

        return strike_deltas
    
    def search_next_market_date( self, expiry, symbol, rounded_underlying_price):
        # Check if there is an option with this expiry (in case it's a holiday or weekend)
        while True:
            # Check if we already know that this expiry doesn't exist
            if expiry in self.non_existing_expiry_dates:
                # Increase the expiry by one day
                expiry += timedelta(days=1)
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

        return expiry
        
    def get_next_expiration_date(self, days_to_expiration, symbol, strike_price):
        dt = self.get_datetime()
        suggested_date = self.get_option_expiration_after_date(dt + timedelta(days=days_to_expiration))
        return self.search_next_market_date(suggested_date, symbol, strike_price)
            

if __name__ == "__main__":
        # Backtest this strategy
        backtesting_start = datetime(2022, 1, 1)
        # backtesting_start = datetime(2020, 1, 1)
        backtesting_end = datetime(2023, 12, 15)

        trading_fee = TradingFee(percent_fee=0.003)  # IMS closer to .60 per leg

        # polygon_has_paid_subscription is set to true to api calls are not thottled
        OptionsIronCondor.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset=OptionsIronCondor.parameters["symbol"],
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
            polygon_api_key=POLYGON_CONFIG["API_KEY"],
            polygon_has_paid_subscription=True,
            name=OptionsIronCondor.strategy_name,
            budget = OptionsIronCondor.parameters["budget"],
        )
 
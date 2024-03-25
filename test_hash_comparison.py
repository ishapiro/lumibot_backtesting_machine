import hashlib
import json

strategy_parameters = {
        "symbol": "IBM",
        "trade_strategy" : "iron-condor",  # iron-condor, bull-put-spread, bear-call-spread, hybrid
        "option_duration": 40,  # How many days until the call option expires when we sell it
        "strike_step_size": 5,  # IMS Is this the strike spacing of the specific asset, can we get this from Polygon?
        "max_strikes" : 25,  # This needs to be appropriate for the name and the strike size
        "call_delta_required": 0.16, # The delta values are different if we are skewing the condor
        "put_delta_required": 0.16,
        "maximum_rolls": 2,  # The maximum number of rolls we will do
        "days_before_expiry_to_buy_back": 7,  # How many days before expiry to buy back the call
        "quantity_to_trade": 10,  # The number of contracts to trade
        "minimum_hold_period": 7,  # The of number days to wait before exiting a strategy -- this strategy only trades once a day
        "distance_of_wings" : 10, # Distance of the longs from the shorts in dollars -- the wings
        "budget" : 20000, # 
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
        "ending_date" : "2022-12-31",
        "trading_fee" : 0.65,  # The trading fee in dollars per contract
    }

# Create a string representation of the sorted dictionary
sorted_dict_string = json.dumps(strategy_parameters, sort_keys=True, default=str)

# Create a hash object
hash_object = hashlib.sha256(sorted_dict_string.encode())

# Print the hexadecimal representation of hash
print(hash_object.hexdigest())


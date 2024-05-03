import sqlite3
import hashlib
import json

def add_benchmark_run_to_db(stats_file_name, strategy_return, benchmark_return, strategy_parameters, tearsheet_html):

    # Create a string representation of the sorted dictionary
    sorted_dict_string = json.dumps(strategy_parameters, sort_keys=True, default=str)

    # Create a hash object
    parameter_hash = hashlib.sha256(sorted_dict_string.encode()).hexdigest()

    conn = sqlite3.connect('mwt_backtesting_machine_results.db')  # Connect to the database
    cursor = conn.cursor()

    tearsheet_content = None
    # Read the file tearsheet_html and insert it into the database
    if (tearsheet_html != ""):
        with open(tearsheet_html, 'r') as file:
            tearsheet_content = file.read()

    # Insert new data
    status = cursor.execute('''
        INSERT INTO mwt_benchmark_returns (
            symbol,
            trade_strategy,
            strategy_return,
            benchmark_return,
            starting_date,
            ending_date,
            option_duration,
            call_delta_required, 
            put_delta_required, 
            minimum_hold_period, 
            distance_of_wings,
            strike_step_size,
            max_strikes,
            maximum_rolls,
            days_before_expiry_to_buy_back,
            quantity_to_trade,
            budget,
            strike_roll_distance,
            max_loss_multiplier,
            roll_strategy,
            skip_on_max_rolls,
            delta_threshold,
            maximum_portfolio_allocation,
            max_loss_trade_days_to_skip,
            max_volitility_days_to_skip,
            max_symbol_volitility,
            trading_fee,
            stats_file_name,
            tearsheet_html,
            parameter_hash)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (strategy_parameters["symbol"],
            strategy_parameters["trade_strategy"],
            strategy_return,
            benchmark_return,
            strategy_parameters["starting_date"],
            strategy_parameters["ending_date"],
            strategy_parameters["option_duration"],
            strategy_parameters["call_delta_required"],
            strategy_parameters["put_delta_required"], 
            strategy_parameters["minimum_hold_period"],
            strategy_parameters["distance_of_wings"],
            strategy_parameters["strike_step_size"],
            strategy_parameters["max_strikes"],
            strategy_parameters["maximum_rolls"],
            strategy_parameters["days_before_expiry_to_buy_back"],
            strategy_parameters["quantity_to_trade"],
            strategy_parameters["budget"],
            strategy_parameters["strike_roll_distance"],
            strategy_parameters["max_loss_multiplier"],
            strategy_parameters["roll_strategy"],
            strategy_parameters["skip_on_max_rolls"],
            strategy_parameters["delta_threshold"],
            strategy_parameters["maximum_portfolio_allocation"],
            strategy_parameters["max_loss_trade_days_to_skip"],
            strategy_parameters["max_volitility_days_to_skip"],
            strategy_parameters["max_symbol_volitility"],
            strategy_parameters["trading_fee"],
            stats_file_name,
            tearsheet_content,
            parameter_hash)
    )

    # Commit the transaction
    conn.commit()

    # Close the connection
    conn.close()

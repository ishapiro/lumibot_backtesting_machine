import sqlite3

def create_database_and_table():
    conn = sqlite3.connect('mwt_backtesting_machine_results.db')  # Creates a new database if not exists
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mwt_benchmark_returns (
            symbol TEXT,
            trade_strategy TEXT,
            strategy_return REAL,
            benchmark_return REAL,
            starting_date DATETIME,
            ending_date DATETIME,
            option_duration INTEGER,
            call_delta_required REAL, 
            put_delta_required REAL, 
            minimum_hold_period INTEGER, 
            distance_of_wings INTEGER,
            strike_step_size INTEGER,
            max_strikes INTEGER,
            maximum_rolls INTEGER,
            days_before_expiry_to_buy_back INTEGER,
            quantity_to_trade INTEGER,
            budget REAL,
            strike_roll_distance REAL,
            max_loss_multiplier REAL,
            roll_strategy ,
            skip_on_max_rolls BOOLEAN,
            delta_threshold REAL,
            maximum_portfolio_allocation REAL,
            max_loss_trade_days_to_skip INTEGER,
            max_volitility_days_to_skip INTEGER,
            max_symbol_volitility REAL,
            trading_fee REAL,
            stats_file_name TEXT,
            parameter_hash TEXT
        )
    ''')

    print("Table created successfully")

    # Close connection
    conn.close()

if __name__ == "__main__":
    create_database_and_table()
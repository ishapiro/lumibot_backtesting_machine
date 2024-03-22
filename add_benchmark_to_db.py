import sqlite3

def add_benchmark_run_to_db(stats_file_name, strategy_return, underlying_asset_return, strategy, start_date, end_date):
    conn = sqlite3.connect('mwt_backtesting_machine_results.db')  # Connect to the database
    cursor = conn.cursor()

    # Insert new data
    status = cursor.execute('''
        INSERT INTO mwt_benchmark_returns (stats_file_name, strategy_return, underlying_asset_return, strategy, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)
    ''', (stats_file_name, strategy_return, underlying_asset_return, strategy, start_date, end_date))

    # Commit the transaction
    conn.commit()

    # Close the connection
    conn.close()

if __name__ == "__main__":
    add_benchmark_run_to_db("stats_file.csv", 0.1, 0.2, "iron_condor", "2021-01-01", "2021-01-31")
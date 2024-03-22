import sqlite3

def create_database_and_table():
    conn = sqlite3.connect('lumibot_backtesting_machine_results.db')  # Creates a new database if not exists
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            strategy_return FLOAT,
            underlying_asset_return FLOAT,
            strategy TEXT,
            start_date DATETIME,
            end_date DATETIME
        )
    ''')

    print("Table created successfully")

    # Close connection
    conn.close()

if __name__ == "__main__":
    create_database_and_table()
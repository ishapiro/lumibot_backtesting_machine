def check_for_previous_run(strategy_parameters):
    '''
    Check if the data already exists in the database
    '''
    import sqlite3
    import hashlib
    import json

    # Create a string representation of the sorted dictionary
    sorted_dict_string = json.dumps(strategy_parameters, sort_keys=True, default=str)

    # Create a hash object
    parameter_hash = hashlib.sha256(sorted_dict_string.encode()).hexdigest()

    conn = sqlite3.connect('mwt_backtesting_machine_results.db')  # Connect to the database
    cursor = conn.cursor()

    # Check if the data already exists
    cursor.execute('''
        SELECT * FROM mwt_benchmark_returns WHERE parameter_hash = ?
    ''', (f"{parameter_hash}",))
    data = cursor.fetchall()
    
    if len(data) > 0:
        print("****** Data already exists in the database.  Skipping insert.")
        return True
    
    return False
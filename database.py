import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('driver_management.db')
    try:
        yield conn
    finally:
        conn.close()

def check_table_schema():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales'")
        if cursor.fetchone() is not None:
            # Check if zettel_fee column exists
            cursor.execute("PRAGMA table_info(sales)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'zettel_fee' not in columns or 'week_number' not in columns:
                # Drop and recreate if columns are missing
                cursor.execute('DROP TABLE sales')
                conn.commit()
                return False
        return True

def init_db():
    schema_up_to_date = check_table_schema()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Create or recreate tables if needed
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                oil_card_number TEXT NOT NULL,
                weekly_target REAL NOT NULL
            )
        ''')

        if not schema_up_to_date:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER,
                    date TEXT NOT NULL,
                    uber_sales REAL,
                    bolt_sales REAL,
                    zettel_sales REAL,
                    zettel_fee REAL,
                    other_sales REAL,
                    other_sales_type TEXT,
                    oil_expense REAL,
                    week_number INTEGER,
                    FOREIGN KEY (driver_id) REFERENCES drivers (id)
                )
            ''')
        conn.commit()

def add_driver(name, oil_card_number, weekly_target):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO drivers (name, oil_card_number, weekly_target) VALUES (?, ?, ?)',
            (name, oil_card_number, weekly_target)
        )
        conn.commit()

def update_driver(driver_id, name, oil_card_number, weekly_target):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE drivers 
            SET name = ?, oil_card_number = ?, weekly_target = ?
            WHERE id = ?
        ''', (name, oil_card_number, weekly_target, driver_id))
        conn.commit()

def get_driver(driver_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM drivers WHERE id = ?', (driver_id,))
        return cursor.fetchone()

def get_all_drivers():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM drivers')
        return cursor.fetchall()

def delete_driver(driver_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM drivers WHERE id = ?', (driver_id,))
        conn.commit()

def add_sales_record(driver_id, date, uber_sales, bolt_sales, zettel_sales, zettel_fee,
                     other_sales, other_sales_type, oil_expense, week_number):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sales (
                driver_id, date, uber_sales, bolt_sales, zettel_sales, zettel_fee,
                other_sales, other_sales_type, oil_expense, week_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (driver_id, date, uber_sales, bolt_sales, zettel_sales, zettel_fee,
              other_sales, other_sales_type, oil_expense, week_number))
        conn.commit()

def get_driver_sales(driver_id, date):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sales 
            WHERE driver_id = ? AND date = ?
        ''', (driver_id, date))
        return cursor.fetchone()

def get_weekly_sales(driver_id, week_number):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                SUM(uber_sales) as total_uber,
                SUM(bolt_sales) as total_bolt,
                SUM(zettel_sales - zettel_fee) as total_zettel,
                SUM(other_sales) as total_other,
                SUM(oil_expense) as total_oil,
                SUM(zettel_fee) as total_zettel_fee
            FROM sales 
            WHERE driver_id = ? AND week_number = ?
        ''', (driver_id, week_number))
        return cursor.fetchone()

def get_historical_sales(driver_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                week_number,
                SUM(uber_sales) as total_uber,
                SUM(bolt_sales) as total_bolt,
                SUM(zettel_sales - zettel_fee) as total_zettel,
                SUM(other_sales) as total_other,
                SUM(oil_expense) as total_oil,
                SUM(zettel_fee) as total_zettel_fee
            FROM sales 
            WHERE driver_id = ?
            GROUP BY week_number
            ORDER BY week_number DESC
        ''', (driver_id,))
        return cursor.fetchall()

def reset_weekly_sales(driver_id, week_number):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM sales 
            WHERE driver_id = ? AND week_number = ?
        ''', (driver_id, week_number))
        conn.commit()

def reset_all_sales(driver_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sales WHERE driver_id = ?', (driver_id,))
        conn.commit()

def get_weekly_sales_records(driver_id, week_number):
    """
    Get all individual sales records for a specific driver and week.
    
    Args:
        driver_id: The driver ID
        week_number: The week number to retrieve records for
        
    Returns:
        A list of sales records with all details
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, date, uber_sales, bolt_sales, zettel_sales, zettel_fee,
                   other_sales, other_sales_type, oil_expense
            FROM sales 
            WHERE driver_id = ? AND week_number = ?
            ORDER BY date ASC
        ''', (driver_id, week_number))
        return cursor.fetchall()

def update_sales_record(record_id, uber_sales, bolt_sales, zettel_sales, zettel_fee,
                      other_sales, other_sales_type, oil_expense):
    """
    Update an existing sales record.
    
    Args:
        record_id: The ID of the sales record to update
        uber_sales: Uber sales value
        bolt_sales: Bolt sales value
        zettel_sales: Zettel sales value
        zettel_fee: Zettel fee value
        other_sales: Other sales value
        other_sales_type: Type of other sales
        oil_expense: Oil expense value
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sales 
            SET uber_sales = ?, bolt_sales = ?, zettel_sales = ?, zettel_fee = ?,
                other_sales = ?, other_sales_type = ?, oil_expense = ?
            WHERE id = ?
        ''', (uber_sales, bolt_sales, zettel_sales, zettel_fee,
              other_sales, other_sales_type, oil_expense, record_id))
        conn.commit()
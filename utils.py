from datetime import datetime, timedelta
import pandas as pd

def calculate_total_sales(uber_sales, bolt_sales, zettel_sales, other_sales):
    return sum(filter(None, [uber_sales, bolt_sales, zettel_sales, other_sales]))

def format_currency(amount):
    if amount is None:
        return "SEK 0.00"
    return f"SEK {amount:,.2f}"

def validate_numeric_input(value):
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_current_week():
    return datetime.now().isocalendar()[1]

def get_week_dates(year, week_number):
    """
    Return the start date (Monday) and end date (Sunday) of a given ISO week number and year.
    
    Args:
        year: The year (e.g., 2025)
        week_number: The ISO week number (1-53)
        
    Returns:
        tuple: (start_date, end_date) as strings in format 'YYYY-MM-DD'
    """
    if week_number < 1 or week_number > 53:
        raise ValueError("Week number must be between 1 and 53")
    
    # Find the first day of the specified year
    first_day = datetime(year, 1, 1)
    
    # Find the first day of week 1
    # In ISO calendar, week 1 is the week containing Jan 4
    jan_4 = datetime(year, 1, 4)
    # Find the day of the week (0 = Monday, 6 = Sunday)
    weekday = jan_4.weekday()
    # Calculate start of week containing Jan 4 (i.e., start of week 1)
    week1_start = jan_4 - timedelta(days=weekday)
    
    # Calculate start of requested week by adding (week_number - 1) weeks to start of week 1
    requested_week_start = week1_start + timedelta(weeks=week_number - 1)
    requested_week_end = requested_week_start + timedelta(days=6)
    
    # Return formatted dates
    return (
        requested_week_start.strftime('%Y-%m-%d'),
        requested_week_end.strftime('%Y-%m-%d')
    )

def prepare_report_data(driver_name, sales_data, target):
    net_zettel = sales_data.get('zettel_sales', 0) - sales_data.get('zettel_fee', 0)
    total_sales = calculate_total_sales(
        sales_data.get('uber_sales', 0),
        sales_data.get('bolt_sales', 0),
        net_zettel,
        sales_data.get('other_sales', 0)
    )

    return {
        'driver_name': driver_name,
        'date': get_current_date(),
        'sales_breakdown': {
            **sales_data,
            'net_zettel_sales': net_zettel
        },
        'total_sales': total_sales,
        'target': target,
        'target_achieved': total_sales >= target
    }

def prepare_historical_report_data(driver_name, historical_df):
    total_sales = {
        'uber': historical_df['Uber'].sum(),
        'bolt': historical_df['Bolt'].sum(),
        'zettel': historical_df['Zettel'].sum(),  # This is already net (after fee)
        'other': historical_df['Other'].sum(),
        'oil': historical_df['Oil'].sum(),
        'zettel_fee': historical_df['Zettel Fee'].sum() if 'Zettel Fee' in historical_df.columns else 0,
        'total_net': historical_df['Total Net Sales'].sum() if 'Total Net Sales' in historical_df.columns else 0
    }

    return {
        'driver_name': driver_name,
        'date': get_current_date(),
        'historical_data': historical_df,
        'total_sales': total_sales
    }

def prepare_comparison_data(drivers_data):
    """
    Prepare data for driver comparison visualization.

    Args:
        drivers_data: List of tuples containing (driver_name, weekly_sales, target, oil_card)
    Returns:
        Dict with processed data for visualization
    """
    metrics = ['Uber', 'Bolt', 'Zettel', 'Other']
    comparison_data = {
        'drivers': [],
        'metrics': metrics,
        'values': [],
        'targets': [],
        'achievement_rates': [],
        'driver_info': []  # Add driver info storage
    }

    for driver_name, sales, target, oil_card in drivers_data:
        if sales and any(s is not None for s in sales):
            comparison_data['drivers'].append(driver_name)
            # Unpack sales data (uber, bolt, zettel, other, oil, zettel_fee)
            uber, bolt, zettel, other, _, _ = sales

            # Calculate total sales
            total_sales = sum(filter(None, [uber, bolt, zettel, other]))
            achievement_rate = (total_sales / target * 100) if target > 0 else 0

            comparison_data['values'].append([
                uber or 0,
                bolt or 0,
                zettel or 0,  # This is already net (after fee)
                other or 0
            ])
            comparison_data['targets'].append(target)
            comparison_data['achievement_rates'].append(achievement_rate)
            comparison_data['driver_info'].append({
                'card': oil_card,
                'target': target
            })

    return comparison_data
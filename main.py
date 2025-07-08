import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import utils
import report_generator

# Initialize the database
db.init_db()

# Page configuration
st.set_page_config(page_title="Driver Management System", layout="wide")
st.title("Driver Management System")

# Week selection
col1, col2 = st.columns(2)
with col1:
    current_week = utils.get_current_week()
    current_year = datetime.now().year
    selected_week = st.number_input("Week Number", min_value=1, max_value=53, value=current_week)
with col2:
    st.info(f"Current Week: {current_week}")

# Get week date range
week_start_date, week_end_date = utils.get_week_dates(current_year, selected_week)

# Add All Drivers Summary for Selected Week
st.header(f"Week {selected_week} - All Drivers Summary ({week_start_date} to {week_end_date})")
all_drivers = db.get_all_drivers()

if all_drivers:
    total_uber = 0
    total_bolt = 0
    total_zettel = 0
    total_other = 0
    total_oil = 0
    total_zettel_fee = 0
    all_drivers_data = []

    # Calculate totals for all drivers
    for driver in all_drivers:
        driver_sales = db.get_weekly_sales(driver[0], selected_week)
        if driver_sales and any(sales is not None for sales in driver_sales):
            uber, bolt, zettel, other, oil, zettel_fee = driver_sales
            all_drivers_data.append({
                'name': driver[1],
                'oil_card': driver[2],
                'target': driver[3],
                'uber': uber or 0,
                'bolt': bolt or 0,
                'zettel': zettel or 0,
                'other': other or 0,
                'oil': oil or 0,
                'zettel_fee': zettel_fee or 0
            })
            total_uber += uber or 0
            total_bolt += bolt or 0
            total_zettel += zettel or 0
            total_other += other or 0
            total_oil += oil or 0
            total_zettel_fee += zettel_fee or 0

    # Display overall totals
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Uber Sales", utils.format_currency(total_uber))
        st.metric("Total Bolt Sales", utils.format_currency(total_bolt))
    with col2:
        st.metric("Total Zettel Sales (Net)", utils.format_currency(total_zettel))
        st.metric("Total Other Sales", utils.format_currency(total_other))
    with col3:
        st.metric("Total Oil Expenses", utils.format_currency(total_oil))
        total_net_sales = total_uber + total_bolt + total_zettel + total_other
        st.metric("Total Net Sales", utils.format_currency(total_net_sales))

    # Create a DataFrame for all drivers
    if all_drivers_data:
        st.subheader("Individual Drivers Breakdown")
        df = pd.DataFrame(all_drivers_data)
        df['Total'] = df['uber'] + df['bolt'] + df['zettel'] + df['other']

        # Format the DataFrame for display
        display_df = df.copy()
        for col in ['uber', 'bolt', 'zettel', 'other', 'oil', 'zettel_fee', 'Total']:
            display_df[col] = display_df[col].apply(lambda x: utils.format_currency(x))

        st.dataframe(display_df.set_index('name'))

        # Export button for weekly summary
        if st.button("Export Weekly Summary (All Drivers)"):
            weekly_summary_data = {
                'date': utils.get_current_date(),
                'week_number': selected_week,
                'week_start_date': week_start_date,
                'week_end_date': week_end_date,
                'sales_breakdown': {
                    'uber_sales': total_uber,
                    'bolt_sales': total_bolt,
                    'zettel_sales': total_zettel + total_zettel_fee,
                    'zettel_fee': total_zettel_fee,
                    'other_sales': total_other,
                    'other_sales_type': "All Drivers Summary",
                    'oil_expense': total_oil
                },
                'total_sales': total_net_sales,
                'drivers': all_drivers_data
            }
            pdf_buffer = report_generator.generate_summary_report(weekly_summary_data)
            filename = f"all_drivers_week_{selected_week}_summary.pdf"
            st.download_button(
                "Download All Drivers Summary PDF",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf"
            )

# Sidebar for driver management
with st.sidebar:
    st.header("Driver Management")

    # Add new driver form
    with st.form("add_driver_form"):
        st.subheader("Add New Driver")
        new_driver_name = st.text_input("Driver Name")
        new_oil_card = st.text_input("Oil Card Number")
        new_target = st.number_input("Weekly Target (SEK)", min_value=0.0, step=100.0)

        if st.form_submit_button("Add Driver"):
            if new_driver_name and new_oil_card and new_target:
                db.add_driver(new_driver_name, new_oil_card, new_target)
                st.success("Driver added successfully!")
            else:
                st.error("Please fill all fields")

    # List all drivers with edit/delete functionality
    st.subheader("Existing Drivers")
    drivers = db.get_all_drivers()
    driver_dict = {
        driver[1]: {
            "id": driver[0],
            "oil_card": driver[2],
            "target": driver[3]
        } for driver in drivers
    }

    for driver in drivers:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"{driver[1]}")
            st.caption(f"Card: {driver[2]} | Target: {utils.format_currency(driver[3])}")
        with col2:
            if st.button("Edit", key=f"edit_{driver[0]}"):
                st.session_state.editing_driver = driver[0]
                st.rerun()
        with col3:
            if st.button("Delete", key=f"del_{driver[0]}"):
                db.delete_driver(driver[0])
                st.rerun()

    # Edit driver form
    if 'editing_driver' in st.session_state:
        driver = db.get_driver(st.session_state.editing_driver)
        if driver:
            st.subheader("Edit Driver")
            with st.form("edit_driver_form"):
                edit_name = st.text_input("Driver Name", value=driver[1])
                edit_oil_card = st.text_input("Oil Card Number", value=driver[2])
                edit_target = st.number_input("Weekly Target (SEK)",
                                            value=driver[3],
                                            min_value=0.0,
                                            step=100.0)

                if st.form_submit_button("Update Driver"):
                    db.update_driver(driver[0], edit_name, edit_oil_card, edit_target)
                    del st.session_state.editing_driver
                    st.success("Driver updated successfully!")
                    st.rerun()

# Main content
st.header("Sales Entry")

# Driver selection
selected_driver = st.selectbox("Select Driver", options=list(driver_dict.keys()))

if selected_driver:
    driver_info = driver_dict[selected_driver]
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Oil Card Number: {driver_info['oil_card']}")
    with col2:
        st.info(f"Weekly Target: {utils.format_currency(driver_info['target'])}")

    # Weekly sales summary
    weekly_sales = db.get_weekly_sales(driver_info['id'], selected_week)

    if weekly_sales and any(sales is not None for sales in weekly_sales):
        st.subheader(f"Week {selected_week} Sales Summary ({week_start_date} to {week_end_date})")
        total_uber, total_bolt, total_zettel, total_other, total_oil, total_zettel_fee = weekly_sales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Uber", utils.format_currency(total_uber or 0))
            st.metric("Total Bolt", utils.format_currency(total_bolt or 0))
        with col2:
            st.metric("Total Zettel", utils.format_currency(total_zettel or 0))
            st.metric("Total Other", utils.format_currency(total_other or 0))
        with col3:
            st.metric("Total Oil Expense", utils.format_currency(total_oil or 0))
            total_net_sales = sum(filter(None, [total_uber, total_bolt, total_zettel, total_other]))
            st.metric("Total Weekly Sales", utils.format_currency(total_net_sales))

        # Weekly summary actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Reset Weekly Data"):
                db.reset_weekly_sales(driver_info['id'], selected_week)
                st.success(f"Week {selected_week} data has been reset")
                st.rerun()
        with col2:
            if st.button("Export Weekly Summary"):
                total_net_sales = (total_uber or 0) + (total_bolt or 0) + (total_zettel or 0) + (total_other or 0)
                weekly_report_data = {
                    'driver_name': selected_driver,
                    'oil_card': driver_info['oil_card'],
                    'target': driver_info['target'],
                    'date': utils.get_current_date(),
                    'week_number': selected_week,
                    'week_start_date': week_start_date,
                    'week_end_date': week_end_date,
                    'sales_breakdown': {
                        'uber_sales': total_uber or 0,
                        'bolt_sales': total_bolt or 0,
                        'zettel_sales': (total_zettel or 0) + (total_zettel_fee or 0),
                        'zettel_fee': total_zettel_fee or 0,
                        'other_sales': total_other or 0,
                        'other_sales_type': "Multiple",  # For weekly summary
                        'oil_expense': total_oil or 0
                    },
                    'total_sales': total_net_sales,
                    'target_achieved': total_net_sales >= driver_info['target']
                }
                pdf_buffer = report_generator.generate_pdf_report(weekly_report_data)
                filename = f"{selected_driver}_week_{selected_week}_summary.pdf"
                st.download_button(
                    "Download Weekly Summary PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )

    # Initialize lock states if not exists
    if 'uber_locked' not in st.session_state:
        st.session_state.uber_locked = False
    if 'bolt_locked' not in st.session_state:
        st.session_state.bolt_locked = False
    if 'zettel_locked' not in st.session_state:
        st.session_state.zettel_locked = False
    if 'zettel_fee_locked' not in st.session_state:
        st.session_state.zettel_fee_locked = False
    if 'other_locked' not in st.session_state:
        st.session_state.other_locked = False
    if 'oil_locked' not in st.session_state:
        st.session_state.oil_locked = False

    # Lock/Unlock buttons section (outside the form)
    st.subheader("Input Field Controls")
    lock_col1, lock_col2, lock_col3, lock_col4, lock_col5, lock_col6 = st.columns(6)
    
    with lock_col1:
        if st.button("🔒" if st.session_state.uber_locked else "🔓", key="uber_lock", help="Lock/Unlock Uber input"):
            st.session_state.uber_locked = not st.session_state.uber_locked
        st.caption("Uber")
    
    with lock_col2:
        if st.button("🔒" if st.session_state.bolt_locked else "🔓", key="bolt_lock", help="Lock/Unlock Bolt input"):
            st.session_state.bolt_locked = not st.session_state.bolt_locked
        st.caption("Bolt")
    
    with lock_col3:
        if st.button("🔒" if st.session_state.zettel_locked else "🔓", key="zettel_lock", help="Lock/Unlock Zettel input"):
            st.session_state.zettel_locked = not st.session_state.zettel_locked
        st.caption("Zettel")
    
    with lock_col4:
        if st.button("🔒" if st.session_state.zettel_fee_locked else "🔓", key="zettel_fee_lock", help="Lock/Unlock Zettel Fee input"):
            st.session_state.zettel_fee_locked = not st.session_state.zettel_fee_locked
        st.caption("Zettel Fee")
    
    with lock_col5:
        if st.button("🔒" if st.session_state.other_locked else "🔓", key="other_lock", help="Lock/Unlock Other input"):
            st.session_state.other_locked = not st.session_state.other_locked
        st.caption("Other")
    
    with lock_col6:
        if st.button("🔒" if st.session_state.oil_locked else "🔓", key="oil_lock", help="Lock/Unlock Oil input"):
            st.session_state.oil_locked = not st.session_state.oil_locked
        st.caption("Oil")

    # Sales entry form
    with st.form("sales_entry_form"):
        col1, col2 = st.columns(2)

        with col1:
            uber_sales = st.number_input("Uber Sales (SEK)", min_value=0.0, step=10.0, key="uber_input", disabled=st.session_state.uber_locked)
            bolt_sales = st.number_input("Bolt Sales (SEK)", min_value=0.0, step=10.0, key="bolt_input", disabled=st.session_state.bolt_locked)

        with col2:
            zettel_sales = st.number_input("Zettel Sales (SEK)", min_value=0.0, step=10.0, key="zettel_input", disabled=st.session_state.zettel_locked)
            zettel_fee = st.number_input("Zettel Fee (SEK)", min_value=0.0, step=1.0, key="zettel_fee_input", disabled=st.session_state.zettel_fee_locked)
            other_sales = st.number_input("Other Sales (SEK)", step=10.0, key="other_input", disabled=st.session_state.other_locked)

        other_type = st.selectbox("Other Sales Type",
                                   ["Cash", "Card", "Swish", "Transfer", "Other"],
                                   disabled=False,
                                   key="other_type_input")

        oil_expense = st.number_input("Oil Expense (SEK)", min_value=0.0, step=10.0, key="oil_input", disabled=st.session_state.oil_locked)

        total_sales = utils.calculate_total_sales(uber_sales, bolt_sales,
                                               zettel_sales - zettel_fee, other_sales)

        st.markdown(f"**Total Sales: {utils.format_currency(total_sales)}**")

        if st.form_submit_button("Save Record"):
            db.add_sales_record(
                driver_info['id'],
                utils.get_current_date(),
                uber_sales,
                bolt_sales,
                zettel_sales,
                zettel_fee,
                other_sales,
                other_type,
                oil_expense,
                selected_week
            )
            st.success("Sales record saved successfully!")
            # Clear the form by clearing session state
            for key in ["uber_input", "bolt_input", "zettel_input", "zettel_fee_input", "other_input", "other_type_input", "oil_input"]:
                if key in st.session_state:
                    del st.session_state[key]
            # Reset lock states
            for lock_key in ["uber_locked", "bolt_locked", "zettel_locked", "zettel_fee_locked", "other_locked", "oil_locked"]:
                if lock_key in st.session_state:
                    st.session_state[lock_key] = False
            st.rerun()

    # Historical Data Section
    st.header("Historical Sales Data")
    historical_sales = db.get_historical_sales(driver_info['id'])
    current_year = datetime.now().year

    if historical_sales:
        # Create DataFrame with basic data
        historical_df = pd.DataFrame(historical_sales,
                                   columns=['Week', 'Uber', 'Bolt', 'Zettel', 'Other', 'Oil', 'Zettel Fee'])
        
        # Add date range column
        date_ranges = []
        for week in historical_df['Week']:
            start_date, end_date = utils.get_week_dates(current_year, int(week))
            date_ranges.append(f"{start_date} to {end_date}")
        
        # Insert date range column after Week column
        historical_df.insert(1, 'Date Range', date_ranges)
        
        # Calculate and add Total Net Sales column
        total_net_sales = []
        for i, row in historical_df.iterrows():
            # Get values from each row
            uber = float(row['Uber'])
            bolt = float(row['Bolt'])
            zettel = float(row['Zettel'])  # This is already net zettel from database query
            zettel_fee = float(row['Zettel Fee'])
            other = float(row['Other'])
            
            # Calculate total net sales (zettel is already net, so just add all components)
            net_total = utils.calculate_total_sales(uber, bolt, zettel, other)
            total_net_sales.append(net_total)
        
        # Add Total Net Sales column after Oil column
        historical_df['Total Net Sales'] = total_net_sales
        
        # Add action buttons - we'll use session state to track which button was clicked
        edit_week = st.session_state.get('edit_week', None)
        edit_week_mode = st.session_state.get('edit_week_mode', False)
        print_week = st.session_state.get('print_week', None)
        
        # Create an integrated table with data and buttons
        # First create column headers
        col_headers = st.columns([1, 1.5, 1, 1, 1, 1, 1, 1.5, 1, 1]) 
        
        with col_headers[0]:
            st.write("Week")
        with col_headers[1]:
            st.write("Date Range")
        with col_headers[2]:
            st.write("Uber")
        with col_headers[3]:
            st.write("Bolt")
        with col_headers[4]:
            st.write("Zettel")
        with col_headers[5]:
            st.write("Other")
        with col_headers[6]:
            st.write("Oil")
        with col_headers[7]:
            st.write("Total Net Sales")
        with col_headers[8]:
            st.write("Edit")
        with col_headers[9]:
            st.write("Print")
        
        # Style for the entire table and buttons
        st.markdown("""
        <style>
        /* Add more padding to all elements to increase row height */
        .stButton > button {
            height: 45px;
            width: 45px;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 10px;
        }
        
        /* Improve appearance of data rows */
        div[data-testid="column"] > div > div > div > div > div {
            padding: 12px 0px;
            line-height: 2.5;
            border-bottom: 1px solid #eee;
            height: 50px;
            display: flex;
            align-items: center;
        }
        
        /* Add styling for column headers */
        div[data-testid="column"] > div > div:first-child {
            font-weight: bold;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 8px;
            margin-bottom: 10px;
            color: #2c3e50;
        }
        
        /* Fix button alignment and spacing */
        [data-testid="column"]:nth-of-type(9) .stButton, 
        [data-testid="column"]:nth-of-type(10) .stButton {
            margin-top: 15px;
            margin-bottom: 15px;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 50px;
        }
        
        /* Add consistent spacing between rows */
        div[data-testid="column"] > div {
            margin-bottom: 5px;
        }
        
        /* Fix spacing for Historical Data reset/export buttons */
        .block-container > div:nth-child(1) > div > div:nth-of-type(5) .stButton {
            margin-top: 15px;
            margin-left: 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # For each week in the data, create a row with data and buttons
        for i, row in historical_df.iterrows():
            week = row['Week']
            date_range = row['Date Range']
            uber = row['Uber']
            bolt = row['Bolt']
            zettel = row['Zettel']
            other = row['Other']
            oil = row['Oil']
            
            cols = st.columns([1, 1.5, 1, 1, 1, 1, 1, 1.5, 1, 1])
            
            with cols[0]:
                st.write(f"{int(week)}")
            with cols[1]:
                st.write(f"{date_range}")
            with cols[2]:
                st.write(f"{utils.format_currency(uber)}")
            with cols[3]:
                st.write(f"{utils.format_currency(bolt)}")
            with cols[4]:
                st.write(f"{utils.format_currency(zettel)}")
            with cols[5]:
                st.write(f"{utils.format_currency(other)}")
            with cols[6]:
                st.write(f"{utils.format_currency(oil)}")
            with cols[7]:
                st.write(f"{utils.format_currency(row['Total Net Sales'])}")
            with cols[8]:
                if st.button(f"✏️", key=f"edit_week_{week}", help=f"Edit Week {week} data"):
                    st.session_state.edit_week = week
                    st.session_state.edit_week_mode = True
                    st.session_state.print_week = None  # Clear any print selection
                    st.rerun()
            with cols[9]:
                if st.button(f"🖨️", key=f"print_week_{week}", help=f"Print Week {week} data"):
                    st.session_state.print_week = week
                    st.rerun()
        
        # Handle print action if a print button was clicked
        if print_week is not None:
            try:
                # Get the week data - with error handling
                filtered_df = historical_df[historical_df['Week'] == print_week]
                
                if filtered_df.empty:
                    st.error(f"No data found for week {print_week}. Please select a valid week.")
                    if st.button("Back", key="back_from_error", type="secondary"):
                        st.session_state.print_week = None
                        st.rerun()
                else:
                    week_row = filtered_df.iloc[0]
                    start_date, end_date = utils.get_week_dates(current_year, int(print_week))
                    
                    # Prepare data for the weekly report
                    week_data = {
                        'driver_name': selected_driver,
                        'oil_card': driver_dict[selected_driver]['oil_card'],
                        'target': driver_dict[selected_driver]['target'],
                        'week_number': print_week,
                        'week_start_date': start_date,
                        'week_end_date': end_date,
                        'sales_breakdown': {
                            'uber_sales': float(week_row['Uber']),
                            'bolt_sales': float(week_row['Bolt']),
                            'zettel_sales': float(week_row['Zettel']) + float(week_row['Zettel Fee']),
                            'zettel_fee': float(week_row['Zettel Fee']),
                            'other_sales': float(week_row['Other']),
                            'other_sales_type': "Other",
                            'oil_expense': float(week_row['Oil'])
                        }
                    }
                    
                    # Calculate total sales
                    total_week_sales = utils.calculate_total_sales(
                        week_data['sales_breakdown']['uber_sales'],
                        week_data['sales_breakdown']['bolt_sales'],
                        week_data['sales_breakdown']['zettel_sales'],
                        week_data['sales_breakdown']['other_sales']
                    )
                    
                    week_data['total_sales'] = total_week_sales
                    week_data['target_achieved'] = total_week_sales >= driver_dict[selected_driver]['target']
                    
                    # Generate PDF report
                    pdf_buffer = report_generator.generate_pdf_report(week_data)
                    filename = f"{selected_driver}_week_{print_week}_report.pdf"
                    
                    # Create download button
                    st.download_button(
                        f"Download Week {print_week} Report",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf"
                    )
                    
                    # Add button to clear the print selection and return to normal view
                    if st.button("Back to Overview", type="secondary"):
                        st.session_state.print_week = None
                        st.rerun()
            except Exception as e:
                st.error(f"An error occurred when generating the report: {str(e)}")
                st.info("Try selecting a different week or going back to the main view.")
                if st.button("Return to Main View", type="secondary"):
                    st.session_state.print_week = None
                    st.rerun()
        
        # Show edit form if a week is selected
        elif edit_week_mode and edit_week:
            st.subheader(f"Edit Week {edit_week} ({utils.get_week_dates(current_year, int(edit_week))[0]} to {utils.get_week_dates(current_year, int(edit_week))[1]})")
            
            # Get daily sales records for the selected week
            daily_records = db.get_weekly_sales_records(driver_info['id'], edit_week)
            
            if daily_records:
                # Create tabs for each daily record
                daily_tabs = st.tabs([f"Day {i+1}: {record[1]}" for i, record in enumerate(daily_records)])
                
                for i, (tab, record) in enumerate(zip(daily_tabs, daily_records)):
                    with tab:
                        record_id = record[0]
                        record_date = record[1]
                        
                        # Create edit form for this record
                        with st.form(key=f"edit_record_{record_id}"):
                            st.write(f"Edit Sales for {record_date}")
                            
                            # Get current values
                            current_uber = record[2] or 0
                            current_bolt = record[3] or 0
                            current_zettel = record[4] or 0
                            current_zettel_fee = record[5] or 0
                            current_other = record[6] or 0
                            current_other_type = record[7] or ""
                            current_oil = record[8] or 0
                            
                            # Create input fields with current values
                            col1, col2 = st.columns(2)
                            with col1:
                                new_uber = st.number_input("Uber Sales (SEK)", 
                                                         value=float(current_uber),
                                                         step=100.0,
                                                         format="%.2f")
                                new_bolt = st.number_input("Bolt Sales (SEK)", 
                                                         value=float(current_bolt),
                                                         step=100.0,
                                                         format="%.2f")
                                new_zettel = st.number_input("Zettel Sales (SEK)", 
                                                         value=float(current_zettel),
                                                         step=100.0,
                                                         format="%.2f")
                                new_zettel_fee = st.number_input("Zettel Fee (SEK)", 
                                                             value=float(current_zettel_fee),
                                                             step=10.0,
                                                             format="%.2f")
                            
                            with col2:
                                new_other = st.number_input("Other Sales (SEK)", 
                                                         value=float(current_other),
                                                         step=100.0,
                                                         format="%.2f")
                                new_other_type = st.selectbox("Other Sales Type",
                                    ["Cash", "Card", "Swish", "Transfer", "Other"],
                                    index=["Cash", "Card", "Swish", "Transfer", "Other"].index(current_other_type) if current_other_type in ["Cash", "Card", "Swish", "Transfer", "Other"] else 0)
                                new_oil = st.number_input("Oil Expense (SEK)", 
                                                       value=float(current_oil),
                                                       step=50.0,
                                                       format="%.2f")
                            
                            # Calculate the new total
                            new_total = utils.calculate_total_sales(
                                new_uber, 
                                new_bolt, 
                                new_zettel, 
                                new_other
                            )
                            
                            st.metric("New Total Sales", utils.format_currency(new_total))
                            
                            # Form actions
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Update Sales Record"):
                                    # Update the record in the database
                                    db.update_sales_record(
                                        record_id, 
                                        new_uber, 
                                        new_bolt, 
                                        new_zettel, 
                                        new_zettel_fee,
                                        new_other, 
                                        new_other_type, 
                                        new_oil
                                    )
                                    st.success(f"Sales record for {record_date} updated successfully!")
                                    st.rerun()  # Rerun the app to show updated data
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    st.session_state.edit_week_mode = False
                                    st.rerun()
            else:
                # No existing records found - create a new one
                st.info(f"No daily records found for Week {edit_week}")
                
                # Extract the values from the weekly summary if available
                filtered_rows = historical_df[historical_df['Week'] == edit_week]
                if len(filtered_rows) > 0:
                    week_row = filtered_rows.iloc[0]
                    uber_val = float(week_row['Uber'])
                    bolt_val = float(week_row['Bolt'])
                    zettel_val = float(week_row['Zettel'])
                    other_val = float(week_row['Other'])
                    oil_val = float(week_row['Oil'])
                    zettel_fee_val = float(week_row.get('Zettel Fee', 0))
                else:
                    # Set default values if no data is available
                    uber_val = 0.0
                    bolt_val = 0.0
                    zettel_val = 0.0
                    other_val = 0.0
                    oil_val = 0.0
                    zettel_fee_val = 0.0
                
                # Create new record form
                with st.form(key=f"create_record_{edit_week}"):
                    st.write(f"Create New Record for Week {edit_week}")
                    
                    start_date, _ = utils.get_week_dates(current_year, int(edit_week))
                    record_date = st.date_input("Record Date", 
                                              value=datetime.strptime(start_date, "%Y-%m-%d").date(),
                                              format="YYYY-MM-DD")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_uber = st.number_input("Uber Sales (SEK)", 
                                                 value=uber_val,
                                                 step=100.0,
                                                 format="%.2f")
                        new_bolt = st.number_input("Bolt Sales (SEK)", 
                                                 value=bolt_val,
                                                 step=100.0,
                                                 format="%.2f")
                        new_zettel = st.number_input("Zettel Sales (SEK)", 
                                                   value=zettel_val + zettel_fee_val,
                                                   step=100.0,
                                                   format="%.2f")
                        new_zettel_fee = st.number_input("Zettel Fee (SEK)", 
                                                       value=zettel_fee_val,
                                                       step=10.0,
                                                       format="%.2f")
                    
                    with col2:
                        new_other = st.number_input("Other Sales (SEK)", 
                                                  value=other_val,
                                                  step=100.0,
                                                  format="%.2f")
                        new_other_type = st.text_input("Other Sales Type", value="Other")
                        new_oil = st.number_input("Oil Expense (SEK)", 
                                                value=oil_val,
                                                step=50.0,
                                                format="%.2f")
                    
                    # Calculate the new total
                    new_total = utils.calculate_total_sales(
                        new_uber, 
                        new_bolt, 
                        new_zettel, 
                        new_other
                    )
                    
                    st.metric("Total Sales", utils.format_currency(new_total))
                    
                    # Form actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Create Record"):
                            # Add a record with these values
                            db.add_sales_record(
                                driver_info['id'],
                                record_date.strftime("%Y-%m-%d"),
                                new_uber,
                                new_bolt,
                                new_zettel,  # This is the gross amount
                                new_zettel_fee,
                                new_other,
                                new_other_type,
                                new_oil,
                                edit_week
                            )
                            
                            st.success(f"Created new record for Week {edit_week}")
                            st.session_state.edit_week_mode = False
                            st.rerun()  # Rerun the app to show the new record
                    with col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state.edit_week_mode = False
                            st.rerun()

        # Add extra space before buttons
        st.write("")
        st.write("")
        
        # Style for the action buttons
        st.markdown("""
        <style>
        /* Style for action buttons */
        div.stButton > button[kind="secondary"] {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 0.5rem 1rem;
            font-size: 1rem;
            width: 100%;
            height: 45px;
            margin-top: 10px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Reset All Historical Data", key="reset_btn", type="secondary"):
                db.reset_all_sales(driver_info['id'])
                st.success("All historical data has been reset")
                st.rerun()
        with col2:
            if st.button("Export Historical Data", key="export_btn", type="secondary"):
                historical_report_data = utils.prepare_historical_report_data(
                    selected_driver,
                    historical_df
                )
                pdf_buffer = report_generator.generate_historical_report(historical_report_data)
                filename = f"{selected_driver}_historical_sales_summary.pdf"
                st.download_button(
                    "Download Historical Summary PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )

    # Driver Performance Comparison
    st.header("Driver Performance Comparison")

    # Get all drivers and their data
    comparison_drivers = st.multiselect(
        "Select Drivers to Compare",
        options=[d[1] for d in all_drivers],
        default=[selected_driver] if selected_driver else None
    )

    if comparison_drivers:
        drivers_data = []
        for driver_name in comparison_drivers:
            driver_id = driver_dict[driver_name]['id']
            target = driver_dict[driver_name]['target']
            oil_card = driver_dict[driver_name]['oil_card']
            weekly_sales = db.get_weekly_sales(driver_id, selected_week)
            drivers_data.append((driver_name, weekly_sales, target, oil_card))

        comparison_data = utils.prepare_comparison_data(drivers_data)
        comparison_fig = report_generator.create_comparison_chart(comparison_data)

        if comparison_fig:
            st.plotly_chart(comparison_fig, use_container_width=True)

            # Add a table with numerical comparison
            st.subheader("Numerical Comparison")
            comparison_df = pd.DataFrame(
                comparison_data['values'],
                columns=comparison_data['metrics'],
                index=comparison_data['drivers']
            )
            comparison_df['Target'] = comparison_data['targets']
            comparison_df['Achievement Rate'] = [
                f"{rate:.1f}%" for rate in comparison_data['achievement_rates']
            ]

            # Add driver info to the DataFrame index
            driver_info = [f"{name}\nCard: {info['card']}\nTarget: {utils.format_currency(info['target'])}"
                          for name, info in zip(comparison_data['drivers'], comparison_data['driver_info'])]
            comparison_df.index = driver_info

            st.dataframe(comparison_df.style.format({
                'Uber': 'SEK {:,.2f}'.format,
                'Bolt': 'SEK {:,.2f}'.format,
                'Zettel': 'SEK {:,.2f}'.format,
                'Other': 'SEK {:,.2f}'.format,
                'Target': 'SEK {:,.2f}'.format
            }))

            # Add export button for comparison report
            if st.button("Export Comparison Report", key="export_comparison_btn", type="secondary"):
                # Add week dates to comparison data
                comparison_data['week_number'] = selected_week
                comparison_data['week_start_date'] = week_start_date
                comparison_data['week_end_date'] = week_end_date
                
                pdf_buffer = report_generator.generate_comparison_report(comparison_data)
                current_date = utils.get_current_date()
                filename = f"driver_comparison_week_{selected_week}_{current_date}.pdf"
                st.download_button(
                    "Download Comparison Report PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )

        else:
            st.warning("No data available for comparison")

    # Target achievement check
    st.header("Target Achievement Status")
    if selected_driver and driver_info:
        target = driver_dict[selected_driver]["target"]  # Get target from the driver_dict

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Weekly Target", utils.format_currency(target))
        with col2:
            st.metric("Current Total", utils.format_currency(total_sales))

        if total_sales >= target:
            st.success("🎉 Target Achieved Successfully!")
        else:
            st.error("⚠️ Target Not Achieved")
            st.info(f"Missing: {utils.format_currency(target - total_sales)}")

    # Daily report generation (Renamed to Daily Report for clarity)
    st.header("Generate Daily Report")

    # Get week dates for report - reuse the current_year variable from the top of the file
    week_start, week_end = utils.get_week_dates(current_year, selected_week)

    # Use actual weekly sales data if available, otherwise use form data
    if weekly_sales and any(sales is not None for sales in weekly_sales):
        # Use actual saved weekly data
        total_uber_saved, total_bolt_saved, total_zettel_saved, total_other_saved, total_oil_saved, total_zettel_fee_saved = weekly_sales
        report_data = {
            'driver_name': selected_driver,
            'oil_card': driver_dict[selected_driver]['oil_card'],
            'target': driver_dict[selected_driver]['target'],
            'date': utils.get_current_date(),
            'week_number': selected_week,
            'week_start_date': week_start,
            'week_end_date': week_end,
            'sales_breakdown': {
                'uber_sales': total_uber_saved or 0,
                'bolt_sales': total_bolt_saved or 0,
                'zettel_sales': (total_zettel_saved or 0) + (total_zettel_fee_saved or 0),  # Gross Zettel
                'zettel_fee': total_zettel_fee_saved or 0,
                'other_sales': total_other_saved or 0,
                'other_sales_type': "Multiple",  # For weekly summary
                'oil_expense': total_oil_saved or 0
            },
            'total_sales': (total_uber_saved or 0) + (total_bolt_saved or 0) + (total_zettel_saved or 0) + (total_other_saved or 0),
            'target_achieved': ((total_uber_saved or 0) + (total_bolt_saved or 0) + (total_zettel_saved or 0) + (total_other_saved or 0)) >= driver_dict[selected_driver]['target']
        }
    else:
        # Use form data if no saved data available
        report_data = {
            'driver_name': selected_driver,
            'oil_card': driver_dict[selected_driver]['oil_card'],
            'target': driver_dict[selected_driver]['target'],
            'date': utils.get_current_date(),
            'week_number': selected_week,
            'week_start_date': week_start,
            'week_end_date': week_end,
            'sales_breakdown': {
                'uber_sales': uber_sales,
                'bolt_sales': bolt_sales,
                'zettel_sales': zettel_sales,
                'zettel_fee': zettel_fee,
                'other_sales': other_sales,
                'other_sales_type': other_type,
                'oil_expense': oil_expense
            },
            'total_sales': total_sales,
            'target_achieved': total_sales >= driver_dict[selected_driver]['target']
        }

    # Display the chart in the Streamlit interface
    fig = report_generator.create_sales_figure(report_data)
    st.plotly_chart(fig)

    if st.button("Export Daily Report", key="export_daily_btn", type="secondary"):
        pdf_buffer = report_generator.generate_pdf_report(report_data)
        current_date = utils.get_current_date()
        filename = f"{selected_driver}_daily_report_{current_date}.pdf"
        st.download_button(
            "Download Daily Report PDF",
            data=pdf_buffer,
            file_name=filename,
            mime="application/pdf"
        )
else:
    st.warning("Please add a driver to begin entering sales data.")
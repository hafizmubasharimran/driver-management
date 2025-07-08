import streamlit as st
import plotly.graph_objects as go
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
import utils

def create_sales_figure(report_data):
    sales = report_data['sales_breakdown']
    net_zettel = sales['zettel_sales'] - sales['zettel_fee']

    fig = go.Figure(data=[
        go.Bar(
            x=['Uber', 'Bolt', 'Zettel (Net)', 'Other'],
            y=[sales['uber_sales'], sales['bolt_sales'], 
               net_zettel, sales['other_sales']],
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        )
    ])

    fig.update_layout(
        title=f"Sales Breakdown for {report_data['driver_name']}",
        xaxis_title="Source",
        yaxis_title="Amount (SEK)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_sales_chart(report_data):
    drawing = Drawing(400, 200)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300

    sales = report_data['sales_breakdown']
    net_zettel = sales['zettel_sales'] - sales['zettel_fee']
    data = [[
        sales['uber_sales'],
        sales['bolt_sales'],
        net_zettel,
        sales['other_sales']
    ]]

    bc.data = data
    bc.categoryAxis.categoryNames = ['Uber', 'Bolt', 'Zettel (Net)', 'Other']
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(data[0]) * 1.2
    bc.bars[0].fillColor = colors.steelblue

    drawing.add(bc)
    return drawing

def generate_pdf_report(report_data):
    buffer = io.BytesIO()
    # Use landscape orientation with adjusted margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=50,
        rightMargin=50,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=20,
        textColor=colors.HexColor('#1f77b4')
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=5
    )

    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=2
    )

    # Header Section
    # Check if this is a weekly report or daily report
    is_weekly = 'week_number' in report_data

    report_title = "Weekly Sales Report" if is_weekly else "Daily Sales Report"
    elements.append(Paragraph(report_title, title_style))
    elements.append(Paragraph(f"Driver: {report_data['driver_name']}", header_style))

    # Add week number and date range for both daily and weekly reports
    if is_weekly:
        elements.append(Paragraph(f"Week {report_data['week_number']} ({report_data['week_start_date']} to {report_data['week_end_date']})", info_style))
    elif 'week_number' in report_data and 'week_start_date' in report_data and 'week_end_date' in report_data:
        elements.append(Paragraph(f"Week {report_data['week_number']} ({report_data['week_start_date']} to {report_data['week_end_date']})", info_style))

    # Add current date for both report types
    current_date = datetime.now().strftime("%Y-%m-%d")
    elements.append(Paragraph(f"Date Generated: {report_data.get('date', current_date)}", info_style))
    elements.append(Paragraph(f"Oil Card: {report_data['oil_card']}", info_style))
    elements.append(Spacer(1, 20))

    # Calculate correct total sales using net Zettel first
    sales = report_data['sales_breakdown']
    net_zettel = sales['zettel_sales'] - sales['zettel_fee']
    correct_total_sales = utils.calculate_total_sales(
        sales['uber_sales'], 
        sales['bolt_sales'], 
        net_zettel, 
        sales['other_sales']
    )

    # Target Achievement Section
    achieved = correct_total_sales >= report_data['target']
    achievement_style = ParagraphStyle(
        'Achievement',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#27ae60') if achieved else colors.HexColor('#c0392b'),
        alignment=1  # Center alignment
    )
    elements.append(Paragraph(
        f"{'✓ Target Achieved!' if achieved else '✗ Target Not Achieved'}",
        achievement_style
    ))
    elements.append(Spacer(1, 10))

    # Target Info Table
    target_data = [
        ['Weekly Target', 'Current Sales', 'Difference'],
        [
            utils.format_currency(report_data['target']),
            utils.format_currency(correct_total_sales),
            utils.format_currency(correct_total_sales - report_data['target'])
        ]
    ]
    target_table = Table(target_data, colWidths=[200] * 3)
    target_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1),
         colors.HexColor('#e8f6f3') if achieved else colors.HexColor('#fdedec')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(target_table)
    elements.append(Spacer(1, 20))

    # Sales Breakdown Section
    elements.append(Paragraph("Sales Breakdown", header_style))
    elements.append(Spacer(1, 10))

    sales = report_data['sales_breakdown']
    net_zettel = sales['zettel_sales'] - sales['zettel_fee']

    sales_data = [
        ['Source', 'Amount'],
        ['Uber', utils.format_currency(sales['uber_sales'])],
        ['Bolt', utils.format_currency(sales['bolt_sales'])],
        ['Zettel (Gross)', utils.format_currency(sales['zettel_sales'])],
        ['Zettel Fee', f"- {utils.format_currency(sales['zettel_fee'])}"],
        ['Zettel (Net)', utils.format_currency(net_zettel)],
        [f"Other ({sales['other_sales_type']})", utils.format_currency(sales['other_sales'])],
        ['Oil Expense', utils.format_currency(sales['oil_expense'])]
    ]

    # Update Other row with type
    for i, row in enumerate(sales_data):
        if row[0] == f"Other ({sales['other_sales_type']})":
            sales_data[i] = ['Other', f"{utils.format_currency(sales['other_sales'])} ({sales['other_sales_type']})"]

    sales_table = Table(sales_data, colWidths=[300, 200])
    sales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f6fa')),
    ]))
    elements.append(sales_table)
    elements.append(Spacer(1, 20))

    # Add chart with controlled size
    chart = create_sales_chart(report_data)
    chart.width = 500
    chart.height = 200
    elements.append(chart)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_historical_report(report_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Historical Sales Report - {report_data['driver_name']}", styles['Title']))
    elements.append(Paragraph(f"Generated on: {report_data['date']}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Total Summary
    total_sales = report_data['total_sales']
    summary_data = [
        ['Total Sales by Source', 'Amount'],
        ['Uber', f"SEK {total_sales['uber']:.2f}"],
        ['Bolt', f"SEK {total_sales['bolt']:.2f}"],
        ['Zettel', f"SEK {total_sales['zettel']:.2f}"],
        ['Other', f"SEK {total_sales['other']:.2f}"],
        ['Total Oil Expenses', f"SEK {total_sales['oil']:.2f}"],
        ['Total Net Sales', f"SEK {total_sales['total_net']:.2f}"],
    ]

    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Highlight the Total Net Sales row with a different background
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
    ]))

    elements.append(Paragraph("Total Sales Summary", styles['Heading2']))
    elements.append(Spacer(1, 12))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Weekly Breakdown
    elements.append(Paragraph("Weekly Sales Breakdown", styles['Heading2']))
    elements.append(Spacer(1, 12))

    historical_df = report_data['historical_data']
    # Include date range column and Total Net Sales in the table header
    weekly_data = [['Week', 'Date Range', 'Uber', 'Bolt', 'Zettel', 'Other', 'Oil', 'Total Net Sales']]

    for _, row in historical_df.iterrows():
        weekly_data.append([
            str(int(row['Week'])),
            row['Date Range'],
            f"SEK {row['Uber']:.2f}",
            f"SEK {row['Bolt']:.2f}",
            f"SEK {row['Zettel']:.2f}",
            f"SEK {row['Other']:.2f}",
            f"SEK {row['Oil']:.2f}",
            f"SEK {row['Total Net Sales']:.2f}"
        ])

    # Adjust column widths for the table with the date range column and Total Net Sales
    col_widths = [40, 120, 70, 70, 70, 70, 70, 90]  # Week, Date Range, Sales columns, and Total Net Sales
    weekly_table = Table(weekly_data, colWidths=col_widths)
    # Create a list for the table style
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Center align week number column
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Left align date range column
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Right align all numeric columns
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),     # Slightly smaller header font
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),     # Smaller font for data
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Highlight the Total Net Sales column
        ('BACKGROUND', (-1, 0), (-1, 0), colors.HexColor('#2c3e50')),
    ]

    # Add alternating row colors for better readability
    for i in range(1, len(weekly_data)):
        if i % 2 == 0:  # Even rows
            table_style.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))
        else:  # Odd rows - slightly different color
            table_style.append(('BACKGROUND', (0, i), (-1, i), colors.lightgrey))

    weekly_table.setStyle(TableStyle(table_style))

    elements.append(weekly_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def create_comparison_chart(comparison_data):
    """Create an interactive comparison chart using Plotly."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if not comparison_data['drivers']:
        return None

    # Create subplots: one for sales comparison, one for target achievement
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Sales by Category', 'Target Achievement Rate (%)'),
        row_heights=[0.7, 0.3],
        vertical_spacing=0.2
    )

    # Add sales comparison bars
    for i, driver in enumerate(comparison_data['drivers']):
        fig.add_trace(
            go.Bar(
                name=driver,
                x=comparison_data['metrics'],
                y=comparison_data['values'][i],
                text=[f"SEK {val:,.2f}" for val in comparison_data['values'][i]],
                textposition='auto',
            ),
            row=1, col=1
        )

    # Add target achievement rates
    fig.add_trace(
        go.Bar(
            name='Target Achievement',
            x=comparison_data['drivers'],
            y=comparison_data['achievement_rates'],
            text=[f"{rate:.1f}%" for rate in comparison_data['achievement_rates']],
            textposition='auto',
            marker_color=['#2ecc71' if rate >= 100 else '#e74c3c' 
                         for rate in comparison_data['achievement_rates']]
        ),
        row=2, col=1
    )

    # Update layout
    fig.update_layout(
        title_text="Driver Performance Comparison",
        barmode='group',
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Add a horizontal line at 100% for target achievement
    fig.add_hline(y=100, line_dash="dash", line_color="red", row=2, col=1)

    return fig

def generate_comparison_report(comparison_data):
    """Generate a PDF report comparing driver performance."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = []

    # Create custom style for better spacing
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        spaceAfter=30,
        fontSize=24
    )

    # Create custom style for driver info
    driver_info_style = ParagraphStyle(
        'DriverInfo',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=6
    )

    # Title
    # Check if week data exists
    has_week_data = 'week_number' in comparison_data

    if has_week_data:
        report_title = f"Driver Performance Comparison Report - Week {comparison_data['week_number']}"
    else:
        report_title = "Driver Performance Comparison Report"

    elements.append(Paragraph(report_title, title_style))

    # Add week date range if available
    if has_week_data:
        elements.append(Paragraph(
            f"Period: {comparison_data['week_start_date']} to {comparison_data['week_end_date']}", 
            styles['Normal']
        ))

    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Sales Comparison Table
    elements.append(Paragraph("Sales Comparison by Category", styles['Heading2']))
    elements.append(Spacer(1, 12))

    # Calculate column widths based on content
    col_widths = [200]  # Driver name column (increased for additional info)
    metric_width = 100  # Width for metric columns
    col_widths.extend([metric_width] * len(comparison_data['metrics']))
    col_widths.extend([metric_width, metric_width])  # Target and Achievement columns

    # Prepare table data
    table_data = [['Driver'] + comparison_data['metrics'] + ['Target', 'Achievement']]

    # Pre-calculate background colors for achievement rates
    achievement_colors = []
    for rate in comparison_data['achievement_rates']:
        achievement_colors.append(colors.lightgreen if rate >= 100 else colors.lightpink)

    for i, driver in enumerate(comparison_data['drivers']):
        # Create driver info paragraph
        driver_info = comparison_data['driver_info'][i]
        driver_text = Paragraph(
            f"{driver}<br/>"
            f"<font size=8>Card: {driver_info['card']}<br/>"
            f"Target: SEK {driver_info['target']:,.2f}</font>",
            driver_info_style
        )

        row = [driver_text]
        # Add sales values
        for val in comparison_data['values'][i]:
            row.append(f"SEK {val:,.2f}")
        # Add target and achievement rate
        row.append(f"SEK {comparison_data['targets'][i]:,.2f}")
        row.append(f"{comparison_data['achievement_rates'][i]:.1f}%")
        table_data.append(row)

    # Create and style the table
    table = Table(table_data, colWidths=col_widths)

    # Basic table style
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Right align numbers
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertical alignment
    ]

    # Add alternating row background colors for better readability
    for i in range(1, len(table_data)):
        if i % 2 == 0:  # Even rows
            table_style.append(('BACKGROUND', (0, i), (-2, i), colors.whitesmoke))
        else:  # Odd rows - slightly different color
            table_style.append(('BACKGROUND', (0, i), (-2, i), colors.lightgrey))

    # Add background colors for achievement rates - explicitly add each one to avoid lambda issues
    for i, color in enumerate(achievement_colors, start=1):
        if color == colors.lightgreen:
            table_style.append(('BACKGROUND', (-1, i), (-1, i), colors.lightgreen))
        else:
            table_style.append(('BACKGROUND', (-1, i), (-1, i), colors.lightpink))

    table.setStyle(TableStyle(table_style))

    elements.append(table)
    elements.append(Spacer(1, 30))

    # Performance Highlights
    elements.append(Paragraph("Performance Highlights", styles['Heading2']))
    elements.append(Spacer(1, 12))

    # Find top performers using safer method
    # Find driver with highest Uber sales
    top_uber_value = -1
    top_uber = 0
    for i in range(len(comparison_data['drivers'])):
        uber_value = comparison_data['values'][i][0]
        if uber_value > top_uber_value:
            top_uber_value = uber_value
            top_uber = i

    # Find driver with best achievement rate
    top_achievement_value = -1
    top_achievement = 0
    for i in range(len(comparison_data['drivers'])):
        achievement_value = comparison_data['achievement_rates'][i]
        if achievement_value > top_achievement_value:
            top_achievement_value = achievement_value
            top_achievement = i

    # Create a highlight table
    highlight_data = [
        ['Category', 'Top Performer', 'Achievement'],
        ['Highest Uber Sales', 
         comparison_data['drivers'][top_uber],
         f"SEK {comparison_data['values'][top_uber][0]:,.2f}"],
        ['Best Target Achievement',
         comparison_data['drivers'][top_achievement],
         f"{comparison_data['achievement_rates'][top_achievement]:.1f}%"]
    ]

    highlight_table = Table(highlight_data, colWidths=[200, 200, 200])
    # Create highlight table style as a list first
    highlight_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    # Add row colors separately to avoid lambda issues
    highlight_style.append(('BACKGROUND', (0, 1), (-1, 1), colors.lightgreen))
    highlight_style.append(('BACKGROUND', (0, 2), (-1, 2), colors.lightgreen))

    # Apply style to table
    highlight_table.setStyle(TableStyle(highlight_style))

    elements.append(highlight_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def format_currency(amount):
    return f"SEK {amount:,.2f}"

def generate_summary_report(summary_data):
    """Generate a PDF report for all drivers' weekly summary."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                          leftMargin=40,
                          rightMargin=40,
                          topMargin=40,
                          bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Custom styles with smaller fonts
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        spaceAfter=20
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12
    )

    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='CJK'
    )

    elements.append(Paragraph(f"Week {summary_data['week_number']} - All Drivers Summary", title_style))
    elements.append(Paragraph(f"Period: {summary_data['week_start_date']} to {summary_data['week_end_date']}", info_style))
    elements.append(Paragraph(f"Report Generated on: {summary_data['date']}", info_style))
    elements.append(Spacer(1, 20))

    # Driver breakdown with adjusted layout
    elements.append(Paragraph("Individual Drivers Breakdown", header_style))

    # Create breakdown table with proper spacing
    breakdown_headers = ['Driver', 'Uber', 'Bolt', 'Zettel', 'Other', 'Oil', 'Total']
    breakdown_data = [breakdown_headers]

    for driver in summary_data['drivers']:
        driver_total = sum([
            driver['uber'],
            driver['bolt'],
            driver['zettel'],
            driver['other']
        ])

        # Create wrapped driver info
        driver_text = Paragraph(
            f"{driver['name']}<br/>"
            f"<font size=7>Card: {driver.get('oil_card', 'N/A')}<br/>"
            f"Target: {utils.format_currency(driver.get('target', 0))}</font>",
            info_style
        )

        breakdown_data.append([
            driver_text,
            f"SEK {driver['uber']:,.2f}",
            f"SEK {driver['bolt']:,.2f}",
            f"SEK {driver['zettel']:,.2f}",
            f"SEK {driver['other']:,.2f}",
            f"SEK {driver['oil']:,.2f}",
            f"SEK {driver_total:,.2f}"
        ])

    # Adjusted column widths
    col_widths = [160] + [80] * (len(breakdown_headers) - 1)
    breakdown_table = Table(breakdown_data, colWidths=col_widths)

    # Table styling with smaller fonts
    breakdown_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    # Add alternating row background colors for better readability
    for i in range(1, len(breakdown_data)):
        if i % 2 == 0:  # Even rows
            breakdown_style.append(('BACKGROUND', (0, i), (-2, i), colors.whitesmoke))
        else:  # Odd rows - slightly different color
            breakdown_style.append(('BACKGROUND', (0, i), (-2, i), colors.lightgrey))

    # Apply the background color for total column separately (overrides row coloring)
    for i in range(1, len(breakdown_data)):
        breakdown_style.append(('BACKGROUND', (-1, i), (-1, i), colors.lightyellow))

    breakdown_table.setStyle(TableStyle(breakdown_style))

    elements.append(breakdown_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
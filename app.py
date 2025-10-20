import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Construction Site",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SPREADSHEET_ID = "10H_Er872srJihxthzQJEUy7RwG6NS5q54G-Ex9VPOnI"

@st.cache_resource
def get_google_sheet():
    """Connect to Google Sheets"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def get_transactions_sheet(spreadsheet):
    """Get transactions sheet"""
    try:
        return spreadsheet.sheet1
    except Exception as e:
        st.error(f"Error getting transactions sheet: {e}")
        return None

def get_credentials_sheet(spreadsheet):
    """Get or create credentials sheet"""
    try:
        try:
            sheet = spreadsheet.worksheet("credentials")
        except:
            # Create credentials sheet if it doesn't exist
            sheet = spreadsheet.add_worksheet(title="credentials", rows="100", cols="5")
            # Add headers
            sheet.append_row(["Username", "Password", "Phone", "Name", "Role"])
            # Add admin account
            sheet.append_row(["admin", "admin123", "0000000000", "Admin", "admin"])
        return sheet
    except Exception as e:
        st.error(f"Error with credentials sheet: {e}")
        return None

def authenticate_user(cred_sheet, username, password):
    """Authenticate user against credentials sheet"""
    try:
        data = cred_sheet.get_all_records()

        for row in data:
            if row['Username'].lower() == username.lower() and row['Password'] == password:
                return True, row['Role'], row['Name']
        return False, None, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None, None

def create_user_account(cred_sheet, username, password, phone, name):
    """Create new user account"""
    try:
        # Check if username already exists
        data = cred_sheet.get_all_records()
        for row in data:
            if row['Username'].lower() == username.lower():
                return False, "Username already exists"

        # Add new user
        cred_sheet.append_row([username, password, phone, name, "user"])
        return True, "Account created successfully"
    except Exception as e:
        return False, f"Error creating account: {e}"

def add_transaction(sheet, name, description, amount, transaction_type, payment_mode, username):
    """Add a transaction to Google Sheets"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, username, name, description, amount, transaction_type, payment_mode]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error adding transaction: {e}")
        return False

def get_transactions(sheet):
    """Get all transactions from Google Sheets"""
    try:
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # Convert Timestamp to datetime
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching transactions: {e}")
        return pd.DataFrame()

def initialize_transactions_sheet(sheet):
    """Initialize sheet with headers if empty"""
    try:
        if sheet.row_count == 0 or not sheet.row_values(1):
            headers = ["Timestamp", "User", "Name", "Description", "Amount", "Type", "Payment Mode"]
            sheet.append_row(headers)
    except Exception as e:
        st.error(f"Error initializing sheet: {e}")

def get_today_stats(df, username, is_admin):
    """Get today's statistics"""
    today = datetime.now().date()

    # Filter for today
    if not df.empty and 'Timestamp' in df.columns:
        df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
        today_df = df[df['Date'] == today]

        # Filter by user if not admin
        if not is_admin:
            today_df = today_df[today_df['User'] == username]

        if not today_df.empty:
            paid = today_df[today_df['Type'] == 'Paid']['Amount'].sum()
            received = today_df[today_df['Type'] == 'Received']['Amount'].sum()
            balance = received - paid
            return paid, received, balance

    return 0, 0, 0

def get_user_summary(df, start_date, end_date):
    """Get summary by user for admin view"""
    if df.empty:
        return pd.DataFrame()

    # Filter by date range
    df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    if filtered_df.empty:
        return pd.DataFrame()

    # Group by user
    user_summary = []
    for user in filtered_df['User'].unique():
        user_df = filtered_df[filtered_df['User'] == user]
        paid = user_df[user_df['Type'] == 'Paid']['Amount'].sum()
        received = user_df[user_df['Type'] == 'Received']['Amount'].sum()
        balance = received - paid

        user_summary.append({
            'User': user,
            'Paid': paid,
            'Received': received,
            'Balance': balance
        })

    return pd.DataFrame(user_summary)

def create_pdf_statement(df, start_date, end_date, username, is_admin):
    """Generate PDF statement"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=1  # Center
    )

    # Title
    title = Paragraph("Statement of Accounts", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Date range and user info
    info_text = f"<b>Period:</b> {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}<br/>"
    if not is_admin:
        info_text += f"<b>User:</b> {username}<br/>"
    info_text += f"<b>Generated on:</b> {datetime.now().strftime('%d %b %Y %I:%M %p')}"

    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 20))

    # Summary
    total_paid = df[df['Type'] == 'Paid']['Amount'].sum()
    total_received = df[df['Type'] == 'Received']['Amount'].sum()
    balance = total_received - total_paid

    summary_data = [
        ['Summary', ''],
        ['Total Paid', f'₹{total_paid:,.2f}'],
        ['Total Received', f'₹{total_received:,.2f}'],
        ['Net Balance', f'₹{balance:,.2f}']
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    # Transaction table
    table_data = [['Date', 'Name', 'Type', 'Amount', 'Payment', 'Description']]

    for idx, row in df.sort_values('Timestamp', ascending=False).iterrows():
        desc_value = row.get('Description', row.get('Notes', ''))
        table_data.append([
            row['Timestamp'].strftime('%d %b %y'),
            row['Name'][:20],
            row['Type'],
            f"₹{row['Amount']:,.0f}",
            row['Payment Mode'],
            str(desc_value)[:30] if desc_value else ''
        ])

    transactions_table = Table(table_data, colWidths=[0.9*inch, 1.2*inch, 0.9*inch, 1*inch, 0.9*inch, 1.6*inch])
    transactions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(transactions_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Navy Blue Theme CSS
st.markdown("""
    <style>
    /* Navy Blue Theme */
    :root {
        --navy-dark: #001f3f;
        --navy-medium: #003d7a;
        --navy-light: #0056b3;
        --navy-accent: #1e88e5;
    }

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #001f3f 0%, #003d7a 100%);
    }

    /* Content area */
    .block-container {
        background-color: rgba(255, 255, 255, 0.98);
        border-radius: 15px;
        padding: 1.5rem !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    /* Headers */
    h1, h2, h3 {
        color: #001f3f !important;
    }

    h1 {
        font-size: 28px !important;
        margin-bottom: 5px !important;
        margin-top: 5px !important;
    }

    h2 {
        font-size: 20px !important;
        margin-top: 15px !important;
        margin-bottom: 10px !important;
    }

    h3 {
        font-size: 18px !important;
        margin-top: 10px !important;
        margin-bottom: 8px !important;
    }

    /* Buttons - Navy Blue Theme */
    .stButton > button {
        width: 100%;
        height: 65px;
        font-size: 20px;
        font-weight: bold;
        margin: 8px 0;
        border-radius: 12px;
        touch-action: manipulation;
        transition: all 0.2s ease;
        border: 2px solid transparent;
    }

    /* Primary buttons (selected) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #001f3f 0%, #0056b3 100%) !important;
        color: white !important;
        border: 2px solid #1e88e5 !important;
        box-shadow: 0 4px 12px rgba(0, 31, 63, 0.4) !important;
    }

    /* Secondary buttons (unselected) */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        color: #001f3f !important;
        border: 2px solid #90caf9 !important;
    }

    /* Button hover effects */
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 31, 63, 0.3) !important;
    }

    /* Text inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        font-size: 18px !important;
        padding: 12px !important;
        border: 2px solid #90caf9 !important;
        border-radius: 8px !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #001f3f !important;
        box-shadow: 0 0 0 2px rgba(0, 31, 63, 0.2) !important;
    }

    /* Metric cards - Navy Blue */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #90caf9;
    }

    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #001f3f !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
        color: #003d7a !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e3f2fd;
        border-radius: 10px;
        padding: 5px;
    }

    .stTabs [data-baseweb="tab"] {
        color: #001f3f !important;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 20px;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #001f3f 0%, #0056b3 100%) !important;
        color: white !important;
    }

    /* Date inputs */
    .stDateInput > div > div > input {
        font-size: 16px !important;
        border: 2px solid #90caf9 !important;
        border-radius: 8px !important;
    }

    /* Success/Error messages */
    .stSuccess {
        background-color: #c8e6c9 !important;
        color: #1b5e20 !important;
        border-left: 4px solid #4caf50 !important;
    }

    .stError {
        background-color: #ffcdd2 !important;
        color: #b71c1c !important;
        border-left: 4px solid #f44336 !important;
    }

    /* Dataframes */
    .stDataFrame {
        border: 2px solid #90caf9 !important;
        border-radius: 10px !important;
    }

    /* Column spacing */
    div[data-testid="column"] {
        padding: 5px !important;
    }

    /* Hide sidebar */
    section[data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'display_name' not in st.session_state:
    st.session_state.display_name = ""
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'transaction_type' not in st.session_state:
    st.session_state.transaction_type = None
if 'payment_mode' not in st.session_state:
    st.session_state.payment_mode = None
if 'show_register' not in st.session_state:
    st.session_state.show_register = False

# Login/Registration section
if not st.session_state.logged_in:
    st.title("Login")

    # Connect to Google Sheets for credentials
    spreadsheet = get_google_sheet()

    if spreadsheet:
        cred_sheet = get_credentials_sheet(spreadsheet)

        if cred_sheet:
            if not st.session_state.show_register:
                # Login form
                username = st.text_input("Username", key="login_username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", key="login_password", placeholder="Enter password")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("🔐 Login", key="login_btn", use_container_width=True, type="primary"):
                        if username and password:
                            success, role, name = authenticate_user(cred_sheet, username, password)
                            if success:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.display_name = name
                                st.session_state.is_admin = (role == "admin")
                                st.rerun()
                            else:
                                st.error("Invalid username or password")
                        else:
                            st.warning("Please enter username and password")

                with col2:
                    if st.button("👤 Create Account", key="create_account_btn", use_container_width=True):
                        st.session_state.show_register = True
                        st.rerun()

            else:
                # Registration form
                st.subheader("Create New Account")

                new_name = st.text_input("Full Name", key="reg_name", placeholder="Enter your full name")
                new_phone = st.text_input("Phone Number", key="reg_phone", placeholder="Enter your phone number")
                new_username = st.text_input("Username", key="reg_username", placeholder="Choose a username")
                new_password = st.text_input("Password", key="reg_password", placeholder="Choose a password")
                confirm_password = st.text_input("Confirm Password", key="reg_confirm_password", placeholder="Confirm your password")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✅ Register", key="register_btn", use_container_width=True, type="primary"):
                        if not all([new_name, new_phone, new_username, new_password]):
                            st.error("Please fill all fields")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match")
                        elif len(new_password) < 4:
                            st.error("Password must be at least 4 characters")
                        else:
                            success, message = create_user_account(cred_sheet, new_username, new_password, new_phone, new_name)
                            if success:
                                st.success(message)
                                st.info("Please login with your new credentials")
                                st.session_state.show_register = False
                                st.rerun()
                            else:
                                st.error(message)

                with col2:
                    if st.button("← Back to Login", key="back_login_btn", use_container_width=True):
                        st.session_state.show_register = False
                        st.rerun()
        else:
            st.error("Could not access credentials sheet")
    else:
        st.error("Could not connect to Google Sheets")

else:
    # Logout button at top right
    col1, col2, col3 = st.columns([8, 1, 1])
    with col3:
        if st.button("🚪", key="logout_btn", help="Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.display_name = ""
            st.session_state.is_admin = False
            st.session_state.transaction_type = None
            st.session_state.payment_mode = None
            st.rerun()

    # Connect to Google Sheets
    spreadsheet = get_google_sheet()

    if spreadsheet:
        trans_sheet = get_transactions_sheet(spreadsheet)

        if trans_sheet:
            # Initialize sheet if needed
            initialize_transactions_sheet(trans_sheet)

            # Get all transactions
            df = get_transactions(trans_sheet)

            # Filter based on user role
            user_df = df.copy() if not df.empty else df
            if not df.empty and not st.session_state.is_admin:
                user_df = df[df['User'] == st.session_state.username]

            # TODAY'S KPI BOXES AT TOP
            st.markdown("### 📅 Today's Summary")
            today_paid, today_received, today_balance = get_today_stats(user_df, st.session_state.username, st.session_state.is_admin)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("💸 Paid", f"₹{today_paid:,.0f}")

            with col2:
                st.metric("💰 Received", f"₹{today_received:,.0f}")

            with col3:
                st.metric("💵 Balance", f"₹{today_balance:,.0f}")

            st.markdown("---")

            # TABS: Different for admin vs user
            if st.session_state.is_admin:
                tab1, tab2, tab3 = st.tabs(["➕ New Entry", "📥 Download Statement", "👥 User Summary"])
            else:
                tab1, tab2 = st.tabs(["➕ New Entry", "📥 Download Statement"])

            with tab1:
                # Transaction Entry Form
                with st.form(key="transaction_form", clear_on_submit=True):
                    st.header("📝 New Entry")

                    # Stack all inputs vertically for mobile
                    name = st.text_input("Name", placeholder="Enter person/vendor name")

                    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.0f")

                    description = st.text_area("Description (Optional)", placeholder="Add details...", height=80)

                    # Transaction Type Buttons
                    st.subheader("Type")
                    col1, col2 = st.columns(2)

                    with col1:
                        btn_type = "primary" if st.session_state.transaction_type == "Paid" else "secondary"
                        if st.form_submit_button("💸 PAID", use_container_width=True, type=btn_type):
                            st.session_state.transaction_type = "Paid"

                    with col2:
                        btn_type = "primary" if st.session_state.transaction_type == "Received" else "secondary"
                        if st.form_submit_button("💰 RECEIVED", use_container_width=True, type=btn_type):
                            st.session_state.transaction_type = "Received"

                    # Payment Mode Buttons
                    st.subheader("Payment Mode")
                    col1, col2 = st.columns(2)

                    with col1:
                        btn_type = "primary" if st.session_state.payment_mode == "Online" else "secondary"
                        if st.form_submit_button("🌐 Online", use_container_width=True, type=btn_type):
                            st.session_state.payment_mode = "Online"

                        btn_type = "primary" if st.session_state.payment_mode == "Phone" else "secondary"
                        if st.form_submit_button("📞 Phone", use_container_width=True, type=btn_type):
                            st.session_state.payment_mode = "Phone"

                    with col2:
                        btn_type = "primary" if st.session_state.payment_mode == "GPay" else "secondary"
                        if st.form_submit_button("📱 GPay", use_container_width=True, type=btn_type):
                            st.session_state.payment_mode = "GPay"

                        btn_type = "primary" if st.session_state.payment_mode == "Cash" else "secondary"
                        if st.form_submit_button("💵 Cash", use_container_width=True, type=btn_type):
                            st.session_state.payment_mode = "Cash"

                    # Display current selections
                    if st.session_state.transaction_type:
                        st.info(f"Type: **{st.session_state.transaction_type}**")
                    if st.session_state.payment_mode:
                        st.info(f"Payment: **{st.session_state.payment_mode}**")

                    # Submit Button
                    st.markdown("---")
                    submitted = st.form_submit_button("✅ SUBMIT", type="primary", use_container_width=True)

                    if submitted:
                        if not name:
                            st.error("Please enter a name")
                        elif amount <= 0:
                            st.error("Please enter a valid amount")
                        elif not st.session_state.transaction_type:
                            st.error("Please select type (Paid or Received)")
                        elif not st.session_state.payment_mode:
                            st.error("Please select payment mode")
                        else:
                            if add_transaction(
                                trans_sheet,
                                name,
                                description,
                                amount,
                                st.session_state.transaction_type,
                                st.session_state.payment_mode,
                                st.session_state.username
                            ):
                                st.success("✅ Entry added successfully!")
                                # Reset selections
                                st.session_state.transaction_type = None
                                st.session_state.payment_mode = None
                                st.rerun()

            with tab2:
                # Download Statement Tab
                st.header("📥 Download Statement")
                st.write("Select date range to download your statement")

                # Date range selection
                col1, col2 = st.columns(2)

                with col1:
                    start_date = st.date_input(
                        "Start Date",
                        value=datetime.now().date() - timedelta(days=30),
                        max_value=datetime.now().date(),
                        key="start_date"
                    )

                with col2:
                    end_date = st.date_input(
                        "End Date",
                        value=datetime.now().date(),
                        max_value=datetime.now().date(),
                        key="end_date"
                    )

                if start_date > end_date:
                    st.error("Start date must be before end date")
                else:
                    # Filter data by date range
                    if not user_df.empty:
                        user_df['Date'] = pd.to_datetime(user_df['Timestamp']).dt.date
                        filtered_df = user_df[(user_df['Date'] >= start_date) & (user_df['Date'] <= end_date)]

                        if not filtered_df.empty:
                            # Calculate summary
                            total_paid = filtered_df[filtered_df['Type'] == 'Paid']['Amount'].sum()
                            total_received = filtered_df[filtered_df['Type'] == 'Received']['Amount'].sum()
                            balance = total_received - total_paid

                            # Display summary
                            st.subheader("📊 Summary")
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Total Paid", f"₹{total_paid:,.0f}")

                            with col2:
                                st.metric("Total Received", f"₹{total_received:,.0f}")

                            with col3:
                                st.metric("Net Balance", f"₹{balance:,.0f}")

                            st.markdown("---")

                            # Show all transactions in this period
                            st.subheader(f"All Entries ({len(filtered_df)} total)")

                            # Display as cards
                            for idx, row in filtered_df.sort_values('Timestamp', ascending=False).iterrows():
                                type_emoji = "💸" if row['Type'] == 'Paid' else "💰"
                                amount_color = "red" if row['Type'] == 'Paid' else "green"
                                desc_value = row.get('Description', row.get('Notes', ''))

                                with st.container():
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**{type_emoji} {row['Name']}**")
                                        st.caption(f"{row['Payment Mode']} • {row['Timestamp'].strftime('%d %b %Y %I:%M %p')}")
                                        if desc_value:
                                            st.caption(f"📝 {desc_value}")
                                    with col2:
                                        st.markdown(f"**<span style='color:{amount_color}'>₹{row['Amount']:,.0f}</span>**",
                                                   unsafe_allow_html=True)
                                    st.markdown("---")

                            # Download PDF button
                            st.markdown("---")

                            # Generate PDF
                            pdf_buffer = create_pdf_statement(
                                filtered_df,
                                start_date,
                                end_date,
                                st.session_state.username,
                                st.session_state.is_admin
                            )

                            st.download_button(
                                label="📥 Download as PDF",
                                data=pdf_buffer,
                                file_name=f"statement_{start_date}_{end_date}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        else:
                            st.info("No entries found in selected date range.")
                    else:
                        st.info("No entries available.")

            # Admin-only User Summary tab
            if st.session_state.is_admin:
                with tab3:
                    st.header("👥 User Summary")
                    st.write("View summary of all users' transactions")

                    # Date range selection
                    col1, col2 = st.columns(2)

                    with col1:
                        admin_start_date = st.date_input(
                            "Start Date",
                            value=datetime.now().date() - timedelta(days=30),
                            max_value=datetime.now().date(),
                            key="admin_start_date"
                        )

                    with col2:
                        admin_end_date = st.date_input(
                            "End Date",
                            value=datetime.now().date(),
                            max_value=datetime.now().date(),
                            key="admin_end_date"
                        )

                    if admin_start_date > admin_end_date:
                        st.error("Start date must be before end date")
                    else:
                        # Get user summary
                        if not df.empty:
                            user_summary_df = get_user_summary(df, admin_start_date, admin_end_date)

                            if not user_summary_df.empty:
                                st.subheader(f"📊 Summary from {admin_start_date.strftime('%d %b %Y')} to {admin_end_date.strftime('%d %b %Y')}")

                                # Display as styled dataframe
                                st.dataframe(
                                    user_summary_df.style.format({
                                        'Paid': '₹{:,.0f}',
                                        'Received': '₹{:,.0f}',
                                        'Balance': '₹{:,.0f}'
                                    }),
                                    use_container_width=True,
                                    hide_index=True
                                )

                                # Total summary
                                st.markdown("---")
                                st.subheader("📈 Overall Totals")

                                col1, col2, col3 = st.columns(3)

                                with col1:
                                    total_paid = user_summary_df['Paid'].sum()
                                    st.metric("Total Paid (All Users)", f"₹{total_paid:,.0f}")

                                with col2:
                                    total_received = user_summary_df['Received'].sum()
                                    st.metric("Total Received (All Users)", f"₹{total_received:,.0f}")

                                with col3:
                                    total_balance = user_summary_df['Balance'].sum()
                                    st.metric("Total Balance", f"₹{total_balance:,.0f}")
                            else:
                                st.info("No transactions found in selected date range.")
                        else:
                            st.info("No transactions available.")
        else:
            st.error("Could not access transactions sheet")
    else:
        st.error("Failed to connect to Google Sheets. Please check your configuration.")

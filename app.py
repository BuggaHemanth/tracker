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
    initial_sidebar_state="collapsed",
)

# Google Sheets setup
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID = "10H_Er872srJihxthzQJEUy7RwG6NS5q54G-Ex9VPOnI"


@st.cache_resource
def get_google_sheet():
    """Connect to Google Sheets"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES
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
        sheet = spreadsheet.sheet1
        # Test if sheet is accessible by getting row count
        _ = sheet.row_count
        return sheet
    except Exception as e:
        st.error(f"Could not access transactions sheet: {e}")
        return None


def get_credentials_sheet(spreadsheet):
    """Get or create credentials sheet"""
    try:
        try:
            sheet = spreadsheet.worksheet("credentials")
        except:
            sheet = spreadsheet.add_worksheet(title="credentials", rows="100", cols="5")
            sheet.append_row(["Username", "Password", "Phone", "Name", "Role"])
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
            if (
                row["Username"].lower() == username.lower()
                and row["Password"] == password
            ):
                return True, row["Role"], row["Name"]
        return False, None, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None, None


def create_user_account(cred_sheet, username, password, phone, name):
    """Create new user account"""
    try:
        data = cred_sheet.get_all_records()
        for row in data:
            if row["Username"].lower() == username.lower():
                return False, "Username already exists"
        cred_sheet.append_row([username, password, phone, name, "user"])
        return True, "Account created successfully"
    except Exception as e:
        return False, f"Error creating account: {e}"


def add_transaction(
    sheet, name, description, amount, transaction_type, payment_mode, username
):
    """Add a transaction to Google Sheets"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            username,
            name,
            description,
            amount,
            transaction_type,
            payment_mode,
        ]
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
            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching transactions: {e}")
        return pd.DataFrame()


def initialize_transactions_sheet(sheet):
    """Initialize sheet with headers if empty"""
    try:
        if sheet.row_count == 0 or not sheet.row_values(1):
            headers = [
                "Timestamp",
                "User",
                "Name",
                "Purpose",
                "Amount",
                "Type",
                "Payment Mode",
            ]
            sheet.append_row(headers)
    except Exception as e:
        st.error(f"Error initializing sheet: {e}")


def get_today_stats(df, username, is_admin):
    """Get today's statistics"""
    today = datetime.now().date()
    if not df.empty and "Timestamp" in df.columns:
        df = df.copy()  # Avoid modifying the original dataframe
        df["Date"] = pd.to_datetime(df["Timestamp"]).dt.date
        today_df = df[df["Date"] == today]
        if not is_admin:
            today_df = today_df[today_df["User"] == username]
        if not today_df.empty:
            paid = today_df[today_df["Type"] == "Paid"]["Amount"].sum()
            received = today_df[today_df["Type"] == "Received"]["Amount"].sum()
            balance = received - paid
            return paid, received, balance
    return 0, 0, 0


def get_user_summary(df, start_date, end_date):
    """Get summary by user for admin view"""
    if df.empty:
        return pd.DataFrame()
    df = df.copy()  # Avoid modifying the original dataframe
    df["Date"] = pd.to_datetime(df["Timestamp"]).dt.date
    filtered_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
    if filtered_df.empty:
        return pd.DataFrame()
    user_summary = []
    for user in filtered_df["User"].unique():
        user_df = filtered_df[filtered_df["User"] == user]
        paid = user_df[user_df["Type"] == "Paid"]["Amount"].sum()
        received = user_df[user_df["Type"] == "Received"]["Amount"].sum()
        balance = received - paid
        user_summary.append(
            {"User": user, "Paid": paid, "Received": received, "Balance": balance}
        )
    return pd.DataFrame(user_summary)


def create_pdf_statement(df, start_date, end_date, username, is_admin):
    """Generate PDF statement"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=18,
    )
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.Color(0, 0, 104 / 255),
        spaceAfter=30,
        alignment=1,
    )
    title = Paragraph("Statement of Accounts", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    info_text = f"<b>Period:</b> {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}<br/>"
    if not is_admin:
        info_text += f"<b>User:</b> {username}<br/>"
    info_text += f"<b>Generated on:</b> {datetime.now().strftime('%d %b %Y %I:%M %p')}"
    info = Paragraph(info_text, styles["Normal"])
    elements.append(info)
    elements.append(Spacer(1, 20))
    total_paid = df[df["Type"] == "Paid"]["Amount"].sum()
    total_received = df[df["Type"] == "Received"]["Amount"].sum()
    balance = total_received - total_paid
    summary_data = [
        ["Summary", ""],
        ["Total Paid", f"₹{total_paid:,.2f}"],
        ["Total Received", f"₹{total_received:,.2f}"],
        ["Net Balance", f"₹{balance:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0, 0, 104 / 255)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 11),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    table_data = [["Date", "Name", "Type", "Amount", "Payment", "Purpose"]]
    for idx, row in df.sort_values("Timestamp", ascending=False).iterrows():
        desc_value = row.get("Description", row.get("Notes", ""))
        table_data.append(
            [
                row["Timestamp"].strftime("%d %b %y"),
                row["Name"][:20],
                row["Type"],
                f"₹{row['Amount']:,.0f}",
                row["Payment Mode"],
                str(desc_value)[:30] if desc_value else "",
            ]
        )
    transactions_table = Table(
        table_data,
        colWidths=[
            0.9 * inch,
            1.2 * inch,
            0.9 * inch,
            1 * inch,
            0.9 * inch,
            1.6 * inch,
        ],
    )
    transactions_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0, 0, 104 / 255)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(transactions_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# Navy Blue Theme CSS - RGB(0,0,104) - Mobile Optimized
st.markdown(
    """
    <style>
    /* Universal box-sizing and overflow prevention */
    * {
        box-sizing: border-box !important;
    }

    /* Main background - Navy Blue RGB(0,0,104) */
    .stApp {
        background: rgb(0, 0, 104);
        overflow-x: visible !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Content area - MOBILE-FIRST responsive layout */
    .block-container {
        background-color: #ffffff;
        border-radius: 0px !important;
        padding: 0rem !important;
        width: 100% !important;
        max-width: 100vw !important;
        margin: 0 !important;
        overflow-x: visible !important;
        box-sizing: border-box !important;
    }

    /* Wider screens get constrained width */
    @media (min-width: 500px) {
        .block-container {
            max-width: 500px !important;
            padding: 0rem !important;
        }
    }

    /* Headers */
    h1, h2, h3 {
        color: rgb(0, 0, 104) !important;
        padding-left: 4px !important;
        padding-right: 4px !important;
    }
    h1 { font-size: 22px !important; margin: 5px 0 !important; }
    h2 { font-size: 18px !important; margin: 10px 0 5px 0 !important; }
    h3 { font-size: 16px !important; margin: 5px 0 8px 0 !important; }

    /* Ensure all labels are visible */
    label, .stMarkdown p {
        color: rgb(0, 0, 104) !important;
    }

    /* MOBILE-FIRST: Buttons fit within column exactly */
    .stButton > button {
        width: 100% !important;
        white-space: normal !important;     /* allow wrap */
        overflow: visible !important;
        text-overflow: unset !important;
        line-height: 1.2 !important;
        font-size: 10px !important;          /* slightly larger for readability */
        padding: 8px 2px !important;
        box-sizing: border-box !important;
        margin: 0 !important;
        border-radius: 0px !important;
    }

    /* Primary buttons - Navy Blue RGB(0,0,104) */
    .stButton > button[kind="primary"] {
        background: rgb(0, 0, 104) !important;
        color: white !important;
        border: 1px solid rgb(0, 0, 104) !important;
    }

    /* Secondary buttons */
    .stButton > button[kind="secondary"] {
        background: #e6f2ff !important;
        color: rgb(0, 0, 104) !important;
        border: 1px solid #99ccff !important;
    }

    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 2px 8px rgba(0, 0, 104, 0.3) !important;
    }

    /* Text inputs - Compact with visible labels */
    .stTextInput label,
    .stNumberInput label {
        color: rgb(0, 0, 104) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        margin-bottom: 3px !important;
        padding-left: 4px !important;
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        font-size: 15px !important;
        padding: 6px !important;
        border: 1px solid #99ccff !important;
        border-radius: 4px !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: rgb(0, 0, 104) !important;
        box-shadow: 0 0 0 1px rgba(0, 0, 104, 0.2) !important;
    }

    /* Reduce spacing between input fields */
    .stTextInput,
    .stNumberInput {
        margin-bottom: 6px !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        padding-left: 4px !important;
        padding-right: 4px !important;
    }

    /* Metric cards - Fully responsive and fit within column */
    [data-testid="stMetric"] {
        background: #e6f2ff;
        padding: 8px !important;
        border-radius: 0px;
        border: 0.5px solid #99ccff;
        margin-bottom: 0.5rem !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        box-sizing: border-box !important;
        width: 100% !important;
        max-width: 100% !important;
    }

    [data-testid="stMetricValue"] {
        font-size: clamp(12px, 3vw, 14px) !important;
        font-weight: bold !important;
        color: rgb(0, 0, 104) !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: clamp(8px, 2vw, 10px) !important;
        color: rgb(0, 0, 104) !important;
        font-weight: 600 !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
    }

      /* Horizontal container */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;   /* keep side-by-side */
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: visible !important; /* KEY FIX */
        gap: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Force exact 50/50 columns */
    div[data-testid="column"] {
        flex: 0 0 50% !important;
        width: 50% !important;
        max-width: 50% !important;
        min-width: 0 !important;        /* CRITICAL */
        box-sizing: border-box !important;
        padding: 0px !important;
    }


    /* Remove ALL column spacing on mobile */
    div[data-testid="column"]:first-child {
        padding: 0 !important;
        margin: 0 !important;
        border-right: 0.5px solid transparent !important;
    }

    div[data-testid="column"]:last-child {
        padding: 0 !important;
        margin: 0 !important;
        border-left: 0.5px solid transparent !important;
    }

    div[data-testid="column"]:not(:first-child):not(:last-child) {
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Remove any layout gaps on mobile */
    .row-widget.stHorizontal {
        display: flex !important;
        flex-direction: row !important;
        gap: 0px !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Tabs - Reduced spacing */
    .stTabs {
        margin-top: -10px !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #e6f2ff;
        border-radius: 8px;
        padding: 4px;
        margin-bottom: 10px !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: rgb(0, 0, 104) !important;
        font-weight: 600;
        font-size: 14px !important;
        padding: 8px 12px !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgb(0, 0, 104) !important;
        color: white !important;
    }

    /* Date inputs with visible labels */
    .stDateInput label {
        color: rgb(0, 0, 104) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }

    .stDateInput > div > div > input {
        font-size: 14px !important;
        border: 2px solid #99ccff !important;
        border-radius: 6px !important;
    }

    /* Ensure subheaders are visible */
    .stMarkdown h2 {
        margin-top: 8px !important;
        margin-bottom: 6px !important;
    }

    /* Force all elements inside columns to fit */
    [data-testid="column"] > div {
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Ensure button containers match column width exactly */
    .stButton {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }

    /* Ensure all child divs respect parent width */
    [data-testid="column"] * {
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    /* Remove ALL default streamlit element spacing */
    [data-testid="column"] .element-container {
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Remove Streamlit's default vertical rhythm */
    [data-testid="column"] > div > div {
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Remove all padding from element containers */
    .element-container {
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Ensure main container has no extra padding */
    .main .block-container {
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }

    /* Remove default Streamlit padding */
    .main {
        padding: 0 !important;
    }

    /* Success/Error messages */
    .stSuccess {
        background-color: #d4edda !important;
        color: #155724 !important;
        padding: 12px !important;
        border-radius: 8px !important;
        border-left: 4px solid #28a745 !important;
        font-weight: bold !important;
    }

    .stError {
        background-color: #f8d7da !important;
        color: #721c24 !important;
        border-left: 4px solid #dc3545 !important;
    }

    /* Info messages */
    .stInfo {
        background-color: #d1ecf1 !important;
        color: #0c5460 !important;
        font-size: 14px !important;
    }

    /* Hide sidebar */
    section[data-testid="stSidebar"] { display: none; }

    /* PORTRAIT MODE: Very narrow screens (phones in portrait) */
    @media (max-width: 600px) {
        .block-container {
            padding: 0rem !important;
            max-width: 100vw !important;
            width: 100% !important;
        }

        /* Ultra-compact buttons for portrait - EXCEPT login buttons */
        .stButton > button {
            font-size: 10px !important;
            padding: 8px 2px !important;
            min-height: 32px !important;
            margin: 0 !important;
            border-radius: 0px !important;
        }

        /* EXCEPTION: Keep login buttons normal size even in portrait */
        button[data-testid*="baseButton"][kind="primary"],
        [data-testid="column"]:has(button[key*="login"]) .stButton > button,
        [data-testid="column"]:has(button[key*="register"]) .stButton > button,
        [data-testid="column"]:has(button[key*="account"]) .stButton > button {
            padding: 12px 16px !important;
            font-size: 14px !important;
            min-height: 42px !important;
            margin: 4px 0 !important;
        }

        /* Smaller metrics for portrait */
        [data-testid="stMetricValue"] {
            font-size: 12px !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 9px !important;
        }

        [data-testid="stMetric"] {
            padding: 4px !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
        }

    /* Force true 50% columns */
    div[data-testid="column"] {
        flex: 0 0 50% !important;
        width: 50% !important;
        max-width: 50% !important;
        min-width: 0 !important;          /* 🔑 allows shrinking */
        box-sizing: border-box !important;
        padding: 0px !important;
    }


        div[data-testid="stHorizontalBlock"] {
            gap: 0px !important;
        }

        /* Smaller text in portrait */
        h1 { font-size: 16px !important; }
        h2 { font-size: 14px !important; }
        h3 { font-size: 13px !important; }

        /* Tighter input spacing */
        .stTextInput, .stNumberInput {
            margin-bottom: 4px !important;
        }

        /* EXCEPTION: Login page inputs need normal size */
        .stTextInput:has(input[key*="login"]) input,
        .stTextInput:has(input[key*="register"]) input {
            font-size: 16px !important;
            padding: 10px !important;
            min-height: 40px !important;
        }
    }

    /* LANDSCAPE MODE: Wider screens (landscape phones, tablets, desktop) */
    @media (min-width: 601px) {
        div[data-testid="stHorizontalBlock"] {
            gap: 0px !important;
        }

    /* Force true 50% columns */
    div[data-testid="column"] {
        flex: 0 0 50% !important;
        width: 50% !important;
        max-width: 50% !important;
        min-width: 0 !important;          /* 🔑 allows shrinking */
        box-sizing: border-box !important;
        padding: 0px !important;
    }


        .stButton > button {
            padding: 8px 6px !important;
            min-height: 40px !important;
        }
    }
    /* STEP 2: Force button container to respect column width */
    [data-testid="column"] .stButton {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
    }

    /* STEP 3: Force the button itself to not exceed 50% column */
    .stButton > button {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;

    padding: 8px 2px !important;
    font-size: 10px !important;

    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    border-radius: 0px !important;
    }

        /* FINAL OVERRIDE – MUST BE LAST */
    div[data-testid="stHorizontalBlock"] {
        overflow-x: visible !important;
    }

    div[data-testid="column"] {
        flex: 0 0 50% !important;
        width: 50% !important;
        max-width: 50% !important;
        min-width: 0 !important;
    }

    [data-testid="column"] .stButton {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }

    .stButton > button {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        font-size: 9px !important;
        padding: 4px 2px !important;
        white-space: nowrap !important;
    }


    /* Remove Streamlit column gap completely */
    div[data-testid="stHorizontalBlock"] {
        gap: 0 !important;
        column-gap: 0 !important;
    }

    /* FORCE EXACT 2-COLUMN GRID – NO OVERFLOW */
    div[data-testid="stHorizontalBlock"] {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: visible !important;
    }

    /* =========================================================
   FINAL OVERRIDES — MUST BE AT THE VERY END
   This fixes horizontal scrolling permanently
   ========================================================= */

/* Force Streamlit rows to be EXACTLY 2 columns */
div[data-testid="stHorizontalBlock"] {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    width: 100% !important;
    max-width: 100% !important;
    gap: 0 !important;
    overflow-x: hidden !important;
}

    /* Columns must fully fit grid cell */
    div[data-testid="column"] {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        box-sizing: border-box !important;
    }

    /* Button containers */
    [data-testid="column"] .stButton {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }

    /* Actual buttons */
    .stButton > button {
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        padding: 8px 2px !important;
        font-size: 10px !important;
        white-space: normal !important;
        border-radius: 0px !important;
    }

    /* FIX: Login/Register buttons need normal sizing for clickability */
    button[data-testid*="baseButton"][kind="primary"],
    .stButton > button:first-child {
        padding: 12px 20px !important;
        font-size: 15px !important;
        min-height: 44px !important;
    }

    /* Specifically target login page buttons */
    [data-testid="column"]:has(button[key*="login"]) .stButton > button,
    [data-testid="column"]:has(button[key*="register"]) .stButton > button,
    [data-testid="column"]:has(button[key*="account"]) .stButton > button {
        padding: 12px 20px !important;
        font-size: 15px !important;
        min-height: 44px !important;
    }

    /* === PAYMENT MODE BUTTON GRID (2x2) === */
    div[data-testid="stHorizontalBlock"]:has(button) {
        margin: 0 !important;
        padding: 0 !important;
    }

    [data-testid="column"] {
        padding: 0 !important;      /* remove extra space */
        margin: 0 !important;
    }

    .stButton {
        margin-bottom: 2px !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }

    /* === STICKY LOGOUT BUTTON === */
    .logout-bar {
        position: sticky;
        top: 0;
        z-index: 1000;
        background: white;
        padding: 6px 8px;
        display: flex;
        justify-content: flex-end;
    }

    /* ============================================
       FINAL OVERRIDE: LOGIN BUTTONS MUST BE CLICKABLE
       This rule must be LAST to override all others
       ============================================ */
    button[key="login_btn"],
    button[key="register_btn"],
    button[key="create_account_btn"],
    button[key="back_login_btn"],
    [data-testid="column"]:nth-child(1) > div > div > div > button[kind="primary"]:first-of-type,
    [data-testid="column"]:nth-child(2) > div > div > div > button {
        padding: 12px 20px !important;
        font-size: 15px !important;
        min-height: 44px !important;
        margin: 4px 0 !important;
        white-space: normal !important;
    }

    /* Login page text inputs must be readable */
    input[key="login_username"],
    input[key="login_password"],
    input[key="reg_name"],
    input[key="reg_phone"],
    input[key="reg_username"],
    input[key="reg_password"],
    input[key="reg_confirm_password"] {
        font-size: 16px !important;
        padding: 10px !important;
        min-height: 42px !important;
    }

    /* ============================================
       ABSOLUTE FINAL FIX: Ensure login buttons work
       ============================================ */
    /* Login button containers must be visible and clickable */
    [data-testid="column"]:has(button[kind="primary"]) {
        position: relative !important;
        z-index: 100 !important;
        overflow: visible !important;
    }

    /* Login buttons must be fully visible and clickable */
    button[kind="primary"],
    button[data-baseweb="button"] {
        pointer-events: auto !important;
        position: relative !important;
        z-index: 101 !important;
        cursor: pointer !important;
    }


    /* ================================
    FIX HUGE GAP INSIDE WHITE CARD
    ================================ */

    /* MOBILE: force tight 2-column grid */
    @media (max-width: 600px) {
        div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 6px !important;
        }
    }

    /* DESKTOP / LANDSCAPE: stop grid stretching */
    @media (min-width: 601px) {
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            justify-content: space-between !important;
            gap: 8px !important;
        }

        /* Prevent columns from expanding */
        div[data-testid="column"] {
            flex: 0 0 auto !important;
            max-width: 240px !important;   /* 👈 key fix */
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "display_name" not in st.session_state:
    st.session_state.display_name = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "transaction_type" not in st.session_state:
    st.session_state.transaction_type = None
if "payment_mode" not in st.session_state:
    st.session_state.payment_mode = None
if "show_register" not in st.session_state:
    st.session_state.show_register = False
if "show_success" not in st.session_state:
    st.session_state.show_success = False
if "refresh_data" not in st.session_state:
    st.session_state.refresh_data = True
if "transactions_df" not in st.session_state:
    st.session_state.transactions_df = pd.DataFrame()

# Login/Registration section
if not st.session_state.logged_in:
    st.title("Login")

    spreadsheet = get_google_sheet()
    if spreadsheet:
        cred_sheet = get_credentials_sheet(spreadsheet)
        if cred_sheet:
            if not st.session_state.show_register:
                username = st.text_input(
                    "Username", key="login_username", placeholder="Enter your username"
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    key="login_password",
                    placeholder="Enter password",
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "Login",
                        key="login_btn",
                        use_container_width=True,
                        type="primary",
                    ):
                        if username and password:
                            success, role, name = authenticate_user(
                                cred_sheet, username, password
                            )
                            if success:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.display_name = name
                                st.session_state.is_admin = role == "admin"
                                st.session_state.refresh_data = (
                                    True  # Fetch data on login
                                )
                                st.rerun()
                            else:
                                st.error("Invalid username or password")
                        else:
                            st.warning("Please enter username and password")
                with col2:
                    if st.button(
                        "Create Account",
                        key="create_account_btn",
                        use_container_width=True,
                    ):
                        st.session_state.show_register = True
                        st.rerun()
            else:
                st.subheader("Create New Account")
                new_name = st.text_input(
                    "Full Name", key="reg_name", placeholder="Enter your full name"
                )
                new_phone = st.text_input(
                    "Phone Number",
                    key="reg_phone",
                    placeholder="Enter your phone number",
                )
                new_username = st.text_input(
                    "Username", key="reg_username", placeholder="Choose a username"
                )
                new_password = st.text_input(
                    "Password", key="reg_password", placeholder="Choose a password"
                )
                confirm_password = st.text_input(
                    "Confirm Password",
                    key="reg_confirm_password",
                    placeholder="Confirm your password",
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "Register",
                        key="register_btn",
                        use_container_width=True,
                        type="primary",
                    ):
                        if not all([new_name, new_phone, new_username, new_password]):
                            st.error("Please fill all fields")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match")
                        elif len(new_password) < 4:
                            st.error("Password must be at least 4 characters")
                        else:
                            success, message = create_user_account(
                                cred_sheet,
                                new_username,
                                new_password,
                                new_phone,
                                new_name,
                            )
                            if success:
                                st.success(message)
                                st.info("Please login with your new credentials")
                                st.session_state.show_register = False
                                st.rerun()
                            else:
                                st.error(message)
                with col2:
                    if st.button(
                        "Back to Login", key="back_login_btn", use_container_width=True
                    ):
                        st.session_state.show_register = False
                        st.rerun()
        else:
            st.error("Could not access credentials sheet")
    else:
        st.error("Could not connect to Google Sheets")

else:
    # Logout button at top right
    with st.container():
        st.markdown(
            """
        <div class="logout-bar">
        """,
            unsafe_allow_html=True,
        )

        if st.button("Logout", key="logout_btn", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.display_name = ""
            st.session_state.is_admin = False
            st.session_state.transaction_type = None
            st.session_state.payment_mode = None
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    spreadsheet = get_google_sheet()
    if spreadsheet:
        trans_sheet = get_transactions_sheet(spreadsheet)
        if trans_sheet:
            initialize_transactions_sheet(trans_sheet)

            # Only fetch data when refresh_data flag is True
            if st.session_state.refresh_data:
                st.session_state.transactions_df = get_transactions(trans_sheet)
                st.session_state.refresh_data = False

            df = st.session_state.transactions_df
            user_df = df.copy() if not df.empty else df
            if not df.empty and not st.session_state.is_admin:
                user_df = df[df["User"] == st.session_state.username]

            # TODAY'S KPI BOXES - Paid and Received side by side, Balance below
            st.markdown("### Today's Summary")
            today_paid, today_received, today_balance = get_today_stats(
                user_df, st.session_state.username, st.session_state.is_admin
            )

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Paid", f"₹{today_paid:,.0f}")
            with col2:
                st.metric("Received", f"₹{today_received:,.0f}")

            st.metric("Balance", f"₹{today_balance:,.0f}")

            # TABS
            if st.session_state.is_admin:
                tab1, tab2, tab3 = st.tabs(
                    ["New Entry", "Download Statement", "User Summary"]
                )
            else:
                tab1, tab2 = st.tabs(["New Entry", "Download Statement"])

            with tab1:
                st.header("New Entry")

                name = st.text_input(
                    "Name",
                    placeholder="Enter person/vendor name",
                    key="name_field",
                )
                amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.0,
                    step=10.0,
                    format="%.0f",
                    key="amount_field",
                )
                description = st.text_input(
                    "Purpose",
                    placeholder="Add details...",
                    key="desc_field",
                )

                st.subheader("Type")
                # Hardcoded 2 columns for Type buttons
                col1, col2 = st.columns([1, 1])
                with col1:
                    btn_type = (
                        "primary"
                        if st.session_state.transaction_type == "Paid"
                        else "secondary"
                    )
                    if st.button(
                        "PAID",
                        use_container_width=True,
                        type=btn_type,
                        key="btn_paid",
                    ):
                        st.session_state.transaction_type = "Paid"
                        st.rerun()
                with col2:
                    btn_type = (
                        "primary"
                        if st.session_state.transaction_type == "Received"
                        else "secondary"
                    )
                    if st.button(
                        "RECEIVED",
                        use_container_width=True,
                        type=btn_type,
                        key="btn_received",
                    ):
                        st.session_state.transaction_type = "Received"
                        st.rerun()

                # Payment Mode Buttons - Hardcoded 2x2 layout (2 rows, 2 columns)
                st.subheader("Payment Mode")

                # Row 1: Online and GPay
                col1, col2 = st.columns([1, 1])
                with col1:
                    btn_type = (
                        "primary"
                        if st.session_state.payment_mode == "Online"
                        else "secondary"
                    )
                    if st.button(
                        "Online",
                        use_container_width=True,
                        type=btn_type,
                        key="btn_online",
                    ):
                        st.session_state.payment_mode = "Online"
                        st.rerun()
                with col2:
                    btn_type = (
                        "primary"
                        if st.session_state.payment_mode == "GPay"
                        else "secondary"
                    )
                    if st.button(
                        "GPay",
                        use_container_width=True,
                        type=btn_type,
                        key="btn_gpay",
                    ):
                        st.session_state.payment_mode = "GPay"
                        st.rerun()

                # Row 2: PhonePe and Cash
                col3, col4 = st.columns([1, 1])
                with col3:
                    btn_type = (
                        "primary"
                        if st.session_state.payment_mode == "PhonePe"
                        else "secondary"
                    )
                    if st.button(
                        "PhonePe",
                        use_container_width=True,
                        type=btn_type,
                        key="btn_phone",
                    ):
                        st.session_state.payment_mode = "PhonePe"
                        st.rerun()
                with col4:
                    btn_type = (
                        "primary"
                        if st.session_state.payment_mode == "Cash"
                        else "secondary"
                    )
                    if st.button(
                        "Cash",
                        use_container_width=True,
                        type=btn_type,
                        key="btn_cash",
                    ):
                        st.session_state.payment_mode = "Cash"
                        st.rerun()

                st.markdown("")  # spacing

                # Submit button
                if st.button(
                    "Submit Transaction",
                    use_container_width=True,
                    type="primary",
                    key="btn_submit",
                ):
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
                            st.session_state.username,
                        ):
                            st.session_state.show_success = True
                            st.session_state.transaction_type = None
                            st.session_state.payment_mode = None
                            st.session_state.refresh_data = True  # Trigger data refresh
                            # Clear form fields by deleting the keys
                            if "name_field" in st.session_state:
                                del st.session_state.name_field
                            if "amount_field" in st.session_state:
                                del st.session_state.amount_field
                            if "desc_field" in st.session_state:
                                del st.session_state.desc_field
                            st.rerun()

                # Show success message right after submit button
                if st.session_state.show_success:
                    st.success("Transaction submitted successfully!")
                    st.session_state.show_success = False

            with tab2:
                st.header("Download Statement")
                st.write("Select date range to download your statement")
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "Start Date",
                        value=datetime.now().date() - timedelta(days=30),
                        max_value=datetime.now().date(),
                        key="start_date",
                    )
                with col2:
                    end_date = st.date_input(
                        "End Date",
                        value=datetime.now().date(),
                        max_value=datetime.now().date(),
                        key="end_date",
                    )

                if start_date > end_date:
                    st.error("Start date must be before end date")
                else:
                    if not user_df.empty:
                        temp_df = (
                            user_df.copy()
                        )  # Avoid modifying the original dataframe
                        temp_df["Date"] = pd.to_datetime(temp_df["Timestamp"]).dt.date
                        filtered_df = temp_df[
                            (temp_df["Date"] >= start_date)
                            & (temp_df["Date"] <= end_date)
                        ]
                        if not filtered_df.empty:
                            total_paid = filtered_df[filtered_df["Type"] == "Paid"][
                                "Amount"
                            ].sum()
                            total_received = filtered_df[
                                filtered_df["Type"] == "Received"
                            ]["Amount"].sum()
                            balance = total_received - total_paid
                            st.subheader("Summary")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Paid", f"₹{total_paid:,.0f}")
                            with col2:
                                st.metric("Total Received", f"₹{total_received:,.0f}")
                            with col3:
                                st.metric("Net Balance", f"₹{balance:,.0f}")
                            st.markdown("---")
                            st.subheader(f"All Entries ({len(filtered_df)} total)")
                            for idx, row in filtered_df.sort_values(
                                "Timestamp", ascending=False
                            ).iterrows():
                                type_emoji = "" if row["Type"] == "Paid" else ""
                                amount_color = (
                                    "red" if row["Type"] == "Paid" else "green"
                                )
                                desc_value = row.get(
                                    "Description", row.get("Notes", "")
                                )
                                with st.container():
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**{row['Name']}**")
                                        st.caption(
                                            f"{row['Payment Mode']} • {row['Timestamp'].strftime('%d %b %Y %I:%M %p')}"
                                        )
                                        if desc_value:
                                            st.caption(f"{desc_value}")
                                    with col2:
                                        st.markdown(
                                            f"**<span style='color:{amount_color}'>₹{row['Amount']:,.0f}</span>**",
                                            unsafe_allow_html=True,
                                        )
                                    st.markdown("---")
                            pdf_buffer = create_pdf_statement(
                                filtered_df,
                                start_date,
                                end_date,
                                st.session_state.username,
                                st.session_state.is_admin,
                            )
                            st.download_button(
                                label="Download as PDF",
                                data=pdf_buffer,
                                file_name=f"statement_{start_date}_{end_date}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        else:
                            st.info("No entries found in selected date range.")
                    else:
                        st.info("No entries available.")

            if st.session_state.is_admin:
                with tab3:
                    st.header("User Summary")
                    st.write("View summary of all users")
                    col1, col2 = st.columns(2)
                    with col1:
                        admin_start_date = st.date_input(
                            "Start Date",
                            value=datetime.now().date() - timedelta(days=30),
                            max_value=datetime.now().date(),
                            key="admin_start_date",
                        )
                    with col2:
                        admin_end_date = st.date_input(
                            "End Date",
                            value=datetime.now().date(),
                            max_value=datetime.now().date(),
                            key="admin_end_date",
                        )

                    if admin_start_date > admin_end_date:
                        st.error("Start date must be before end date")
                    else:
                        if not df.empty:
                            user_summary_df = get_user_summary(
                                df, admin_start_date, admin_end_date
                            )
                            if not user_summary_df.empty:
                                st.subheader(
                                    f"Summary from {admin_start_date.strftime('%d %b %Y')} to {admin_end_date.strftime('%d %b %Y')}"
                                )
                                st.dataframe(
                                    user_summary_df.style.format(
                                        {
                                            "Paid": "₹{:,.0f}",
                                            "Received": "₹{:,.0f}",
                                            "Balance": "₹{:,.0f}",
                                        }
                                    ),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.markdown("---")
                                st.subheader("Overall Totals")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric(
                                        "Total Paid (All Users)",
                                        f"₹{user_summary_df['Paid'].sum():,.0f}",
                                    )
                                with col2:
                                    st.metric(
                                        "Total Received (All Users)",
                                        f"₹{user_summary_df['Received'].sum():,.0f}",
                                    )
                                with col3:
                                    st.metric(
                                        "Total Balance",
                                        f"₹{user_summary_df['Balance'].sum():,.0f}",
                                    )
                            else:
                                st.info("No transactions found in selected date range.")
                        else:
                            st.info("No transactions available.")
            else:
                st.error("Could not access transactions sheet")
        else:
            st.error(
                "Failed to connect to Google Sheets. Please check your configuration."
            )

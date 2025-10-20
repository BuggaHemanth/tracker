import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime

# ----------------------------
# 1️⃣ PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="Construction Transactions",
    layout="centered",
    initial_sidebar_state="collapsed"
)
st.markdown(
    """
    <style>
    /* Mobile responsive buttons */
    @media (max-width: 600px) {
        .stButton>button {
            width: 100% !important;
            margin-top: 5px;
        }
        .stDownloadButton>button {
            width: 100% !important;
            margin-top: 5px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------
# 2️⃣ LOAD SECRETS & AUTHENTICATE
# ----------------------------
try:
    user_password = st.secrets["user_password"]
    admin_password = st.secrets["admin_password"]
    service_account_info = st.secrets["gcp_service_account"]
except Exception as e:
    st.error("❌ Secrets not found. Please check Streamlit Cloud → Secrets tab.")
    st.stop()

# Google Sheets authentication
try:
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
except Exception as e:
    st.error("❌ Failed to authenticate with Google Cloud credentials.")
    st.stop()

# ----------------------------
# 3️⃣ CONNECT TO GOOGLE SHEET
# ----------------------------
SPREADSHEET_ID = "YOUR_SHEET_ID_HERE"  # 👈 Replace with your actual sheet ID

try:
    sheet = client.open_by_key(SPREADSHEET_ID)
except Exception as e:
    st.error("❌ Could not open Google Sheet. Make sure the service account has edit access.")
    st.stop()

# Ensure sheets exist
for tab in ["credentials", "transactions"]:
    try:
        sheet.worksheet(tab)
    except gspread.exceptions.WorksheetNotFound:
        sheet.add_worksheet(title=tab, rows=100, cols=10)

credentials_ws = sheet.worksheet("credentials")
transactions_ws = sheet.worksheet("transactions")

# ----------------------------
# 4️⃣ LOGIN SECTION
# ----------------------------
st.title("🏗️ Construction Transaction Tracker")

username = st.text_input("Username")
password = st.text_input("Password", type="password")
login_btn = st.button("🔑 Login")

if not login_btn:
    st.stop()

if username == "admin" and password == admin_password:
    role = "admin"
elif password == user_password:
    role = "user"
else:
    st.error("Invalid credentials.")
    st.stop()

st.success(f"Welcome, {username}! You are logged in as {role}.")

# ----------------------------
# 5️⃣ TRANSACTION ENTRY FORM
# ----------------------------
st.subheader("💰 Record a Transaction")

with st.form("txn_form"):
    col1, col2 = st.columns(2)
    with col1:
        txn_type = st.selectbox("Type", ["Paid", "Received"])
        amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
        mode = st.selectbox("Mode", ["Online", "GPay", "PhonePe", "Cash"])
    with col2:
        description = st.text_area("Description")
        date = st.date_input("Date", datetime.now())
    submitted = st.form_submit_button("📥 Submit")

if submitted:
    try:
        transactions_ws.append_row(
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             username, txn_type, amount, mode, description, str(date)]
        )
        st.success("✅ Transaction recorded successfully!")
    except Exception as e:
        st.error("❌ Failed to write to Google Sheet.")

# ----------------------------
# 6️⃣ ADMIN PANEL
# ----------------------------
if role == "admin":
    st.subheader("📊 Admin Panel")

    try:
        df = pd.DataFrame(transactions_ws.get_all_records())
        if not df.empty:
            df["Amount"] = df["Amount"].astype(float)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            total_paid = df.loc[df["Type"] == "Paid", "Amount"].sum()
            total_received = df.loc[df["Type"] == "Received", "Amount"].sum()
            st.metric("Total Paid", f"₹{total_paid:,.0f}")
            st.metric("Total Received", f"₹{total_received:,.0f}")
            st.metric("Balance", f"₹{total_received - total_paid:,.0f}")
            st.dataframe(df)
        else:
            st.info("No transactions yet.")
    except Exception as e:
        st.error("❌ Could not load transactions.")

else:
    st.info("You are logged in as a user. Admin-only dashboard hidden.")

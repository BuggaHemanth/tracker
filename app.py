import streamlit as st
import pandas as pd
import datetime
from google.oauth2 import service_account
import gspread
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
import os

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Construction Transactions", layout="wide")

# ---------- MOBILE RESPONSIVE STYLING ----------
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important;}
    button[kind="primary"], button[kind="secondary"] {
        width: 100% !important;
        margin-top: 6px !important;
        border-radius: 10px !important;
        font-size: 16px !important;
    }
    .stTextInput, .stSelectbox, .stDateInput, .stNumberInput {
        width: 100% !important;
    }
    .stDataFrame {overflow-x: auto !important;}
    h1, h2, h3 {text-align: center !important;}
    </style>
""", unsafe_allow_html=True)

# ---------- READ CONFIG FROM SECRETS ----------
try:
    creds_dict = st.secrets["gcp_service_account"]
    SPREADSHEET_ID = st.secrets["spreadsheet"]["id"]
except Exception as e:
    st.error("❌ Secrets not found. Please set up your .streamlit/secrets.toml file correctly.")
    st.stop()

# ---------- GOOGLE SHEET AUTH ----------
creds = service_account.Credentials.from_service_account_info(creds_dict)
client = gspread.authorize(creds)

try:
    sheet = client.open_by_key(SPREADSHEET_ID)
except Exception as e:
    st.error("Error connecting to Google Sheet. Check Sheet ID & permissions.")
    st.stop()

# ---------- ENSURE WORKSHEETS ----------
for name in ["transactions", "credentials"]:
    try:
        sheet.worksheet(name)
    except:
        sheet.add_worksheet(title=name, rows=1000, cols=20)

transactions_ws = sheet.worksheet("transactions")
credentials_ws = sheet.worksheet("credentials")

# ---------- AUTH ----------
st.title("🏗 Construction Site Transactions")

auth_choice = st.sidebar.radio("Authentication", ["Login", "Register"])

if auth_choice == "Register":
    st.subheader("New User Registration")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    if st.button("Register"):
        if new_user and new_pass:
            creds_data = credentials_ws.get_all_records()
            if any(u["username"] == new_user for u in creds_data):
                st.warning("Username already exists.")
            else:
                credentials_ws.append_row([new_user, new_pass])
                st.success("User registered successfully! Please log in.")
        else:
            st.warning("Enter all fields.")
    st.stop()

# ---------- LOGIN ----------
st.sidebar.subheader("User Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login = st.sidebar.button("Login")

if not login:
    st.stop()

creds_data = credentials_ws.get_all_records()
user_found = next((u for u in creds_data if u["username"] == username and u["password"] == password), None)

if not user_found:
    st.error("Invalid username or password.")
    st.stop()

st.sidebar.success(f"Logged in as {username}")

# ---------- MAIN APP ----------
tab1, tab2, tab3 = st.tabs(["➕ Add Transaction", "📜 Generate Statement", "📊 Admin (All Users)"])

# ---------- TAB 1 ----------
with tab1:
    st.subheader("Add Transaction")

    col1, col2 = st.columns(2)
    with col1:
        txn_type = st.selectbox("Transaction Type", ["Paid", "Received"])
        amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
    with col2:
        mode = st.selectbox("Mode", ["Online", "GPay", "PhonePe", "Cash"])
        remark = st.text_input("Remark")

    date = st.date_input("Date", datetime.date.today())

    if st.button("💾 Save Transaction"):
        if amount <= 0:
            st.warning("Amount must be greater than zero.")
        else:
            transactions_ws.append_row([
                username, str(date), txn_type, amount, mode, remark,
                str(datetime.datetime.now())
            ])
            st.success("Transaction saved successfully!")

# ---------- TAB 2 ----------
with tab2:
    st.subheader("Generate Statement (PDF)")

    user_data = pd.DataFrame(transactions_ws.get_all_records())
    if user_data.empty or username not in user_data["username"].unique():
        st.info("No transactions yet.")
    else:
        df_user = user_data[user_data["username"] == username]

        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
        end_date = st.date_input("End Date", datetime.date.today())

        df_filtered = df_user[
            (pd.to_datetime(df_user["date"]) >= pd.Timestamp(start_date)) &
            (pd.to_datetime(df_user["date"]) <= pd.Timestamp(end_date))
        ]

        if not df_filtered.empty:
            st.dataframe(df_filtered, use_container_width=True)

            total_paid = df_filtered[df_filtered["transaction_type"] == "Paid"]["amount"].sum()
            total_received = df_filtered[df_filtered["transaction_type"] == "Received"]["amount"].sum()
            balance = total_received - total_paid

            st.markdown(f"### 💰 Summary: Paid ₹{total_paid:,.0f} | Received ₹{total_received:,.0f} | Balance ₹{balance:,.0f}")

            if st.button("📄 Generate PDF"):
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                pdf_path = tmp_file.name

                c = canvas.Canvas(pdf_path, pagesize=letter)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(200, 750, "Transaction Statement")
                c.setFont("Helvetica", 12)
                c.drawString(50, 730, f"User: {username}")
                c.drawString(50, 715, f"Date Range: {start_date} to {end_date}")
                c.drawString(50, 700, f"Generated On: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

                y = 670
                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y, "Date")
                c.drawString(120, y, "Type")
                c.drawString(180, y, "Amount")
                c.drawString(250, y, "Mode")
                c.drawString(330, y, "Remark")

                y -= 15
                c.setFont("Helvetica", 9)
                for _, row in df_filtered.iterrows():
                    c.drawString(50, y, str(row["date"]))
                    c.drawString(120, y, row["transaction_type"])
                    c.drawString(180, y, f"{row['amount']:.0f}")
                    c.drawString(250, y, row["mode"])
                    c.drawString(330, y, row["remark"])
                    y -= 12
                    if y < 50:
                        c.showPage()
                        y = 750

                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y - 20, f"Total Paid: ₹{total_paid:,.0f}")
                c.drawString(200, y - 20, f"Total Received: ₹{total_received:,.0f}")
                c.drawString(400, y - 20, f"Balance: ₹{balance:,.0f}")
                c.save()

                with open(pdf_path, "rb") as f:
                    st.download_button("⬇ Download PDF", f, file_name="statement.pdf")
                os.remove(pdf_path)
        else:
            st.info("No transactions found in this period.")

# ---------- TAB 3 ----------
with tab3:
    st.subheader("Admin Dashboard")
    if username.lower() != "admin":
        st.warning("Only admin can access this section.")
    else:
        df_all = pd.DataFrame(transactions_ws.get_all_records())
        if not df_all.empty:
            st.dataframe(df_all, use_container_width=True)
            df_summary = (
                df_all.groupby(["username", "transaction_type"])["amount"].sum().unstack(fill_value=0).reset_index()
            )
            df_summary["Balance"] = df_summary.get("Received", 0) - df_summary.get("Paid", 0)
            st.dataframe(df_summary.style.format({
                "Paid": "₹{:,.0f}",
                "Received": "₹{:,.0f}",
                "Balance": "₹{:,.0f}"
            }), use_container_width=True)
        else:
            st.info("No transactions yet.")

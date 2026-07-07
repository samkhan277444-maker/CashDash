import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="CashDash Ultra", layout="wide", initial_sidebar_state="collapsed")

# ---------- CLEAN LIGHT THEME (PhonePe Style) CSS ----------
st.markdown("""
<style>
    /* Light & Clean Background */
    .stApp {
        background-color: #f5f7fa;
        color: #1e293b;
    }
    /* PhonePe-style Cards */
    .card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a73e8; /* PhonePe Blue Accent */
    }
    .metric-label {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 600;
    }
    /* Custom Buttons */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        background: #1a73e8;
        color: white;
        border: none;
        font-weight: 600;
    }
    .stButton button:hover {
        background: #1557b0;
    }
    /* Clean Inputs */
    .stTextInput input, .stSelectbox div, .stDateInput input {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        background: #ffffff;
    }
    /* Hide Streamlit clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Mobile Adjustments */
    @media (max-width: 768px) {
        .stApp { padding: 0px 10px; }
    }
</style>
""", unsafe_allow_html=True)

# ---------- GOOGLE SHEETS CONNECTION (Cached for speed) ----------
def get_gsheet_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        return None

SHEET_NAME = "CashDash_Ultra_Data"

# Caching data to avoid slow mobile reloads (Updates every 5 mins)
@st.cache_data(ttl=300)
def load_worksheet(ws_name):
    try:
        gc = get_gsheet_client()
        if gc:
            sh = gc.open(SHEET_NAME)
            try:
                ws = sh.worksheet(ws_name)
            except:
                sh.add_worksheet(title=ws_name, rows=200, cols=20)
                ws = sh.worksheet(ws_name)
            records = ws.get_all_records()
            return pd.DataFrame(records) if records else pd.DataFrame()
    except:
        pass
    return pd.DataFrame()

def append_to_worksheet(ws_name, row_data):
    try:
        gc = get_gsheet_client()
        if gc:
            sh = gc.open(SHEET_NAME)
            try:
                ws = sh.worksheet(ws_name)
            except:
                sh.add_worksheet(title=ws_name, rows=200, cols=20)
                ws = sh.worksheet(ws_name)
            ws.append_row(row_data)
    except Exception as e:
        st.warning(f"⚠️ Could not sync to Google Sheet: {e}")

# ---------- SESSION STATE (App Data) ----------
if 'transactions' not in st.session_state:
    st.session_state.transactions = load_worksheet('Transactions')
    if st.session_state.transactions.empty:
        st.session_state.transactions = pd.DataFrame(columns=['Date','Description','Category','Amount','Type','Payment Mode','Status'])

if 'budget' not in st.session_state:
    st.session_state.budget = load_worksheet('BudgetPlanner')
    if st.session_state.budget.empty:
        st.session_state.budget = pd.DataFrame({
            'Category': ['Rent','Groceries','Mobile','EMI','Vegetables'],
            'Budget': [3200,2500,1000,1572,2000],
            'Actual': [3200,2500,1000,0,2000]
        })

if 'accounts' not in st.session_state:
    st.session_state.accounts = load_worksheet('Accounts')
    if st.session_state.accounts.empty:
        st.session_state.accounts = pd.DataFrame({
            'Account': ['BOB','BOM','UPI','Cash'],
            'Balance': [0,0,0,0]
        })

# ---------- HELPER FUNCTIONS ----------
def total_balance():
    return st.session_state.accounts['Balance'].sum()

def format_currency(amount):
    return f"₹ {amount:,.0f}"

# ---------- APP UI ----------
st.markdown("<h2 style='color:#1a73e8; margin-bottom:0;'>💎 CashDash Ultra</h2>", unsafe_allow_html=True)
st.markdown(f"<small style='color:#64748b;'>{datetime.now().strftime('%d %b %Y')}</small>", unsafe_allow_html=True)

# Navigation
nav = st.radio(
    "Navigation",
    ["🏠 Home", "➕ Add", "🎯 Budget", "📊 Reports"],
    index=0,
    horizontal=True,
    label_visibility="collapsed"
)

# ---------- HOME PAGE ----------
if nav == "🏠 Home":
    st.markdown("## 🏠 Dashboard")
    
    # Top Metrics
    total = total_balance()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card" style="text-align:center;">
            <div class="metric-label">Total Balance</div>
            <div class="metric-value" style="color:#1a73e8;">{format_currency(total)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card" style="text-align:center;">
            <div class="metric-label">Recent Expense</div>
            <div class="metric-value" style="color:#e53e3e;">{format_currency(st.session_state.transactions[st.session_state.transactions['Type']=='Expense']['Amount'].sum())}</div>
        </div>
        """, unsafe_allow_html=True)

    # Recent Transactions (Only top 5 for mobile speed)
    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        # Using st.table for lighter performance on mobile
        st.table(recent[['Date','Description','Category','Amount']].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0))
    else:
        st.info("No transactions yet. Add one!")

# ---------- ADD TRANSACTION (Fixed Duplicate Key) ----------
elif nav == "➕ Add":
    st.markdown("## ➕ Add Transaction")
    
    with st.form("add_transaction"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
            description = st.text_input("Description")
            amount = st.number_input("Amount ₹", min_value=0.0, step=100.0)
        with col2:
            category = st.selectbox("Category", ['Salary','Rent','Groceries','EMI','Mobile','Shopping','Others'])
            ttype = st.selectbox("Type", ["Income", "Expense"])
            mode = st.selectbox("Payment Mode", ["UPI","BOB","Cash"])
        
        # Fixed: Added key="submit_btn" to avoid DuplicateElementKey error
        if st.form_submit_button("✅ Add Transaction", key="submit_btn"):
            try:
                new_row = [date.strftime('%Y-%m-%d'), description, category, amount, ttype, mode, '✅']
                new_df = pd.DataFrame({
                    'Date': [date.strftime('%Y-%m-%d')],
                    'Description': [description],
                    'Category': [category],
                    'Amount': [amount],
                    'Type': [ttype],
                    'Payment Mode': [mode],
                    'Status': ['✅']
                })
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                
                # Sync to Google Sheet in background
                append_to_worksheet('Transactions', new_row)
                
                st.success("✅ Transaction Added Successfully!")
                st.rerun() # Refresh to show new data instantly
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ---------- BUDGET PAGE ----------
elif nav == "🎯 Budget":
    st.markdown("## 🎯 Budget Planner")
    df_budget = st.session_state.budget
    df_budget['Remaining'] = df_budget['Budget'] - df_budget['Actual']
    st.dataframe(df_budget, use_container_width=True, hide_index=True)

# ---------- REPORTS PAGE ----------
elif nav == "📊 Reports":
    st.markdown("## 📊 Quick Insights")
    if not st.session_state.transactions.empty:
        df = st.session_state.transactions
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Monthly Income vs Expense
        df['Month'] = df['Date'].dt.month_name()
        summary = df.groupby(['Month', 'Type'])['Amount'].sum().reset_index()
        
        fig = px.bar(summary, x='Month', y='Amount', color='Type', barmode='group', 
                     color_discrete_map={'Income': '#1a73e8', 'Expense': '#e53e3e'})
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f5f7fa')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add some transactions to see reports.")

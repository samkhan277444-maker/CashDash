# =========================================================
# CashDash Ultra Pro – Full Feature App (Streamlit Cloud)
# =========================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="CashDash Ultra Pro", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .card { background: #1f1f2e; border-radius: 16px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #00d4ff; }
    .metric-label { font-size: 0.85rem; color: #888; }
    @media (max-width: 768px) { .stButton button { font-size: 16px; } }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

SHEET_NAME = "CashDash_Ultra_Data"

def load_worksheet(ws_name):
    try:
        gc = get_gsheet_client()
        sh = gc.open(SHEET_NAME)
        try:
            ws = sh.worksheet(ws_name)
        except:
            sh.add_worksheet(title=ws_name, rows=200, cols=20)
            ws = sh.worksheet(ws_name)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except:
        return pd.DataFrame()

def append_to_worksheet(ws_name, row_data):
    try:
        gc = get_gsheet_client()
        sh = gc.open(SHEET_NAME)
        try:
            ws = sh.worksheet(ws_name)
        except:
            sh.add_worksheet(title=ws_name, rows=200, cols=20)
            ws = sh.worksheet(ws_name)
        ws.append_row(row_data)
    except Exception as e:
        st.warning(f"Google Sheet sync failed: {e}")

def update_worksheet(ws_name, df):
    try:
        gc = get_gsheet_client()
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(ws_name)
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.warning(f"Google Sheet update failed: {e}")

if 'transactions' not in st.session_state:
    st.session_state.transactions = load_worksheet('Transactions')
    if st.session_state.transactions.empty:
        st.session_state.transactions = pd.DataFrame(columns=['Date','Description','Category','Amount','Type','Payment Mode','Status'])

if 'budget' not in st.session_state:
    st.session_state.budget = load_worksheet('BudgetPlanner')
    if st.session_state.budget.empty:
        st.session_state.budget = pd.DataFrame({
            'Category': ['Rent','Groceries','Vegetables','Mobile','EMI','Entertainment','Shopping','Baby','Education','Fuel'],
            'Budget': [3200,2500,2000,1000,1572,1000,1000,2000,500,1500],
            'Actual': [3200,2500,2000,1000,0,1200,500,0,0,800]
        })

if 'accounts' not in st.session_state:
    st.session_state.accounts = load_worksheet('Accounts')
    if st.session_state.accounts.empty:
        st.session_state.accounts = pd.DataFrame({
            'Account': ['Cash','BOB Savings','BOM Savings','PhonePe','Google Pay','Paytm'],
            'Balance': [0,0,0,0,0,0]
        })

def total_balance():
    return st.session_state.accounts['Balance'].sum()

def net_worth():
    assets = total_balance()
    liabilities = st.session_state.budget['Actual'].sum() - st.session_state.budget['Budget'].sum()
    return assets - max(0, liabilities)

def get_monthly_summary():
    df = st.session_state.transactions
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.month_name()
    income = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
    expense = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
    return income, expense

def format_currency(amount):
    return f"₹ {amount:,.0f}"

st.markdown("<h1 style='color:#00d4ff;'>💎 CashDash Ultra Pro</h1>", unsafe_allow_html=True)
st.markdown(f"📅 {datetime.now().strftime('%d %b %Y')}")

nav = st.radio("Navigation", ["🏠 Home", "➕ Add", "🎯 Budget", "🏧 Bank", "⚡ More"], index=0, horizontal=True)

if nav == "🏠 Home":
    st.markdown("## 🏠 Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='card' style='text-align:center;'><div class='metric-label'>Total Balance</div><div class='metric-value'>{format_currency(total_balance())}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='card' style='text-align:center;'><div class='metric-label'>Net Worth</div><div class='metric-value' style='color:#ffaa00;'>{format_currency(net_worth())}</div></div>", unsafe_allow_html=True)
    with col3:
        inc, exp = get_monthly_summary()
        month_inc = inc[inc['Month']==datetime.now().strftime('%B')]['Amount'].sum() if not inc.empty else 0
        st.markdown(f"<div class='card' style='text-align:center;'><div class='metric-label'>Income</div><div class='metric-value' style='color:#4caf50;'>{format_currency(month_inc)}</div></div>", unsafe_allow_html=True)
    with col4:
        inc, exp = get_monthly_summary()
        month_exp = exp[exp['Month']==datetime.now().strftime('%B')]['Amount'].sum() if not exp.empty else 0
        st.markdown(f"<div class='card' style='text-align:center;'><div class='metric-label'>Expense</div><div class='metric-value' style='color:#f44336;'>{format_currency(month_exp)}</div></div>", unsafe_allow_html=True)

    st.markdown("### ⚡ Quick Actions")
    cola, colb = st.columns(2)
    with cola:
        st.button("➕ Add Income/Expense", use_container_width=True)
    with colb:
        st.button("📊 Reports", use_container_width=True)

    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        st.dataframe(recent[['Date','Description','Category','Amount','Type']], use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet. Add one!")

elif nav == "➕ Add":
    st.markdown("## ➕ Add Transaction")
    with st.form("add_transaction"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
            description = st.text_input("Description")
            amount = st.number_input("Amount ₹", min_value=0.0, step=100.0)
        with col2:
            category = st.selectbox("Category", ['Salary','Rent','Groceries','Vegetables','EMI','Mobile','Fuel','Entertainment','Shopping','Baby','Education','Others'])
            ttype = st.selectbox("Type", ["Income", "Expense"])
            payment_mode = st.selectbox("Payment Mode", ["UPI","BOB","BOM","Cash","PhonePe","GPay","Paytm"])
        
        if st.form_submit_button("✅ Add Transaction"):
            try:
                # 1. Local Data में Save करो (ताकि कम से कम काम तो हो)
                new_row = [date.strftime('%Y-%m-%d'), description, category, amount, ttype, payment_mode, '✅']
                new_df = pd.DataFrame({
                    'Date': [date.strftime('%Y-%m-%d')],
                    'Description': [description],
                    'Category': [category],
                    'Amount': [amount],
                    'Type': [ttype],
                    'Payment Mode': [payment_mode],
                    'Status': ['✅']
                })
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                
                # 2. Google Sheet में Sync करने की कोशिश करो
                append_to_worksheet('Transactions', new_row)
                st.success("✅ Transaction Added & Synced to Google Sheet!")
                
            except Exception as e:
                # अगर गूगल शीट फेल होती है, तो Error दिखाओ और बताओ कि Data Local में सेव है
                st.error(f"❌ Google Sheet Sync Failed! Error: {e}")
                st.warning("⚠️ Don't worry! Transaction is saved locally in your app. Please check your Secrets (JSON format) or Internet.")
            
            # 3. App को Refresh करो ताकि Transaction List में तुरंत दिखे
            st.rerun()
        if st.form_submit_button("✅ Add Transaction"):
            new_row = [date.strftime('%Y-%m-%d'), description, category, amount, ttype, payment_mode, '✅']
            new_df = pd.DataFrame({
                'Date': [date.strftime('%Y-%m-%d')],
                'Description': [description],
                'Category': [category],
                'Amount': [amount],
                'Type': [ttype],
                'Payment Mode': [payment_mode],
                'Status': ['✅']
            })
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
            append_to_worksheet('Transactions', new_row)
            st.success("Transaction Added!")
            st.rerun()

elif nav == "🎯 Budget":
    st.markdown("## 🎯 Budget Planner")
    df_budget = st.session_state.budget
    df_budget['Remaining'] = df_budget['Budget'] - df_budget['Actual']
    df_budget['Progress'] = (df_budget['Actual'] / df_budget['Budget']).clip(0,1)
    df_budget['Status'] = df_budget.apply(lambda row: "⚠️ Over" if row['Actual'] > row['Budget'] else "✅ On Track", axis=1)
    st.dataframe(df_budget, use_container_width=True, hide_index=True)

elif nav == "🏧 Bank":
    st.markdown("## 🏧 My Accounts")
    st.dataframe(st.session_state.accounts, use_container_width=True, hide_index=True)
    st.markdown("### 💰 Update Account Balance")
    account = st.selectbox("Select Account", st.session_state.accounts['Account'])
    add_amt = st.number_input("Add/Subtract Amount ₹", min_value=-999999.0, step=100.0)
    if st.button("Update Balance"):
        st.session_state.accounts.loc[st.session_state.accounts['Account']==account, 'Balance'] += add_amt
        update_worksheet('Accounts', st.session_state.accounts)
        st.success(f"Balance updated for {account}")
        st.rerun()

elif nav == "⚡ More":
    st.markdown("## 🚀 Premium Features")
    tabs = st.tabs(["📊 Reports", "🏦 EMI", "👶 Baby", "⛽ Fuel", "🧾 Bills"])
    with tabs[0]:
        st.markdown("### 📊 Reports")
        inc, exp = get_monthly_summary()
        if not inc.empty and not exp.empty:
            merged = pd.merge(inc, exp, on='Month', how='outer').fillna(0)
            merged.columns = ['Month','Income','Expense']
            merged['Savings'] = merged['Income'] - merged['Expense']
            fig = px.bar(merged, x='Month', y=['Income','Expense','Savings'], barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="CashDash of Riyaz Pathan", layout="wide", initial_sidebar_state="collapsed")

# ---------- MOBILE-OPTIMIZED CSS ----------
st.markdown("""
<style>
    .stApp { background-color: #f1f3f6; color: #1e293b; }
    .sheet-card {
        background: #ffffff;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
        min-width: 100px;
    }
    .sheet-card-header {
        color: #64748b;
        font-size: 0.7rem;
        font-weight: 600;
        margin-bottom: 2px;
        text-transform: uppercase;
    }
    .sheet-card-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f172a;
    }
    .sheet-card-sub {
        font-size: 0.6rem;
        color: #94a3b8;
        margin-top: 2px;
    }
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        border: none;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    /* Mobile responsiveness: auto-stack columns */
    @media (max-width: 768px) {
        .sheet-card { min-width: 70px; padding: 8px; }
        .sheet-card-value { font-size: 1.1rem; }
        .stColumns { flex-wrap: wrap !important; }
        .stColumn { flex: 1 1 45% !important; min-width: 70px; }
    }
    @media (max-width: 480px) {
        .stColumn { flex: 1 1 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# ---------- GOOGLE SHEET CONNECTION (CACHED FOR 1 HOUR) ----------
SHEET_NAME = "CashDash" 

def get_gsheet_client():
    try:
        secret_content = st.secrets["gcp_service_account"]
        secret_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', secret_content)
        if isinstance(secret_content, str):
            secret_content = json.loads(secret_content)
        creds = Credentials.from_service_account_info(
            secret_content,
            scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}. Please check your Secrets JSON format and Sheet permissions.")
        return None

# ---------- SINGLE CACHED DATA LOAD (QUOTA FIX) ----------
@st.cache_data(ttl=3600)  # 1 hour cache to avoid 429 quota errors
def load_all_sheets():
    gc = get_gsheet_client()
    if gc is None:
        return {}
    
    data = {}
    worksheet_names = ['Transactions', 'Budget', 'Accounts', 'Investments', 'EmiManager', 
                       'Goals', 'BabyTracker', 'FuelTracker', 'Bills', 'Insurance', 'Assets']
    
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ Google Sheet named '{SHEET_NAME}' not found in your Drive. Please create it with this exact name.")
        return {}
    
    for ws_name in worksheet_names:
        try:
            ws = sh.worksheet(ws_name)
            records = ws.get_all_records()
            data[ws_name] = pd.DataFrame(records) if records else pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            # Create if not exists
            sh.add_worksheet(title=ws_name, rows=200, cols=20)
            ws = sh.worksheet(ws_name)
            data[ws_name] = pd.DataFrame()
        except Exception as e:
            st.warning(f"⚠️ Could not load {ws_name}: {e}")
            data[ws_name] = pd.DataFrame()
    
    return data

def append_to_worksheet(ws_name, row_data):
    gc = get_gsheet_client()
    if gc is None:
        st.error("❌ Data not synced to Google Sheet (Connection Issue). But saved locally.")
        return
    try:
        sh = gc.open(SHEET_NAME)
        try:
            ws = sh.worksheet(ws_name)
        except:
            sh.add_worksheet(title=ws_name, rows=200, cols=20)
            ws = sh.worksheet(ws_name)
        ws.append_row(row_data)
    except Exception as e:
        st.error(f"❌ Error syncing: {e}")

def update_worksheet(ws_name, df):
    gc = get_gsheet_client()
    if gc is None: return
    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(ws_name)
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.warning(f"⚠️ Update failed: {e}")

# ---------- SESSION STATE (Fallback to cache) ----------
def init_session_state():
    # Load all data at once into session state
    if 'data_loaded' not in st.session_state:
        all_data = load_all_sheets()
        st.session_state.data_loaded = True
    else:
        # Use cached data, but allow local updates
        pass
    
    # Initialize dataframes if not present, using cached data as fallback
    if 'transactions' not in st.session_state:
        all_data = load_all_sheets()
        st.session_state.transactions = all_data.get('Transactions', pd.DataFrame(columns=['Date','Description','Category','Amount','Type','Payment Mode','Status']))
        st.session_state.budget = all_data.get('Budget', pd.DataFrame({
            'Category': ['Rent','Groceries','Vegetables','Mobile','EMI','Entertainment','Shopping','Baby','Education','Fuel','Investment'],
            'Current Month Budget': [3200,2500,2000,1000,1572,1000,1000,2000,500,1500,500],
            'Previous Month Budget': [3200,2500,2000,1000,1572,1000,1000,2000,500,1500,500],
            'Actual This Month': [3200,2500,2000,1000,0,1200,500,0,0,800,0]
        }))
        st.session_state.accounts = all_data.get('Accounts', pd.DataFrame({
            'Account': ['BOB - UPI', 'BOM - UPI', 'PhonePe Wallet', 'Cash'],
            'Balance': [0,0,0,0]
        }))
        st.session_state.investments = all_data.get('Investments', pd.DataFrame(columns=['Name','Type','Amount','Frequency','Total Invested','Current Value']))
        st.session_state.emi = all_data.get('EmiManager', pd.DataFrame(columns=['Loan Name','Total Loan','EMI Amount','Remaining','Months Left']))
        st.session_state.goals = all_data.get('Goals', pd.DataFrame(columns=['Goal Name', 'Target', 'Saved']))
        st.session_state.baby = all_data.get('BabyTracker', pd.DataFrame(columns=['Category', 'Budget', 'This Month']))
        st.session_state.fuel = all_data.get('FuelTracker', pd.DataFrame(columns=['Date', 'Distance (km)', 'Fuel (L)', 'Cost (₹)']))
        st.session_state.bills = all_data.get('Bills', pd.DataFrame(columns=['Bill Name', 'Amount', 'Due Date', 'Status']))
        st.session_state.insurance = all_data.get('Insurance', pd.DataFrame(columns=['Type', 'Premium', 'Renewal Date']))
        st.session_state.assets = all_data.get('Assets', pd.DataFrame(columns=['Asset Name', 'Value (₹)', 'Warranty']))

init_session_state()

if 'page' not in st.session_state:
    st.session_state.page = "🏠 Home"
if 'add_type' not in st.session_state:
    st.session_state.add_type = "Income"

# ---------- HELPER FUNCTIONS ----------
def format_currency(amount):
    return f"₹ {amount:,.0f}"

def total_balance():
    return st.session_state.accounts['Balance'].sum()

def get_monthly_summary():
    df = st.session_state.transactions
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.month_name()
    inc = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
    exp = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
    return inc, exp

# ---------- APP UI ----------
st.markdown("<h2 style='color:#1e293b; margin-bottom:0;'>💎 CashDash of Riyaz Pathan</h2>", unsafe_allow_html=True)
st.markdown(f"<div style='color:#64748b; font-size:0.8rem;'>🕌 Assalamu Alaikum! | 📅 {datetime.now().strftime('%d %b %Y')} | 📆 Salary Cycle 10th → 9th</div>", unsafe_allow_html=True)

# Navigation
nav = st.radio(
    "Menu",
    ["🏠 Home", "➕ Add", "🎯 Budget", "🏦 Bank", "⚡ More"],
    index=0, horizontal=True, key='nav_radio'
)
st.session_state.page = nav

# ===================== HOME =====================
if st.session_state.page == "🏠 Home":
    st.markdown("## 📊 Dashboard")
    
    current_month = datetime.now().strftime('%B')
    df_tx = st.session_state.transactions
    
    total_bal = total_balance()
    bank_bal = st.session_state.accounts.loc[st.session_state.accounts['Account'].isin(['BOB - UPI', 'BOM - UPI']), 'Balance'].sum()
    upi_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='PhonePe Wallet', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
    cash_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='Cash', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
    emi_due = st.session_state.emi['EMI Amount'].sum() if not st.session_state.emi.empty else 0
    net_worth = total_bal + st.session_state.investments['Current Value'].sum() - emi_due
    
    monthly_inc = 0
    monthly_exp = 0
    if not df_tx.empty:
        df_tx['Date'] = pd.to_datetime(df_tx['Date'])
        df_month = df_tx[df_tx['Date'].dt.month_name() == current_month]
        monthly_inc = df_month[df_month['Type']=='Income']['Amount'].sum()
        monthly_exp = df_month[df_month['Type']=='Expense']['Amount'].sum()
    
    savings = monthly_inc - monthly_exp
    total_budget = st.session_state.budget['Current Month Budget'].sum()
    budget_left = total_budget - monthly_exp
    today_txns = df_tx[df_tx['Date'] == datetime.now().strftime('%Y-%m-%d')].shape[0] if not df_tx.empty else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>💰 Total Balance</div><div class='sheet-card-value'>{format_currency(total_bal)}</div><div class='sheet-card-sub'>{'0%' if savings==0 else '📈 Positive' if savings>0 else '📉 Negative'}</div></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🏦 Bank</div><div class='sheet-card-value'>{format_currency(bank_bal)}</div><div class='sheet-card-sub'>BOB + BOM</div></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📱 UPI</div><div class='sheet-card-value'>{format_currency(upi_bal)}</div><div class='sheet-card-sub'>PhonePe</div></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📉 EMI Due</div><div class='sheet-card-value' style='color:#ef4444;'>{format_currency(emi_due)}</div><div class='sheet-card-sub'>{len(st.session_state.emi)} Active Loans</div></div>", unsafe_allow_html=True)
    with col5: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📊 Net Worth</div><div class='sheet-card-value' style='color:#3b82f6;'>{format_currency(net_worth)}</div><div class='sheet-card-sub'>Assets - Liabilities</div></div>", unsafe_allow_html=True)

    col6, col7, col8, col9, col10 = st.columns(5)
    with col6: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📈 Income</div><div class='sheet-card-value' style='color:#10b981;'>{format_currency(monthly_inc)}</div><div class='sheet-card-sub'>This Month</div></div>", unsafe_allow_html=True)
    with col7: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📉 Expenses</div><div class='sheet-card-value' style='color:#ef4444;'>{format_currency(monthly_exp)}</div><div class='sheet-card-sub'>This Month</div></div>", unsafe_allow_html=True)
    with col8: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>💎 Savings</div><div class='sheet-card-value' style='color:#f59e0b;'>{format_currency(savings)}</div><div class='sheet-card-sub'>{ f'{(savings/monthly_inc)*100:.0f}%' if monthly_inc>0 else '0%' }</div></div>", unsafe_allow_html=True)
    with col9: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🎯 Budget Left</div><div class='sheet-card-value' style='color:#3b82f6;'>{format_currency(budget_left)}</div><div class='sheet-card-sub'>from {format_currency(total_budget)}</div></div>", unsafe_allow_html=True)
    with col10: st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>⚡ Today</div><div class='sheet-card-value'>{today_txns}</div><div class='sheet-card-sub'>{'txns' if today_txns>0 else 'No txns yet'}</div></div>", unsafe_allow_html=True)

    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(10)
    if not recent.empty:
        st.table(recent[['Date','Description','Category','Amount','Type']].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0))
    else:
        st.info("No transactions yet.")

# ===================== ADD TRANSACTION =====================
elif st.session_state.page == "➕ Add":
    st.subheader("➕ Add Transaction")
    
    default_type = st.session_state.get('add_type', 'Income')
    base_cats = ['Salary','Rent','Groceries','Vegetables','EMI','Mobile','Fuel','Entertainment','Shopping','Baby','Education','Investment','Others']
    
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            desc = st.text_input("Description")
            amount = st.number_input("Amount ₹", min_value=0.0)
        with col2:
            category = st.selectbox("Category", base_cats)
            ttype = st.selectbox("Type", ["Income", "Expense", "Investment"], index=["Income", "Expense", "Investment"].index(default_type))
            payment_mode = st.selectbox("Payment Mode", ["BOB - UPI", "BOM - UPI", "PhonePe Wallet", "Cash"])
        
        if st.form_submit_button("✅ Add Transaction", key="submit_btn"):
            try:
                new_row = [date.strftime('%Y-%m-%d'), desc, category, amount, ttype, payment_mode, '✅']
                new_df = pd.DataFrame([{
                    'Date': date.strftime('%Y-%m-%d'), 'Description': desc, 'Category': category,
                    'Amount': amount, 'Type': ttype, 'Payment Mode': payment_mode, 'Status': '✅'
                }])
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                append_to_worksheet('Transactions', new_row)
                
                # Clear cache so new data appears, but keep API calls low
                st.cache_data.clear()
                st.success("✅ Transaction Saved Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

    # Delete Transaction
    st.markdown("---")
    st.markdown("### 🗑️ Delete a Transaction")
    if not st.session_state.transactions.empty:
        df_del = st.session_state.transactions.copy()
        df_del['Display'] = df_del['Date'].astype(str).fillna('') + " | " + df_del['Description'].astype(str).fillna('') + " | ₹" + df_del['Amount'].astype(str).fillna('0')
        to_delete = st.selectbox("Select transaction to delete", df_del['Display'])
        if st.button("🗑️ Delete Selected Transaction"):
            idx = df_del[df_del['Display'] == to_delete].index[0]
            st.session_state.transactions = st.session_state.transactions.drop(idx).reset_index(drop=True)
            update_worksheet('Transactions', st.session_state.transactions)
            st.cache_data.clear()
            st.success("✅ Transaction Deleted successfully!")
            st.rerun()
    else:
        st.info("No transactions available to delete.")

# ===================== BUDGET =====================
elif st.session_state.page == "🎯 Budget":
    st.subheader("🎯 Budget Planner (Monthly)")
    
    df = st.session_state.budget
    df['Diff'] = df['Current Month Budget'] - df['Previous Month Budget']
    df['Progress'] = (df['Actual This Month'] / df['Current Month Budget'] * 100).fillna(0).round(1)
    st.dataframe(df.style.format({
        'Current Month Budget': '₹ {:.0f}', 'Previous Month Budget': '₹ {:.0f}',
        'Actual This Month': '₹ {:.0f}', 'Diff': '₹ {:.0f}', 'Progress': '{:.1f}%'
    }), use_container_width=True, hide_index=True)

    with st.expander("✏️ Add / Edit Budget Category"):
        new_cat = st.text_input("New Category Name (Leave blank to edit existing)")
        sel_cat = st.selectbox("Or select existing", df['Category'].tolist() + ["New"])
        
        curr = st.number_input("Current Month Budget ₹", min_value=0.0, step=100.0)
        prev = st.number_input("Previous Month Budget ₹", min_value=0.0, step=100.0)
        actual = st.number_input("Actual This Month ₹", min_value=0.0, step=100.0)
        
        if st.button("Save / Update Budget"):
            if new_cat:
                new_row = pd.DataFrame({'Category':[new_cat], 'Current Month Budget':[curr], 'Previous Month Budget':[prev], 'Actual This Month':[actual]})
                st.session_state.budget = pd.concat([st.session_state.budget, new_row], ignore_index=True)
            else:
                idx = df[df['Category'] == sel_cat].index
                if not idx.empty:
                    st.session_state.budget.loc[idx, 'Current Month Budget'] = curr
                    st.session_state.budget.loc[idx, 'Previous Month Budget'] = prev
                    st.session_state.budget.loc[idx, 'Actual This Month'] = actual
            update_worksheet('Budget', st.session_state.budget)
            st.cache_data.clear()
            st.success("Budget Updated!")
            st.rerun()

# ===================== BANK =====================
elif st.session_state.page == "🏦 Bank":
    st.subheader("🏦 My Accounts")
    st.dataframe(st.session_state.accounts.style.format({'Balance': '₹ {:.0f}'}), use_container_width=True, hide_index=True)
    with st.expander("💰 Update Balance"):
        acc = st.selectbox("Select Account", st.session_state.accounts['Account'])
        amt = st.number_input("Add/Subtract Amount ₹", step=100.0)
        if st.button("Update"):
            st.session_state.accounts.loc[st.session_state.accounts['Account']==acc, 'Balance'] += amt
            update_worksheet('Accounts', st.session_state.accounts)
            st.cache_data.clear()
            st.success("Balance Updated!")
            st.rerun()

# ===================== MORE (PREMIUM MODULES) =====================
elif st.session_state.page == "⚡ More":
    st.subheader("🚀 Premium Modules (Full Tracking)")
    tabs = st.tabs(["📈 Investments", "🏦 EMI", "🎯 Goals", "👶 Baby", "⛽ Fuel", "🧾 Bills", "🛡️ Insurance", "📦 Assets", "📊 Reports"])
    
    # 1. Investments
    with tabs[0]:
        st.dataframe(st.session_state.investments, hide_index=True, use_container_width=True)
        with st.expander("➕ Add / Edit Investment"):
            inv_name = st.text_input("Investment Name")
            inv_type = st.selectbox("Type", ["SIP", "Gold", "MF", "Stock", "Other"])
            freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
            amt = st.number_input("Amount ₹", min_value=0.0)
            invested = st.number_input("Total Invested So Far ₹", min_value=0.0)
            curr = st.number_input("Current Value ₹", min_value=0.0)
            if st.button("Save Investment"):
                new_inv = pd.DataFrame({'Name':[inv_name], 'Type':[inv_type], 'Amount':[amt], 'Frequency':[freq], 'Total Invested':[invested], 'Current Value':[curr]})
                st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                update_worksheet('Investments', st.session_state.investments)
                st.cache_data.clear()
                st.success("Investment Saved!")
                st.rerun()
        if not st.session_state.investments.empty:
            inv_del = st.selectbox("Select Investment to Delete", st.session_state.investments['Name'])
            if st.button("🗑️ Delete Selected Investment"):
                idx = st.session_state.investments[st.session_state.investments['Name'] == inv_del].index[0]
                st.session_state.investments = st.session_state.investments.drop(idx).reset_index(drop=True)
                update_worksheet('Investments', st.session_state.investments)
                st.cache_data.clear()
                st.success("Investment Deleted!")
                st.rerun()

    # 2. EMI
    with tabs[1]:
        st.dataframe(st.session_state.emi, hide_index=True, use_container_width=True)
        with st.expander("➕ Add EMI"):
            loan = st.text_input("Loan Name")
            total = st.number_input("Total Loan ₹", min_value=0.0)
            emi = st.number_input("EMI per Month ₹", min_value=0.0)
            remaining = st.number_input("Remaining Balance ₹", min_value=0.0)
            months = st.number_input("Months Left", min_value=0)
            if st.button("Save EMI"):
                new_emi = pd.DataFrame({'Loan Name':[loan], 'Total Loan':[total], 'EMI Amount':[emi], 'Remaining':[remaining], 'Months Left':[months]})
                st.session_state.emi = pd.concat([st.session_state.emi, new_emi], ignore_index=True)
                update_worksheet('EmiManager', st.session_state.emi)
                st.cache_data.clear()
                st.success("EMI Saved!")
                st.rerun()
        if not st.session_state.emi.empty:
            emi_del = st.selectbox("Select EMI to Delete", st.session_state.emi['Loan Name'])
            if st.button("🗑️ Delete Selected EMI"):
                idx = st.session_state.emi[st.session_state.emi['Loan Name'] == emi_del].index[0]
                st.session_state.emi = st.session_state.emi.drop(idx).reset_index(drop=True)
                update_worksheet('EmiManager', st.session_state.emi)
                st.cache_data.clear()
                st.success("EMI Deleted!")
                st.rerun()

    # 3. Goals
    with tabs[2]:
        st.dataframe(st.session_state.goals, hide_index=True, use_container_width=True)
        with st.form("add_goal"):
            g_name = st.text_input("Goal Name")
            g_target = st.number_input("Target ₹", min_value=1)
            g_saved = st.number_input("Saved ₹", min_value=0)
            if st.form_submit_button("Add Goal"):
                new_goal = pd.DataFrame({'Goal Name':[g_name], 'Target':[g_target], 'Saved':[g_saved]})
                st.session_state.goals = pd.concat([st.session_state.goals, new_goal], ignore_index=True)
                update_worksheet('Goals', st.session_state.goals)
                st.cache_data.clear()
                st.success("Goal Added!")
                st.rerun()
        if not st.session_state.goals.empty:
            g_del = st.selectbox("Select Goal to Delete", st.session_state.goals['Goal Name'])
            if st.button("🗑️ Delete Selected Goal"):
                idx = st.session_state.goals[st.session_state.goals['Goal Name'] == g_del].index[0]
                st.session_state.goals = st.session_state.goals.drop(idx).reset_index(drop=True)
                update_worksheet('Goals', st.session_state.goals)
                st.cache_data.clear()
                st.success("Goal Deleted!")
                st.rerun()

    # 4. Baby
    with tabs[3]:
        st.dataframe(st.session_state.baby, hide_index=True, use_container_width=True)
        with st.form("add_baby"):
            baby_cat = st.text_input("Category Name")
            baby_budget = st.number_input("Budget ₹", min_value=0.0)
            baby_actual = st.number_input("This Month ₹", min_value=0.0)
            if st.form_submit_button("Add Baby Category"):
                new_baby = pd.DataFrame({'Category':[baby_cat], 'Budget':[baby_budget], 'This Month':[baby_actual]})
                st.session_state.baby = pd.concat([st.session_state.baby, new_baby], ignore_index=True)
                update_worksheet('BabyTracker', st.session_state.baby)
                st.cache_data.clear()
                st.success("Baby Category Added!")
                st.rerun()
        if not st.session_state.baby.empty:
            baby_del = st.selectbox("Select Category to Delete", st.session_state.baby['Category'])
            if st.button("🗑️ Delete Selected Category"):
                idx = st.session_state.baby[st.session_state.baby['Category'] == baby_del].index[0]
                st.session_state.baby = st.session_state.baby.drop(idx).reset_index(drop=True)
                update_worksheet('BabyTracker', st.session_state.baby)
                st.cache_data.clear()
                st.success("Category Deleted!")
                st.rerun()

    # 5. Fuel
    with tabs[4]:
        st.dataframe(st.session_state.fuel, hide_index=True, use_container_width=True)
        with st.form("add_fuel"):
            f_date = st.date_input("Date")
            f_dist = st.number_input("Distance (km)", min_value=0.0)
            f_fuel = st.number_input("Fuel (L)", min_value=0.0)
            f_cost = st.number_input("Cost ₹", min_value=0.0)
            if st.form_submit_button("Add Fuel Entry"):
                new_fuel = pd.DataFrame({'Date':[f_date.strftime('%Y-%m-%d')], 'Distance (km)':[f_dist], 'Fuel (L)':[f_fuel], 'Cost (₹)':[f_cost]})
                st.session_state.fuel = pd.concat([st.session_state.fuel, new_fuel], ignore_index=True)
                update_worksheet('FuelTracker', st.session_state.fuel)
                st.cache_data.clear()
                st.success("Fuel Entry Added!")
                st.rerun()
        if not st.session_state.fuel.empty:
            f_del = st.selectbox("Select Entry to Delete", st.session_state.fuel['Date'].astype(str) + " - " + st.session_state.fuel['Distance (km)'].astype(str) + "km")
            if st.button("🗑️ Delete Selected Fuel Entry"):
                idx = st.session_state.fuel[st.session_state.fuel['Date'].astype(str) + " - " + st.session_state.fuel['Distance (km)'].astype(str) + "km" == f_del].index[0]
                st.session_state.fuel = st.session_state.fuel.drop(idx).reset_index(drop=True)
                update_worksheet('FuelTracker', st.session_state.fuel)
                st.cache_data.clear()
                st.success("Fuel Entry Deleted!")
                st.rerun()

    # 6. Bills
    with tabs[5]:
        st.dataframe(st.session_state.bills, hide_index=True, use_container_width=True)
        with st.form("add_bill"):
            bill_name = st.text_input("Bill Name")
            bill_amt = st.number_input("Amount ₹", min_value=0.0)
            bill_due = st.date_input("Due Date")
            bill_status = st.selectbox("Status", ["Paid", "Pending"])
            if st.form_submit_button("Add Bill"):
                new_bill = pd.DataFrame({'Bill Name':[bill_name], 'Amount':[bill_amt], 'Due Date':[bill_due.strftime('%Y-%m-%d')], 'Status':[bill_status]})
                st.session_state.bills = pd.concat([st.session_state.bills, new_bill], ignore_index=True)
                update_worksheet('Bills', st.session_state.bills)
                st.cache_data.clear()
                st.success("Bill Added!")
                st.rerun()

    # 7. Insurance
    with tabs[6]:
        st.dataframe(st.session_state.insurance, hide_index=True, use_container_width=True)
        with st.form("add_insurance"):
            ins_type = st.text_input("Insurance Type")
            ins_prem = st.number_input("Premium ₹", min_value=0.0)
            ins_renew = st.date_input("Renewal Date")
            if st.form_submit_button("Add Insurance"):
                new_ins = pd.DataFrame({'Type':[ins_type], 'Premium':[ins_prem], 'Renewal Date':[ins_renew.strftime('%Y-%m-%d')]})
                st.session_state.insurance = pd.concat([st.session_state.insurance, new_ins], ignore_index=True)
                update_worksheet('Insurance', st.session_state.insurance)
                st.cache_data.clear()
                st.success("Insurance Added!")
                st.rerun()

    # 8. Assets
    with tabs[7]:
        st.dataframe(st.session_state.assets, hide_index=True, use_container_width=True)
        with st.form("add_asset"):
            asset_name = st.text_input("Asset Name")
            asset_val = st.number_input("Value ₹", min_value=0.0)
            asset_warr = st.text_input("Warranty (e.g., 2027-01)")
            if st.form_submit_button("Add Asset"):
                new_asset = pd.DataFrame({'Asset Name':[asset_name], 'Value (₹)':[asset_val], 'Warranty':[asset_warr]})
                st.session_state.assets = pd.concat([st.session_state.assets, new_asset], ignore_index=True)
                update_worksheet('Assets', st.session_state.assets)
                st.cache_data.clear()
                st.success("Asset Added!")
                st.rerun()

    # 9. Reports (3 Charts)
    with tabs[8]:
        st.markdown("### 📊 Financial Reports")
        df = st.session_state.transactions
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date'].dt.month_name()
            
            # 1. Income vs Expense Bar Chart
            inc = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
            exp = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
            merged = pd.merge(inc, exp, on='Month', how='outer').fillna(0)
            merged.columns = ['Month','Income','Expense']
            fig1 = px.bar(merged, x='Month', y=['Income','Expense'], barmode='group', color_discrete_map={'Income':'#10b981', 'Expense':'#ef4444'})
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6')
            st.plotly_chart(fig1, use_container_width=True)
            
            # 2. Month over Month Progress (Expense)
            exp_monthly = exp.copy()
            if len(exp_monthly) >= 2:
                fig2 = px.line(exp_monthly, x='Month', y='Amount', markers=True, title="📉 Month-Over-Month Expense Progress")
                fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Need at least 2 months of expense data for progress chart.")

            # 3. Expense Breakdown Pie Chart
            df_exp = df[df['Type']=='Expense'].groupby('Category')['Amount'].sum().reset_index()
            if not df_exp.empty:
                fig3 = px.pie(df_exp, names='Category', values='Amount', title="🧾 Expense Breakdown", hole=0.3)
                fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6')
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Add some transactions to see detailed reports.")

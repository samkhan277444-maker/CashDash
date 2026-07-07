import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="CashDash of Riyaz Pathan", layout="wide", initial_sidebar_state="collapsed")

# ---------- LIGHT THEME CSS ----------
st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; color: #1e293b; }
    .card { background: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); border: 1px solid #e9ecef; }
    .metric-value { font-size: 1.6rem; font-weight: 700; color: #1a73e8; }
    .metric-label { font-size: 0.8rem; color: #64748b; font-weight: 600; }
    .stButton button { width: 100%; border-radius: 8px; background: #1a73e8; color: white; border: none; font-weight: 600; }
    .stButton button:hover { background: #1557b0; }
    .stTextInput input, .stSelectbox div, .stDateInput input { border-radius: 8px; border: 1px solid #e2e8f0; background: #ffffff; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    @media (max-width: 768px) { .stApp { padding: 0px 10px; } }
    .greeting-text { color: #2c3e50; font-weight: 500; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------- GOOGLE SHEET CONNECTION ----------
def get_gsheet_client():
    try:
        secret_content = st.secrets["gcp_service_account"]
        if isinstance(secret_content, str):
            secret_content = json.loads(secret_content)
        creds = Credentials.from_service_account_info(
            secret_content,
            scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ Google Sheet Connection Error: {e}")
        return None

SHEET_NAME = "CashDash_Ultra_Data"

# ---------- DATA LOADERS (Cached) ----------
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
        st.warning(f"⚠️ Sync Warning: {e} (Data saved locally)")

def update_worksheet(ws_name, df):
    try:
        gc = get_gsheet_client()
        if gc:
            sh = gc.open(SHEET_NAME)
            ws = sh.worksheet(ws_name)
            ws.clear()
            ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.warning(f"⚠️ Update Warning: {e}")

# ---------- SESSION STATE ----------
if 'custom_categories' not in st.session_state:
    st.session_state.custom_categories = []  # Store user-added categories

if 'transactions' not in st.session_state:
    st.session_state.transactions = load_worksheet('Transactions')
    if st.session_state.transactions.empty:
        st.session_state.transactions = pd.DataFrame(columns=['Date','Description','Category','Amount','Type','Payment Mode','Status'])

# Budget
if 'budget' not in st.session_state:
    st.session_state.budget = load_worksheet('Budget')
    if st.session_state.budget.empty:
        st.session_state.budget = pd.DataFrame({
            'Category': ['Rent','Groceries','Vegetables','Mobile','EMI','Entertainment','Shopping','Baby','Education','Fuel','Investment','Bachat Gat','Daily SIP','Daily Gold'],
            'Current Month Budget': [3200,2500,2000,1000,1572,1000,1000,2000,500,1500,500,2000,300,600],
            'Previous Month Budget': [3200,2500,2000,1000,1572,1000,1000,2000,500,1500,500,2000,300,600],
            'Actual This Month': [3200,2500,2000,1000,0,1200,500,0,0,800,0,0,0,0]
        })

# Accounts: only BOB UPI, BOM UPI, PhonePe Wallet, Cash
if 'accounts' not in st.session_state:
    st.session_state.accounts = load_worksheet('Accounts')
    if st.session_state.accounts.empty:
        st.session_state.accounts = pd.DataFrame({
            'Account': ['BOB - UPI', 'BOM - UPI', 'PhonePe Wallet', 'Cash'],
            'Balance': [0,0,0,0]
        })

# Investments
if 'investments' not in st.session_state:
    st.session_state.investments = load_worksheet('Investments')
    if st.session_state.investments.empty:
        st.session_state.investments = pd.DataFrame({
            'Investment': ['Axis Gold Fund (SIP)','Daily Gold Saving','Other SIP'],
            'Type': ['Mutual Fund','Gold','SIP'],
            'Daily': [10,20,0],
            'Monthly': [300,600,0],
            'Invested': [0,0,0],
            'Current': [0,0,0],
            'ROI': [0,0,0]
        })

# EMI
if 'emi' not in st.session_state:
    st.session_state.emi = load_worksheet('EmiManager')
    if st.session_state.emi.empty:
        st.session_state.emi = pd.DataFrame({
            'Loan': ['CreditBee','Snapmint'],
            'Total': [6000,10000],
            'EMI': [800,772],
            'Remaining': [7200,6948],
            'Months Left': [9,9]
        })

# Goals
if 'goals' not in st.session_state:
    st.session_state.goals = load_worksheet('Goals')
    if st.session_state.goals.empty:
        st.session_state.goals = pd.DataFrame({
            'Goal': ['Emergency Fund','Vacation','New Phone'],
            'Target': [50000,20000,15000],
            'Saved': [12000,3000,0]
        })

# Baby
if 'baby' not in st.session_state:
    st.session_state.baby = load_worksheet('BabyTracker')
    if st.session_state.baby.empty:
        st.session_state.baby = pd.DataFrame({
            'Category': ['Milk','Diapers','Medicine','Doctor','Vaccination','Clothes','Toys','Education','Others'],
            'Budget': [1000,500,300,1000,2000,1000,500,500,500],
            'This Month': [0,0,0,0,0,0,0,0,0]
        })

# Fuel
if 'fuel' not in st.session_state:
    st.session_state.fuel = load_worksheet('FuelTracker')
    if st.session_state.fuel.empty:
        st.session_state.fuel = pd.DataFrame({
            'Date': [], 'Distance (km)': [], 'Fuel (L)': [], 'Cost (₹)': []
        })

# Bills
if 'bills' not in st.session_state:
    st.session_state.bills = load_worksheet('Bills')
    if st.session_state.bills.empty:
        st.session_state.bills = pd.DataFrame({
            'Bill': ['Rent','Mobile Recharge','Insurance'],
            'Amount': [3200,1000,5000],
            'Due Date': ['2026-07-05','2026-07-10','2026-07-20'],
            'Status': ['Paid','Pending','Pending']
        })

# Insurance
if 'insurance' not in st.session_state:
    st.session_state.insurance = load_worksheet('Insurance')
    if st.session_state.insurance.empty:
        st.session_state.insurance = pd.DataFrame({
            'Type': ['Health','Car','Life'],
            'Premium': [1000,500,2000],
            'Renewal Date': ['2026-08-01','2026-09-15','2026-12-01']
        })

# Assets
if 'assets' not in st.session_state:
    st.session_state.assets = load_worksheet('Assets')
    if st.session_state.assets.empty:
        st.session_state.assets = pd.DataFrame({
            'Asset': ['Laptop','Phone','Furniture'],
            'Value (₹)': [50000,20000,15000],
            'Warranty': ['2027-01','2026-12','N/A']
        })

# ---------- HELPER FUNCTIONS ----------
def format_currency(amount):
    return f"₹ {amount:,.0f}"

def total_balance():
    return st.session_state.accounts['Balance'].sum()

def get_monthly_summary():
    df = st.session_state.transactions
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.month_name()
    inc = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
    exp = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
    return inc, exp

# ---------- APP UI ----------
# App Name with Islamic Greeting
st.markdown("<h2 style='color:#1a73e8; margin-bottom:0;'>💰 CashDash of Riyaz Pathan</h2>", unsafe_allow_html=True)
st.markdown("<div class='greeting-text'>🕌 Assalamu Alaikum! (Bismillahir Rahmanir Rahim)</div>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now().strftime('%d %b %Y')}")

# Bottom Navigation
nav = st.radio("Menu", ["🏠 Home", "➕ Add", "🎯 Budget", "🏦 Bank", "⚡ More"], index=0, horizontal=True, label_visibility="collapsed")

# ===================== HOME =====================
if nav == "🏠 Home":
    st.subheader("🏠 Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='card'><div class='metric-label'>Total Balance</div><div class='metric-value'>{format_currency(total_balance())}</div></div>", unsafe_allow_html=True)
    with col2:
        inc, exp = get_monthly_summary()
        m_inc = inc[inc['Month']==datetime.now().strftime('%B')]['Amount'].sum() if not inc.empty else 0
        st.markdown(f"<div class='card'><div class='metric-label'>Monthly Income</div><div class='metric-value' style='color:#4caf50;'>{format_currency(m_inc)}</div></div>", unsafe_allow_html=True)
    with col3:
        m_exp = exp[exp['Month']==datetime.now().strftime('%B')]['Amount'].sum() if not exp.empty else 0
        st.markdown(f"<div class='card'><div class='metric-label'>Monthly Expenses</div><div class='metric-value' style='color:#e53e3e;'>{format_currency(m_exp)}</div></div>", unsafe_allow_html=True)

    # Budget vs Expense Alert (Red/Green)
    st.markdown("### ⚠️ Budget & Expense Alert")
    
    # Calculate Total Budget and Current Month Actual Expense
    current_month = datetime.now().strftime('%B')
    df_tx = st.session_state.transactions
    total_budget = st.session_state.budget['Current Month Budget'].sum()
    
    current_expense = 0
    if not df_tx.empty:
        df_tx['Date'] = pd.to_datetime(df_tx['Date'])
        current_expense = df_tx[(df_tx['Type']=='Expense') & (df_tx['Date'].dt.month_name() == current_month)]['Amount'].sum()
    
    diff = current_expense - total_budget
    
    if diff > 0:
        # RED ALERT (Over Budget)
        st.markdown(f"""
        <div class='card' style='border-left: 6px solid #e53e3e; background-color: #fff5f5;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <div style='color: #e53e3e; font-weight: 700; font-size: 1.1rem;'>🔴 ALERT! You are Over Budget!</div>
                    <div style='color: #e53e3e;'>Expenses are exceeding the planned budget by <b>{format_currency(diff)}</b> this month.</div>
                </div>
                <div style='text-align: right;'>
                    <div style='font-size: 0.9rem; color: #64748b;'>Budget</div>
                    <div style='font-weight: 700; color: #1a73e8;'>{format_currency(total_budget)}</div>
                    <div style='font-size: 0.8rem; color: #64748b;'>Spent</div>
                    <div style='font-weight: 700; color: #e53e3e;'>{format_currency(current_expense)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # GREEN SUCCESS (On Track)
        remaining = total_budget - current_expense
        st.markdown(f"""
        <div class='card' style='border-left: 6px solid #4caf50; background-color: #f0fff4;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <div style='color: #4caf50; font-weight: 700; font-size: 1.1rem;'>🟢 On Track!</div>
                    <div style='color: #2d3748;'>You are within budget by <b>{format_currency(remaining)}</b> this month. Keep it up!</div>
                </div>
                <div style='text-align: right;'>
                    <div style='font-size: 0.9rem; color: #64748b;'>Budget</div>
                    <div style='font-weight: 700; color: #1a73e8;'>{format_currency(total_budget)}</div>
                    <div style='font-size: 0.8rem; color: #64748b;'>Spent</div>
                    <div style='font-weight: 700; color: #4caf50;'>{format_currency(current_expense)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Recent Transactions
    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        st.table(recent[['Date','Description','Category','Amount']].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0))
    else:
        st.info("No transactions yet.")

# ===================== ADD TRANSACTION =====================
elif nav == "➕ Add":
    st.subheader("➕ Add Transaction")
    
    # Static + Dynamic Categories
    base_categories = ['Salary','Rent','Groceries','Vegetables','EMI','Mobile','Fuel','Entertainment','Shopping','Baby','Education','Investment','Bachat Gat','Daily SIP','Daily Gold']
    available_categories = base_categories + st.session_state.custom_categories + ['Others']
    
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            description = st.text_input("Description")
            amount = st.number_input("Amount ₹", min_value=0.0)
        with col2:
            category = st.selectbox("Category", available_categories)
            ttype = st.selectbox("Type", ["Income", "Expense"])
            payment_mode = st.selectbox("Payment Mode", ["BOB - UPI", "BOM - UPI", "PhonePe Wallet", "Cash"])
        
        # Custom Category Entry if "Others" selected
        final_category = category
        if category == 'Others':
            custom_cat = st.text_input("✨ Enter New Custom Category Name")
            if custom_cat:
                final_category = custom_cat
                # Add to session state for next time
                if custom_cat not in st.session_state.custom_categories:
                    st.session_state.custom_categories.append(custom_cat)
        
        if st.form_submit_button("✅ Add Transaction", key="submit_btn"):
            new_row = [date.strftime('%Y-%m-%d'), description, final_category, amount, ttype, payment_mode, '✅']
            new_df = pd.DataFrame([{
                'Date': date.strftime('%Y-%m-%d'), 'Description': description, 'Category': final_category,
                'Amount': amount, 'Type': ttype, 'Payment Mode': payment_mode, 'Status': '✅'
            }])
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
            append_to_worksheet('Transactions', new_row)
            
            st.success(f"✅ '{final_category}' Transaction Saved Successfully!")
            st.rerun()

# ===================== BUDGET =====================
elif nav == "🎯 Budget":
    st.subheader("🎯 Budget Planner (Monthly)")
    
    # Display current budget
    df = st.session_state.budget
    # Compute comparison
    df['Difference'] = df['Current Month Budget'] - df['Previous Month Budget']
    df['Progress'] = (df['Actual This Month'] / df['Current Month Budget'] * 100).fillna(0).round(1)
    df['Status'] = df.apply(lambda row: "✅ On Track" if row['Actual This Month'] <= row['Current Month Budget'] else "⚠️ Over", axis=1)

    st.dataframe(df.style.format({
        'Current Month Budget': '₹ {:.0f}', 'Previous Month Budget': '₹ {:.0f}',
        'Actual This Month': '₹ {:.0f}', 'Difference': '₹ {:.0f}',
        'Progress': '{:.1f}%'
    }), use_container_width=True, hide_index=True)

    # Add/Edit Budget Form
    with st.expander("✏️ Add / Edit Budget Category"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_cat = st.text_input("New Category Name (leave blank to edit existing)")
            cat_select = st.selectbox("Or select existing", df['Category'].tolist() + ["New"])
        with col2:
            curr_budget = st.number_input("Current Month Budget ₹", min_value=0.0, step=100.0)
            prev_budget = st.number_input("Previous Month Budget ₹", min_value=0.0, step=100.0)
        with col3:
            actual = st.number_input("Actual This Month ₹", min_value=0.0, step=100.0)
        
        if st.button("Update Budget"):
            if new_cat:
                # Add new category
                new_row = pd.DataFrame({
                    'Category': [new_cat],
                    'Current Month Budget': [curr_budget],
                    'Previous Month Budget': [prev_budget],
                    'Actual This Month': [actual]
                })
                df = pd.concat([df, new_row], ignore_index=True)
            else:
                # Update existing
                idx = df[df['Category']==cat_select].index
                if not idx.empty:
                    df.loc[idx, 'Current Month Budget'] = curr_budget
                    df.loc[idx, 'Previous Month Budget'] = prev_budget
                    df.loc[idx, 'Actual This Month'] = actual
            st.session_state.budget = df
            update_worksheet('Budget', df)
            st.success("Budget Updated!")
            st.rerun()

# ===================== BANK =====================
elif nav == "🏦 Bank":
    st.subheader("🏦 My Accounts")
    st.dataframe(st.session_state.accounts.style.format({'Balance': '₹ {:.0f}'}), use_container_width=True, hide_index=True)
    
    with st.expander("💰 Update Balance"):
        acc = st.selectbox("Select Account", st.session_state.accounts['Account'])
        amt = st.number_input("Add/Subtract Amount ₹", step=100.0)
        if st.button("Update"):
            st.session_state.accounts.loc[st.session_state.accounts['Account']==acc, 'Balance'] += amt
            update_worksheet('Accounts', st.session_state.accounts)
            st.success("Balance Updated!")
            st.rerun()

# ===================== MORE (PREMIUM MODULES) =====================
elif nav == "⚡ More":
    st.subheader("🚀 Premium Modules")
    tabs = st.tabs(["📈 Investments", "🏦 EMI", "🎯 Goals", "👶 Baby", "⛽ Fuel", "🧾 Bills", "🛡️ Insurance", "📦 Assets", "📊 Reports"])
    
    # 1. Investments
    with tabs[0]:
        st.dataframe(st.session_state.investments, hide_index=True, use_container_width=True)
        with st.expander("➕ Add / Edit Investment"):
            inv_name = st.text_input("Investment Name")
            inv_type = st.selectbox("Type", ["Mutual Fund", "Gold", "SIP", "Other"])
            daily = st.number_input("Daily ₹", min_value=0.0)
            monthly = st.number_input("Monthly ₹", min_value=0.0)
            invested = st.number_input("Invested So Far ₹", min_value=0.0)
            current = st.number_input("Current Value ₹", min_value=0.0)
            if st.button("Save Investment"):
                new_inv = pd.DataFrame({
                    'Investment': [inv_name], 'Type': [inv_type], 'Daily': [daily],
                    'Monthly': [monthly], 'Invested': [invested], 'Current': [current],
                    'ROI': [((current - invested) / invested * 100) if invested > 0 else 0]
                })
                st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                update_worksheet('Investments', st.session_state.investments)
                st.success("Investment Saved!")
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
                new_emi = pd.DataFrame({'Loan':[loan], 'Total':[total], 'EMI':[emi], 'Remaining':[remaining], 'Months Left':[months]})
                st.session_state.emi = pd.concat([st.session_state.emi, new_emi], ignore_index=True)
                update_worksheet('EmiManager', st.session_state.emi)
                st.success("EMI Saved!")
                st.rerun()

    # 3. Goals
    with tabs[2]:
        goals = st.session_state.goals
        goals['Remaining'] = goals['Target'] - goals['Saved']
        goals['Progress'] = (goals['Saved'] / goals['Target'] * 100).round(1)
        st.dataframe(goals, hide_index=True, use_container_width=True)
        with st.form("add_goal"):
            g_name = st.text_input("Goal Name")
            g_target = st.number_input("Target ₹", min_value=1)
            g_saved = st.number_input("Saved ₹", min_value=0)
            if st.form_submit_button("Add Goal"):
                new_goal = pd.DataFrame({'Goal':[g_name], 'Target':[g_target], 'Saved':[g_saved]})
                st.session_state.goals = pd.concat([st.session_state.goals, new_goal], ignore_index=True)
                update_worksheet('Goals', st.session_state.goals)
                st.success("Goal Added!")
                st.rerun()

    # 4. Baby
    with tabs[3]:
        st.dataframe(st.session_state.baby, hide_index=True, use_container_width=True)
        with st.expander("✏️ Update Baby Expense"):
            baby_cat = st.selectbox("Category", st.session_state.baby['Category'])
            new_amt = st.number_input("This Month Expense ₹", min_value=0.0)
            if st.button("Update Baby"):
                idx = st.session_state.baby[st.session_state.baby['Category']==baby_cat].index
                st.session_state.baby.loc[idx, 'This Month'] = new_amt
                update_worksheet('BabyTracker', st.session_state.baby)
                st.success("Baby Expense Updated!")
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
                st.success("Fuel Entry Added!")
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
                new_bill = pd.DataFrame({'Bill':[bill_name], 'Amount':[bill_amt], 'Due Date':[bill_due.strftime('%Y-%m-%d')], 'Status':[bill_status]})
                st.session_state.bills = pd.concat([st.session_state.bills, new_bill], ignore_index=True)
                update_worksheet('Bills', st.session_state.bills)
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
                new_asset = pd.DataFrame({'Asset':[asset_name], 'Value (₹)':[asset_val], 'Warranty':[asset_warr]})
                st.session_state.assets = pd.concat([st.session_state.assets, new_asset], ignore_index=True)
                update_worksheet('Assets', st.session_state.assets)
                st.success("Asset Added!")
                st.rerun()

    # 9. Reports
    with tabs[8]:
        st.markdown("### 📊 Financial Reports")
        
        # Income vs Expense Chart
        inc, exp = get_monthly_summary()
        if not inc.empty and not exp.empty:
            merged = pd.merge(inc, exp, on='Month', how='outer').fillna(0)
            merged.columns = ['Month','Income','Expense']
            fig1 = px.bar(merged, x='Month', y=['Income','Expense'], barmode='group', color_discrete_map={'Income':'#1a73e8', 'Expense':'#e53e3e'})
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f5f7fa')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Add transactions to see income/expense charts.")

        # Budget vs Actual Chart
        df_bud = st.session_state.budget
        if not df_bud.empty:
            fig2 = px.bar(df_bud, x='Category', y=['Current Month Budget','Actual This Month'], barmode='group', color_discrete_map={'Current Month Budget':'#1a73e8', 'Actual This Month':'#e53e3e'})
            fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f5f7fa')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No budget data available.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="CashDash Ultra Pro", layout="wide", initial_sidebar_state="collapsed")

# ---------- LIGHT PHONEPE THEME CSS ----------
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
</style>
""", unsafe_allow_html=True)

# ---------- GOOGLE SHEET CONNECTION (ERROR FIXED) ----------
def get_gsheet_client():
    try:
        # 🛡️ FIX: JSON ko string se dictionary mein convert karo
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

# ---------- DATA LOADERS (Cached for speed) ----------
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

# ---------- SESSION STATE (Full Features) ----------
if 'transactions' not in st.session_state:
    st.session_state.transactions = load_worksheet('Transactions')
    if st.session_state.transactions.empty:
        st.session_state.transactions = pd.DataFrame(columns=['Date','Description','Category','Amount','Type','Payment Mode','Status'])

if 'budget' not in st.session_state:
    st.session_state.budget = load_worksheet('BudgetPlanner')
    if st.session_state.budget.empty:
        st.session_state.budget = pd.DataFrame({
            'Category': ['Rent','Groceries','Vegetables','Mobile','EMI','Entertainment','Shopping','Baby','Education'],
            'Budget': [3200,2500,2000,1000,1572,1000,1000,2000,500],
            'Actual': [3200,2500,2000,1000,0,1200,500,0,0]
        })

if 'accounts' not in st.session_state:
    st.session_state.accounts = load_worksheet('Accounts')
    if st.session_state.accounts.empty:
        st.session_state.accounts = pd.DataFrame({
            'Account': ['BOB Savings','BOM Savings','PhonePe','Google Pay','Paytm','Cash'],
            'Balance': [0,0,0,0,0,0]
        })

if 'investments' not in st.session_state:
    st.session_state.investments = load_worksheet('Investments')
    if st.session_state.investments.empty:
        st.session_state.investments = pd.DataFrame({
            'Investment': ['Axis Gold Fund (SIP)','Daily Gold Saving'],
            'Type': ['Mutual Fund','Gold'],
            'Daily': [10,20],
            'Monthly': [300,600],
            'Invested': [0,0],
            'Current': [0,0],
            'ROI': [0,0]
        })

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

if 'goals' not in st.session_state:
    st.session_state.goals = load_worksheet('Goals')
    if st.session_state.goals.empty:
        st.session_state.goals = pd.DataFrame({
            'Goal': ['Emergency Fund','Vacation','New Phone'],
            'Target': [50000,20000,15000],
            'Saved': [12000,3000,0]
        })

if 'baby' not in st.session_state:
    st.session_state.baby = load_worksheet('BabyTracker')
    if st.session_state.baby.empty:
        st.session_state.baby = pd.DataFrame({
            'Category': ['Milk','Diapers','Medicine','Doctor','Vaccination','Clothes','Toys','Education','Others'],
            'Budget': [1000,500,300,1000,2000,1000,500,500,500],
            'This Month': [0,0,0,0,0,0,0,0,0]
        })

if 'fuel' not in st.session_state:
    st.session_state.fuel = load_worksheet('FuelTracker')
    if st.session_state.fuel.empty:
        st.session_state.fuel = pd.DataFrame({
            'Date': [], 'Distance (km)': [], 'Fuel (L)': [], 'Cost (₹)': []
        })

if 'bills' not in st.session_state:
    st.session_state.bills = load_worksheet('Bills')
    if st.session_state.bills.empty:
        st.session_state.bills = pd.DataFrame({
            'Bill': ['Rent','Mobile Recharge','Insurance'],
            'Amount': [3200,1000,5000],
            'Due Date': ['2026-07-05','2026-07-10','2026-07-20'],
            'Status': ['Paid','Pending','Pending']
        })

if 'insurance' not in st.session_state:
    st.session_state.insurance = load_worksheet('Insurance')
    if st.session_state.insurance.empty:
        st.session_state.insurance = pd.DataFrame({
            'Type': ['Health','Car','Life'],
            'Premium': [1000,500,2000],
            'Renewal Date': ['2026-08-01','2026-09-15','2026-12-01']
        })

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
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.month_name()
    inc = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
    exp = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
    return inc, exp

# ---------- APP UI ----------
st.markdown("<h2 style='color:#1a73e8;'>💎 CashDash Ultra Pro</h2>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now().strftime('%d %b %Y')}")

# Bottom Navigation
nav = st.radio("Menu", ["🏠 Home", "➕ Add", "🎯 Budget", "🏦 Bank", "⚡ More"], index=0, horizontal=True, label_visibility="collapsed")

# ===================== HOME =====================
if nav == "🏠 Home":
    st.subheader("🏠 Dashboard")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='card'><div class='metric-label'>Balance</div><div class='metric-value'>{format_currency(total_balance())}</div></div>", unsafe_allow_html=True)
    with col2:
        inc, exp = get_monthly_summary()
        m_inc = inc[inc['Month']==datetime.now().strftime('%B')]['Amount'].sum() if not inc.empty else 0
        st.markdown(f"<div class='card'><div class='metric-label'>Income (Month)</div><div class='metric-value' style='color:#4caf50;'>{format_currency(m_inc)}</div></div>", unsafe_allow_html=True)
    with col3:
        m_exp = exp[exp['Month']==datetime.now().strftime('%B')]['Amount'].sum() if not exp.empty else 0
        st.markdown(f"<div class='card'><div class='metric-label'>Expense (Month)</div><div class='metric-value' style='color:#e53e3e;'>{format_currency(m_exp)}</div></div>", unsafe_allow_html=True)

    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        st.table(recent[['Date','Description','Category','Amount']].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0))
    else:
        st.info("No transactions yet.")

# ===================== ADD TRANSACTION =====================
elif nav == "➕ Add":
    st.subheader("➕ Add Transaction")
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            desc = st.text_input("Description")
            amt = st.number_input("Amount ₹", min_value=0.0)
        with col2:
            cat = st.selectbox("Category", ['Salary','Rent','Groceries','EMI','Mobile','Fuel','Entertainment','Shopping','Baby','Education','Others'])
            ttype = st.selectbox("Type", ["Income", "Expense"])
            mode = st.selectbox("Payment Mode", ["UPI","BOB","BOM","Cash","PhonePe","GPay"])
        
        # 🛡️ KEY FIXED
        if st.form_submit_button("✅ Add Transaction", key="submit_btn"):
            new_row = [date.strftime('%Y-%m-%d'), desc, cat, amt, ttype, mode, '✅']
            new_df = pd.DataFrame([{
                'Date': date.strftime('%Y-%m-%d'), 'Description': desc, 'Category': cat,
                'Amount': amt, 'Type': ttype, 'Payment Mode': mode, 'Status': '✅'
            }])
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
            append_to_worksheet('Transactions', new_row)
            st.success("✅ Transaction Added!")
            st.rerun()

# ===================== BUDGET =====================
elif nav == "🎯 Budget":
    st.subheader("🎯 Budget Planner")
    df = st.session_state.budget
    df['Remaining'] = df['Budget'] - df['Actual']
    df['Progress'] = (df['Actual'] / df['Budget'] * 100).round(1).fillna(0)
    st.dataframe(df.style.format({'Budget': '₹ {:.0f}', 'Actual': '₹ {:.0f}', 'Remaining': '₹ {:.0f}', 'Progress': '{:.1f}%'}), use_container_width=True, hide_index=True)

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
            st.rerun()

# ===================== MORE (ALL PREMIUM FEATURES) =====================
elif nav == "⚡ More":
    st.subheader("🚀 Premium Modules")
    tabs = st.tabs(["📈 Investments", "🏦 EMI", "🎯 Goals", "👶 Baby", "⛽ Fuel", "🧾 Bills", "🛡️ Insurance", "📦 Assets", "📊 Reports"])
    
    # 1. Investments
    with tabs[0]:
        st.dataframe(st.session_state.investments, hide_index=True, use_container_width=True)
        if st.button("🔄 Refresh Portfolio (Simulated)"):
            df_inv = st.session_state.investments
            df_inv['Current'] = df_inv['Invested'] * (1 + np.random.uniform(-0.05, 0.15, len(df_inv)))
            df_inv['ROI'] = ((df_inv['Current'] - df_inv['Invested']) / df_inv['Invested'] * 100).round(1)
            st.session_state.investments = df_inv
            update_worksheet('Investments', df_inv)
            st.rerun()

    # 2. EMI
    with tabs[1]:
        st.dataframe(st.session_state.emi, hide_index=True, use_container_width=True)

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
                st.rerun()

    # 4. Baby
    with tabs[3]:
        st.dataframe(st.session_state.baby, hide_index=True, use_container_width=True)

    # 5. Fuel
    with tabs[4]:
        st.dataframe(st.session_state.fuel, hide_index=True, use_container_width=True)

    # 6. Bills
    with tabs[5]:
        st.dataframe(st.session_state.bills, hide_index=True, use_container_width=True)

    # 7. Insurance
    with tabs[6]:
        st.dataframe(st.session_state.insurance, hide_index=True, use_container_width=True)

    # 8. Assets
    with tabs[7]:
        st.dataframe(st.session_state.assets, hide_index=True, use_container_width=True)

    # 9. Reports
    with tabs[8]:
        inc, exp = get_monthly_summary()
        if not inc.empty and not exp.empty:
            merged = pd.merge(inc, exp, on='Month', how='outer').fillna(0)
            merged.columns = ['Month','Income','Expense']
            fig = px.bar(merged, x='Month', y=['Income','Expense'], barmode='group', color_discrete_map={'Income':'#1a73e8', 'Expense':'#e53e3e'})
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f5f7fa')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add transactions to see reports.")

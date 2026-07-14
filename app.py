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
        padding: 8px 10px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
        min-width: 80px;
    }
    .sheet-card-header {
        color: #64748b;
        font-size: 0.65rem;
        font-weight: 600;
        margin-bottom: 2px;
        text-transform: uppercase;
    }
    .sheet-card-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0f172a;
    }
    .sheet-card-sub {
        font-size: 0.55rem;
        color: #94a3b8;
        margin-top: 2px;
    }
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        font-size: 0.85rem;
    }
    .stDataFrame { font-size: 0.8rem; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    @media (max-width: 768px) {
        .sheet-card { min-width: 60px; padding: 6px; }
        .sheet-card-value { font-size: 1rem; }
        .stColumns { flex-wrap: wrap !important; }
        .stColumn { flex: 1 1 45% !important; min-width: 60px; }
    }
    @media (max-width: 480px) {
        .stColumn { flex: 1 1 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# ---------- GOOGLE SHEET CONNECTION ----------
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
        st.error(f"❌ Connection Error: {e}")
        return None

# ---------- CACHED DATA LOAD (60 SECONDS TTL) ----------
@st.cache_data(ttl=60)
def load_all_sheets():
    gc = get_gsheet_client()
    if gc is None:
        return {}
    
    data = {}
    worksheet_names = ['Transactions', 'Budget', 'Accounts', 'Investments', 'EmiManager', 
                       'Goals', 'FuelTracker', 'Settings', 'CustomTypes', 'CustomCategories', 'CustomNatures']
    
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ Sheet '{SHEET_NAME}' not found in Drive. Please create it.")
        return {}
    
    for ws_name in worksheet_names:
        try:
            ws = sh.worksheet(ws_name)
            records = ws.get_all_records()
            data[ws_name] = pd.DataFrame(records) if records else pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            data[ws_name] = pd.DataFrame()
        except Exception:
            data[ws_name] = pd.DataFrame()
    
    return data

def append_to_worksheet(ws_name, row_data):
    gc = get_gsheet_client()
    if gc is None:
        st.error("❌ Google Sheet not connected. Data saved locally only.")
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
        st.error(f"❌ Error syncing to Google Sheet: {e}")

def update_worksheet(ws_name, df):
    gc = get_gsheet_client()
    if gc is None:
        st.error("❌ Google Sheet not connected. Update failed.")
        return
    try:
        sh = gc.open(SHEET_NAME)
        try:
            ws = sh.worksheet(ws_name)
        except gspread.exceptions.WorksheetNotFound:
            sh.add_worksheet(title=ws_name, rows=200, cols=20)
            ws = sh.worksheet(ws_name)
        ws.clear()
        df_clean = df.fillna('').astype(str)
        ws.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())
    except Exception as e:
        st.warning(f"⚠️ Update failed for '{ws_name}': {e}")

def update_settings(key, value):
    gc = get_gsheet_client()
    if gc is None: return
    try:
        sh = gc.open(SHEET_NAME)
        try:
            ws = sh.worksheet('Settings')
        except:
            sh.add_worksheet(title='Settings', rows=10, cols=2)
            ws = sh.worksheet('Settings')
            ws.update([['Key', 'Value']])
        
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame(columns=['Key','Value'])
        if key in df['Key'].values:
            idx = df[df['Key']==key].index[0]
            ws.update_cell(idx+2, 2, value)
        else:
            ws.append_row([key, value])
    except Exception as e:
        st.warning(f"Could not update settings: {e}")

# ---------- SESSION STATE ----------
def init_session_state():
    all_data = load_all_sheets()
    
    # 1. Transactions
    loaded = all_data.get('Transactions', pd.DataFrame())
    required_cols = ['Date','Description','Category','Amount','Type','Payment Mode','Status']
    if loaded.empty or not all(c in loaded.columns for c in required_cols):
        st.session_state.transactions = pd.DataFrame(columns=required_cols)
    else:
        st.session_state.transactions = loaded

    # 2. Budget
    loaded = all_data.get('Budget', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Category','Current Month Budget','Previous Month Budget','Actual This Month']):
        st.session_state.budget = pd.DataFrame({
            'Category': ['Rent','Groceries','Vegetables','Mobile','EMI','Entertainment','Shopping','Education','Fuel','Investment','BC'],
            'Current Month Budget': [3200,2500,2000,1000,1572,1000,1000,500,1500,500,1000],
            'Previous Month Budget': [3200,2500,2000,1000,1572,1000,1000,500,1500,500,1000],
            'Actual This Month': [3200,2500,2000,1000,0,1200,500,0,0,800,0]
        })
    else:
        st.session_state.budget = loaded

    # 3. Accounts
    loaded = all_data.get('Accounts', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Account','Balance']):
        st.session_state.accounts = pd.DataFrame({
            'Account': ['BOB Bank', 'BOM Bank', 'PhonePe Wallet', 'Cash'],
            'Balance': [0,0,0,0]
        })
    else:
        st.session_state.accounts = loaded

    # 4. Investments
    loaded = all_data.get('Investments', pd.DataFrame())
    if not loaded.empty and 'Name' in loaded.columns:
        loaded = loaded[loaded['Name'].notna() & (loaded['Name'].astype(str).str.strip() != '')]
    
    req_inv_cols = ['Name','Type','Amount','Frequency','Total Invested','Current Value']
    if loaded.empty or not all(c in loaded.columns for c in req_inv_cols):
        st.session_state.investments = pd.DataFrame(columns=req_inv_cols)
    else:
        st.session_state.investments = loaded

    # 5. EMI
    loaded = all_data.get('EmiManager', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Loan Name','Total Loan','EMI Amount','Remaining','Months Left']):
        st.session_state.emi = pd.DataFrame(columns=['Loan Name','Total Loan','EMI Amount','Remaining','Months Left'])
    else:
        st.session_state.emi = loaded

    # 6. Goals
    loaded = all_data.get('Goals', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Goal Name','Target','Saved']):
        st.session_state.goals = pd.DataFrame(columns=['Goal Name', 'Target', 'Saved'])
    else:
        st.session_state.goals = loaded

    # 7. Fuel
    loaded = all_data.get('FuelTracker', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Date','Distance (km)','Fuel (L)','Cost (₹)']):
        st.session_state.fuel = pd.DataFrame(columns=['Date', 'Distance (km)', 'Fuel (L)', 'Cost (₹)'])
    else:
        st.session_state.fuel = loaded

    # 8. Settings
    loaded = all_data.get('Settings', pd.DataFrame())
    if loaded.empty:
        st.session_state.master_budget = 0.0
        st.session_state.last_sync_time = "Never"
    else:
        if 'master_budget' in loaded['Key'].values:
            try:
                st.session_state.master_budget = float(loaded[loaded['Key']=='master_budget']['Value'].values[0])
            except:
                st.session_state.master_budget = 0.0
        else:
            st.session_state.master_budget = 0.0
        
        if 'last_sync_time' in loaded['Key'].values:
            st.session_state.last_sync_time = loaded[loaded['Key']=='last_sync_time']['Value'].values[0]
        else:
            st.session_state.last_sync_time = "Never"

    # 9. Custom Types
    loaded = all_data.get('CustomTypes', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['TypeName','Nature']):
        st.session_state.custom_types = pd.DataFrame(columns=['TypeName','Nature'])
    else:
        st.session_state.custom_types = loaded

    # 10. Custom Categories
    loaded = all_data.get('CustomCategories', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Category']):
        st.session_state.custom_categories = pd.DataFrame(columns=['Category'])
    else:
        st.session_state.custom_categories = loaded

    # 11. Custom Natures
    loaded = all_data.get('CustomNatures', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Nature']):
        st.session_state.custom_natures = pd.DataFrame({'Nature': ['Income', 'Expense']})
    else:
        st.session_state.custom_natures = loaded

if 'initialized' not in st.session_state:
    init_session_state()
    st.session_state.initialized = True

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

# ---------- SYNC FUNCTION ----------
def force_sync():
    try:
        update_worksheet('Transactions', st.session_state.transactions)
        update_worksheet('Budget', st.session_state.budget)
        update_worksheet('Accounts', st.session_state.accounts)
        update_worksheet('Investments', st.session_state.investments)
        update_worksheet('EmiManager', st.session_state.emi)
        update_worksheet('Goals', st.session_state.goals)
        update_worksheet('FuelTracker', st.session_state.fuel)
        update_worksheet('CustomTypes', st.session_state.custom_types)
        update_worksheet('CustomCategories', st.session_state.custom_categories)
        update_worksheet('CustomNatures', st.session_state.custom_natures)
        
        sync_time = datetime.now().strftime("%d %b %Y, %H:%M:%S")
        update_settings('last_sync_time', sync_time)
        st.session_state.last_sync_time = sync_time
        
        st.cache_data.clear()
        return True, "✅ All data synced successfully!"
    except Exception as e:
        return False, f"❌ Sync failed: {e}"

# ---------- APP UI ----------
st.markdown("<h2 style='color:#1e293b; margin-bottom:0;'>💎 CashDash of Riyaz Pathan</h2>", unsafe_allow_html=True)
st.markdown(f"<div style='color:#64748b; font-size:0.8rem;'>🕌 Assalamu Alaikum! | 📅 {datetime.now().strftime('%d %b %Y')} | 📆 Salary Cycle 10th → 9th</div>", unsafe_allow_html=True)

# Radio Navigation
nav = st.radio("Menu", ["🏠 Home", "➕ Add", "🎯 Budget", "🏦 Bank", "⚡ More"], index=0, horizontal=True, key='nav_radio')
st.session_state.page = nav

# ===================== HOME =====================
if st.session_state.page == "🏠 Home":
    st.markdown("## 📊 Dashboard")
    
    current_month = datetime.now().strftime('%B')
    df_tx = st.session_state.transactions
    
    # Bank balances
    bob_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='BOB Bank', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
    bom_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='BOM Bank', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
    upi_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='PhonePe Wallet', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
    cash_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='Cash', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
    
    monthly_inc = 0
    monthly_exp = 0
    if not df_tx.empty:
        df_tx['Date'] = pd.to_datetime(df_tx['Date'])
        df_month = df_tx[df_tx['Date'].dt.month_name() == current_month]
        monthly_inc = df_month[df_month['Type']=='Income']['Amount'].sum()
        monthly_exp = df_month[df_month['Type']=='Expense']['Amount'].sum()
    
    savings = monthly_inc - monthly_exp
    total_budget_val = st.session_state.budget['Current Month Budget'].sum()
    
    # Investment stats
    inv_df = st.session_state.investments
    if not inv_df.empty and 'Name' in inv_df.columns:
        sip_mask = inv_df['Name'].str.upper() == 'SIP'
        gold_mask = inv_df['Name'].str.upper() == 'GOLD'
        sip_inv = inv_df.loc[sip_mask, 'Total Invested'].sum() if sip_mask.any() else 0
        gold_inv = inv_df.loc[gold_mask, 'Total Invested'].sum() if gold_mask.any() else 0
        sip_curr = inv_df.loc[sip_mask, 'Current Value'].sum() if sip_mask.any() else 0
        gold_curr = inv_df.loc[gold_mask, 'Current Value'].sum() if gold_mask.any() else 0
    else:
        sip_inv = gold_inv = sip_curr = gold_curr = 0
    
    total_invested = sip_inv + gold_inv
    current_value = sip_curr + gold_curr
    
    # EMI stats
    total_emi_remaining = st.session_state.emi['Remaining'].sum() if not st.session_state.emi.empty else 0
    total_emi_due = st.session_state.emi['EMI Amount'].sum() if not st.session_state.emi.empty else 0
    
    # BC stats
    bc_total = df_tx[df_tx['Type']=='BC']['Amount'].sum() if not df_tx.empty else 0

    # Hand Loan stats
    if not df_tx.empty:
        handloan_income = df_tx[(df_tx['Category'] == 'Hand Loan') & (df_tx['Type'] == 'Income')]['Amount'].sum()
        handloan_expense = df_tx[(df_tx['Category'] == 'Hand Loan') & (df_tx['Type'] == 'Expense')]['Amount'].sum()
        handloan_outstanding = handloan_income - handloan_expense
    else:
        handloan_outstanding = 0

    # Row 1: Accounts
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🏦 BOB Bank</div><div class='sheet-card-value'>{format_currency(bob_bal)}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🏦 BOM Bank</div><div class='sheet-card-value'>{format_currency(bom_bal)}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📱 PhonePe Wallet</div><div class='sheet-card-value'>{format_currency(upi_bal)}</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>💵 Cash</div><div class='sheet-card-value'>{format_currency(cash_bal)}</div></div>", unsafe_allow_html=True)

    # Row 2: Income, Expense, Hand Loan, Budget
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📈 Total Income</div><div class='sheet-card-value' style='color:#10b981;'>{format_currency(monthly_inc)}</div><div class='sheet-card-sub'>This Month</div></div>", unsafe_allow_html=True)
    with col6:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📉 Total Expense</div><div class='sheet-card-value' style='color:#ef4444;'>{format_currency(monthly_exp)}</div><div class='sheet-card-sub'>This Month</div></div>", unsafe_allow_html=True)
    with col7:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🤝 Hand Loan</div><div class='sheet-card-value' style='color:#8b5cf6;'>{format_currency(handloan_outstanding)}</div><div class='sheet-card-sub'>Outstanding</div></div>", unsafe_allow_html=True)
    with col8:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🎯 This Month Budget</div><div class='sheet-card-value' style='color:#3b82f6;'>{format_currency(total_budget_val)}</div></div>", unsafe_allow_html=True)

    # Row 3: Investment, EMI, BC
    col9, col10, col11 = st.columns(3)
    with col9:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📈 Total Invested (SIP+Gold)</div><div class='sheet-card-value' style='color:#10b981;'>{format_currency(total_invested)}</div><div class='sheet-card-sub'>Current Value: {format_currency(current_value)}</div></div>", unsafe_allow_html=True)
    with col10:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>🏦 EMI Summary</div>
            <div class='sheet-card-value' style='color:#ef4444;'>{format_currency(total_emi_remaining)}</div>
            <div class='sheet-card-sub'>Monthly EMI: {format_currency(total_emi_due)}</div>
            <div class='sheet-card-sub' style='font-size:0.5rem;'>(Auto-debits update Remaining)</div>
        </div>
        """, unsafe_allow_html=True)
    with col11:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>💳 BC (Bachat Gat)</div><div class='sheet-card-value' style='color:#3b82f6;'>{format_currency(bc_total)}</div><div class='sheet-card-sub'>All time</div></div>", unsafe_allow_html=True)

    # Row 4: Recent Transactions
    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        st.table(recent[['Date','Description','Category','Amount','Type']].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0))
    else:
        st.info("No transactions yet.")

    # Row 5: MANUAL SYNC BUTTON
    st.markdown("---")
    col_sync1, col_sync2 = st.columns([3, 1])
    with col_sync1:
        if st.button("💾 Save & Sync to Google Sheet", use_container_width=True):
            success, msg = force_sync()
            if success:
                st.success(msg)
            else:
                st.error(msg)
    with col_sync2:
        st.markdown(f"<div style='text-align:right; font-size:0.7rem; color:#94a3b8;'>Last synced: {st.session_state.last_sync_time}</div>", unsafe_allow_html=True)

# ===================== ADD TRANSACTION =====================
elif st.session_state.page == "➕ Add":
    st.subheader("➕ Add Transaction")
    
    budget_cats = st.session_state.budget['Category'].tolist()
    inv_names = st.session_state.investments['Name'].tolist() if not st.session_state.investments.empty else []
    emi_names = st.session_state.emi['Loan Name'].tolist() if not st.session_state.emi.empty else []
    goal_names = st.session_state.goals['Goal Name'].tolist() if not st.session_state.goals.empty else []
    
    custom_cats = st.session_state.custom_categories['Category'].tolist() if not st.session_state.custom_categories.empty else []
    all_cats = list(set(['Transfer', 'Hand Loan'] + budget_cats + inv_names + emi_names + goal_names + custom_cats))
    all_cats = sorted(all_cats)
    
    if 'add_transaction_type' not in st.session_state:
        st.session_state.add_transaction_type = st.session_state.get('add_type', 'Income')
    
    def on_type_change():
        st.session_state.add_transaction_type = st.session_state.selected_type
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", datetime.now())
        desc = st.text_input("Description")
        amount = st.number_input("Amount ₹", min_value=0.0)
    with col2:
        custom_type_names = st.session_state.custom_types['TypeName'].tolist() if not st.session_state.custom_types.empty else []
        default_types = ["Income", "Expense", "Investment", "Transfer", "BC"]
        all_types = list(set(default_types + custom_type_names))
        all_types = sorted(all_types)
        
        ttype = st.selectbox("Type", all_types, index=all_types.index(st.session_state.add_transaction_type) if st.session_state.add_transaction_type in all_types else 0, key='selected_type', on_change=on_type_change)
        st.session_state.add_transaction_type = ttype
        
        default_nature_map = {
            "Income": "Income",
            "Expense": "Expense",
            "Investment": "Expense",
            "Transfer": "Neutral",
            "BC": "Expense"
        }
        custom_nature = None
        if ttype in st.session_state.custom_types['TypeName'].values:
            custom_nature = st.session_state.custom_types[st.session_state.custom_types['TypeName'] == ttype]['Nature'].values[0]
        nature = custom_nature if custom_nature else default_nature_map.get(ttype, "Income")
        if nature is None or nature == "Neutral":
            nature = "Income"   # fallback
        st.text(f"Nature: {nature} (auto-assigned)")
        
        category = None
        if ttype != "Income" and nature != "Income":
            category = st.selectbox("Category", all_cats)
        else:
            category = "Salary" if ttype == "Income" else "General"
            st.text(f"Category: {category} (auto-set)")
        
        payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])
    
    # Transfer fields
    from_acc = None
    to_acc = None
    if ttype == "Transfer":
        from_acc = st.selectbox("From Account", st.session_state.accounts['Account'], key='from')
        to_acc = st.selectbox("To Account", st.session_state.accounts['Account'], key='to')
        if from_acc == to_acc:
            st.warning("⚠️ From and To accounts must be different.")
    
    # EMI fields
    is_emi = (ttype == "Expense") and (category in emi_names or (category and 'emi' in category.lower()))
    emi_loan = None
    if is_emi:
        if not st.session_state.emi.empty:
            loan_options = st.session_state.emi['Loan Name'].tolist()
            emi_loan = st.selectbox("Select Loan for this EMI payment", loan_options)
            if emi_loan:
                emi_row = st.session_state.emi[st.session_state.emi['Loan Name'] == emi_loan].iloc[0]
                st.info(f"💡 Remaining: {format_currency(emi_row['Remaining'])}. After payment: {format_currency(emi_row['Remaining'] - amount)}")
        else:
            st.info("No EMI loans added yet. Go to More > EMI to add a loan.")
    
    # Investment fields
    is_investment = (ttype == "Investment") or (category and category in inv_names)
    inv_name = None
    if is_investment:
        existing_inv = st.session_state.investments['Name'].tolist() if not st.session_state.investments.empty else []
        if category and category in existing_inv:
            inv_name = category
        else:
            inv_options = ['New Investment'] + existing_inv
            inv_name = st.selectbox("Select Investment", inv_options)
            if inv_name == 'New Investment':
                inv_name = st.text_input("Enter new investment name")
        if inv_name in existing_inv:
            inv_row = st.session_state.investments[st.session_state.investments['Name'] == inv_name]
            if not inv_row.empty:
                st.info(f"Current Total Invested: {format_currency(inv_row.iloc[0]['Total Invested'])}")
    
    # Fuel fields
    is_fuel = (ttype == "Expense") and (category == 'Fuel' or (category and 'fuel' in category.lower()))
    f_dist = None
    f_litres = None
    if is_fuel:
        f_dist = st.number_input("Distance (km)", min_value=0.0, step=1.0)
        f_litres = st.number_input("Fuel (L)", min_value=0.0, step=0.1)
        if not desc.strip():
            if f_dist > 0:
                desc = f"Fuel - {f_litres:.1f} L, {f_dist:.1f} km"
            else:
                desc = f"Fuel - {f_litres:.1f} L"
    
    if st.button("✅ Add Transaction", key="submit_btn"):
        success_msg = None
        error_msg = None
        try:
            new_row = [date.strftime('%Y-%m-%d'), desc, category, amount, ttype, payment_mode, '✅']
            new_df = pd.DataFrame([{
                'Date': date.strftime('%Y-%m-%d'), 'Description': desc, 'Category': category,
                'Amount': amount, 'Type': ttype, 'Payment Mode': payment_mode, 'Status': '✅'
            }])
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
            append_to_worksheet('Transactions', new_row)
            
            # 1. Transfer
            if ttype == "Transfer" and from_acc and to_acc and from_acc != to_acc:
                from_idx = st.session_state.accounts[st.session_state.accounts['Account'] == from_acc].index[0]
                to_idx = st.session_state.accounts[st.session_state.accounts['Account'] == to_acc].index[0]
                st.session_state.accounts.loc[from_idx, 'Balance'] -= amount
                st.session_state.accounts.loc[to_idx, 'Balance'] += amount
                update_worksheet('Accounts', st.session_state.accounts)
            
            # 2. Payment Mode Balance (non-transfer)
            else:
                acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                if not acc_idx.empty:
                    idx = acc_idx[0]
                    if nature == "Income":
                        st.session_state.accounts.loc[idx, 'Balance'] += amount
                    elif nature in ["Expense", "BC"]:
                        st.session_state.accounts.loc[idx, 'Balance'] -= amount
                    update_worksheet('Accounts', st.session_state.accounts)

            # 3. EMI
            if is_emi and ttype == "Expense" and emi_loan and amount > 0:
                emi_idx = st.session_state.emi[st.session_state.emi['Loan Name'] == emi_loan].index[0]
                current_remaining = st.session_state.emi.loc[emi_idx, 'Remaining']
                st.session_state.emi.loc[emi_idx, 'Remaining'] = max(0, current_remaining - amount)
                update_worksheet('EmiManager', st.session_state.emi)
            
            # 4. Investment
            if is_investment and inv_name and amount > 0:
                if inv_name in st.session_state.investments['Name'].values:
                    idx = st.session_state.investments[st.session_state.investments['Name'] == inv_name].index[0]
                    st.session_state.investments.loc[idx, 'Total Invested'] += amount
                    if 'Current Value' in st.session_state.investments.columns:
                        st.session_state.investments.loc[idx, 'Current Value'] += amount
                else:
                    new_inv = pd.DataFrame({
                        'Name': [inv_name],
                        'Type': ['Other'],
                        'Amount': [0],
                        'Frequency': ['Monthly'],
                        'Total Invested': [amount],
                        'Current Value': [amount]
                    })
                    st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                update_worksheet('Investments', st.session_state.investments)
            
            # 5. Fuel
            if is_fuel and ttype == "Expense" and f_dist is not None and f_litres is not None:
                fuel_row = [date.strftime('%Y-%m-%d'), f_dist, f_litres, amount]
                st.session_state.fuel = pd.concat([st.session_state.fuel, pd.DataFrame([{
                    'Date': date.strftime('%Y-%m-%d'),
                    'Distance (km)': f_dist,
                    'Fuel (L)': f_litres,
                    'Cost (₹)': amount
                }])], ignore_index=True)
                update_worksheet('FuelTracker', st.session_state.fuel)
            
            # 6. Auto-sync Category to Budget
            if category not in budget_cats and category not in ['Transfer', 'Hand Loan']:
                new_budget_row = pd.DataFrame({
                    'Category': [category],
                    'Current Month Budget': [0.0],
                    'Previous Month Budget': [0.0],
                    'Actual This Month': [amount if ttype == 'Expense' else 0.0]
                })
                st.session_state.budget = pd.concat([st.session_state.budget, new_budget_row], ignore_index=True)
                update_worksheet('Budget', st.session_state.budget)
            
            # 7. Update Budget Actual
            if ttype in ['Expense', 'Investment']:
                if category in st.session_state.budget['Category'].values:
                    cat_idx = st.session_state.budget[st.session_state.budget['Category'] == category].index[0]
                    current_actual = st.session_state.budget.loc[cat_idx, 'Actual This Month']
                    st.session_state.budget.loc[cat_idx, 'Actual This Month'] = current_actual + amount
                    update_worksheet('Budget', st.session_state.budget)
            
            success_msg = "✅ Transaction Saved Successfully! (Balances, Budget, EMI, Fuel, Investments updated)"
        except Exception as e:
            error_msg = f"❌ Error: {e}"
        
        if success_msg:
            st.success(success_msg)
        if error_msg:
            st.error(error_msg)
        
        # 🔥 FIX: Safe Radio Navigation + Cache Clear
        try:
            st.session_state['nav_radio'] = "🏠 Home"
        except:
            pass
        st.session_state.page = "🏠 Home"
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### 🗑️ Delete a Transaction")
    if not st.session_state.transactions.empty:
        df_del = st.session_state.transactions.copy()
        df_del['Display'] = df_del['Date'].astype(str).fillna('') + " | " + df_del['Description'].astype(str).fillna('') + " | ₹" + df_del['Amount'].astype(str).fillna('0')
        to_delete = st.selectbox("Select transaction to delete", df_del['Display'])
        if st.button("🗑️ Delete Selected Transaction"):
            success_msg = None
            error_msg = None
            try:
                idx = df_del[df_del['Display'] == to_delete].index[0]
                tx = st.session_state.transactions.iloc[idx]
                ttype = tx['Type']
                category = tx['Category']
                amount = tx['Amount']
                payment_mode = tx['Payment Mode']
                
                # Reverse budget
                if ttype in ['Expense', 'Investment'] and category in st.session_state.budget['Category'].values:
                    cat_idx = st.session_state.budget[st.session_state.budget['Category'] == category].index[0]
                    st.session_state.budget.loc[cat_idx, 'Actual This Month'] -= amount
                    update_worksheet('Budget', st.session_state.budget)
                
                # Reverse EMI
                if ttype == 'Expense' and 'EMI' in category and not st.session_state.emi.empty:
                    for loan in st.session_state.emi['Loan Name']:
                        if loan in tx['Description'] or loan in category:
                            emi_idx = st.session_state.emi[st.session_state.emi['Loan Name'] == loan].index[0]
                            st.session_state.emi.loc[emi_idx, 'Remaining'] += amount
                            update_worksheet('EmiManager', st.session_state.emi)
                            break
                
                # Reverse Investment
                if ttype == 'Investment':
                    inv_name = None
                    for inv in st.session_state.investments['Name']:
                        if inv in tx['Description'] or inv in category:
                            inv_name = inv
                            break
                    if inv_name and inv_name in st.session_state.investments['Name'].values:
                        idx_inv = st.session_state.investments[st.session_state.investments['Name'] == inv_name].index[0]
                        st.session_state.investments.loc[idx_inv, 'Total Invested'] -= amount
                        if 'Current Value' in st.session_state.investments.columns:
                            st.session_state.investments.loc[idx_inv, 'Current Value'] -= amount
                        update_worksheet('Investments', st.session_state.investments)
                
                # Reverse Fuel
                if ttype == 'Expense' and 'Fuel' in category:
                    fuel_idx = st.session_state.fuel[
                        (st.session_state.fuel['Date'] == tx['Date']) & 
                        (st.session_state.fuel['Cost (₹)'] == amount)
                    ].index
                    if not fuel_idx.empty:
                        st.session_state.fuel = st.session_state.fuel.drop(fuel_idx[0]).reset_index(drop=True)
                        update_worksheet('FuelTracker', st.session_state.fuel)
                
                # Reverse Account Balance
                if ttype != "Transfer":
                    acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                    if not acc_idx.empty:
                        idx = acc_idx[0]
                        default_nature_map = {
                            "Income": "Income",
                            "Expense": "Expense",
                            "Investment": "Expense",
                            "Transfer": "Neutral",
                            "BC": "Expense"
                        }
                        custom_nature = None
                        if ttype in st.session_state.custom_types['TypeName'].values:
                            custom_nature = st.session_state.custom_types[st.session_state.custom_types['TypeName'] == ttype]['Nature'].values[0]
                        nature = custom_nature if custom_nature else default_nature_map.get(ttype, "Income")
                        if nature == "Income":
                            st.session_state.accounts.loc[idx, 'Balance'] -= amount
                        elif nature in ["Expense", "BC"]:
                            st.session_state.accounts.loc[idx, 'Balance'] += amount
                        update_worksheet('Accounts', st.session_state.accounts)
                
                st.session_state.transactions = st.session_state.transactions.drop(idx).reset_index(drop=True)
                update_worksheet('Transactions', st.session_state.transactions)
                success_msg = "✅ Transaction Deleted successfully! (All synced data reversed)"
            except Exception as e:
                error_msg = f"❌ Error: {e}"
            
            if success_msg:
                st.success(success_msg)
            if error_msg:
                st.error(error_msg)
            
            # 🔥 FIX: Safe Radio Navigation + Cache Clear
            try:
                st.session_state['nav_radio'] = "🏠 Home"
            except:
                pass
            st.session_state.page = "🏠 Home"
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("No transactions available to delete.")

# ===================== BUDGET =====================
elif st.session_state.page == "🎯 Budget":
    st.subheader("🎯 Budget Planner (Monthly)")
    
    df = st.session_state.budget
    master_budget = st.session_state.master_budget
    
    total_budget_val = df['Current Month Budget'].sum()
    total_spent_val = df['Actual This Month'].sum()
    total_prev_val = df['Previous Month Budget'].sum()
    
    effective_cap = master_budget if master_budget > 0 else total_budget_val
    remaining_val = effective_cap - total_spent_val
    
    st.markdown("### 📊 Monthly Overview")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>💰 Category Budget</div><div class='sheet-card-value'>{format_currency(total_budget_val)}</div></div>", unsafe_allow_html=True)
    with col_t2:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>🎯 Master Cap</div><div class='sheet-card-value'>{format_currency(master_budget) if master_budget>0 else 'Not Set'}</div></div>", unsafe_allow_html=True)
    with col_t3:
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>📉 Total Spent</div><div class='sheet-card-value' style='color:#ef4444;'>{format_currency(total_spent_val)}</div></div>", unsafe_allow_html=True)
    with col_t4:
        status_color = "#10b981" if remaining_val >= 0 else "#ef4444"
        status_text = "✅ On Track" if remaining_val >= 0 else "⚠️ Over Budget"
        st.markdown(f"<div class='sheet-card'><div class='sheet-card-header'>✅ Remaining</div><div class='sheet-card-value' style='color:{status_color};'>{format_currency(remaining_val)}</div><div class='sheet-card-sub'>{status_text}</div></div>", unsafe_allow_html=True)

    with st.expander("✏️ Set Overall Monthly Budget Cap"):
        new_master = st.number_input("Enter your ideal monthly budget cap (₹)", value=master_budget, step=500.0)
        if st.button("Save Master Budget Cap"):
            st.session_state.master_budget = new_master
            update_settings('master_budget', new_master)
            st.cache_data.clear()
            st.success(f"Master budget cap set to {format_currency(new_master)}!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Category Breakdown")
    
    df_display = df.copy()
    df_display['Diff'] = df_display['Current Month Budget'] - df_display['Previous Month Budget']
    df_display['Progress'] = (df_display['Actual This Month'] / df_display['Current Month Budget'] * 100).fillna(0).round(1)
    
    total_progress = (total_spent_val / total_budget_val * 100) if total_budget_val > 0 else 0
    total_row = pd.DataFrame({
        'Category': ['💰 TOTAL'],
        'Current Month Budget': [total_budget_val],
        'Previous Month Budget': [total_prev_val],
        'Actual This Month': [total_spent_val],
        'Diff': [total_budget_val - total_prev_val],
        'Progress': [total_progress]
    })
    df_display = pd.concat([df_display, total_row], ignore_index=True)
    
    st.dataframe(df_display.style.format({
        'Current Month Budget': '₹ {:.0f}', 'Previous Month Budget': '₹ {:.0f}',
        'Actual This Month': '₹ {:.0f}', 'Diff': '₹ {:.0f}', 'Progress': '{:.1f}%'
    }), use_container_width=True, hide_index=True)

    with st.expander("✏️ Add / Edit Budget Category"):
        st.markdown("#### 🗑️ Delete a Category")
        if not df.empty:
            del_cat = st.selectbox("Select category to delete", df['Category'])
            if st.button("🗑️ Delete Selected Category"):
                idx = df[df['Category'] == del_cat].index[0]
                st.session_state.budget = df.drop(idx).reset_index(drop=True)
                update_worksheet('Budget', st.session_state.budget)
                st.cache_data.clear()
                st.success(f"Category '{del_cat}' deleted!")
                st.rerun()
        else:
            st.info("No categories to delete.")

        st.markdown("---")
        st.markdown("### ✏️ Edit Category (Actual This Month auto-updates from Transactions)")
        new_cat = st.text_input("New Category Name (Leave blank to edit existing)")
        sel_cat = st.selectbox("Or select existing to edit", df['Category'].tolist() + ["New"])
        
        curr = st.number_input("Current Month Budget ₹", min_value=0.0, step=100.0)
        prev = st.number_input("Previous Month Budget ₹", min_value=0.0, step=100.0)
        
        if st.button("Save / Update Budget"):
            if new_cat:
                new_row = pd.DataFrame({
                    'Category': [new_cat],
                    'Current Month Budget': [curr],
                    'Previous Month Budget': [prev],
                    'Actual This Month': [0.0]
                })
                st.session_state.budget = pd.concat([st.session_state.budget, new_row], ignore_index=True)
            else:
                idx = df[df['Category'] == sel_cat].index
                if not idx.empty:
                    st.session_state.budget.loc[idx, 'Current Month Budget'] = curr
                    st.session_state.budget.loc[idx, 'Previous Month Budget'] = prev
            update_worksheet('Budget', st.session_state.budget)
            st.cache_data.clear()
            st.success("Budget Updated!")
            st.rerun()

# ===================== BANK =====================
elif st.session_state.page == "🏦 Bank":
    st.subheader("🏦 My Accounts")
    st.dataframe(st.session_state.accounts.style.format({'Balance': '₹ {:.0f}'}), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 💰 Quick Actions")
    
    # 1. Add Money
    with st.expander("➕ Add Money"):
        acc_add = st.selectbox("Select Account", st.session_state.accounts['Account'], key='add_acc')
        amt_add = st.number_input("Amount ₹", min_value=0.0, step=100.0, key='add_amt')
        desc_add = st.text_input("Description (optional)", value="Cash Deposit", key='add_desc')
        if st.button("Add Money", key="add_money_btn"):
            if amt_add > 0:
                idx = st.session_state.accounts[st.session_state.accounts['Account'] == acc_add].index[0]
                st.session_state.accounts.loc[idx, 'Balance'] += amt_add
                # Create transaction
                new_row = [datetime.now().strftime('%Y-%m-%d'), desc_add, "Deposit", amt_add, "Income", acc_add, '✅']
                new_df = pd.DataFrame([{
                    'Date': datetime.now().strftime('%Y-%m-%d'), 'Description': desc_add, 'Category': "Deposit",
                    'Amount': amt_add, 'Type': "Income", 'Payment Mode': acc_add, 'Status': '✅'
                }])
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                append_to_worksheet('Transactions', new_row)
                update_worksheet('Accounts', st.session_state.accounts)
                st.success(f"✅ {format_currency(amt_add)} added to {acc_add}")
                
                try:
                    st.session_state['nav_radio'] = "🏠 Home"
                except:
                    pass
                st.session_state.page = "🏠 Home"
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Amount must be greater than 0.")

    # 2. Withdraw Money
    with st.expander("➖ Withdraw Money"):
        acc_with = st.selectbox("Select Account", st.session_state.accounts['Account'], key='with_acc')
        amt_with = st.number_input("Amount ₹", min_value=0.0, step=100.0, key='with_amt')
        desc_with = st.text_input("Description (optional)", value="Cash Withdrawal", key='with_desc')
        if st.button("Withdraw", key="withdraw_btn"):
            if amt_with > 0:
                idx = st.session_state.accounts[st.session_state.accounts['Account'] == acc_with].index[0]
                current_bal = st.session_state.accounts.loc[idx, 'Balance']
                if current_bal >= amt_with:
                    st.session_state.accounts.loc[idx, 'Balance'] -= amt_with
                    # Create transaction
                    new_row = [datetime.now().strftime('%Y-%m-%d'), desc_with, "Withdrawal", amt_with, "Expense", acc_with, '✅']
                    new_df = pd.DataFrame([{
                        'Date': datetime.now().strftime('%Y-%m-%d'), 'Description': desc_with, 'Category': "Withdrawal",
                        'Amount': amt_with, 'Type': "Expense", 'Payment Mode': acc_with, 'Status': '✅'
                    }])
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                    append_to_worksheet('Transactions', new_row)
                    update_worksheet('Accounts', st.session_state.accounts)
                    st.success(f"✅ {format_currency(amt_with)} withdrawn from {acc_with}")
                    
                    try:
                        st.session_state['nav_radio'] = "🏠 Home"
                    except:
                        pass
                    st.session_state.page = "🏠 Home"
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Insufficient balance!")
            else:
                st.error("Amount must be greater than 0.")

    # 3. Transfer
    with st.expander("🔄 Transfer"):
        from_acc = st.selectbox("From Account", st.session_state.accounts['Account'], key='trans_from')
        to_acc = st.selectbox("To Account", st.session_state.accounts['Account'], key='trans_to')
        amt_trans = st.number_input("Amount ₹", min_value=0.0, step=100.0, key='trans_amt')
        desc_trans = st.text_input("Description (optional)", value="Internal Transfer", key='trans_desc')
        if st.button("Transfer", key="transfer_btn"):
            if amt_trans > 0:
                if from_acc == to_acc:
                    st.error("From and To accounts must be different.")
                else:
                    from_idx = st.session_state.accounts[st.session_state.accounts['Account'] == from_acc].index[0]
                    from_bal = st.session_state.accounts.loc[from_idx, 'Balance']
                    if from_bal >= amt_trans:
                        to_idx = st.session_state.accounts[st.session_state.accounts['Account'] == to_acc].index[0]
                        st.session_state.accounts.loc[from_idx, 'Balance'] -= amt_trans
                        st.session_state.accounts.loc[to_idx, 'Balance'] += amt_trans
                        # Create transaction
                        new_row = [datetime.now().strftime('%Y-%m-%d'), f"{desc_trans} (From {from_acc} to {to_acc})", "Transfer", amt_trans, "Transfer", f"{from_acc} -> {to_acc}", '✅']
                        new_df = pd.DataFrame([{
                            'Date': datetime.now().strftime('%Y-%m-%d'), 
                            'Description': f"{desc_trans} (From {from_acc} to {to_acc})", 
                            'Category': "Transfer",
                            'Amount': amt_trans, 
                            'Type': "Transfer", 
                            'Payment Mode': f"{from_acc} -> {to_acc}", 
                            'Status': '✅'
                        }])
                        st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                        append_to_worksheet('Transactions', new_row)
                        update_worksheet('Accounts', st.session_state.accounts)
                        st.success(f"✅ {format_currency(amt_trans)} transferred from {from_acc} to {to_acc}")
                        
                        try:
                            st.session_state['nav_radio'] = "🏠 Home"
                        except:
                            pass
                        st.session_state.page = "🏠 Home"
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Insufficient balance in source account!")
            else:
                st.error("Amount must be greater than 0.")

    # 🔴 Reset All Balances to Zero
    st.markdown("---")
    with st.expander("⚠️ Reset All Account Balances to Zero"):
        st.error("This will set all bank, wallet, and cash balances to ₹0. This action cannot be undone.")
        if st.button("✅ Yes, Reset All Balances to ₹0", key="reset_balances_btn"):
            st.session_state.accounts['Balance'] = 0.0
            update_worksheet('Accounts', st.session_state.accounts)
            st.cache_data.clear()
            st.success("✅ All account balances reset to ₹0!")
            
            try:
                st.session_state['nav_radio'] = "🏠 Home"
            except:
                pass
            st.session_state.page = "🏠 Home"
            st.rerun()

# ===================== MORE (Premium Modules) =====================
elif st.session_state.page == "⚡ More":
    st.subheader("🚀 Premium Modules")
    tabs = st.tabs(["📈 Investments", "🏦 EMI", "🎯 Goals", "📊 Reports", "⚙️ Customization", "📋 All Transactions"])
    
    # ---------- Investments ----------
    with tabs[0]:
        st.dataframe(st.session_state.investments, hide_index=True, use_container_width=True)
        with st.expander("➕ Add / Edit Investment"):
            inv_name = st.text_input("Investment Name")
            inv_type = st.selectbox("Type", ["SIP", "Gold", "MF", "Stock", "Other"])
            freq = st.selectbox("Frequency", ["Monthly", "Weekly"])
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
    
    # ---------- EMI ----------
    with tabs[1]:
        st.dataframe(st.session_state.emi, hide_index=True, use_container_width=True)
        with st.expander("➕ Add EMI (One-time setup)"):
            st.info("Add your EMI loan details here. After this, future payments will be auto-synced from transactions.")
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
    
    # ---------- Goals ----------
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
    
    # ---------- Reports ----------
    with tabs[3]:
        st.markdown("### 📊 Monthly Analysis")
        df = st.session_state.transactions
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date'].dt.month_name()
            
            # 1. Income vs Expense
            inc = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
            exp = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
            merged = pd.merge(inc, exp, on='Month', how='outer').fillna(0)
            merged.columns = ['Month','Income','Expense']
            fig1 = px.bar(merged, x='Month', y=['Income','Expense'], barmode='group', color_discrete_map={'Income':'#10b981', 'Expense':'#ef4444'})
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6', margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig1, use_container_width=True)
            
            # 2. Expense Breakdown
            df_exp = df[df['Type']=='Expense'].groupby('Category')['Amount'].sum().reset_index()
            if not df_exp.empty:
                fig2 = px.pie(df_exp, names='Category', values='Amount', title="🧾 Expense Breakdown", hole=0.3)
                fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6', margin=dict(l=0,r=0,t=30,b=0))
                st.plotly_chart(fig2, use_container_width=True)
            
            # 3. Fuel
            fuel_df = st.session_state.fuel
            if not fuel_df.empty:
                fuel_df['Date'] = pd.to_datetime(fuel_df['Date'])
                fuel_df['Month'] = fuel_df['Date'].dt.month_name()
                fuel_monthly = fuel_df.groupby('Month')['Cost (₹)'].sum().reset_index()
                fig3 = px.bar(fuel_monthly, x='Month', y='Cost (₹)', title="⛽ Fuel Cost Per Month", color_discrete_sequence=['#f59e0b'])
                fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6', margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig3, use_container_width=True)
            
            # 4. EMI
            emi_tx = df[(df['Category']=='EMI') & (df['Type']=='Expense')]
            if not emi_tx.empty:
                emi_monthly = emi_tx.groupby('Month')['Amount'].sum().reset_index()
                fig4 = px.bar(emi_monthly, x='Month', y='Amount', title="🏦 EMI Payments Per Month", color_discrete_sequence=['#ef4444'])
                fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6', margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig4, use_container_width=True)
            
            # 5. Investment (SIP+Gold)
            inv_df = st.session_state.investments
            if not inv_df.empty:
                total_inv = inv_df[inv_df['Name'].str.upper().isin(['SIP','GOLD'])]['Total Invested'].sum()
                curr_val = inv_df[inv_df['Name'].str.upper().isin(['SIP','GOLD'])]['Current Value'].sum()
                if total_inv > 0:
                    st.info(f"📈 Investment (SIP+Gold): Total Invested: {format_currency(total_inv)} | Current Value: {format_currency(curr_val)} | ROI: {((curr_val/total_inv)-1)*100:.1f}%")
                
                inv_compare = inv_df[inv_df['Name'].str.upper().isin(['SIP','GOLD'])].copy()
                if not inv_compare.empty:
                    fig5 = px.bar(inv_compare, x='Name', y=['Total Invested', 'Current Value'], barmode='group', title="📈 SIP & Gold Performance")
                    fig5.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6', margin=dict(l=0,r=0,t=20,b=0))
                    st.plotly_chart(fig5, use_container_width=True)
            
            # 6. BC
            bc_tx = df[df['Type']=='BC']
            if not bc_tx.empty:
                bc_monthly = bc_tx.groupby('Month')['Amount'].sum().reset_index()
                fig6 = px.bar(bc_monthly, x='Month', y='Amount', title="💳 BC (Bachat Gat) Per Month", color_discrete_sequence=['#3b82f6'])
                fig6.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#f1f3f6', margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("Add some transactions to see detailed reports.")
    
    # ---------- Customization ----------
    with tabs[4]:
        st.markdown("### ⚙️ Custom Types, Categories & Natures")
        st.info("Add your own Transaction Types, Categories, and Natures. They will appear in the Add Transaction dropdowns.")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("#### 📌 Custom Types")
            if not st.session_state.custom_types.empty:
                st.dataframe(st.session_state.custom_types, hide_index=True, use_container_width=True)
            else:
                st.info("No custom types added yet.")
            
            with st.form("add_custom_type"):
                type_name = st.text_input("Type Name")
                type_nature = st.selectbox("Nature", st.session_state.custom_natures['Nature'].tolist())
                if st.form_submit_button("Add Type"):
                    if type_name:
                        new_type = pd.DataFrame({'TypeName':[type_name], 'Nature':[type_nature]})
                        st.session_state.custom_types = pd.concat([st.session_state.custom_types, new_type], ignore_index=True)
                        update_worksheet('CustomTypes', st.session_state.custom_types)
                        st.cache_data.clear()
                        st.success(f"Type '{type_name}' added!")
                        st.rerun()
            
            if not st.session_state.custom_types.empty:
                type_to_del = st.selectbox("Delete a Custom Type", st.session_state.custom_types['TypeName'])
                if st.button("🗑️ Delete Type"):
                    idx = st.session_state.custom_types[st.session_state.custom_types['TypeName'] == type_to_del].index[0]
                    st.session_state.custom_types = st.session_state.custom_types.drop(idx).reset_index(drop=True)
                    update_worksheet('CustomTypes', st.session_state.custom_types)
                    st.cache_data.clear()
                    st.success(f"Type '{type_to_del}' deleted!")
                    st.rerun()
        
        with col_t2:
            st.markdown("#### 🏷️ Custom Categories")
            if not st.session_state.custom_categories.empty:
                st.dataframe(st.session_state.custom_categories, hide_index=True, use_container_width=True)
            else:
                st.info("No custom categories added yet.")
            
            with st.form("add_custom_category"):
                cat_name = st.text_input("Category Name")
                if st.form_submit_button("Add Category"):
                    if cat_name:
                        new_cat = pd.DataFrame({'Category':[cat_name]})
                        st.session_state.custom_categories = pd.concat([st.session_state.custom_categories, new_cat], ignore_index=True)
                        update_worksheet('CustomCategories', st.session_state.custom_categories)
                        st.cache_data.clear()
                        st.success(f"Category '{cat_name}' added!")
                        st.rerun()
            
            if not st.session_state.custom_categories.empty:
                cat_to_del = st.selectbox("Delete a Custom Category", st.session_state.custom_categories['Category'])
                if st.button("🗑️ Delete Category"):
                    idx = st.session_state.custom_categories[st.session_state.custom_categories['Category'] == cat_to_del].index[0]
                    st.session_state.custom_categories = st.session_state.custom_categories.drop(idx).reset_index(drop=True)
                    update_worksheet('CustomCategories', st.session_state.custom_categories)
                    st.cache_data.clear()
                    st.success(f"Category '{cat_to_del}' deleted!")
                    st.rerun()
        
        # Custom Natures
        st.markdown("#### 🌿 Custom Natures")
        st.info("Add new natures like 'Neutral', 'Credit', 'Debit'. (Default 'Income' and 'Expense' are protected and cannot be deleted.)")
        if not st.session_state.custom_natures.empty:
            st.dataframe(st.session_state.custom_natures, hide_index=True, use_container_width=True)
        else:
            st.info("No custom natures added yet.")
        
        with st.form("add_custom_nature"):
            nature_name = st.text_input("Nature Name")
            if st.form_submit_button("Add Nature"):
                if nature_name:
                    if nature_name in st.session_state.custom_natures['Nature'].values:
                        st.warning("Nature already exists.")
                    else:
                        new_nature = pd.DataFrame({'Nature':[nature_name]})
                        st.session_state.custom_natures = pd.concat([st.session_state.custom_natures, new_nature], ignore_index=True)
                        update_worksheet('CustomNatures', st.session_state.custom_natures)
                        st.cache_data.clear()
                        st.success(f"Nature '{nature_name}' added!")
                        st.rerun()
        
        if not st.session_state.custom_natures.empty:
            deletable_natures = st.session_state.custom_natures[~st.session_state.custom_natures['Nature'].isin(['Income', 'Expense'])]
            if not deletable_natures.empty:
                nature_to_del = st.selectbox("Delete a Custom Nature", deletable_natures['Nature'])
                if st.button("🗑️ Delete Nature"):
                    idx = st.session_state.custom_natures[st.session_state.custom_natures['Nature'] == nature_to_del].index[0]
                    st.session_state.custom_natures = st.session_state.custom_natures.drop(idx).reset_index(drop=True)
                    update_worksheet('CustomNatures', st.session_state.custom_natures)
                    st.cache_data.clear()
                    st.success(f"Nature '{nature_to_del}' deleted!")
                    st.rerun()
            else:
                st.info("Only custom natures can be deleted. 'Income' and 'Expense' are default.")
    
    # ---------- All Transactions ----------
    with tabs[5]:
        st.markdown("### 📋 All Transactions")
        df = st.session_state.transactions
        if not df.empty:
            st.dataframe(df.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)
            st.markdown("#### 🗑️ Delete a Transaction")
            if not df.empty:
                df_del = df.copy()
                df_del['Display'] = df_del['Date'].astype(str) + " | " + df_del['Description'].astype(str) + " | ₹" + df_del['Amount'].astype(str)
                to_delete = st.selectbox("Select transaction to delete", df_del['Display'])
                if st.button("🗑️ Delete Selected Transaction"):
                    success_msg = None
                    error_msg = None
                    try:
                        idx = df_del[df_del['Display'] == to_delete].index[0]
                        tx = st.session_state.transactions.iloc[idx]
                        ttype = tx['Type']
                        category = tx['Category']
                        amount = tx['Amount']
                        payment_mode = tx['Payment Mode']
                        
                        # Reverse budget, EMI, Investment, Fuel, Account Balance (same logic)
                        if ttype in ['Expense', 'Investment'] and category in st.session_state.budget['Category'].values:
                            cat_idx = st.session_state.budget[st.session_state.budget['Category'] == category].index[0]
                            st.session_state.budget.loc[cat_idx, 'Actual This Month'] -= amount
                            update_worksheet('Budget', st.session_state.budget)
                        
                        if ttype == 'Expense' and 'EMI' in category and not st.session_state.emi.empty:
                            for loan in st.session_state.emi['Loan Name']:
                                if loan in tx['Description'] or loan in category:
                                    emi_idx = st.session_state.emi[st.session_state.emi['Loan Name'] == loan].index[0]
                                    st.session_state.emi.loc[emi_idx, 'Remaining'] += amount
                                    update_worksheet('EmiManager', st.session_state.emi)
                                    break
                        
                        if ttype == 'Investment':
                            inv_name = None
                            for inv in st.session_state.investments['Name']:
                                if inv in tx['Description'] or inv in category:
                                    inv_name = inv
                                    break
                            if inv_name and inv_name in st.session_state.investments['Name'].values:
                                idx_inv = st.session_state.investments[st.session_state.investments['Name'] == inv_name].index[0]
                                st.session_state.investments.loc[idx_inv, 'Total Invested'] -= amount
                                if 'Current Value' in st.session_state.investments.columns:
                                    st.session_state.investments.loc[idx_inv, 'Current Value'] -= amount
                                update_worksheet('Investments', st.session_state.investments)
                        
                        if ttype == 'Expense' and 'Fuel' in category:
                            fuel_idx = st.session_state.fuel[
                                (st.session_state.fuel['Date'] == tx['Date']) & 
                                (st.session_state.fuel['Cost (₹)'] == amount)
                            ].index
                            if not fuel_idx.empty:
                                st.session_state.fuel = st.session_state.fuel.drop(fuel_idx[0]).reset_index(drop=True)
                                update_worksheet('FuelTracker', st.session_state.fuel)
                        
                        if ttype != "Transfer":
                            acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                            if not acc_idx.empty:
                                idx = acc_idx[0]
                                default_nature_map = {
                                    "Income": "Income",
                                    "Expense": "Expense",
                                    "Investment": "Expense",
                                    "Transfer": "Neutral",
                                    "BC": "Expense"
                                }
                                custom_nature = None
                                if ttype in st.session_state.custom_types['TypeName'].values:
                                    custom_nature = st.session_state.custom_types[st.session_state.custom_types['TypeName'] == ttype]['Nature'].values[0]
                                nature = custom_nature if custom_nature else default_nature_map.get(ttype, "Income")
                                if nature == "Income":
                                    st.session_state.accounts.loc[idx, 'Balance'] -= amount
                                elif nature in ["Expense", "BC"]:
                                    st.session_state.accounts.loc[idx, 'Balance'] += amount
                                update_worksheet('Accounts', st.session_state.accounts)
                        
                        st.session_state.transactions = st.session_state.transactions.drop(idx).reset_index(drop=True)
                        update_worksheet('Transactions', st.session_state.transactions)
                        success_msg = "✅ Transaction Deleted successfully!"
                    except Exception as e:
                        error_msg = f"❌ Error: {e}"
                    
                    if success_msg:
                        st.success(success_msg)
                    if error_msg:
                        st.error(error_msg)
                    
                    try:
                        st.session_state['nav_radio'] = "🏠 Home"
                    except:
                        pass
                    st.session_state.page = "🏠 Home"
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.info("No transactions yet.")

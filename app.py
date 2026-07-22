import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import re
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import requests

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="CashDash - Riyaz Pathan", layout="wide", initial_sidebar_state="collapsed")

# ---------- LIGHT THEME (NO DARK MODE) ----------
BG_GRADIENT = "linear-gradient(135deg, #e0e7ff 0%, #f0e6ff 50%, #fce4ec 100%)"

CSS = f"""
<style>
    .stApp {{
        background: {BG_GRADIENT};
        min-height: 100vh;
    }}
    .custom-header {{
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #d946ef);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 10px rgba(99, 102, 241, 0.2);
        display: inline-block;
    }}
    .custom-badge {{
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(4px);
        border-radius: 30px;
        padding: 4px 16px;
        font-size: 0.8rem;
        color: #4f46e5;
        border: 1px solid rgba(255, 255, 255, 0.4);
        display: inline-block;
        margin-left: 12px;
    }}
    .greeting-text {{
        color: #1e293b;
        font-size: 1.2rem;
        font-weight: 500;
    }}
    .sheet-card {{
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 16px 20px;
        margin-bottom: 16px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        text-align: center;
        transition: all 0.3s ease;
    }}
    .sheet-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
    }}
    .sheet-card-header {{
        color: #64748b;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .sheet-card-value {{
        font-size: 1.6rem;
        font-weight: 700;
    }}
    .sheet-card-sub {{
        font-size: 0.55rem;
        color: #94a3b8;
        margin-top: 4px;
    }}
    .progress-bar {{
        width: 100%;
        height: 6px;
        background: #e2e8f0;
        border-radius: 10px;
        margin: 6px 0;
        overflow: hidden;
    }}
    .progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        border-radius: 10px;
        transition: width 0.5s ease;
    }}
    .stButton button {{
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        border: none;
        background: #6366f1;
        color: white;
        padding: 12px 0;
        transition: 0.3s;
    }}
    .stButton button:hover {{
        background: #4f46e5;
        transform: scale(1.02);
    }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    @media (max-width: 768px) {{
        .sheet-card {{ padding: 10px 12px; min-width: 60px; }}
        .sheet-card-value {{ font-size: 1.2rem; }}
        .stColumns {{ flex-wrap: wrap !important; }}
        .stColumn {{ flex: 1 1 45% !important; min-width: 60px; }}
    }}
    @media (max-width: 480px) {{
        .stColumn {{ flex: 1 1 100% !important; }}
    }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------- HEADER WITH GREETING ----------
def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "🌅 Good Morning"
    elif 12 <= hour < 17:
        return "☀️ Good Afternoon"
    elif 17 <= hour < 21:
        return "🌇 Good Evening"
    else:
        return "🌙 Good Night"

greeting = get_greeting()
st.markdown(f"""
<div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 10px 0;'>
    <div>
        <span class='custom-header'>💎 CashDash</span>
        <span class='custom-badge'>Riyaz Pathan</span>
    </div>
    <div>
        <span class='greeting-text'>{greeting}, Riyaz! 👋</span>
        <span style='color:#94a3b8; margin-left: 10px; font-size:0.9rem;'>📅 {datetime.now().strftime('%d %b %Y')}</span>
    </div>
</div>
<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.3); margin: 5px 0 20px 0;'>
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

# ---------- CACHED DATA LOAD ----------
@st.cache_data(ttl=60)
def load_all_sheets():
    gc = get_gsheet_client()
    if gc is None:
        return {}
    data = {}
    worksheet_names = ['Transactions', 'Budget', 'Accounts', 'Investments', 'EmiManager',
                       'Goals', 'FuelTracker', 'Settings', 'CustomTypes', 'CustomCategories', 'CustomNatures', 'Recurring']
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

# ---------- LIVE PRICE FUNCTIONS (PHONEPE / MCX GOLD & AXIS MF) ----------
@st.cache_data(ttl=3600)
def get_gold_price_inr_per_gram():
    try:
        gold = yf.Ticker("GC=F")
        data = gold.history(period="1d")
        usd_per_ounce = data['Close'].iloc[-1]
        usd_inr = yf.Ticker("USDINR=X")
        rate_data = usd_inr.history(period="1d")
        inr_per_usd = rate_data['Close'].iloc[-1]
        price_per_gram = (usd_per_ounce * inr_per_usd) / 31.1035
        return round(price_per_gram, 2)
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_axis_gold_fund_nav():
    try:
        scheme_code = 120724  # Axis Gold Fund Regular Growth
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            nav = float(data['data'][0]['nav'])
            return round(nav, 4)
        else:
            return None
    except Exception as e:
        return None

# ---------- AI SUBSCRIPTION DETECTIVE ----------
def detect_subscription_anomalies():
    df = st.session_state.transactions
    if df.empty:
        return []
    df['Date'] = pd.to_datetime(df['Date'])
    df = df[df['Type'] == 'Expense']
    if df.empty:
        return []
    desc_counts = df['Description'].value_counts()
    recurring_desc = desc_counts[desc_counts >= 2].index.tolist()
    alerts = []
    telecom_keywords = ['jio', 'airtel', 'vi', 'vodafone', 'recharge']
    for desc in recurring_desc:
        sub_df = df[df['Description'] == desc].sort_values('Date')
        if len(sub_df) >= 2:
            prices = sub_df['Amount'].values
            if len(prices) >= 2 and prices[-1] != prices[0]:
                is_telecom = any(kw in desc.lower() for kw in telecom_keywords)
                if is_telecom:
                    alerts.append(f"⚠️ AI Detective: Your {desc} recharge price increased from ₹{prices[0]:.0f} to ₹{prices[-1]:.0f}!")
                else:
                    alerts.append(f"⚠️ AI Detective: {desc} charges changed from ₹{prices[0]:.0f} to ₹{prices[-1]:.0f}.")
    return alerts

# ---------- CLEANUP AUTO ENTRIES ----------
def cleanup_auto_entries():
    if 'auto_entries_cleaned' in st.session_state:
        return
    if 'transactions' not in st.session_state or st.session_state.transactions.empty:
        st.session_state.auto_entries_cleaned = True
        return
    desc_to_remove = ["Daily Gold Saving", "Axis Gold Fund (SIP)"]
    old_len = len(st.session_state.transactions)
    st.session_state.transactions = st.session_state.transactions[
        ~st.session_state.transactions['Description'].isin(desc_to_remove)
    ]
    new_len = len(st.session_state.transactions)
    if old_len != new_len:
        update_worksheet('Transactions', st.session_state.transactions)
    st.session_state.auto_entries_cleaned = True

# ---------- SESSION STATE ----------
def init_session_state():
    all_data = load_all_sheets()

    # Transactions
    loaded = all_data.get('Transactions', pd.DataFrame())
    required_cols = ['Date','Description','Category','Amount','Type','Payment Mode','Status']
    if loaded.empty or not all(c in loaded.columns for c in required_cols):
        st.session_state.transactions = pd.DataFrame(columns=required_cols)
    else:
        st.session_state.transactions = loaded
    cleanup_auto_entries()

    # Budget
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

    # Accounts - ensure BC account exists
    loaded = all_data.get('Accounts', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Account','Balance']):
        st.session_state.accounts = pd.DataFrame({
            'Account': ['BOB Bank', 'BOM Bank', 'PhonePe Wallet', 'Cash', '💳 BC (Bachat Gat)'],
            'Balance': [0, 0, 0, 0, 0]
        })
    else:
        if '💳 BC (Bachat Gat)' not in loaded['Account'].values:
            new_row = pd.DataFrame({'Account': ['💳 BC (Bachat Gat)'], 'Balance': [0]})
            loaded = pd.concat([loaded, new_row], ignore_index=True)
        st.session_state.accounts = loaded

    # Investments - ensure Units column
    loaded = all_data.get('Investments', pd.DataFrame())
    if not loaded.empty and 'Name' in loaded.columns:
        loaded = loaded[loaded['Name'].notna() & (loaded['Name'].astype(str).str.strip() != '')]
    req_inv_cols = ['Name','Type','Amount','Frequency','Total Invested','Current Value']
    if loaded.empty or not all(c in loaded.columns for c in req_inv_cols):
        st.session_state.investments = pd.DataFrame(columns=req_inv_cols + ['Units'])
    else:
        if 'Units' not in loaded.columns:
            loaded['Units'] = 0.0
        st.session_state.investments = loaded

    # ---- FIX: Convert columns to float to avoid Pandas int assignment TypeError ----
    if 'Current Value' in st.session_state.investments.columns:
        st.session_state.investments['Current Value'] = st.session_state.investments['Current Value'].astype(float)
    if 'Total Invested' in st.session_state.investments.columns:
        st.session_state.investments['Total Invested'] = st.session_state.investments['Total Invested'].astype(float)
    if 'Units' in st.session_state.investments.columns:
        st.session_state.investments['Units'] = st.session_state.investments['Units'].astype(float)

    # EMI
    loaded = all_data.get('EmiManager', pd.DataFrame())
    required_emi_cols = ['Lender','Total Loan','EMI Amount','Tenure (Months)','Interest Charged',
                         'Net Disbursed','Total Due','Remaining Due','Next Due Date','Frequency',
                         'Installment Day','Schedule','Installments Paid','Status']
    if loaded.empty or not all(c in loaded.columns for c in required_emi_cols):
        st.session_state.emi = pd.DataFrame(columns=required_emi_cols)
    else:
        st.session_state.emi = loaded

    # Goals
    loaded = all_data.get('Goals', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Goal Name','Target','Saved']):
        st.session_state.goals = pd.DataFrame(columns=['Goal Name', 'Target', 'Saved'])
    else:
        st.session_state.goals = loaded

    # Fuel
    loaded = all_data.get('FuelTracker', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Date','Distance (km)','Fuel (L)','Cost (₹)']):
        st.session_state.fuel = pd.DataFrame(columns=['Date', 'Distance (km)', 'Fuel (L)', 'Cost (₹)'])
    else:
        st.session_state.fuel = loaded

    # Settings
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

    # Custom Types
    loaded = all_data.get('CustomTypes', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['TypeName','Nature']):
        st.session_state.custom_types = pd.DataFrame(columns=['TypeName','Nature'])
    else:
        st.session_state.custom_types = loaded

    # Custom Categories
    loaded = all_data.get('CustomCategories', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Category']):
        st.session_state.custom_categories = pd.DataFrame(columns=['Category'])
    else:
        st.session_state.custom_categories = loaded

    # Custom Natures
    loaded = all_data.get('CustomNatures', pd.DataFrame())
    if loaded.empty or not all(c in loaded.columns for c in ['Nature']):
        st.session_state.custom_natures = pd.DataFrame({'Nature': ['Income', 'Expense']})
    else:
        st.session_state.custom_natures = loaded

    # Recurring
    loaded = all_data.get('Recurring', pd.DataFrame())
    if loaded.empty:
        st.session_state.recurring = pd.DataFrame(columns=['Description','Category','Amount','Type','Payment Mode','Frequency','NextDate'])
    else:
        st.session_state.recurring = loaded

if 'initialized' not in st.session_state:
    init_session_state()
    st.session_state.initialized = True

if 'page' not in st.session_state:
    st.session_state.page = "🏠 Home"

# ---------- HELPER FUNCTIONS ----------
def format_currency(amount):
    return f"₹ {amount:,.0f}"

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
        update_worksheet('Recurring', st.session_state.recurring)
        sync_time = datetime.now().strftime("%d %b %Y, %H:%M:%S")
        update_settings('last_sync_time', sync_time)
        st.session_state.last_sync_time = sync_time
        st.cache_data.clear()
        return True, "✅ All data synced successfully!"
    except Exception as e:
        return False, f"❌ Sync failed: {e}"

# ---------- NAVIGATION ----------
nav = st.radio("Menu", ["🏠 Home", "➕ Add", "🎯 Budget", "🏦 Bank", "⚡ More"], index=0, horizontal=True, key='nav_radio')
st.session_state.page = nav

# ===================== HOME =====================
if st.session_state.page == "🏠 Home":
    st.markdown("## 📊 Dashboard")

    # Live Price Cards for Gold
    live_gold_price = get_gold_price_inr_per_gram()
    if live_gold_price:
        st.markdown(f"""
        <div style='display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;'>
            <div style='background: rgba(255,255,255,0.8); padding: 10px 15px; border-radius: 12px; border-left: 5px solid #f59e0b;'>
                <span style='font-weight:600; color:#64748b;'>🥇 Live Gold (₹/gm)</span>
                <span style='font-weight:800; font-size:1.4rem; color:#f59e0b; margin-left:8px;'>₹{live_gold_price}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Could not fetch Live Gold price. Check internet.")

    alerts = detect_subscription_anomalies()
    for alert in alerts:
        st.warning(alert)

    current_month = datetime.now().strftime('%B')
    df_tx = st.session_state.transactions

    # Account balances
    accounts_df = st.session_state.accounts
    bob_bal = accounts_df.loc[accounts_df['Account']=='BOB Bank', 'Balance'].values[0] if not accounts_df.empty else 0
    bom_bal = accounts_df.loc[accounts_df['Account']=='BOM Bank', 'Balance'].values[0] if not accounts_df.empty else 0
    upi_bal = accounts_df.loc[accounts_df['Account']=='PhonePe Wallet', 'Balance'].values[0] if not accounts_df.empty else 0
    cash_bal = accounts_df.loc[accounts_df['Account']=='Cash', 'Balance'].values[0] if not accounts_df.empty else 0
    bc_bal = accounts_df.loc[accounts_df['Account']=='💳 BC (Bachat Gat)', 'Balance'].values[0] if not accounts_df.empty else 0

    monthly_inc = 0
    monthly_exp = 0
    if not df_tx.empty:
        df_tx['Date'] = pd.to_datetime(df_tx['Date'])
        df_month = df_tx[df_tx['Date'].dt.month_name() == current_month]
        monthly_inc = df_month[df_month['Type']=='Income']['Amount'].sum()
        monthly_exp = df_month[df_month['Type']=='Expense']['Amount'].sum()
    savings = monthly_inc - monthly_exp
    total_budget_val = st.session_state.budget['Current Month Budget'].sum()

    # Investment cards
    inv_df = st.session_state.investments
    total_invested = inv_df['Total Invested'].sum() if not inv_df.empty else 0
    total_current = inv_df['Current Value'].sum() if not inv_df.empty else 0

    if not inv_df.empty and 'Name' in inv_df.columns:
        sip_mask = inv_df['Name'].str.upper().str.contains('SIP', na=False)
        gold_mask = inv_df['Name'].str.upper().str.contains('GOLD', na=False)
        sip_gold_mask = sip_mask | gold_mask
        sip_gold_inv = inv_df.loc[sip_gold_mask, 'Total Invested'].sum() if sip_gold_mask.any() else 0
        sip_gold_curr = inv_df.loc[sip_gold_mask, 'Current Value'].sum() if sip_gold_mask.any() else 0
    else:
        sip_gold_inv = 0
        sip_gold_curr = 0

    # EMI summary
    emi_df = st.session_state.emi
    active_loans = emi_df[emi_df['Status'] == 'Active'] if not emi_df.empty else pd.DataFrame()
    total_emi_remaining = active_loans['Remaining Due'].sum() if not active_loans.empty else 0
    total_emi_monthly = active_loans['EMI Amount'].sum() if not active_loans.empty else 0
    total_emi_tenure = active_loans['Tenure (Months)'].sum() if not active_loans.empty else 0
    total_emi_paid = active_loans['Installments Paid'].sum() if not active_loans.empty else 0

    # Row 1: Bank Accounts
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>🏦 BOB Bank</div>
            <div class='sheet-card-value' style='color:#6366f1;'>{format_currency(bob_bal)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>🏦 BOM Bank</div>
            <div class='sheet-card-value' style='color:#8b5cf6;'>{format_currency(bom_bal)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>📱 PhonePe Wallet</div>
            <div class='sheet-card-value' style='color:#06b6d4;'>{format_currency(upi_bal)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>💵 Cash</div>
            <div class='sheet-card-value' style='color:#10b981;'>{format_currency(cash_bal)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 2: Income, Expense, Budget
    col5, col6, col7 = st.columns(3)
    with col5:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>📈 Total Income</div>
            <div class='sheet-card-value' style='color:#10b981;'>{format_currency(monthly_inc)}</div>
            <div class='sheet-card-sub'>This Month</div>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>📉 Total Expense</div>
            <div class='sheet-card-value' style='color:#ef4444;'>{format_currency(monthly_exp)}</div>
            <div class='sheet-card-sub'>This Month</div>
        </div>
        """, unsafe_allow_html=True)
    with col7:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>🎯 This Month Budget</div>
            <div class='sheet-card-value' style='color:#f59e0b;'>{format_currency(total_budget_val)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 3: Investment Cards
    col_inv1, col_inv2, col_inv3 = st.columns(3)
    with col_inv1:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>📈 Total Investment</div>
            <div class='sheet-card-value' style='color:#8b5cf6;'>{format_currency(total_invested)}</div>
            <div class='sheet-card-sub'>Current Value: {format_currency(total_current)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_inv2:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>🥇 Gold + SIP</div>
            <div class='sheet-card-value' style='color:#f59e0b;'>{format_currency(sip_gold_inv)}</div>
            <div class='sheet-card-sub'>Current Value: {format_currency(sip_gold_curr)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_inv3:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>💳 BC (Bachat Gat)</div>
            <div class='sheet-card-value' style='color:#ec4899;'>{format_currency(bc_bal)}</div>
            <div class='sheet-card-sub'>Your Savings Pool</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 4: EMI Summary
    st.markdown("### 🏦 Loan / EMI Summary")
    if not active_loans.empty:
        col_emi1, col_emi2, col_emi3 = st.columns(3)
        with col_emi1:
            st.markdown(f"""
            <div class='sheet-card'>
                <div class='sheet-card-header'>📊 Total Remaining</div>
                <div class='sheet-card-value' style='color:#ef4444;'>{format_currency(total_emi_remaining)}</div>
                <div class='sheet-card-sub'>Across {len(active_loans)} active loans</div>
            </div>
            """, unsafe_allow_html=True)
        with col_emi2:
            st.markdown(f"""
            <div class='sheet-card'>
                <div class='sheet-card-header'>📆 Monthly EMI</div>
                <div class='sheet-card-value' style='color:#6366f1;'>{format_currency(total_emi_monthly)}</div>
                <div class='sheet-card-sub'>Due on {active_loans.iloc[0]['Installment Day']}th of month</div>
            </div>
            """, unsafe_allow_html=True)
        with col_emi3:
            progress = (total_emi_paid / (total_emi_paid + (total_emi_tenure - total_emi_paid))) * 100 if total_emi_tenure > 0 else 0
            st.markdown(f"""
            <div class='sheet-card'>
                <div class='sheet-card-header'>📈 Progress</div>
                <div class='sheet-card-value' style='color:#10b981;'>{progress:.1f}%</div>
                <div class='progress-bar'>
                    <div class='progress-fill' style='width: {min(progress,100)}%;'></div>
                </div>
                <div class='sheet-card-sub'>{total_emi_paid} / {total_emi_tenure} installments paid</div>
            </div>
            """, unsafe_allow_html=True)

        # Active loans details
        st.markdown("#### 📋 Active Loan Details")
        for idx, row in active_loans.iterrows():
            loan_progress = ((row['Installments Paid'] / row['Tenure (Months)']) * 100) if row['Tenure (Months)'] > 0 else 0
            st.markdown(f"""
            <div style='background: rgba(255,255,255,0.5); border-radius: 12px; padding: 10px 16px; margin-bottom: 8px;'>
                <div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>
                    <span><strong>{row['Lender']}</strong></span>
                    <span>Remaining: {format_currency(row['Remaining Due'])}</span>
                    <span>EMI: {format_currency(row['EMI Amount'])}</span>
                    <span>Progress: {loan_progress:.1f}%</span>
                </div>
                <div class='progress-bar' style='margin-top: 4px;'>
                    <div class='progress-fill' style='width: {min(loan_progress,100)}%;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active loans. Add a loan in ⚡ More → EMI Manager.")

    # Row 5: AI Insights
    st.markdown("### 🤖 AI Insights")
    col_ai1, col_ai2 = st.columns(2)
    with col_ai1:
        if not df_tx.empty:
            top_exp = df_month[df_month['Type']=='Expense'].groupby('Category')['Amount'].sum().sort_values(ascending=False).head(1)
            if not top_exp.empty:
                top_cat = top_exp.index[0]
                top_amt = top_exp.values[0]
                st.info(f"📊 Your top spending category this month is **{top_cat}** (₹{top_amt:.0f}).")
            else:
                st.info("No expenses yet.")
        else:
            st.info("Add transactions to see insights.")
    with col_ai2:
        if monthly_inc > 0:
            rate = (savings / monthly_inc) * 100
            st.info(f"💎 Your savings rate this month is **{rate:.1f}%**.")
        else:
            st.info("No income recorded yet.")

    # Row 6: Recent Transactions
    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        st.table(recent[['Date','Description','Category','Amount','Type']].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0))
    else:
        st.info("No transactions yet.")

    # Row 7: Sync
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
    if 'BC' not in budget_cats:
        budget_cats.append('BC')

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", datetime.now())
        desc = st.text_input("Description")
        amount = st.number_input("Amount ₹", min_value=0.0)
    with col2:
        type_options = ["Expense", "Income", "Transfer", "Investment", "Loan"]
        ttype = st.selectbox("Type", type_options)

        if ttype == "Loan":
            loan_subtype = st.selectbox("Loan Action", ["Loan Taken", "Loan Returned"])
            if loan_subtype == "Loan Taken":
                nature = "Income"
                payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])
                category = "Loan Taken"
                st.info("💡 Loan Taken → Income (balance will increase)")
            else:
                nature = "Expense"
                payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])
                category = "Loan Returned"
                st.info("💡 Loan Returned → Expense (balance will decrease)")
        else:
            if ttype == "Income":
                nature = "Income"
                category = st.selectbox("Category", ["Salary", "Freelance", "Bonus", "Gift", "Other Income"])
                payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])
                st.info("💡 Income → Balance will increase")
            elif ttype == "Expense":
                nature = "Expense"
                category = st.selectbox("Category", budget_cats + ["Other"])
                payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])
                st.info("💡 Expense → Balance will decrease")
            elif ttype == "Transfer":
                nature = "Neutral"
                category = "Transfer"
                payment_mode = "Transfer"
                st.info("💡 Transfer → No balance change (account to account)")
            elif ttype == "Investment":
                nature = "Expense"
                inv_cats = ["SIP", "Gold", "MF", "Stocks", "BC", "Other Investment"]
                category = st.selectbox("Category", inv_cats)
                payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])

                # Units input for Gold/SIP
                units_input = None
                if category in ["Gold", "SIP"]:
                    st.markdown("#### 📊 Units (Optional)")
                    units_input = st.number_input(f"Units for {category} (leave 0 for auto-calc)", min_value=0.0, step=0.001, format="%.4f", value=0.0)
                    if units_input > 0:
                        st.info(f"✅ {units_input:.4f} units will be added to this investment.")
                    else:
                        st.info("💡 Units will be auto-calculated from amount/price if price available.")
                else:
                    units_input = 0.0

                if category == "BC":
                    st.info("💡 BC (Bachat Gat) → Your savings will increase (tracked separately)")
                else:
                    st.info("💡 Investment → Balance will decrease (asset purchased)")

            st.markdown(f"**Nature:** `{nature}` (auto-detected)")

    # Transfer fields
    from_acc = None
    to_acc = None
    if ttype == "Transfer":
        st.markdown("---")
        st.subheader("Transfer Details")
        from_acc = st.selectbox("From Account", st.session_state.accounts['Account'], key='from')
        to_acc = st.selectbox("To Account", st.session_state.accounts['Account'], key='to')
        if from_acc == to_acc:
            st.warning("⚠️ From and To accounts must be different.")

    # EMI fields (Expense with EMI category)
    is_emi = (ttype == "Expense") and (category and 'emi' in category.lower())
    emi_loan = None
    if is_emi:
        st.markdown("---")
        st.subheader("EMI Payment")
        if not st.session_state.emi.empty:
            loan_options = st.session_state.emi['Lender'].tolist()
            emi_loan = st.selectbox("Select Loan for this EMI payment", loan_options)
            if emi_loan:
                emi_row = st.session_state.emi[st.session_state.emi['Lender'] == emi_loan].iloc[0]
                st.info(f"💡 Remaining: {format_currency(emi_row['Remaining Due'])}. After payment: {format_currency(emi_row['Remaining Due'] - amount)}")
        else:
            st.info("No EMI loans added yet. Go to More > EMI to add a loan.")

    # Investment Name (non-BC)
    inv_name = None
    if ttype == "Investment" and category != "BC":
        st.markdown("---")
        st.subheader("Investment Details")
        inv_names = st.session_state.investments['Name'].tolist() if not st.session_state.investments.empty else []
        inv_options = ['New Investment'] + inv_names
        inv_name = st.selectbox("Select Investment", inv_options)
        if inv_name == 'New Investment':
            inv_name = st.text_input("Enter new investment name")
        if inv_name and inv_name in inv_names:
            inv_row = st.session_state.investments[st.session_state.investments['Name'] == inv_name]
            if not inv_row.empty:
                st.info(f"Current Total Invested: {format_currency(inv_row.iloc[0]['Total Invested'])}")
                if 'Units' in inv_row.columns and inv_row.iloc[0]['Units'] > 0:
                    st.info(f"Current Units: {inv_row.iloc[0]['Units']:.4f}")

    # Fuel fields
    is_fuel = (ttype == "Expense") and (category == 'Fuel' or (category and 'fuel' in category.lower()))
    f_dist = None
    f_litres = None
    if is_fuel:
        st.markdown("---")
        st.subheader("Fuel Details")
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
        if amount <= 0:
            st.error("❌ Amount must be greater than 0!")
        elif ttype == "Transfer" and from_acc == to_acc:
            st.error("❌ From and To accounts must be different!")
        else:
            try:
                new_row = [date.strftime('%Y-%m-%d'), desc, category, amount, ttype, payment_mode, '✅']
                new_df = pd.DataFrame([{
                    'Date': date.strftime('%Y-%m-%d'),
                    'Description': desc,
                    'Category': category,
                    'Amount': amount,
                    'Type': ttype,
                    'Payment Mode': payment_mode,
                    'Status': '✅'
                }])
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                append_to_worksheet('Transactions', new_row)

                # ----- UPDATE BALANCES -----
                # Transfer
                if ttype == "Transfer" and from_acc and to_acc and from_acc != to_acc:
                    from_idx = st.session_state.accounts[st.session_state.accounts['Account'] == from_acc].index[0]
                    to_idx = st.session_state.accounts[st.session_state.accounts['Account'] == to_acc].index[0]
                    st.session_state.accounts.loc[from_idx, 'Balance'] -= amount
                    st.session_state.accounts.loc[to_idx, 'Balance'] += amount
                    update_worksheet('Accounts', st.session_state.accounts)

                # Non-transfer
                else:
                    if category == "BC" and ttype == "Investment":
                        # BC account gets PLUS, payment account gets MINUS
                        bc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == '💳 BC (Bachat Gat)'].index[0]
                        st.session_state.accounts.loc[bc_idx, 'Balance'] += amount
                        acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                        if not acc_idx.empty:
                            idx = acc_idx[0]
                            st.session_state.accounts.loc[idx, 'Balance'] -= amount
                        update_worksheet('Accounts', st.session_state.accounts)
                    else:
                        acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                        if not acc_idx.empty:
                            idx = acc_idx[0]
                            if nature == "Income":
                                st.session_state.accounts.loc[idx, 'Balance'] += amount
                            elif nature in ["Expense", "Neutral"]:
                                if ttype != "Transfer":
                                    st.session_state.accounts.loc[idx, 'Balance'] -= amount
                            update_worksheet('Accounts', st.session_state.accounts)

                # ----- EMI UPDATE -----
                if is_emi and ttype == "Expense" and emi_loan and amount > 0:
                    emi_idx = st.session_state.emi[st.session_state.emi['Lender'] == emi_loan].index[0]
                    current_remaining = st.session_state.emi.loc[emi_idx, 'Remaining Due']
                    if current_remaining >= amount:
                        st.session_state.emi.loc[emi_idx, 'Remaining Due'] = current_remaining - amount
                        st.session_state.emi.loc[emi_idx, 'Installments Paid'] += 1
                        if st.session_state.emi.loc[emi_idx, 'Remaining Due'] <= 0:
                            st.session_state.emi.loc[emi_idx, 'Status'] = 'Cleared'
                            st.session_state.emi.loc[emi_idx, 'Installments Paid'] = st.session_state.emi.loc[emi_idx, 'Tenure (Months)']
                        update_worksheet('EmiManager', st.session_state.emi)

                # ----- INVESTMENT (with Units) -----
                if ttype == "Investment" and category != "BC" and inv_name and amount > 0:
                    units_to_add = units_input if units_input and units_input > 0 else 0.0
                    if units_to_add == 0.0:
                        price_per_unit = None
                        if category == "Gold":
                            price_per_unit = get_gold_price_inr_per_gram()
                            if price_per_unit:
                                st.info(f"⚡ Live Gold Price: ₹{price_per_unit}/gm")
                        elif category == "SIP":
                            if inv_name and ('Axis' in inv_name or 'Gold Fund' in inv_name):
                                price_per_unit = get_axis_gold_fund_nav()
                                if price_per_unit:
                                    st.info(f"⚡ Live Axis Gold Fund NAV: ₹{price_per_unit}")
                        if price_per_unit and price_per_unit > 0:
                            units_to_add = amount / price_per_unit
                            st.info(f"✅ Auto-calculated {units_to_add:.4f} units at ₹{price_per_unit:.2f} per unit.")

                    if inv_name in st.session_state.investments['Name'].values:
                        idx_inv = st.session_state.investments[st.session_state.investments['Name'] == inv_name].index[0]
                        st.session_state.investments.loc[idx_inv, 'Total Invested'] += amount
                        if 'Current Value' in st.session_state.investments.columns:
                            st.session_state.investments.loc[idx_inv, 'Current Value'] += amount
                        if units_to_add > 0:
                            st.session_state.investments.loc[idx_inv, 'Units'] = st.session_state.investments.loc[idx_inv, 'Units'] + units_to_add
                    else:
                        new_inv = pd.DataFrame({
                            'Name': [inv_name],
                            'Type': [category],
                            'Amount': [0.0],
                            'Frequency': ['Monthly'],
                            'Total Invested': [float(amount)],
                            'Current Value': [float(amount)],
                            'Units': [float(units_to_add)]
                        })
                        st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                    update_worksheet('Investments', st.session_state.investments)

                # ----- FUEL -----
                if is_fuel and ttype == "Expense" and f_dist is not None and f_litres is not None:
                    fuel_row = [date.strftime('%Y-%m-%d'), f_dist, f_litres, amount]
                    st.session_state.fuel = pd.concat([st.session_state.fuel, pd.DataFrame([{
                        'Date': date.strftime('%Y-%m-%d'),
                        'Distance (km)': f_dist,
                        'Fuel (L)': f_litres,
                        'Cost (₹)': amount
                    }])], ignore_index=True)
                    update_worksheet('FuelTracker', st.session_state.fuel)

                # ----- BUDGET UPDATE -----
                if category not in st.session_state.budget['Category'].values and category not in ['Transfer', 'Loan Taken', 'Loan Returned', 'BC']:
                    new_budget_row = pd.DataFrame({
                        'Category': [category],
                        'Current Month Budget': [0.0],
                        'Previous Month Budget': [0.0],
                        'Actual This Month': [amount if ttype == 'Expense' else 0.0]
                    })
                    st.session_state.budget = pd.concat([st.session_state.budget, new_budget_row], ignore_index=True)
                    update_worksheet('Budget', st.session_state.budget)

                if ttype in ['Expense', 'Investment'] and category != 'BC':
                    if category in st.session_state.budget['Category'].values:
                        cat_idx = st.session_state.budget[st.session_state.budget['Category'] == category].index[0]
                        current_actual = st.session_state.budget.loc[cat_idx, 'Actual This Month']
                        st.session_state.budget.loc[cat_idx, 'Actual This Month'] = current_actual + amount
                        update_worksheet('Budget', st.session_state.budget)

                success_msg = "✅ Transaction Saved Successfully!"
            except Exception as e:
                error_msg = f"❌ Error: {e}"

        if success_msg:
            st.success(success_msg)
        if error_msg:
            st.error(error_msg)

        if success_msg:
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
                if ttype in ['Expense', 'Investment'] and category != 'BC':
                    if category in st.session_state.budget['Category'].values:
                        cat_idx = st.session_state.budget[st.session_state.budget['Category'] == category].index[0]
                        st.session_state.budget.loc[cat_idx, 'Actual This Month'] -= amount
                        update_worksheet('Budget', st.session_state.budget)

                # Reverse EMI
                if ttype == 'Expense' and 'EMI' in category and not st.session_state.emi.empty:
                    for loan in st.session_state.emi['Lender']:
                        if loan in tx['Description'] or loan in category:
                            emi_idx = st.session_state.emi[st.session_state.emi['Lender'] == loan].index[0]
                            st.session_state.emi.loc[emi_idx, 'Remaining Due'] += amount
                            st.session_state.emi.loc[emi_idx, 'Installments Paid'] -= 1
                            if st.session_state.emi.loc[emi_idx, 'Status'] == 'Cleared':
                                st.session_state.emi.loc[emi_idx, 'Status'] = 'Active'
                            update_worksheet('EmiManager', st.session_state.emi)
                            break

                # Reverse Investment (including BC)
                if ttype == 'Investment':
                    if category == 'BC':
                        bc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == '💳 BC (Bachat Gat)'].index[0]
                        st.session_state.accounts.loc[bc_idx, 'Balance'] -= amount
                        acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                        if not acc_idx.empty:
                            idx_acc = acc_idx[0]
                            st.session_state.accounts.loc[idx_acc, 'Balance'] += amount
                        update_worksheet('Accounts', st.session_state.accounts)
                    else:
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

                # Reverse account balance
                if ttype != "Transfer" and not (ttype == 'Investment' and category == 'BC'):
                    acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                    if not acc_idx.empty:
                        idx_acc = acc_idx[0]
                        if ttype == "Income":
                            st.session_state.accounts.loc[idx_acc, 'Balance'] -= amount
                        elif ttype in ["Expense", "Investment"]:
                            st.session_state.accounts.loc[idx_acc, 'Balance'] += amount
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

            if success_msg:
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
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>💰 Category Budget</div>
            <div class='sheet-card-value' style='color:#6366f1;'>{format_currency(total_budget_val)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t2:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>🎯 Master Cap</div>
            <div class='sheet-card-value' style='color:#8b5cf6;'>{format_currency(master_budget) if master_budget>0 else 'Not Set'}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t3:
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>📉 Total Spent</div>
            <div class='sheet-card-value' style='color:#ef4444;'>{format_currency(total_spent_val)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t4:
        status_color = "#10b981" if remaining_val >= 0 else "#ef4444"
        status_text = "✅ On Track" if remaining_val >= 0 else "⚠️ Over Budget"
        st.markdown(f"""
        <div class='sheet-card'>
            <div class='sheet-card-header'>✅ Remaining</div>
            <div class='sheet-card-value' style='color:{status_color};'>{format_currency(remaining_val)}</div>
            <div class='sheet-card-sub'>{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

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
        st.markdown("### ✏️ Edit Category")
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

    with st.expander("➕ Add Money"):
        acc_add = st.selectbox("Select Account", st.session_state.accounts['Account'], key='add_acc')
        amt_add = st.number_input("Amount ₹", min_value=0.0, step=100.0, key='add_amt')
        desc_add = st.text_input("Description (optional)", value="Cash Deposit", key='add_desc')
        if st.button("Add Money", key="add_money_btn"):
            if amt_add > 0:
                idx = st.session_state.accounts[st.session_state.accounts['Account'] == acc_add].index[0]
                st.session_state.accounts.loc[idx, 'Balance'] += amt_add
                new_row = [datetime.now().strftime('%Y-%m-%d'), desc_add, "Deposit", amt_add, "Income", acc_add, '✅']
                new_df = pd.DataFrame([{
                    'Date': datetime.now().strftime('%Y-%m-%d'), 'Description': desc_add, 'Category': "Deposit",
                    'Amount': amt_add, 'Type': "Income", 'Payment Mode': acc_add, 'Status': '✅'
                }])
                st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                append_to_worksheet('Transactions', new_row)
                update_worksheet('Accounts', st.session_state.accounts)
                st.success(f"✅ {format_currency(amt_add)} added to {acc_add}")
                st.session_state.page = "🏠 Home"
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Amount must be greater than 0.")

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
                    new_row = [datetime.now().strftime('%Y-%m-%d'), desc_with, "Withdrawal", amt_with, "Expense", acc_with, '✅']
                    new_df = pd.DataFrame([{
                        'Date': datetime.now().strftime('%Y-%m-%d'), 'Description': desc_with, 'Category': "Withdrawal",
                        'Amount': amt_with, 'Type': "Expense", 'Payment Mode': acc_with, 'Status': '✅'
                    }])
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                    append_to_worksheet('Transactions', new_row)
                    update_worksheet('Accounts', st.session_state.accounts)
                    st.success(f"✅ {format_currency(amt_with)} withdrawn from {acc_with}")
                    st.session_state.page = "🏠 Home"
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Insufficient balance!")
            else:
                st.error("Amount must be greater than 0.")

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
                        st.session_state.page = "🏠 Home"
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Insufficient balance in source account!")
            else:
                st.error("Amount must be greater than 0.")

    st.markdown("---")
    with st.expander("⚠️ Reset All Account Balances to Zero"):
        st.error("This will set all bank, wallet, cash, and BC balances to ₹0. This action cannot be undone.")
        if st.button("✅ Yes, Reset All Balances to ₹0", key="reset_balances_btn"):
            st.session_state.accounts['Balance'] = 0.0
            update_worksheet('Accounts', st.session_state.accounts)
            st.cache_data.clear()
            st.success("✅ All account balances reset to ₹0!")
            st.session_state.page = "🏠 Home"
            st.rerun()

# ===================== MORE =====================
elif st.session_state.page == "⚡ More":
    st.subheader("🚀 Premium Modules")

    budget_cats = st.session_state.budget['Category'].tolist()
    inv_names = st.session_state.investments['Name'].tolist() if not st.session_state.investments.empty else []
    emi_names = st.session_state.emi['Lender'].tolist() if not st.session_state.emi.empty else []
    goal_names = st.session_state.goals['Goal Name'].tolist() if not st.session_state.goals.empty else []
    custom_cats = st.session_state.custom_categories['Category'].tolist() if not st.session_state.custom_categories.empty else []
    all_cats = list(set(['Transfer', 'Hand Loan'] + budget_cats + inv_names + emi_names + goal_names + custom_cats))
    all_cats = sorted(all_cats)

    custom_type_names = st.session_state.custom_types['TypeName'].tolist() if not st.session_state.custom_types.empty else []
    default_types = ["Income", "Expense", "Investment", "Transfer"]
    all_types = list(set(default_types + custom_type_names))
    all_types = sorted(all_types)

    tabs = st.tabs(["📈 Investments", "🏦 EMI Manager", "🎯 Goals", "📊 Reports", "⚙️ Customization", "📋 All Transactions", "🔄 Recurring", "🤖 AI Assistant"])

    # ---------- INVESTMENTS ----------
    with tabs[0]:
        st.markdown("#### 💼 Your Investments")

        # Quick Update Portfolio (new)
        with st.expander("⚡ Quick Update Portfolio"):
            st.markdown("##### 📊 Enter your current units")
            st.caption("Update Gold and Axis Gold Fund units to reflect your portfolio.")

            col_q1, col_q2 = st.columns(2)
            with col_q1:
                gold_units = st.number_input("Gold Units (grams)", value=0.087535, step=0.001, format="%.6f")
            with col_q2:
                axis_units = st.number_input("Axis Gold Fund Units", value=2.932, step=0.001, format="%.3f")

            if st.button("✅ Update Portfolio", key="quick_update_portfolio"):
                # FIX: Convert columns to float before assignment to avoid Pandas TypeError
                st.session_state.investments['Current Value'] = st.session_state.investments['Current Value'].astype(float)
                st.session_state.investments['Total Invested'] = st.session_state.investments['Total Invested'].astype(float)
                updated = False

                # Gold
                gold_name = "PhonePe Gold"
                if gold_name in st.session_state.investments['Name'].values:
                    idx = st.session_state.investments[st.session_state.investments['Name'] == gold_name].index[0]
                    st.session_state.investments.loc[idx, 'Units'] = gold_units
                else:
                    new_inv = pd.DataFrame({
                        'Name': [gold_name],
                        'Type': ['Gold'],
                        'Amount': [0.0],
                        'Frequency': ['Daily'],
                        'Total Invested': [0.0],
                        'Current Value': [0.0],
                        'Units': [float(gold_units)]
                    })
                    st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                updated = True

                # Axis Gold Fund
                axis_name = "Axis Gold Fund (SIP)"
                if axis_name in st.session_state.investments['Name'].values:
                    idx = st.session_state.investments[st.session_state.investments['Name'] == axis_name].index[0]
                    st.session_state.investments.loc[idx, 'Units'] = axis_units
                else:
                    new_inv = pd.DataFrame({
                        'Name': [axis_name],
                        'Type': ['MF'],
                        'Amount': [0.0],
                        'Frequency': ['Daily'],
                        'Total Invested': [0.0],
                        'Current Value': [0.0],
                        'Units': [float(axis_units)]
                    })
                    st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                updated = True

                if updated:
                    # Fetch current values using live APIs
                    for idx, row in st.session_state.investments.iterrows():
                        name = row['Name']
                        if 'Gold' in name:
                            price = get_gold_price_inr_per_gram()
                            if price and row['Units'] > 0:
                                st.session_state.investments.loc[idx, 'Current Value'] = row['Units'] * price
                        elif 'Axis Gold Fund' in name:
                            nav = get_axis_gold_fund_nav()
                            if nav and row['Units'] > 0:
                                st.session_state.investments.loc[idx, 'Current Value'] = row['Units'] * nav

                    update_worksheet('Investments', st.session_state.investments)
                    st.cache_data.clear()
                    st.success("✅ Portfolio updated with live values!")
                    st.rerun()
                else:
                    st.warning("No changes made.")

        # Auto-update current values
        if st.button("🔄 Update Current Values (Gold & SIP)"):
            # FIX: Convert column to float immediately to prevent TypeError on assignment
            if 'Current Value' in st.session_state.investments.columns:
                st.session_state.investments['Current Value'] = st.session_state.investments['Current Value'].astype(float)
            
            updated = False
            for idx, row in st.session_state.investments.iterrows():
                name = row['Name']
                if 'Gold' in name:
                    price = get_gold_price_inr_per_gram()
                    if price and row['Units'] > 0:
                        st.session_state.investments.loc[idx, 'Current Value'] = row['Units'] * price
                        updated = True
                elif 'SIP' in name or 'MF' in name:
                    try:
                        if 'Axis' in name or 'Gold Fund' in name:
                            nav = get_axis_gold_fund_nav()
                            if nav and row['Units'] > 0:
                                st.session_state.investments.loc[idx, 'Current Value'] = row['Units'] * nav
                                updated = True
                    except:
                        pass
            if updated:
                update_worksheet('Investments', st.session_state.investments)
                st.cache_data.clear()
                st.success("✅ Current values updated from live prices!")
                st.rerun()
            else:
                st.info("No investments with units found. Add transactions with Gold/SIP to track.")

        st.dataframe(st.session_state.investments, hide_index=True, use_container_width=True)

        # Edit Units
        with st.expander("✏️ Edit Investment Units"):
            if not st.session_state.investments.empty:
                inv_edit = st.selectbox("Select Investment to Edit", st.session_state.investments['Name'])
                inv_row = st.session_state.investments[st.session_state.investments['Name'] == inv_edit]
                if not inv_row.empty:
                    new_units = st.number_input("Total Units", value=float(inv_row.iloc[0]['Units']), step=0.001, format="%.4f")
                    if st.button("Update Units"):
                        # FIX: Convert column to float immediately
                        st.session_state.investments['Current Value'] = st.session_state.investments['Current Value'].astype(float)
                        
                        idx = inv_row.index[0]
                        st.session_state.investments.loc[idx, 'Units'] = new_units
                        name = inv_row.iloc[0]['Name']
                        if 'Gold' in name:
                            price = get_gold_price_inr_per_gram()
                            if price:
                                st.session_state.investments.loc[idx, 'Current Value'] = new_units * price
                        elif 'SIP' in name or 'MF' in name:
                            try:
                                if 'Axis' in name or 'Gold Fund' in name:
                                    nav = get_axis_gold_fund_nav()
                                    if nav:
                                        st.session_state.investments.loc[idx, 'Current Value'] = new_units * nav
                            except:
                                pass
                        update_worksheet('Investments', st.session_state.investments)
                        st.cache_data.clear()
                        st.success("Units updated!")
                        st.rerun()
            else:
                st.info("No investments to edit.")

        # Add Investment
        with st.expander("➕ Add Investment (Manual)"):
            inv_name = st.text_input("Investment Name")
            inv_type = st.selectbox("Type", ["SIP", "Gold", "MF", "Stock", "Other"])
            freq = st.selectbox("Frequency", ["Monthly", "Weekly"])
            amt = st.number_input("Amount ₹", min_value=0.0)
            invested = st.number_input("Total Invested So Far ₹", min_value=0.0)
            curr = st.number_input("Current Value ₹", min_value=0.0)
            units = st.number_input("Units (for Gold/Funds)", min_value=0.0, step=0.001, format="%.4f")
            if st.button("Save Investment"):
                new_inv = pd.DataFrame({'Name':[inv_name], 'Type':[inv_type], 'Amount':[float(amt)], 'Frequency':[freq], 'Total Invested':[float(invested)], 'Current Value':[float(curr)], 'Units':[float(units)]})
                st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                update_worksheet('Investments', st.session_state.investments)
                st.cache_data.clear()
                st.success("Investment Saved!")
                st.rerun()

        # Delete Investment
        if not st.session_state.investments.empty:
            inv_del = st.selectbox("Select Investment to Delete", st.session_state.investments['Name'])
            if st.button("🗑️ Delete Selected Investment"):
                idx = st.session_state.investments[st.session_state.investments['Name'] == inv_del].index[0]
                st.session_state.investments = st.session_state.investments.drop(idx).reset_index(drop=True)
                update_worksheet('Investments', st.session_state.investments)
                st.cache_data.clear()
                st.success("Investment Deleted!")
                st.rerun()

    # ---------- EMI MANAGER ----------
    with tabs[1]:
        st.markdown("### 🏦 Loan EMI Manager")

        if not st.session_state.emi.empty:
            df_emi = st.session_state.emi.copy()
            st.dataframe(df_emi.style.format({
                'Total Loan': '₹ {:.0f}',
                'EMI Amount': '₹ {:.0f}',
                'Remaining Due': '₹ {:.0f}',
                'Net Disbursed': '₹ {:.0f}',
                'Total Due': '₹ {:.0f}',
                'Interest Charged': '₹ {:.0f}'
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No loans added yet. Add your loan below.")

        # Add Loan
        with st.expander("➕ Add New Loan"):
            st.markdown("#### 📝 Enter Loan Details")
            col_loan1, col_loan2 = st.columns(2)
            with col_loan1:
                lender = st.text_input("Lender Name", placeholder="e.g., Northern Arc Capital Ltd")
                loan_amt = st.number_input("Total Loan Amount ₹", min_value=0.0, step=100.0)
                tenure = st.number_input("Tenure (Months)", min_value=1, step=1, value=9)
                emi_amount = st.number_input("EMI per Month ₹", min_value=0.0, step=10.0)
                interest = st.number_input("Total Interest Charged ₹", min_value=0.0, step=10.0)
            with col_loan2:
                disbursed = st.number_input("Net Disbursed Amount ₹", min_value=0.0, step=100.0)
                total_due = st.number_input("Total Due ₹", min_value=0.0, step=100.0)
                remaining_due = st.number_input("Remaining Due ₹", min_value=0.0, step=100.0)
                next_due_date = st.date_input("Next Due Date", datetime.now())
                frequency = st.selectbox("Frequency", ["Monthly", "Weekly", "Quarterly"], index=0)
                installment_day = st.number_input("Installment Day of Month (1-31)", min_value=1, max_value=31, value=25)

            st.markdown("---")
            st.markdown("#### 📋 Installment Schedule (Optional)")
            st.caption("Enter amounts for each installment (space-separated). Example: 746 746 746 746 746 746 746 746 726")
            custom_schedule = st.text_area("Installment Amounts", placeholder="746 746 746 746 746 746 746 746 726")

            if st.button("💾 Save Loan", key="save_loan_btn"):
                if lender:
                    schedule_list = []
                    if custom_schedule.strip():
                        try:
                            schedule_list = [float(x.strip()) for x in custom_schedule.split() if x.strip()]
                        except:
                            st.warning("Invalid schedule format. Using default EMI amount.")
                    if not schedule_list:
                        schedule_list = [emi_amount] * tenure
                    while len(schedule_list) < tenure:
                        schedule_list.append(emi_amount)
                    while len(schedule_list) > tenure:
                        schedule_list = schedule_list[:tenure]
                    schedule_str = "|".join(str(x) for x in schedule_list)

                    new_loan = pd.DataFrame([{
                        'Lender': lender,
                        'Total Loan': loan_amt,
                        'EMI Amount': emi_amount,
                        'Tenure (Months)': tenure,
                        'Interest Charged': interest,
                        'Net Disbursed': disbursed,
                        'Total Due': total_due,
                        'Remaining Due': remaining_due,
                        'Next Due Date': next_due_date.strftime('%Y-%m-%d'),
                        'Frequency': frequency,
                        'Installment Day': installment_day,
                        'Schedule': schedule_str,
                        'Installments Paid': 1 if remaining_due < total_due else 0,
                        'Status': 'Active' if remaining_due > 0 else 'Cleared'
                    }])
                    st.session_state.emi = pd.concat([st.session_state.emi, new_loan], ignore_index=True)
                    update_worksheet('EmiManager', st.session_state.emi)
                    st.cache_data.clear()
                    st.success(f"✅ Loan from '{lender}' added!")
                    st.rerun()
                else:
                    st.error("❌ Please enter Lender Name.")

        # Quick Add - Northern Arc / Krazybee
        with st.expander("⚡ Quick Add - Northern Arc / Krazybee Loan"):
            st.markdown("#### 📋 Pre-filled Loan Details")
            st.caption("Based on your provided data:")
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                st.markdown("**Lender:** Northern Arc Capital Ltd + Krazybee Services Ltd")
                st.markdown("**Loan Amount:** ₹6,000")
                st.markdown("**Tenure:** 9 months")
                st.markdown("**EMI:** ₹746 (8 installments) + ₹726 (last)")
                st.markdown("**Interest:** ₹711")
            with col_q2:
                st.markdown("**Net Disbursed:** ₹5,633")
                st.markdown("**Total Due:** ₹6,711")
                st.markdown("**Remaining Due:** ₹5,965")
                st.markdown("**1st Installment:** ₹746 (✅ Paid)")

            if st.button("✅ Add This Loan", key="quick_add_loan"):
                existing = st.session_state.emi[st.session_state.emi['Lender'].str.contains('Northern Arc|Krazybee', na=False)]
                if not existing.empty:
                    st.warning("⚠️ This loan already exists! You can mark it as cleared or edit it.")
                else:
                    schedule_str = "746|746|746|746|746|746|746|746|726"
                    new_loan = pd.DataFrame([{
                        'Lender': 'Northern Arc Capital Ltd + Krazybee Services Ltd',
                        'Total Loan': 6000.0,
                        'EMI Amount': 746.0,
                        'Tenure (Months)': 9,
                        'Interest Charged': 711.0,
                        'Net Disbursed': 5633.0,
                        'Total Due': 6711.0,
                        'Remaining Due': 5965.0,
                        'Next Due Date': datetime(datetime.now().year, datetime.now().month, 25).strftime('%Y-%m-%d'),
                        'Frequency': 'Monthly',
                        'Installment Day': 25,
                        'Schedule': schedule_str,
                        'Installments Paid': 1,
                        'Status': 'Active'
                    }])
                    st.session_state.emi = pd.concat([st.session_state.emi, new_loan], ignore_index=True)
                    update_worksheet('EmiManager', st.session_state.emi)
                    st.cache_data.clear()
                    st.success("✅ Loan added successfully!")
                    st.rerun()

        # Manage Loans
        if not st.session_state.emi.empty:
            st.markdown("---")
            st.markdown("#### ⚙️ Manage Loans")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("##### ✅ Mark as Cleared")
                loan_to_clear = st.selectbox("Select Loan to Clear", st.session_state.emi['Lender'])
                if st.button("✅ Mark as Cleared", key="clear_loan_btn"):
                    idx = st.session_state.emi[st.session_state.emi['Lender'] == loan_to_clear].index[0]
                    st.session_state.emi.loc[idx, 'Remaining Due'] = 0.0
                    st.session_state.emi.loc[idx, 'Status'] = 'Cleared'
                    st.session_state.emi.loc[idx, 'Installments Paid'] = st.session_state.emi.loc[idx, 'Tenure (Months)']
                    update_worksheet('EmiManager', st.session_state.emi)
                    st.cache_data.clear()
                    st.success(f"✅ Loan '{loan_to_clear}' marked as cleared!")
                    st.rerun()
            with col_m2:
                st.markdown("##### 🗑️ Delete Loan")
                loan_to_del = st.selectbox("Select Loan to Delete", st.session_state.emi['Lender'], key='del_loan')
                if st.button("🗑️ Delete Loan", key="del_loan_btn"):
                    idx = st.session_state.emi[st.session_state.emi['Lender'] == loan_to_del].index[0]
                    st.session_state.emi = st.session_state.emi.drop(idx).reset_index(drop=True)
                    update_worksheet('EmiManager', st.session_state.emi)
                    st.cache_data.clear()
                    st.success(f"✅ Loan '{loan_to_del}' deleted!")
                    st.rerun()

        # EMI Payment Log
        st.markdown("---")
        st.markdown("#### 📋 EMI Payment History")
        df_tx = st.session_state.transactions
        emi_tx = df_tx[df_tx['Category'] == 'EMI'] if not df_tx.empty else pd.DataFrame()
        if not emi_tx.empty:
            st.dataframe(emi_tx[['Date', 'Description', 'Amount', 'Payment Mode']].sort_values('Date', ascending=False),
                        use_container_width=True, hide_index=True)
            st.caption(f"Total EMI Payments: {len(emi_tx)} | Total Amount: {format_currency(emi_tx['Amount'].sum())}")
        else:
            st.info("No EMI payments recorded yet. Add an Expense transaction with 'EMI' category.")

    # ---------- GOALS ----------
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

    # ---------- REPORTS ----------
    with tabs[3]:
        st.markdown("### 📊 Monthly Analysis")
        df = st.session_state.transactions
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date'].dt.month_name()
            inc = df[df['Type']=='Income'].groupby('Month')['Amount'].sum().reset_index()
            exp = df[df['Type']=='Expense'].groupby('Month')['Amount'].sum().reset_index()
            merged = pd.merge(inc, exp, on='Month', how='outer').fillna(0)
            merged.columns = ['Month','Income','Expense']
            fig1 = px.bar(merged, x='Month', y=['Income','Expense'], barmode='group', color_discrete_map={'Income':'#10b981', 'Expense':'#ef4444'})
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig1, use_container_width=True)

            df_exp = df[df['Type']=='Expense'].groupby('Category')['Amount'].sum().reset_index()
            if not df_exp.empty:
                fig2 = px.pie(df_exp, names='Category', values='Amount', title="🧾 Expense Breakdown", hole=0.3)
                fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=30,b=0))
                st.plotly_chart(fig2, use_container_width=True)

            fuel_df = st.session_state.fuel
            if not fuel_df.empty:
                fuel_df['Date'] = pd.to_datetime(fuel_df['Date'])
                fuel_df['Month'] = fuel_df['Date'].dt.month_name()
                fuel_monthly = fuel_df.groupby('Month')['Cost (₹)'].sum().reset_index()
                fig3 = px.bar(fuel_monthly, x='Month', y='Cost (₹)', title="⛽ Fuel Cost Per Month", color_discrete_sequence=['#f59e0b'])
                fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig3, use_container_width=True)

            emi_tx = df[(df['Category']=='EMI') & (df['Type']=='Expense')]
            if not emi_tx.empty:
                emi_monthly = emi_tx.groupby('Month')['Amount'].sum().reset_index()
                fig4 = px.bar(emi_monthly, x='Month', y='Amount', title="🏦 EMI Payments Per Month", color_discrete_sequence=['#ef4444'])
                fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig4, use_container_width=True)

            inv_df = st.session_state.investments
            if not inv_df.empty:
                total_inv = inv_df['Total Invested'].sum()
                curr_val = inv_df['Current Value'].sum()
                if total_inv > 0:
                    st.info(f"📈 Total Investment: {format_currency(total_inv)} | Current Value: {format_currency(curr_val)} | ROI: {((curr_val/total_inv)-1)*100:.1f}%")
                sip_gold = inv_df[inv_df['Name'].str.upper().str.contains('SIP|GOLD', na=False)]
                if not sip_gold.empty:
                    st.info(f"🥇 Gold + SIP: Invested: {format_currency(sip_gold['Total Invested'].sum())} | Current: {format_currency(sip_gold['Current Value'].sum())}")

            bc_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='💳 BC (Bachat Gat)', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
            st.info(f"💳 BC (Bachat Gat) Balance: {format_currency(bc_bal)}")
        else:
            st.info("Add some transactions to see detailed reports.")

    # ---------- CUSTOMIZATION ----------
    with tabs[4]:
        st.markdown("### ⚙️ Custom Types, Categories & Natures")
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
        st.markdown("#### 🌿 Custom Natures")
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

    # ---------- ALL TRANSACTIONS ----------
    with tabs[5]:
        st.markdown("### 📋 All Transactions")
        df = st.session_state.transactions
        if not df.empty:
            st.dataframe(df.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")

    # ---------- RECURRING ----------
    with tabs[6]:
        st.markdown("### 🔄 Recurring Transactions")
        recurring_df = st.session_state.recurring
        st.dataframe(recurring_df, hide_index=True, use_container_width=True)
        with st.form("add_recurring"):
            col1, col2 = st.columns(2)
            with col1:
                desc = st.text_input("Description")
                amount = st.number_input("Amount ₹", min_value=0.0)
                next_date = st.date_input("Next Due Date", datetime.now())
            with col2:
                freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Yearly"])
                cat = st.selectbox("Category", all_cats)
                ttype = st.selectbox("Type", all_types)
                payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash", "💳 BC (Bachat Gat)"])
            if st.form_submit_button("Add Recurring"):
                new_row = pd.DataFrame([{
                    'Description': desc,
                    'Category': cat,
                    'Amount': amount,
                    'Type': ttype,
                    'Payment Mode': payment_mode,
                    'Frequency': freq,
                    'NextDate': next_date.strftime('%Y-%m-%d')
                }])
                st.session_state.recurring = pd.concat([st.session_state.recurring, new_row], ignore_index=True)
                update_worksheet('Recurring', st.session_state.recurring)
                st.cache_data.clear()
                st.success("Recurring transaction added!")
                st.rerun()
        if not recurring_df.empty:
            if st.button("🗑️ Delete Selected Recurring"):
                idx = st.selectbox("Select recurring to delete", range(len(recurring_df)), format_func=lambda i: recurring_df.iloc[i]['Description'] + " - " + recurring_df.iloc[i]['NextDate'])
                st.session_state.recurring = recurring_df.drop(idx).reset_index(drop=True)
                update_worksheet('Recurring', st.session_state.recurring)
                st.cache_data.clear()
                st.success("Recurring deleted!")
                st.rerun()

    # ---------- AI ASSISTANT ----------
    with tabs[7]:
        st.markdown("### 🤖 AI Assistant")
        st.info("Ask me anything about your finances.")

        def simple_ai_response(query):
            df = st.session_state.transactions
            if df.empty:
                return "No transactions yet. Add some to get insights!"
            current_month = datetime.now().strftime('%B')
            df['Date'] = pd.to_datetime(df['Date'])
            df_month = df[df['Date'].dt.month_name() == current_month]
            query_lower = query.lower()
            if "expense" in query_lower:
                amt = df_month[df_month['Type']=='Expense']['Amount'].sum()
                return f"📉 Total expense this month: {format_currency(amt)}"
            elif "income" in query_lower:
                amt = df_month[df_month['Type']=='Income']['Amount'].sum()
                return f"📈 Total income this month: {format_currency(amt)}"
            elif "saving" in query_lower:
                inc = df_month[df_month['Type']=='Income']['Amount'].sum()
                exp = df_month[df_month['Type']=='Expense']['Amount'].sum()
                return f"💎 Savings this month: {format_currency(inc - exp)}"
            elif "bc" in query_lower or "bachat" in query_lower:
                bc_bal = st.session_state.accounts.loc[st.session_state.accounts['Account']=='💳 BC (Bachat Gat)', 'Balance'].values[0] if not st.session_state.accounts.empty else 0
                return f"💳 BC (Bachat Gat) balance: {format_currency(bc_bal)}"
            elif "investment" in query_lower:
                total_inv = st.session_state.investments['Total Invested'].sum() if not st.session_state.investments.empty else 0
                return f"📈 Total invested: {format_currency(total_inv)}"
            else:
                return "I can tell you about: Expense, Income, Savings, BC, Investment. Ask me!"

        user_query = st.text_input("Ask a question:", placeholder="E.g., How much expense this month?")
        if user_query:
            response = simple_ai_response(user_query)
            st.success(f"🤖 {response}")
        else:
            st.write("💡 Try asking: 'Expense', 'Income', 'Savings', 'BC', or 'Investment'")

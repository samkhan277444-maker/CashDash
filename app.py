import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import io
import base64
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import requests

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="CashDash - Riyaz Pathan", layout="wide", initial_sidebar_state="collapsed")

# ---------- PIN LOCK (SECURITY) ----------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <style>
        .pin-container { text-align: center; margin-top: 100px; }
        .pin-box { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); padding: 50px; border-radius: 30px; box-shadow: 0 20px 60px rgba(0,0,0,0.1); display: inline-block; border: 1px solid rgba(255,255,255,0.5); color: #1e293b; }
        .stTextInput input { background: rgba(255,255,255,0.8); border: 1px solid #cbd5e1; color: #1e293b; border-radius: 12px; }
    </style>
    <div class="pin-container"><div class="pin-box">
    <h2 style="margin-bottom:20px; background: linear-gradient(90deg, #4f46e5, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🔒 Enter PIN</h2>
    """, unsafe_allow_html=True)
    pin_input = st.text_input("", type="password", placeholder="Enter 4-digit PIN", key="pin_input")
    if st.button("Unlock App"):
        if pin_input == "1234":  # Change to your PIN
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Wrong PIN!")
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

# ---------- LIGHT GREEN & BLUE THEME + BIGGER TABS (ADVANCED CSS) ----------
CSS = f"""
<style>
    /* Light Green & Blue Gradient Background */
    .stApp {{
        background: linear-gradient(135deg, #dbeafe 0%, #d1fae5 100%);
        min-height: 100vh;
    }}
    
    /* Animated Gradient Shine for Header */
    @keyframes shine {{
        0% {{ background-position: -200% center; }}
        100% {{ background-position: 200% center; }}
    }}
    .custom-header {{
        background: linear-gradient(90deg, #4f46e5, #ec4899, #4f46e5);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 900;
        letter-spacing: -1px;
        animation: shine 4s linear infinite;
        display: inline-block;
    }}
    .custom-badge {{
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(4px);
        border-radius: 30px;
        padding: 6px 18px;
        font-size: 0.8rem;
        color: #4f46e5;
        border: 1px solid rgba(255, 255, 255, 0.8);
        display: inline-block;
        margin-left: 12px;
    }}
    .greeting-text {{ color: #1e293b; font-size: 1.2rem; font-weight: 500; }}
    
    /* Premium Glass Cards with Glowing Effects */
    .card {{
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 24px;
        padding: 20px 24px;
        margin-bottom: 16px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
    }}
    /* Glowing neon border animation */
    .card::before {{
        content: '';
        position: absolute;
        top: -2px; left: -2px; right: -2px; bottom: -2px;
        background: linear-gradient(45deg, #4f46e5, #ec4899, #4f46e5);
        background-size: 300% 300%;
        border-radius: 24px;
        z-index: -1;
        animation: borderGlow 6s ease-in-out infinite;
        opacity: 0;
        transition: opacity 0.4s;
    }}
    .card:hover::before {{
        opacity: 1;
    }}
    .card:hover {{
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 64px rgba(79, 70, 229, 0.15);
    }}
    @keyframes borderGlow {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    
    .card-header {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }}
    .card-value {{ font-size: 1.8rem; font-weight: 800; color: #0f172a; }}
    .card-sub {{ font-size: 0.65rem; color: #64748b; margin-top: 4px; }}

    /* Glowing Progress Bars */
    .progress-bar {{
        width: 100%; height: 6px; background: rgba(255,255,255,0.5); border-radius: 10px; margin: 8px 0; overflow: hidden;
    }}
    .progress-fill {{
        height: 100%; border-radius: 10px; transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        background: linear-gradient(90deg, #4f46e5, #ec4899);
        box-shadow: 0 0 15px rgba(236, 72, 153, 0.4);
    }}

    /* Futuristic Buttons */
    .stButton button {{
        width: 100%; border-radius: 30px; font-weight: 700; border: none;
        background: linear-gradient(90deg, #4f46e5, #ec4899);
        color: white; padding: 14px 0; transition: 0.3s;
        box-shadow: 0 4px 20px rgba(79, 70, 229, 0.4);
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .stButton button:hover {{
        transform: scale(1.05);
        box-shadow: 0 8px 35px rgba(79, 70, 229, 0.6);
        background: linear-gradient(90deg, #ec4899, #4f46e5);
    }}

    /* BIGGER TABS FOR MORE, BANK, ADD */
    .stTabs [data-baseweb="tab-list"] button {{
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        margin: 0 6px !important;
        border-radius: 16px !important;
        transition: all 0.3s ease !important;
        color: #475569 !important;
        background: rgba(255, 255, 255, 0.4) !important;
        border: 1px solid transparent !important;
    }}
    .stTabs [data-baseweb="tab-list"] button:hover {{
        background: rgba(255, 255, 255, 0.8) !important;
        transform: translateY(-2px) !important;
    }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        background: rgba(255, 255, 255, 0.9) !important;
        color: #4f46e5 !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.15) !important;
        border-bottom: 3px solid #4f46e5 !important;
    }}

    /* Glass Dataframes */
    .stDataFrame {{
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(8px);
        border-radius: 16px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.8);
        color: #1e293b !important;
    }}
    /* Alerts & Info */
    .stAlert {{
        background: rgba(255, 255, 255, 0.8) !important;
        color: #1e293b !important;
        border: 1px solid rgba(255,255,255,0.9) !important;
    }}
    /* Hide default Streamlit footer */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    footer:after {{
        content: '💎 CashDash v3.0 | Made with ❤️ by Riyaz Pathan';
        visibility: visible;
        display: block;
        text-align: center;
        font-size: 0.8rem;
        color: #64748b;
        padding: 20px 0;
    }}
    
    /* Responsive fixes */
    @media (max-width: 768px) {{
        .card {{ padding: 12px 16px; }}
        .card-value {{ font-size: 1.2rem; }}
        .stColumns {{ flex-wrap: wrap !important; }}
        .stColumn {{ flex: 1 1 45% !important; min-width: 60px; }}
    }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------- HEADER ----------
def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12: return "🌅 Good Morning"
    elif 12 <= hour < 17: return "☀️ Good Afternoon"
    elif 17 <= hour < 21: return "🌇 Good Evening"
    else: return "🌙 Good Night"

greeting = get_greeting()
st.markdown(f"""
<div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 10px 0;'>
    <div>
        <span class='custom-header'>💎 CashDash</span>
        <span class='custom-badge'>Riyaz Pathan</span>
    </div>
    <div>
        <span class='greeting-text'>{greeting}, Riyaz! 👋</span>
        <span style='color:#64748b; margin-left: 10px; font-size:0.9rem;'>📅 {datetime.now().strftime('%d %b %Y')}</span>
    </div>
</div>
<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.5); margin: 5px 0 20px 0;'>
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
    if gc is None: return {}
    data = {}
    worksheet_names = ['Transactions', 'Budget', 'Accounts', 'Investments', 'EmiManager',
                       'Goals', 'FuelTracker', 'Settings', 'CustomTypes', 'CustomCategories', 
                       'CustomNatures', 'Recurring', 'Liabilities', 'Insurance', 'Tax', 'Assets']
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ Sheet '{SHEET_NAME}' not found in Drive.")
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
    if gc is None: return
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
    if gc is None: return
    try:
        sh = gc.open(SHEET_NAME)
        try:
            ws = sh.worksheet(ws_name)
        except:
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

# ---------- LIVE PRICE FUNCTIONS ----------
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
    except:
        return None

@st.cache_data(ttl=3600)
def get_axis_gold_fund_nav():
    try:
        scheme_code = 120724
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            nav = float(data['data'][0]['nav'])
            return nav
        else:
            return None
    except:
        return None

# ---------- AI SUBSCRIPTION DETECTIVE ----------
def detect_subscription_anomalies():
    df = st.session_state.transactions
    if df.empty: return []
    df['Date'] = pd.to_datetime(df['Date'])
    df = df[df['Type'] == 'Expense']
    if df.empty: return []
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
    if 'auto_entries_cleaned' in st.session_state: return
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

# ---------- AUTO CATEGORIZATION MAP ----------
CAT_AUTO = {
    'swiggy': 'Food', 'zomato': 'Food', 'uber': 'Travel', 'ola': 'Travel',
    'reliance': 'Fuel', 'hp': 'Fuel', 'indian oil': 'Fuel',
    'jio': 'Mobile', 'airtel': 'Mobile', 'vi': 'Mobile',
    'amazon': 'Shopping', 'flipkart': 'Shopping', 'myntra': 'Shopping',
    'rent': 'Rent', 'emi': 'EMI', 'education': 'Education'
}

# ---------- SESSION STATE (WITH FIX FOR NEW VARIABLES) ----------
def init_session_state():
    all_data = load_all_sheets()

    # Transactions
    loaded = all_data.get('Transactions', pd.DataFrame())
    required_cols = ['Date','Description','Category','Amount','Type','Payment Mode','Status','Receipt_Image','Split_With']
    if loaded.empty or not all(c in loaded.columns for c in ['Date','Description','Category','Amount','Type','Payment Mode','Status']):
        st.session_state.transactions = pd.DataFrame(columns=required_cols)
    else:
        for col in required_cols:
            if col not in loaded.columns:
                loaded[col] = None
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

    # Accounts
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

    # Investments
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
            try: st.session_state.master_budget = float(loaded[loaded['Key']=='master_budget']['Value'].values[0])
            except: st.session_state.master_budget = 0.0
        else: st.session_state.master_budget = 0.0
        if 'last_sync_time' in loaded['Key'].values:
            st.session_state.last_sync_time = loaded[loaded['Key']=='last_sync_time']['Value'].values[0]
        else: st.session_state.last_sync_time = "Never"

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

    # NEW: Liabilities
    loaded = all_data.get('Liabilities', pd.DataFrame())
    if loaded.empty:
        st.session_state.liabilities = pd.DataFrame(columns=['Lender', 'Due Date', 'Total Due', 'Paid', 'Status'])
    else:
        st.session_state.liabilities = loaded

    # NEW: Insurance
    loaded = all_data.get('Insurance', pd.DataFrame())
    if loaded.empty:
        st.session_state.insurance = pd.DataFrame(columns=['Policy', 'Premium', 'Due Date', 'Sum Assured'])
    else:
        st.session_state.insurance = loaded

    # NEW: Tax
    loaded = all_data.get('Tax', pd.DataFrame())
    if loaded.empty:
        st.session_state.tax = pd.DataFrame(columns=['Investment Name', 'Amount', 'Category 80C'])
    else:
        st.session_state.tax = loaded

    # NEW: Assets
    loaded = all_data.get('Assets', pd.DataFrame())
    if loaded.empty:
        st.session_state.assets = pd.DataFrame(columns=['Name', 'Purchase Price', 'Purchase Date', 'Lifespan (Months)'])
    else:
        st.session_state.assets = loaded

# FIX: Handle restart gracefully
if 'initialized' not in st.session_state:
    init_session_state()
    st.session_state.initialized = True
else:
    # Force create new session state variables if they are missing on restart
    if 'liabilities' not in st.session_state:
        st.session_state.liabilities = pd.DataFrame(columns=['Lender', 'Due Date', 'Total Due', 'Paid', 'Status'])
    if 'insurance' not in st.session_state:
        st.session_state.insurance = pd.DataFrame(columns=['Policy', 'Premium', 'Due Date', 'Sum Assured'])
    if 'tax' not in st.session_state:
        st.session_state.tax = pd.DataFrame(columns=['Investment Name', 'Amount', 'Category 80C'])
    if 'assets' not in st.session_state:
        st.session_state.assets = pd.DataFrame(columns=['Name', 'Purchase Price', 'Purchase Date', 'Lifespan (Months)'])

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
        update_worksheet('Liabilities', st.session_state.liabilities)
        update_worksheet('Insurance', st.session_state.insurance)
        update_worksheet('Tax', st.session_state.tax)
        update_worksheet('Assets', st.session_state.assets)
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

    # ----- ROW 1: BANK ACCOUNTS (GLOWING CARDS) -----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>🏦 BOB Bank</div>
            <div class='card-value' style='color:#4f46e5;'>{format_currency(bob_bal)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>🏦 BOM Bank</div>
            <div class='card-value' style='color:#7c3aed;'>{format_currency(bom_bal)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>📱 PhonePe Wallet</div>
            <div class='card-value' style='color:#0891b2;'>{format_currency(upi_bal)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>💵 Cash</div>
            <div class='card-value' style='color:#059669;'>{format_currency(cash_bal)}</div>
        </div>
        """, unsafe_allow_html=True)

    # ----- ROW 2: INCOME, EXPENSE, BUDGET -----
    col5, col6, col7 = st.columns(3)
    with col5:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>📈 Total Income</div>
            <div class='card-value' style='color:#059669;'>{format_currency(monthly_inc)}</div>
            <div class='card-sub'>This Month</div>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>📉 Total Expense</div>
            <div class='card-value' style='color:#dc2626;'>{format_currency(monthly_exp)}</div>
            <div class='card-sub'>This Month</div>
        </div>
        """, unsafe_allow_html=True)
    with col7:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>🎯 This Month Budget</div>
            <div class='card-value' style='color:#d97706;'>{format_currency(total_budget_val)}</div>
        </div>
        """, unsafe_allow_html=True)

    # ----- ROW 3: INVESTMENT CARDS -----
    col_inv1, col_inv2, col_inv3 = st.columns(3)
    with col_inv1:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>📈 Total Investment</div>
            <div class='card-value' style='color:#7c3aed;'>{format_currency(total_invested)}</div>
            <div class='card-sub'>Current Value: {format_currency(total_current)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_inv2:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>🥇 Gold + SIP</div>
            <div class='card-value' style='color:#d97706;'>{format_currency(sip_gold_inv)}</div>
            <div class='card-sub'>Current Value: {format_currency(sip_gold_curr)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_inv3:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>💳 BC (Bachat Gat)</div>
            <div class='card-value' style='color:#db2777;'>{format_currency(bc_bal)}</div>
            <div class='card-sub'>Your Savings Pool</div>
        </div>
        """, unsafe_allow_html=True)

    # ----- ROW 4: EMI SUMMARY -----
    st.markdown("### 🏦 Loan / EMI Summary")
    if not active_loans.empty:
        col_emi1, col_emi2, col_emi3 = st.columns(3)
        with col_emi1:
            st.markdown(f"""
            <div class='card'>
                <div class='card-header'>📊 Total Remaining</div>
                <div class='card-value' style='color:#dc2626;'>{format_currency(total_emi_remaining)}</div>
                <div class='card-sub'>Across {len(active_loans)} active loans</div>
            </div>
            """, unsafe_allow_html=True)
        with col_emi2:
            st.markdown(f"""
            <div class='card'>
                <div class='card-header'>📆 Monthly EMI</div>
                <div class='card-value' style='color:#4f46e5;'>{format_currency(total_emi_monthly)}</div>
                <div class='card-sub'>Due on {active_loans.iloc[0]['Installment Day']}th of month</div>
            </div>
            """, unsafe_allow_html=True)
        with col_emi3:
            progress = (total_emi_paid / (total_emi_paid + (total_emi_tenure - total_emi_paid))) * 100 if total_emi_tenure > 0 else 0
            st.markdown(f"""
            <div class='card'>
                <div class='card-header'>📈 Progress</div>
                <div class='card-value' style='color:#059669;'>{progress:.1f}%</div>
                <div class='progress-bar'><div class='progress-fill' style='width: {min(progress,100)}%;'></div></div>
                <div class='card-sub'>{total_emi_paid} / {total_emi_tenure} installments paid</div>
            </div>
            """, unsafe_allow_html=True)

        for idx, row in active_loans.iterrows():
            loan_progress = ((row['Installments Paid'] / row['Tenure (Months)']) * 100) if row['Tenure (Months)'] > 0 else 0
            st.markdown(f"""
            <div style='background: rgba(255,255,255,0.6); backdrop-filter: blur(8px); border-radius: 16px; padding: 12px 16px; margin-bottom: 8px; border-left: 4px solid #4f46e5; color: #1e293b;'>
                <div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>
                    <span><strong>{row['Lender']}</strong></span>
                    <span>Remaining: {format_currency(row['Remaining Due'])}</span>
                    <span>EMI: {format_currency(row['EMI Amount'])}</span>
                    <span>Progress: {loan_progress:.1f}%</span>
                </div>
                <div class='progress-bar' style='margin-top: 4px;'><div class='progress-fill' style='width: {min(loan_progress,100)}%;'></div></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active loans. Add a loan in ⚡ More → EMI Manager.")

    # ----- ROW 5: NO-SPEND DAY TRACKER + STREAK -----
    st.markdown("### 🏆 No-Spend Day Tracker")
    today = datetime.now().date()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(day=31)
    else:
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    spend_map = {d.strftime('%Y-%m-%d'): 0 for d in pd.date_range(first_day, last_day)}
    if not df_tx.empty:
        df_tx_cpy = df_tx.copy()
        df_tx_cpy['Date'] = pd.to_datetime(df_tx_cpy['Date']).dt.date
        expenses = df_tx_cpy[(df_tx_cpy['Type'] == 'Expense') & (df_tx_cpy['Date'] >= first_day) & (df_tx_cpy['Date'] <= last_day)]
        for date_str in expenses['Date'].astype(str):
            if date_str in spend_map:
                spend_map[date_str] = 1
    
    streak = 0
    for d in sorted(spend_map.keys(), reverse=True):
        if spend_map[d] == 0:
            streak += 1
        else:
            break
    
    st.markdown(f"<div style='margin-bottom:10px; color:#d97706;'><strong>🔥 Current Streak: {streak} days</strong></div>", unsafe_allow_html=True)
    days = list(spend_map.keys())
    for i in range(0, len(days), 7):
        cols = st.columns(7)
        for j in range(7):
            if i+j < len(days):
                d_str = days[i+j]
                color = "#059669" if spend_map[d_str] == 0 else "#dc2626"
                date_obj = datetime.strptime(d_str, '%Y-%m-%d')
                day_num = date_obj.day
                cols[j].markdown(f"""
                <div style='background:{color}; color:white; border-radius:12px; text-align:center; padding:8px 0; font-weight:700; font-size:1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
                    {day_num}
                </div>
                """, unsafe_allow_html=True)

    # ----- ROW 6: NET WORTH CHART -----
    st.markdown("### 📈 Net Worth Trend (This Month)")
    if not df_tx.empty:
        df_net = df_tx.copy()
        df_net['Date'] = pd.to_datetime(df_net['Date']).dt.date
        daily_sum = df_net.groupby('Date')['Amount'].sum().reset_index()
        fig_net = px.line(daily_sum, x='Date', y='Amount', title='Daily Net Cash Flow', markers=True)
        fig_net.update_layout(plot_bgcolor='rgba(255,255,255,0.3)', paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#1e293b'), margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.info("No transactions yet to show Net Worth trend.")

    # ----- ROW 7: SAVINGS MILESTONE (BALLOONS) -----
    total_net_worth = bob_bal + bom_bal + upi_bal + cash_bal + bc_bal + total_current
    milestones = [10000, 25000, 50000, 100000, 250000, 500000]
    for m in milestones:
        if total_net_worth >= m and f'milestone_{m}' not in st.session_state:
            st.session_state[f'milestone_{m}'] = True
            st.balloons()
            st.success(f"🎉 Congratulations! Your Net Worth crossed ₹{m:,}!")

    # ----- ROW 8: AI INSIGHTS -----
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

    # ----- ROW 9: RECENT TRANSACTIONS -----
    st.markdown("### 📋 Recent Transactions")
    recent = st.session_state.transactions.sort_values('Date', ascending=False).head(5)
    if not recent.empty:
        display_cols = ['Date','Description','Category','Amount','Type']
        st.dataframe(recent[display_cols].style.format({'Amount': '₹ {:.0f}'}).hide(axis=0), use_container_width=True)
    else:
        st.info("No transactions yet.")

    # ----- ROW 10: SYNC -----
    st.markdown("---")
    col_sync1, col_sync2 = st.columns([3, 1])
    with col_sync1:
        if st.button("💾 Save & Sync to Google Sheet", use_container_width=True):
            success, msg = force_sync()
            if success: st.success(msg)
            else: st.error(msg)
    with col_sync2:
        st.markdown(f"<div style='text-align:right; font-size:0.7rem; color:#64748b;'>Last synced: {st.session_state.last_sync_time}</div>", unsafe_allow_html=True)

# ===================== ADD TRANSACTION =====================
elif st.session_state.page == "➕ Add":
    st.subheader("➕ Add Transaction")

    budget_cats = st.session_state.budget['Category'].tolist()
    if 'BC' not in budget_cats:
        budget_cats.append('BC')

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", datetime.now())
        desc = st.text_input("Description", key="desc_input")
        suggested_cat = None
        for kw, cat in CAT_AUTO.items():
            if kw in desc.lower():
                suggested_cat = cat
                break
        amount = st.number_input("Amount ₹", min_value=0.0)
    with col2:
        type_options = ["Expense", "Income", "Transfer", "Investment", "Loan"]
        ttype = st.selectbox("Type", type_options)
        category = st.selectbox("Category", budget_cats + ["Other", "Food", "Travel", "Mobile", "EMI", "Shopping", "Fuel", "Rent", "Education"], index=0)
        if suggested_cat and category == budget_cats[0]:
            category = suggested_cat
        payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])

    split_with = None
    if ttype == "Expense":
        split_options = ["Self", "Friend", "Partner", "Family"]
        split_with = st.selectbox("Split Expense With", split_options)
        if split_with != "Self":
            st.info(f"💡 Expense will be split between Self and {split_with}. Main entry amount is full amount.")

    receipt_file = st.file_uploader("📎 Upload Receipt (Optional)", type=["png", "jpg", "jpeg"])

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

    inv_name = None
    if ttype == "Investment" and category != "BC":
        inv_names = st.session_state.investments['Name'].tolist() if not st.session_state.investments.empty else []
        inv_options = ['New Investment'] + inv_names
        inv_name = st.selectbox("Select Investment", inv_options)
        if inv_name == 'New Investment':
            inv_name = st.text_input("Enter new investment name")

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
        duplicate = False
        if not st.session_state.transactions.empty:
            df_last = st.session_state.transactions.copy()
            df_last['Date'] = pd.to_datetime(df_last['Date'])
            now = datetime.now()
            recent_tx = df_last[df_last['Date'] >= (now - timedelta(minutes=10))]
            if not recent_tx.empty:
                for _, row in recent_tx.iterrows():
                    if row['Description'] == desc and row['Amount'] == amount and row['Type'] == ttype:
                        duplicate = True
                        st.warning("⚠️ Duplicate transaction detected within last 10 minutes! Please confirm.")
                        break
        if not duplicate:
            if amount <= 0:
                st.error("❌ Amount must be greater than 0!")
            else:
                try:
                    receipt_b64 = None
                    if receipt_file:
                        receipt_b64 = base64.b64encode(receipt_file.read()).decode('utf-8')

                    actual_amount = amount
                    if split_with and split_with != "Self":
                        actual_amount = amount / 2
                        st.info(f"Split applied: Your share is {format_currency(actual_amount)}")

                    new_row = [date.strftime('%Y-%m-%d'), desc, category, actual_amount, ttype, payment_mode, '✅', receipt_b64, split_with if split_with else "Self"]
                    new_df = pd.DataFrame([{
                        'Date': date.strftime('%Y-%m-%d'),
                        'Description': desc,
                        'Category': category,
                        'Amount': actual_amount,
                        'Type': ttype,
                        'Payment Mode': payment_mode,
                        'Status': '✅',
                        'Receipt_Image': receipt_b64,
                        'Split_With': split_with if split_with else "Self"
                    }])
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                    append_to_worksheet('Transactions', new_row)

                    if ttype == "Transfer":
                        pass
                    else:
                        if category == "BC" and ttype == "Investment":
                            bc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == '💳 BC (Bachat Gat)'].index[0]
                            st.session_state.accounts.loc[bc_idx, 'Balance'] += actual_amount
                            acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                            if not acc_idx.empty:
                                idx = acc_idx[0]
                                st.session_state.accounts.loc[idx, 'Balance'] -= actual_amount
                            update_worksheet('Accounts', st.session_state.accounts)
                        else:
                            acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                            if not acc_idx.empty:
                                idx = acc_idx[0]
                                if ttype == "Income":
                                    st.session_state.accounts.loc[idx, 'Balance'] += actual_amount
                                elif ttype in ["Expense", "Investment"]:
                                    st.session_state.accounts.loc[idx, 'Balance'] -= actual_amount
                                update_worksheet('Accounts', st.session_state.accounts)

                    if is_emi and ttype == "Expense" and emi_loan and actual_amount > 0:
                        emi_idx = st.session_state.emi[st.session_state.emi['Lender'] == emi_loan].index[0]
                        current_remaining = st.session_state.emi.loc[emi_idx, 'Remaining Due']
                        if current_remaining >= actual_amount:
                            st.session_state.emi.loc[emi_idx, 'Remaining Due'] = current_remaining - actual_amount
                            st.session_state.emi.loc[emi_idx, 'Installments Paid'] += 1
                            if st.session_state.emi.loc[emi_idx, 'Remaining Due'] <= 0:
                                st.session_state.emi.loc[emi_idx, 'Status'] = 'Cleared'
                                st.session_state.emi.loc[emi_idx, 'Installments Paid'] = st.session_state.emi.loc[emi_idx, 'Tenure (Months)']
                            update_worksheet('EmiManager', st.session_state.emi)

                    if ttype == "Investment" and category != "BC" and inv_name and actual_amount > 0:
                        if inv_name in st.session_state.investments['Name'].values:
                            idx_inv = st.session_state.investments[st.session_state.investments['Name'] == inv_name].index[0]
                            st.session_state.investments.loc[idx_inv, 'Total Invested'] += actual_amount
                            if 'Current Value' in st.session_state.investments.columns:
                                st.session_state.investments.loc[idx_inv, 'Current Value'] += actual_amount
                        else:
                            new_inv = pd.DataFrame({
                                'Name': [inv_name], 'Type': [category], 'Amount': [0],
                                'Frequency': ['Monthly'], 'Total Invested': [actual_amount],
                                'Current Value': [actual_amount], 'Units': [0.0]
                            })
                            st.session_state.investments = pd.concat([st.session_state.investments, new_inv], ignore_index=True)
                        update_worksheet('Investments', st.session_state.investments)

                    if is_fuel and ttype == "Expense" and f_dist is not None and f_litres is not None:
                        fuel_row = [date.strftime('%Y-%m-%d'), f_dist, f_litres, actual_amount]
                        st.session_state.fuel = pd.concat([st.session_state.fuel, pd.DataFrame([{
                            'Date': date.strftime('%Y-%m-%d'), 'Distance (km)': f_dist, 'Fuel (L)': f_litres, 'Cost (₹)': actual_amount
                        }])], ignore_index=True)
                        update_worksheet('FuelTracker', st.session_state.fuel)

                    if category not in st.session_state.budget['Category'].values and category not in ['Transfer', 'Loan Taken', 'Loan Returned', 'BC']:
                        new_budget_row = pd.DataFrame({
                            'Category': [category], 'Current Month Budget': [0.0], 'Previous Month Budget': [0.0],
                            'Actual This Month': [actual_amount if ttype in ['Expense', 'Investment'] else 0.0]
                        })
                        st.session_state.budget = pd.concat([st.session_state.budget, new_budget_row], ignore_index=True)
                        update_worksheet('Budget', st.session_state.budget)

                    if ttype in ['Expense', 'Investment'] and category != 'BC':
                        if category in st.session_state.budget['Category'].values:
                            cat_idx = st.session_state.budget[st.session_state.budget['Category'] == category].index[0]
                            st.session_state.budget.loc[cat_idx, 'Actual This Month'] += actual_amount
                            update_worksheet('Budget', st.session_state.budget)

                    st.success("✅ Transaction Saved Successfully!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

            st.session_state.page = "🏠 Home"
            st.cache_data.clear()
            st.rerun()

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
        <div class='card'>
            <div class='card-header'>💰 Category Budget</div>
            <div class='card-value' style='color:#4f46e5;'>{format_currency(total_budget_val)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t2:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>🎯 Master Cap</div>
            <div class='card-value' style='color:#7c3aed;'>{format_currency(master_budget) if master_budget>0 else 'Not Set'}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t3:
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>📉 Total Spent</div>
            <div class='card-value' style='color:#dc2626;'>{format_currency(total_spent_val)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t4:
        status_color = "#059669" if remaining_val >= 0 else "#dc2626"
        status_text = "✅ On Track" if remaining_val >= 0 else "⚠️ Over Budget"
        st.markdown(f"""
        <div class='card'>
            <div class='card-header'>✅ Remaining</div>
            <div class='card-value' style='color:{status_color};'>{format_currency(remaining_val)}</div>
            <div class='card-sub'>{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🚨 Budget Alerts")
    alert_count = 0
    for _, row in df.iterrows():
        if row['Current Month Budget'] > 0:
            pct = (row['Actual This Month'] / row['Current Month Budget']) * 100
            if pct >= 100:
                st.error(f"⚠️ **{row['Category']}** has exceeded budget! (Spent: {format_currency(row['Actual This Month'])} / Budget: {format_currency(row['Current Month Budget'])})")
                alert_count += 1
            elif pct >= 80:
                st.warning(f"⚠️ **{row['Category']}** is nearing budget! ({pct:.1f}% used)")
                alert_count += 1
    if alert_count == 0:
        st.success("✅ All categories are within budget limits!")

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

# ===================== MORE =====================
elif st.session_state.page == "⚡ More":
    st.subheader("🚀 Premium Modules")
    tabs = st.tabs(["📈 Investments", "🏦 EMI Manager", "🎯 Goals", "📊 Reports", 
                    "💳 Liabilities", "🛡️ Insurance", "🧮 Tax", "🏠 Assets", 
                    "📁 Import/Export", "⚙️ Customization", "📋 All Transactions", "🔄 Recurring", "🤖 AI Assistant"])

    # --- INVESTMENTS ---
    with tabs[0]:
        st.markdown("#### 💼 Your Investments")
        if st.button("🔄 Update Current Values (Gold & SIP)"):
            updated = False
            for idx, row in st.session_state.investments.iterrows():
                name = row['Name']
                if 'Gold' in name:
                    price = get_gold_price_inr_per_gram()
                    if price and row['Units'] > 0:
                        st.session_state.investments.loc[idx, 'Current Value'] = row['Units'] * price
                        updated = True
                elif 'SIP' in name or 'MF' in name:
                    if 'Axis' in name or 'Gold Fund' in name:
                        nav = get_axis_gold_fund_nav()
                        if nav and row['Units'] > 0:
                            st.session_state.investments.loc[idx, 'Current Value'] = row['Units'] * nav
                            updated = True
            if updated:
                update_worksheet('Investments', st.session_state.investments)
                st.cache_data.clear()
                st.success("✅ Current values updated from live prices!")
                st.rerun()
            else:
                st.info("No investments with units found. Add transactions with Gold/SIP to track.")
        st.dataframe(st.session_state.investments, hide_index=True, use_container_width=True)

    # --- EMI MANAGER ---
    with tabs[1]:
        st.markdown("### 🏦 Loan EMI Manager")
        st.dataframe(st.session_state.emi, use_container_width=True, hide_index=True)
        with st.expander("🧮 Loan Prepayment Calculator"):
            if not st.session_state.emi.empty:
                loan_sel = st.selectbox("Select Loan", st.session_state.emi['Lender'])
                row = st.session_state.emi[st.session_state.emi['Lender'] == loan_sel].iloc[0]
                extra = st.number_input("Extra Amount to Pay (₹)", min_value=0.0, step=100.0)
                if st.button("Calculate Savings"):
                    if extra > 0:
                        remaining = row['Remaining Due']
                        emi = row['EMI Amount']
                        monthly_rate = (row['Interest Charged'] / row['Total Loan']) / row['Tenure (Months)'] if row['Total Loan'] > 0 else 0
                        new_tenure = -np.log(1 - (remaining * monthly_rate) / (emi + extra)) / np.log(1 + monthly_rate) if monthly_rate > 0 else 0
                        st.info(f"💡 If you pay ₹{extra:.0f} extra now, you will save interest and finish the loan in approx {new_tenure:.1f} months (vs {row['Tenure (Months)'] - row['Installments Paid']} months left).")
                    else:
                        st.warning("Enter an extra amount to calculate.")
            else:
                st.info("Add a loan first.")

    # --- REPORTS ---
    with tabs[3]:
        st.markdown("### 📊 Advanced Reports")
        df = st.session_state.transactions
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date'].dt.month_name()
            st.markdown("#### 📆 Cashflow Forecast (Next 3 Months)")
            st.info("Coming soon: Auto-calculated from recurring transactions.")
            
            st.markdown("#### 🗓️ Spending Heatmap")
            df_heat = df[df['Type']=='Expense'].copy()
            if not df_heat.empty:
                df_heat['Day'] = df_heat['Date'].dt.day_name()
                df_heat['Week'] = df_heat['Date'].dt.isocalendar().week
                fig_heat = px.density_heatmap(df_heat, x='Day', y='Week', z='Amount', title='Spending Heatmap')
                fig_heat.update_layout(plot_bgcolor='rgba(255,255,255,0.3)', paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#1e293b'))
                st.plotly_chart(fig_heat, use_container_width=True)

            st.markdown("#### 🔀 Income to Expense Flow")
            inc_df = df[df['Type']=='Income'].groupby('Category')['Amount'].sum().reset_index()
            exp_df = df[df['Type']=='Expense'].groupby('Category')['Amount'].sum().reset_index()
            if not inc_df.empty and not exp_df.empty:
                nodes = list(inc_df['Category']) + list(exp_df['Category'])
                node_indices = {name: i for i, name in enumerate(nodes)}
                source = [node_indices[n] for n in inc_df['Category']]
                target = [node_indices[n] for n in exp_df['Category']]
                st.plotly_chart(go.Figure(data=[go.Sankey(
                    node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5),
                              label=nodes, color="blue"),
                    link=dict(source=source, target=target, value=inc_df['Amount'].tolist())
                )]), use_container_width=True)
        else:
            st.info("No transactions available for reports.")

    # --- LIABILITIES ---
    with tabs[4]:
        st.markdown("#### 💳 Liabilities (Credit Cards / Dues)")
        if 'liabilities' in st.session_state:
            st.dataframe(st.session_state.liabilities, hide_index=True, use_container_width=True)
        else:
            st.info("Liabilities data is initializing...")
        with st.form("add_liability"):
            c1, c2 = st.columns(2)
            with c1:
                lender = st.text_input("Lender / Card Name")
                due = st.date_input("Due Date", datetime.now())
            with c2:
                total_due = st.number_input("Total Due ₹", min_value=0.0)
                paid = st.number_input("Paid ₹", min_value=0.0)
            if st.form_submit_button("Add Liability"):
                new = pd.DataFrame([{'Lender': lender, 'Due Date': due.strftime('%Y-%m-%d'), 'Total Due': total_due, 'Paid': paid, 'Status': 'Pending' if total_due>paid else 'Cleared'}])
                st.session_state.liabilities = pd.concat([st.session_state.liabilities, new], ignore_index=True)
                update_worksheet('Liabilities', st.session_state.liabilities)
                st.cache_data.clear()
                st.success("Liability added!")
                st.rerun()

    # --- INSURANCE ---
    with tabs[5]:
        st.markdown("#### 🛡️ Insurance Tracker")
        st.dataframe(st.session_state.insurance, hide_index=True, use_container_width=True)
        with st.form("add_insurance"):
            c1, c2 = st.columns(2)
            with c1:
                policy = st.text_input("Policy Name")
                premium = st.number_input("Premium ₹", min_value=0.0)
            with c2:
                due_ins = st.date_input("Next Due Date", datetime.now())
                sum_assured = st.number_input("Sum Assured ₹", min_value=0.0)
            if st.form_submit_button("Add Insurance"):
                new = pd.DataFrame([{'Policy': policy, 'Premium': premium, 'Due Date': due_ins.strftime('%Y-%m-%d'), 'Sum Assured': sum_assured}])
                st.session_state.insurance = pd.concat([st.session_state.insurance, new], ignore_index=True)
                update_worksheet('Insurance', st.session_state.insurance)
                st.cache_data.clear()
                st.success("Insurance added!")
                st.rerun()

    # --- TAX ---
    with tabs[6]:
        st.markdown("#### 🧮 Tax 80C Planner")
        st.dataframe(st.session_state.tax, hide_index=True, use_container_width=True)
        total_80c = st.session_state.tax['Amount'].sum() if not st.session_state.tax.empty else 0
        st.info(f"Total 80C Invested so far: {format_currency(total_80c)}. Target: ₹1,50,000.")
        with st.form("add_tax"):
            name = st.text_input("Investment Name (e.g., PPF, ELSS)")
            amt = st.number_input("Amount ₹", min_value=0.0)
            cat = st.selectbox("Category 80C", ["PPF", "ELSS", "ULIP", "Life Insurance", "NSC", "FD"])
            if st.form_submit_button("Add Tax Investment"):
                new = pd.DataFrame([{'Investment Name': name, 'Amount': amt, 'Category 80C': cat}])
                st.session_state.tax = pd.concat([st.session_state.tax, new], ignore_index=True)
                update_worksheet('Tax', st.session_state.tax)
                st.cache_data.clear()
                st.success("Tax investment added!")
                st.rerun()

    # --- ASSETS ---
    with tabs[7]:
        st.markdown("#### 🏠 Asset Depreciation Calculator")
        st.dataframe(st.session_state.assets, hide_index=True, use_container_width=True)
        with st.form("add_asset"):
            c1, c2 = st.columns(2)
            with c1:
                asset_name = st.text_input("Asset Name (e.g., Car, Bike)")
                purchase_price = st.number_input("Purchase Price ₹", min_value=0.0)
            with c2:
                purchase_date = st.date_input("Purchase Date", datetime.now())
                lifespan = st.number_input("Lifespan (Months)", min_value=1, value=60)
            if st.form_submit_button("Add Asset"):
                new = pd.DataFrame([{'Name': asset_name, 'Purchase Price': purchase_price, 'Purchase Date': purchase_date.strftime('%Y-%m-%d'), 'Lifespan (Months)': lifespan}])
                st.session_state.assets = pd.concat([st.session_state.assets, new], ignore_index=True)
                update_worksheet('Assets', st.session_state.assets)
                st.cache_data.clear()
                st.success("Asset added!")
                st.rerun()

    # --- IMPORT/EXPORT ---
    with tabs[8]:
        st.markdown("#### 📁 Data Import / Export")
        if st.button("📥 Export All Data to Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state.transactions.to_excel(writer, sheet_name='Transactions', index=False)
                st.session_state.budget.to_excel(writer, sheet_name='Budget', index=False)
                st.session_state.accounts.to_excel(writer, sheet_name='Accounts', index=False)
                st.session_state.investments.to_excel(writer, sheet_name='Investments', index=False)
                st.session_state.emi.to_excel(writer, sheet_name='EMI', index=False)
            st.download_button(label="📥 Download Excel File", data=output.getvalue(), file_name="CashDash_Backup.xlsx", mime="application/vnd.ms-excel")
        
        st.markdown("#### 📤 Bulk Import Transactions (CSV)")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            try:
                df_import = pd.read_csv(uploaded_file)
                if 'Amount' in df_import.columns and 'Description' in df_import.columns:
                    st.session_state.transactions = pd.concat([st.session_state.transactions, df_import], ignore_index=True)
                    update_worksheet('Transactions', st.session_state.transactions)
                    st.cache_data.clear()
                    st.success(f"✅ {len(df_import)} transactions imported successfully!")
                else:
                    st.error("CSV must have 'Amount' and 'Description' columns.")
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

        # 🛠️ FIX: JSON serialization bug fixed with `default=str`
        if st.button("💾 Download JSON Backup"):
            backup = {
                'transactions': st.session_state.transactions.to_dict(),
                'budget': st.session_state.budget.to_dict(),
                'accounts': st.session_state.accounts.to_dict()
            }
            st.download_button(
                label="📥 Download JSON",
                data=json.dumps(backup, indent=2, default=str),
                file_name="CashDash_Backup.json",
                mime="application/json"
            )

    # --- CUSTOMIZATION ---
    with tabs[9]:
        st.markdown("#### ⚙️ Custom Types, Categories & Natures")
        st.info("Edit your custom types, categories, and natures here.")
        # (Your existing customization UI can be placed here)

    # =====================================================================
    # 🔥 UPDATED: ALL TRANSACTIONS WITH ROW-WISE UI & INLINE DELETE
    # =====================================================================
    with tabs[10]:
        st.markdown("### 📋 All Transactions")
        
        if st.session_state.transactions.empty:
            st.info("No transactions yet.")
        else:
            # Sort transactions by latest date
            df_sorted = st.session_state.transactions.sort_values('Date', ascending=False)
            
            # Loop through each transaction to create a row
            for i, (original_index, row) in enumerate(df_sorted.iterrows()):
                
                # Create horizontal columns: 2 for Date, 4 for Desc, 2 for Amount, 1 for Delete button
                col_date, col_desc, col_amt, col_del = st.columns([2, 4, 2, 1])
                
                with col_date:
                    st.write(f"**{row['Date']}**")
                
                with col_desc:
                    st.write(f"{row['Description']} *({row['Category']})*")
                
                with col_amt:
                    # Color-code the amount based on Type (Income=Green, Expense=Red)
                    if row['Type'] == 'Income':
                        st.markdown(f"<span style='color:#10b981; font-weight:600;'>₹ {row['Amount']:,.0f}</span>", unsafe_allow_html=True)
                    elif row['Type'] == 'Expense':
                        st.markdown(f"<span style='color:#ef4444; font-weight:600;'>- ₹ {row['Amount']:,.0f}</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"₹ {row['Amount']:,.0f}")
                
                with col_del:
                    # Inline Delete Button
                    if st.button("❌", key=f"del_inline_{i}"):
                        success_msg = None
                        error_msg = None
                        try:
                            # Identify the correct row in the original DataFrame using 'original_index'
                            idx = original_index
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

                            # Finally, delete the transaction
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
                            st.cache_data.clear()
                            st.rerun()
                
                # Add a small divider between rows for better visual readability
                st.markdown("---")

    # --- RECURRING (Auto-Add) ---
    with tabs[11]:
        st.markdown("### 🔄 Recurring Transactions")
        st.dataframe(st.session_state.recurring, hide_index=True, use_container_width=True)
        if st.button("🔄 Execute All Due Recurring"):
            today_str = datetime.now().strftime('%Y-%m-%d')
            executed = 0
            for idx, row in st.session_state.recurring.iterrows():
                if row['NextDate'] == today_str:
                    new_tx = pd.DataFrame([{
                        'Date': today_str, 'Description': row['Description'], 'Category': row['Category'],
                        'Amount': row['Amount'], 'Type': row['Type'], 'Payment Mode': row['Payment Mode'], 'Status': '✅'
                    }])
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_tx], ignore_index=True)
                    append_to_worksheet('Transactions', [today_str, row['Description'], row['Category'], row['Amount'], row['Type'], row['Payment Mode'], '✅'])
                    if row['Frequency'] == 'Daily':
                        next_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    elif row['Frequency'] == 'Weekly':
                        next_date = (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d')
                    elif row['Frequency'] == 'Monthly':
                        next_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                    elif row['Frequency'] == 'Yearly':
                        next_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
                    st.session_state.recurring.loc[idx, 'NextDate'] = next_date
                    executed += 1
            update_worksheet('Recurring', st.session_state.recurring)
            if executed > 0:
                st.success(f"✅ {executed} recurring transactions executed and added!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.info("No recurring transactions due today.")

    # --- AI ASSISTANT ---
    with tabs[12]:
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

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
        # ----- TYPE DROPDOWN (Only 5 Types) -----
        ttype = st.selectbox("Type", ["Expense", "Income", "Transfer", "Investment", "Loan"])

        # ----- LOAN SUB-TYPES (Loan Taken / Returned) -----
        loan_subtype = None
        nature = "Neutral"
        
        if ttype == "Loan":
            loan_subtype = st.selectbox("Loan Action", ["Loan Taken", "Loan Returned"])
            payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])
            
            if loan_subtype == "Loan Taken":
                nature = "Income"
                category = "Loan Taken"
                st.info("💡 Loan Taken → Income (balance will increase)")
            else:  # Loan Returned
                nature = "Expense"
                category = "Loan Returned"
                st.info("💡 Loan Returned → Expense (balance will decrease)")

        # ----- OTHER TYPES (Expense, Income, Transfer, Investment) -----
        else:
            category = st.selectbox("Category", budget_cats + ["Other", "Food", "Travel", "Mobile", "EMI", "Shopping", "Fuel", "Rent", "Education"])
            payment_mode = st.selectbox("Payment Mode", ["BOB Bank", "BOM Bank", "PhonePe Wallet", "Cash"])

            # Auto-detect Nature based on Type
            if ttype == "Income":
                nature = "Income"
            elif ttype in ["Expense", "Investment"]:
                nature = "Expense"
            elif ttype == "Transfer":
                nature = "Neutral"
                category = "Transfer"
            
            st.markdown(f"**Nature:** `{nature}` (auto-detected)")

    # ----- SPLIT EXPENSE -----
    split_with = None
    if ttype == "Expense":
        split_options = ["Self", "Friend", "Partner", "Family"]
        split_with = st.selectbox("Split Expense With", split_options)
        if split_with != "Self":
            st.info(f"💡 Expense will be split between Self and {split_with}. Main entry amount is full amount.")

    # ----- RECEIPT UPLOAD -----
    receipt_file = st.file_uploader("📎 Upload Receipt (Optional)", type=["png", "jpg", "jpeg"])

    # ----- EMI FIELDS (Only for Expense+EMI) -----
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

    # ----- INVESTMENT NAME (Non-BC) -----
    inv_name = None
    if ttype == "Investment" and category != "BC":
        inv_names = st.session_state.investments['Name'].tolist() if not st.session_state.investments.empty else []
        inv_options = ['New Investment'] + inv_names
        inv_name = st.selectbox("Select Investment", inv_options)
        if inv_name == 'New Investment':
            inv_name = st.text_input("Enter new investment name")

    # ----- FUEL FIELDS -----
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

    # ----- SUBMIT BUTTON -----
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

                    # Apply Split Logic (if applicable)
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

                    # ================= UPDATE BALANCES =================
                    # 1. TRANSFER
                    if ttype == "Transfer":
                        pass  # Transfers handled separately in Bank tab

                    # 2. BC INVESTMENT (Savings Pool)
                    elif category == "BC" and ttype == "Investment":
                        bc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == '💳 BC (Bachat Gat)'].index[0]
                        st.session_state.accounts.loc[bc_idx, 'Balance'] += actual_amount
                        acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                        if not acc_idx.empty:
                            idx = acc_idx[0]
                            st.session_state.accounts.loc[idx, 'Balance'] -= actual_amount
                        update_worksheet('Accounts', st.session_state.accounts)

                    # 3. LOAN TAKEN / LOAN RETURNED
                    elif ttype == "Loan":
                        acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                        if not acc_idx.empty:
                            idx = acc_idx[0]
                            if loan_subtype == "Loan Taken":
                                st.session_state.accounts.loc[idx, 'Balance'] += actual_amount
                            else:  # Loan Returned
                                st.session_state.accounts.loc[idx, 'Balance'] -= actual_amount
                            update_worksheet('Accounts', st.session_state.accounts)

                    # 4. NORMAL ACCOUNT UPDATE (Income, Expense, Investment)
                    else:
                        acc_idx = st.session_state.accounts[st.session_state.accounts['Account'] == payment_mode].index
                        if not acc_idx.empty:
                            idx = acc_idx[0]
                            if nature == "Income":
                                st.session_state.accounts.loc[idx, 'Balance'] += actual_amount
                            elif nature == "Expense":
                                st.session_state.accounts.loc[idx, 'Balance'] -= actual_amount
                            update_worksheet('Accounts', st.session_state.accounts)

                    # ================= EMI UPDATE =================
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

                    # ================= INVESTMENT UPDATE (Non-BC) =================
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

                    # ================= FUEL UPDATE =================
                    if is_fuel and ttype == "Expense" and f_dist is not None and f_litres is not None:
                        fuel_row = [date.strftime('%Y-%m-%d'), f_dist, f_litres, actual_amount]
                        st.session_state.fuel = pd.concat([st.session_state.fuel, pd.DataFrame([{
                            'Date': date.strftime('%Y-%m-%d'), 'Distance (km)': f_dist, 'Fuel (L)': f_litres, 'Cost (₹)': actual_amount
                        }])], ignore_index=True)
                        update_worksheet('FuelTracker', st.session_state.fuel)

                    # ================= BUDGET UPDATE =================
                    # Add new category to budget if it doesn't exist (except Loan/BC/Transfer)
                    if category not in st.session_state.budget['Category'].values and category not in ['Transfer', 'Loan Taken', 'Loan Returned', 'BC']:
                        new_budget_row = pd.DataFrame({
                            'Category': [category], 'Current Month Budget': [0.0], 'Previous Month Budget': [0.0],
                            'Actual This Month': [actual_amount if ttype in ['Expense', 'Investment'] else 0.0]
                        })
                        st.session_state.budget = pd.concat([st.session_state.budget, new_budget_row], ignore_index=True)
                        update_worksheet('Budget', st.session_state.budget)

                    # Update existing budget actuals (only for Expense/Investment excluding BC and Loan)
                    if ttype in ['Expense', 'Investment'] and category != 'BC' and category not in ['Loan Taken', 'Loan Returned']:
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

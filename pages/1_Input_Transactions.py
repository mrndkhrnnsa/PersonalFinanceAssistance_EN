import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app_utils import load_csv, save_to_csv
import pandas as pd

st.header("💸 Transaction Input")
tabs = st.tabs([' ➕ New Transaction', ' 📄 Transaction History'])

CATEGORIES = ["Income", "Expense"]
SUBCATEGORIES = ["Salary", "Bonus", "Food", "Transport", "Shopping", "Entertainment", "Savings", "Others"]
PAYMENT = ["Cash", "Debit", "Credit", "E-Wallet"]

with tabs[0]:
    st.subheader("Manual Transaction Input")
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            amount = st.number_input("Amount", min_value=0.0, step=1000.0)
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            description = st.text_input("Description")
            payment_method = st.selectbox("Payment Method", PAYMENT)
            subcategory = st.selectbox("Subcategory", SUBCATEGORIES)
        note = st.text_area("Note (optional)", placeholder="Add a note if needed")

        submit_button = st.form_submit_button("💾 Save Transaction")
        if submit_button:
            if not description:
                st.error("Please enter a transaction description!")
            else:
                try:
                    new_row = {
                        "Date": pd.to_datetime(date).strftime("%Y-%m-%d"),
                        "Description": description,
                        "Amount": float(amount),
                        "Category": category,
                        "Subcategory": subcategory,
                        "Payment Method": payment_method,
                        "Note": note if note else ""
                    }
                    
                    # Load existing data
                    df = load_csv()
                    
                    # Add new row
                    new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Save and refresh
                    if save_to_csv(new_df):
                        st.session_state.need_refresh = True
                        st.success("✅ Transaction saved successfully!")
                    else:
                        st.error("Failed to save transaction. Please try again.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    st.subheader("Upload Transaction CSV")
    st.markdown(
        """
        <b>Make sure your CSV file has the following columns:</b>
        <ul>
            Date, Description, Amount, Category, Subcategory, Payment Method, Note
        </ul>
        """,
        unsafe_allow_html=True
    )
    template_df = pd.DataFrame(columns=[
        "Date", "Description", "Amount", "Category", "Subcategory", "Payment Method", "Note"
    ])
    csv = template_df.to_csv(index=False)

    st.download_button(
        label="📥 Download CSV Template",
        data=csv,
        file_name="transaction_template.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        uploaded_df = pd.read_csv(uploaded_file)
        expected_cols = [
            "Date", "Description", "Amount", "Category",
            "Subcategory", "Payment Method", "Note"
        ]
        uploaded_df.columns = [col.strip() for col in uploaded_df.columns]
        missing_cols = [col for col in expected_cols if col not in uploaded_df.columns]
        if missing_cols:
            st.error(f"The following columns are missing in the CSV file: {missing_cols}")
        else:
            uploaded_df = uploaded_df[expected_cols]
            uploaded_df["Date"] = pd.to_datetime(uploaded_df["Date"], errors="coerce")
            uploaded_df = uploaded_df.dropna(subset=["Date"])
            existing_df = load_csv()
            combined_df = pd.concat([existing_df, uploaded_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates()
            save_to_csv(combined_df)
            st.success("✅ Data from CSV uploaded and saved successfully!")

with tabs[1]:
    st.write("Transaction List:")
    
    # Load and prepare data
    df = load_csv()
    
    if df.empty:
        st.info("No transactions found.")
    else:
        # Convert and clean date data
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date", ascending=False).reset_index(drop=True)
        
        # Set min and max dates
        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()

        # Date filter columns
        col1, col2 = st.columns([2, 2])
        with col1:
            start_date = st.date_input("Start Date", value=min_date)
        with col2:
            end_date = st.date_input("End Date", value=max_date)
        
        if end_date < start_date:
            st.warning("End Date cannot be before Start Date")
            end_date = start_date

        # Filter columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            category_filter = st.selectbox("Category Filter", ["All"] + sorted(df["Category"].dropna().unique().tolist()))
        with col2:
            subcategory_filter = st.selectbox("Subcategory Filter", ["All"] + sorted(df["Subcategory"].dropna().unique().tolist()))
        with col3:
            method_filter = st.selectbox("Payment Method Filter", ["All"] + sorted(df["Payment Method"].dropna().unique().tolist()))
        with col4:
            search = st.text_input("Search Description")

        # Apply filters
        filtered_df = df.copy()

        # Apply date filter
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start_date) &
            (filtered_df["Date"].dt.date <= end_date)
        ]
        
        # Apply category filters
        if category_filter != "All":
            filtered_df = filtered_df[filtered_df["Category"] == category_filter]
        if subcategory_filter != "All":
            filtered_df = filtered_df[filtered_df["Subcategory"] == subcategory_filter]
        if method_filter != "All":
            filtered_df = filtered_df[filtered_df["Payment Method"] == method_filter]
        
        # Apply search filter
        if search:
            filtered_df = filtered_df[filtered_df["Description"].str.contains(search, case=False, na=False)]
        
        # Show data in editor
        if len(filtered_df) == 0:
            st.info("No transactions found in the selected date range.")
        else:
            # Show data editor with current filters applied
            edited_df = st.data_editor(
                filtered_df,
                num_rows="dynamic",
                use_container_width=True,
                column_order=[
                    "Date", "Description", "Amount", "Category",
                    "Subcategory", "Payment Method", "Note"
                ]
            )
            
            # Action buttons
            col1, col2 = st.columns([2,2])
            with col1:
                if st.button("💾 Save Changes"):
                    try:
                        save_to_csv(edited_df)
                        st.success("✅ Changes saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save changes: {str(e)}")
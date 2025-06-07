import streamlit as st
import os
import pandas as pd

# Page config
st.set_page_config(page_title="Personal Finance Assistant", page_icon="📝", layout="centered")

# Title and intro
st.title('📝 Personal Finance Assistant')
st.write("""
Welcome to the Personal Finance Assistant! 
This app is designed to help you manage your personal finances better.
You can input transactions, set budgets, and analyze your finances easily.
""")

st.write("Please select an option from the sidebar to get started or click the button below:")

st.markdown("###")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Start Saving!"):
        # Delete all saved data (transactions.csv and budget.csv)
        data_paths = ["data/transactions.csv", "data/budget.csv"]
        for data_path in data_paths:
            if os.path.exists(data_path):
                os.remove(data_path)
        # Overwrite budget.csv
        budget_headers = ["Category", "Amount"]  # Adjust to your actual headers
        pd.DataFrame(columns=budget_headers).to_csv("data/budget.csv", index=False)
        st.switch_page("pages/1_Input_Transactions.py")
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import requests
import re
from app_utils import load_csv, save_budget_csv, get_historical_average_by_category

# Load OpenRouter API key from Streamlit secrets
api_key = st.secrets["openrouter"]["api_key"]

st.header("🧮 Budget Settings")

SUBCATEGORIES = ["Food", "Transport", "Shopping", "Entertainment", "Savings", "Others"]

# Load and preprocess transaction data safely
transactions_df = load_csv()
transactions_df = transactions_df.copy()  # avoid chained assignment warning

# Ensure date column is datetime
transactions_df.loc[:, "Date"] = pd.to_datetime(transactions_df["Date"], errors="coerce")

# Calculate historical averages
historical_averages = get_historical_average_by_category(transactions_df, SUBCATEGORIES, months_back=100)

monthly_income = 0
if not transactions_df.empty:
    income_df = transactions_df[transactions_df["Category"] == "Income"].copy()
    if not income_df.empty:
        income_per_month = (
            income_df.groupby(income_df["Date"].dt.to_period("M"))["Amount"]
            .sum()
        )
        monthly_income = income_per_month.mean()

savings_goal = st.number_input("Target Total Savings (Rp)", min_value=0, step=50000)
free_text_goal = st.text_area("Additional Notes (e.g. 'reduce food expenses', 'save for vacation')")

if st.button("Generate AI Budget"):
    with st.spinner("Generating your budget... hang tight!"):
        history_str = "\n".join([f"- {cat}: Rp{amount:,.0f}" for cat, amount in historical_averages.items()])
        prompt = (
            f"You are a financial assistant. Here are the average monthly expenses based on all historical data:\n{history_str}\n\n"
            f"Estimated income for this month: Rp{monthly_income:,.0f}. Savings target: Rp{savings_goal:,.0f}.\n"
            f"{free_text_goal}\n"
            "Create a reasonable monthly budget. Only use these categories: Food, Transport, Shopping, Entertainment, Savings, Others."
            "Reply in markdown table format and use English."
        )
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://personal-finance-assistance.streamlit.app"
        }
        data = {
            "model": 'deepseek/deepseek-chat-v3-0324',
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        ai_text = response.json()['choices'][0]['message']['content']
        st.subheader("🧠 AI Budget Recommendation")

        parsed_budget = {}
        parsed_percentages = {}
        for line in ai_text.splitlines():
            if re.match(r"\s*\|", line) and not re.match(r"\s*\|[\s\-|]+\|", line):
                cols = [c.strip(" *") for c in line.strip().split("|")[1:-1]]
                if len(cols) >= 2:
                    category = cols[0].lower()
                    amount_str = next((c for c in cols[1:] if re.search(r"\d", c)), None)
                    percent_str = next((c for c in cols[1:] if "%" in c), None)
                    matched = None
                    for allowed in SUBCATEGORIES:
                        if allowed.lower() in category:
                            matched = allowed
                            break
                    if not matched or not amount_str:
                        continue
                    try:
                        amount = float(amount_str.replace("$", "").replace(",", "").replace("%", "").strip())
                        parsed_budget[matched] = amount
                        if percent_str:
                            try:
                                parsed_percentages[matched] = float(percent_str.replace("%", "").replace(",", "").strip())
                            except ValueError:
                                parsed_percentages[matched] = None
                        else:
                            parsed_percentages[matched] = None
                    except ValueError:
                        continue

        if parsed_budget:
            st.session_state.budget_inputs = {cat: parsed_budget.get(cat, 0.0) for cat in SUBCATEGORIES}
            st.session_state.budget_percentages = {cat: parsed_percentages.get(cat, None) for cat in SUBCATEGORIES}
            st.success("AI budget generated! Adjust as needed and save.")
        else:
            st.warning("⚠️ Oops! Could not parse AI budget. Please revise or try again.")
            
if "budget_inputs" in st.session_state:
    st.markdown("✏️ You can adjust the values below before saving:")
    for category in SUBCATEGORIES:
        percent = st.session_state.get("budget_percentages", {}).get(category)
        label = f"{category}"
        if percent is not None:
            label += f" ({percent:.2f}%)"
        st.session_state.budget_inputs[category] = st.number_input(
            label, value=st.session_state.budget_inputs.get(category, 0.0), step=50000.0, key=f"budget_{category}"
        )
    if st.button("💾 Save Budget"):
        save_budget_csv(st.session_state.budget_inputs)
        st.success("✅ Budget saved successfully!")
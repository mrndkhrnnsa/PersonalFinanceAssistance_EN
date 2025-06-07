import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
# Removed unused imports: requests, re, pipeline, json, plt

# Data Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
transactions_data = os.path.join(DATA_DIR, "transactions.csv")
expected_cols = [
    "Date", "Description", "Amount", "Category",
    "Subcategory", "Payment Method", "Note"
]

# Function to save DataFrame to CSV
def save_to_csv(df):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if df is None or df.empty:
            df = pd.DataFrame(columns=expected_cols)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date", ascending=False)
        df.to_csv(transactions_data, index=False, date_format="%Y-%m-%d")
        print(f"Data saved to {transactions_data}")
        return True
    except Exception as e:
        print(f"Error saving data: {str(e)}")
        st.error(f"Error saving data: {str(e)}")
        return False

# Function to load DataFrame from CSV
def load_csv():
    try:
        if os.path.exists(transactions_data):
            print(f"Loading data from {transactions_data}")
            df = pd.read_csv(transactions_data)
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            df = df[expected_cols]
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            df = df.sort_values("Date", ascending=False).reset_index(drop=True)
            print(f"Loaded {len(df)} transactions")
            return df
        else:
            print("Creating new transaction file")
            df = pd.DataFrame(columns=expected_cols)
            df.to_csv(transactions_data, index=False)
            return df
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(columns=expected_cols)

# Function to save budget dictionary to CSV
def save_budget_csv(budget_dict):
    budget_file = os.path.join(DATA_DIR, "budget.csv")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not budget_dict:
            budget_dict = {
                "Food": 0,
                "Transport": 0,
                "Shopping": 0,
                "Entertainment": 0,
                "Savings": 0,
                "Others": 0
            }
        df = pd.DataFrame(list(budget_dict.items()), columns=["Category", "Budget"])
        df.to_csv(budget_file, index=False)
        print(f"Budget saved to {budget_file}")
        return True
    except Exception as e:
        print(f"Error saving budget: {str(e)}")
        st.error(f"Error saving budget: {str(e)}")
        return False

# Function to get historical average spending by category
def get_historical_average_by_category(df, categories, months_back=3):
    if df.empty or "Date" not in df.columns:
        return {cat: 0.0 for cat in categories}
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=["Date"])
    df["Month"] = df["Date"].dt.to_period("M")
    recent_months = sorted(df["Month"].unique())[-months_back:]
    filtered_df = df[df["Month"].isin(recent_months) & df["Category"].isin(categories)]
    averages = (
        filtered_df.groupby("Category")["Amount"]
        .mean()
        .to_dict()
    )
    return {cat: round(averages.get(cat, 0.0), 2) for cat in categories}

# Function to fetch transaction data for filtering (with date range)
def fetch_data_with_range(start_date=None, end_date=None):
    if not os.path.exists(transactions_data):
        return pd.DataFrame()
    df = pd.read_csv(transactions_data)
    df = df.rename(columns={
        "Date": "date",
        "Amount": "amount",
        "Category": "category",
        "Subcategory": "subcategory",
        "Payment Method": "payment_method",
        "Description": "description",
        "Note": "note"
    })
    df["date"] = pd.to_datetime(df["date"])
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    return df

# Function to fetch and prepare data for analysis (always returns English columns)
def fetch_data():
    try:
        if not os.path.exists(transactions_data) or os.path.getsize(transactions_data) == 0:
            return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "note"])
        df = pd.read_csv(transactions_data)
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "note"])
        df = df.rename(columns={
            "Date": "date",
            "Description": "description",
            "Amount": "amount",
            "Category": "category",
            "Subcategory": "subcategory",
            "Payment Method": "payment_method",
            "Note": "note"
        })
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.sort_values("date", ascending=False)
        return df
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "note"])
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "note"])

# --- Financial Summary ---
def get_financial_summary(df):
    if df.empty:
        return {
            "total_income": 0,
            "total_expense": 0,
            "balance": 0
        }
    total_income = df[df["category"] == "Income"]["amount"].sum()
    total_expense = df[df["category"] == "Expense"]["amount"].sum()
    balance = total_income - total_expense
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance
    }

# Function to load budget from CSV
def load_budget_csv():
    budget_file = os.path.join(DATA_DIR, "budget.csv")
    default_budget = {
        "Food": 0,
        "Transport": 0,
        "Shopping": 0,
        "Entertainment": 0,
        "Savings": 0,
        "Others": 0
    }
    try:
        if os.path.exists(budget_file) and os.path.getsize(budget_file) > 0:
            df = pd.read_csv(budget_file)
            if len(df.columns) == 0:
                save_budget_csv(default_budget)
                return default_budget
            return dict(zip(df["Category"], df["Budget"]))
        else:
            save_budget_csv(default_budget)
            return default_budget
    except Exception as e:
        print(f"Error loading budget: {str(e)}")
        st.error(f"Error loading budget: {str(e)}")
        return default_budget
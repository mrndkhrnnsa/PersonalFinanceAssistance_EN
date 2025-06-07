import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app_utils import fetch_data, get_financial_summary, load_budget_csv
import pandas as pd
import calendar
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.header("📊 Financial Analysis")

df = fetch_data()
if df.empty:
    st.warning("No transaction data available for analysis. Please input transactions first on the Input Transactions page.")
    st.stop()

df["month_period"] = df["date"].dt.to_period("M")
df["month"] = df["month_period"].astype(str)

months_mapping = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
}
df["month_label"] = df["date"].dt.month.map(months_mapping) + " " + df["date"].dt.year.astype(str)
df["year"] = df["date"].dt.year

budget = load_budget_csv()
allowed_categories = list(budget.keys()) if budget else ["Food", "Transport", "Shopping", "Entertainment", "Savings", "Others"]

period_type = st.radio("Select Analysis Period", ["Monthly", "Yearly"], horizontal=True)

if period_type == "Monthly":
    month_map = (
        df[["month", "month_label"]]
        .drop_duplicates()
        .sort_values("month")
        .set_index("month")["month_label"]
        .to_dict()
    )
    label_to_month = {v: k for k, v in month_map.items()}

    available_month_labels = list(month_map.values())
    selected_month_label = st.selectbox("Select Month", available_month_labels)
    selected_month = label_to_month[selected_month_label]

    month_df = df[df["month"] == selected_month]
    summary = get_financial_summary(month_df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"Rp {summary['total_income']:,.0f}")
    col2.metric("Total Expense", f"Rp {summary['total_expense']:,.0f}")
    col3.metric("Balance", f"Rp {summary['balance']:,.0f}")

    # 1. Budget vs Actual Spending Bar Chart
    st.subheader("1️⃣ Budget vs Actual Spending")
    actual = (
        month_df[month_df["category"] == "Expense"]
        .groupby("subcategory")["amount"]
        .sum()
        .reindex(allowed_categories, fill_value=0)
    )
    budget_series = pd.Series(budget)
    compare_df = pd.DataFrame({
        "Category": allowed_categories,
        "Actual": actual.values,
        "Budget": budget_series.reindex(allowed_categories, fill_value=0).values
    })
    compare_df = compare_df.melt(id_vars="Category", value_vars=["Actual", "Budget"], var_name="Type", value_name="Amount")
    fig = px.bar(
        compare_df, x="Category", y="Amount", color="Type", barmode="group",
        color_discrete_sequence=["#e43434","#328ed0" ])

    st.plotly_chart(fig, use_container_width=True)

    # 2. Spending Distribution Pie Chart
    st.subheader("2️⃣ Spending Distribution")
    spend_dist = (
        month_df[month_df["category"] == "Expense"]
        .groupby("subcategory")["amount"]
        .sum()
        .reindex(allowed_categories, fill_value=0)
    )
    spend_dist_nonzero = spend_dist[spend_dist > 0]
    if spend_dist_nonzero.sum() > 0:
        fig2 = px.pie(
            names=spend_dist_nonzero.index,
            values=spend_dist_nonzero.values,
            color_discrete_sequence=px.colors.diverging.RdBu_r
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        fig2.update_layout(height=400, width=400, legend_title="Subcategory",)
        st.plotly_chart(fig2)
    else:
        st.info("No expense data for this month.")

    # 3. Calendar Heatmap of Daily Spending (Blues)
    st.subheader("3️⃣ Daily Spending Calendar Heatmap")
    month_df["day"] = month_df["date"].dt.day
    daily_spending = (
        month_df[month_df["category"] == "Expense"]
        .groupby("day")["amount"]
        .sum()
    )

    year, month = month_df["date"].dt.year.iloc[0], month_df["date"].dt.month.iloc[0]
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
    heatmap = np.zeros((len(month_days), 7))
    day_labels = np.full((len(month_days), 7), "", dtype=object)
    for week_idx, week in enumerate(month_days):
        for day_idx, day in enumerate(week):
            if day != 0:
                heatmap[week_idx, day_idx] = daily_spending.get(day, 0)
                day_labels[week_idx, day_idx] = str(day)
            else:
                heatmap[week_idx, day_idx] = np.nan
                day_labels[week_idx, day_idx] = ""

    fig3 = go.Figure(
        data=go.Heatmap(
            z=heatmap,
            x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            y=[f"Week {i+1}" for i in range(len(month_days))],
            colorscale="Blues",
            colorbar=dict(title="Amount (Rp)"),
            hoverinfo="z"
        )
    )

    for week_idx, week in enumerate(month_days):
        for day_idx, day in enumerate(week):
            if day != 0:
                value = heatmap[week_idx, day_idx]
                fig3.add_annotation(
                    x=day_idx, y=week_idx,
                    text=f"{int(day)}<br>{int(value):,}",
                    showarrow=False,
                    font=dict(size=10, color="black"),
                    xanchor="center", yanchor="middle"
                )
    fig3.update_layout(
        xaxis=dict(side="top"),
        height=600, width=600
    )
    st.plotly_chart(fig3)

else:
    available_years = sorted(df["year"].unique().tolist())
    selected_year = st.selectbox("Select Year", available_years)
    year_df = df[df["date"].dt.year == selected_year]

    # 1. Monthly Cashflow Summary Line Chart
    st.subheader("1️⃣ Monthly Cashflow Recap")
    monthly_cashflow = (
        year_df.groupby(year_df["date"].dt.to_period("M")).apply(
            lambda x: x[x["category"] == "Income"]["amount"].sum() - x[x["category"] == "Expense"]["amount"].sum()
        )
    )
    monthly_cashflow.index = [i.strftime("%B %Y") for i in monthly_cashflow.index]
    fig4 = px.line(
        x=monthly_cashflow.index,
        y=monthly_cashflow.values,
        markers=True,
        labels={"x": "Month", "y": "Cashflow (Rp)"},
        color_discrete_sequence=px.colors.diverging.RdBu_r
    )
    st.plotly_chart(fig4, use_container_width=True)

    # 2. Income vs Expense per Month (Blue for Income, Red for Expense)
    st.subheader("2️⃣ Income vs Expense per Month")
    monthly_summary = (
        year_df.groupby([year_df["date"].dt.to_period("M"), "category"])["amount"]
        .sum()
        .reset_index()
    )
    monthly_summary["date"] = monthly_summary["date"].dt.to_timestamp()
    monthly_summary.rename(columns={"date": "Month", "category": "Category", "amount": "Amount"}, inplace=True)
    fig = px.bar(
        monthly_summary,
        x="Month",
        y="Amount",
        color="Category",
        barmode="group",
        color_discrete_map={"Income": "#328ed0", "Expense": "#e43434"}
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Amount (Rp)",
        legend_title="Category",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. Spending by Sub-Category Over the Year
    st.subheader("3️⃣ Yearly Expense Distribution by Category")
    spend_by_cat = (
        year_df[year_df["category"] == "Expense"]
        .groupby([year_df["date"].dt.to_period("M"), "subcategory"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reindex(columns=allowed_categories, fill_value=0)
    )
    spend_by_cat.index = [i.strftime("%B %Y") for i in spend_by_cat.index]
    if not spend_by_cat.empty:
        spend_by_cat_reset = spend_by_cat.reset_index().rename(columns={"index": "Month"})
        spend_by_cat_melt = spend_by_cat_reset.melt(id_vars="Month", var_name="Category", value_name="Amount")
        fig5 = px.bar(
            spend_by_cat_melt,
            x="Month",
            y="Amount",
            color="Category",
            barmode="group",
            title=f"Yearly Expense Distribution by Category - {selected_year}",
            color_discrete_sequence=px.colors.sequential.RdBu_r
        )
        fig5.update_layout(xaxis_title="Month", yaxis_title="Amount (Rp)", legend_title="Subcategory",)
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("No expense data for this year.")
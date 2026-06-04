import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
from utils import *
from logic import *
import database
import plotly.express as px
from smart_tips import generate_smart_work_tips, render_smart_work_section
import proposal

def render(USER, USER_CONFIG):
    import plotly.express as px
    conn = database.conn
    c = database.c
    st.title("💰 Expenses")
    import ai as _ai_exp
    
    df_full = get_activities_df(USER)
    df_full = df_full[df_full['amount'] > 0]
    
    # Keep only last 60 days for delete management view to prevent page lag
    if not df_full.empty:
        cutoff_date = (get_ist_now().date() - timedelta(days=60)).strftime('%Y-%m-%d')
        df = df_full[df_full['date'] >= cutoff_date].copy()
    else:
        df = df_full.copy()
    
    if not df_full.empty:
        df_full['year_str'] = pd.to_datetime(df_full['date']).dt.strftime('%Y')
        df_full['month_str'] = pd.to_datetime(df_full['date']).dt.strftime('%Y-%m')
        
        current_year_str = get_ist_now().date().strftime('%Y')
        current_month_str = get_ist_now().date().strftime('%Y-%m')
        current_month_exp = df_full[df_full['month_str'] == current_month_str]['amount'].sum()
        current_month_cats = df_full[df_full['month_str'] == current_month_str]['type'].nunique()
    
        e1, e2 = st.columns(2)
        e1.metric(f"Current Month Expenses ({current_month_str})", f"₹{round(current_month_exp, 2)}")
        e2.metric("Categories (Current Month)", f"{current_month_cats}")
    
        # Month-wise Expenses
        st.markdown("### 📅 Month-wise Expenses")
        month_wise_exp = df_full.groupby('month_str')['amount'].sum().reset_index().sort_values('month_str', ascending=False)
        st.dataframe(month_wise_exp.rename(columns={'month_str': 'Month', 'amount': 'Total Expense (₹)'}), width='stretch', hide_index=True)
    
        # Year-wise Expenses
        st.markdown("### 📅 Year-wise Expenses")
        year_wise_exp = df_full.groupby('year_str')['amount'].sum().reset_index().sort_values('year_str', ascending=False)
        st.dataframe(year_wise_exp.rename(columns={'year_str': 'Year', 'amount': 'Total Expense (₹)'}), width='stretch', hide_index=True)
    
        # Date-wise Breakdown
        st.markdown("### 📅 Date-wise Expense Breakdown")
        date_breakdown_df = df_full[['date', 'type', 'subject', 'chapter', 'amount']].copy()
        date_breakdown_df = date_breakdown_df.rename(columns={
            'date': 'Date',
            'type': 'Category',
            'subject': 'Subject',
            'chapter': 'Description/Details',
            'amount': 'Amount (₹)'
        }).sort_values('Date', ascending=False)
        st.dataframe(date_breakdown_df, width='stretch', hide_index=True)
    
        # Category breakdown by Year & Month
        st.markdown("### 🔍 Category Breakdown")
        
        col_yr, col_mn = st.columns(2)
        with col_yr:
            selected_year = st.selectbox("Select Year", year_wise_exp['year_str'].tolist(), key="cat_breakdown_year")
            
        if selected_year:
            year_df = df_full[df_full['year_str'] == selected_year].copy()
            year_df['month_num'] = pd.to_datetime(year_df['date']).dt.month
            
            import calendar as _cal
            available_months = sorted(year_df['month_num'].unique())
            month_options = ["All Months"] + [_cal.month_name[m] for m in available_months]
            
            with col_mn:
                selected_month_name = st.selectbox("Select Month", month_options, key="cat_breakdown_month")
            
            if selected_month_name != "All Months":
                month_idx = list(_cal.month_name).index(selected_month_name)
                filtered_df = year_df[year_df['month_num'] == month_idx]
                title_suffix = f"{selected_month_name} {selected_year}"
            else:
                filtered_df = year_df
                title_suffix = f"{selected_year}"
                
            exp_grp = filtered_df.groupby('type')['amount'].sum().sort_values(ascending=False).reset_index()
            
            col_eb, col_ep = st.columns(2)
            with col_eb:
                st.dataframe(exp_grp.rename(columns={'type':'Category', 'amount':'Amount (₹)'}), width='stretch', hide_index=True)
            with col_ep:
                fig_ep = px.pie(exp_grp, names='type', values='amount',
                                title=f"Expense Distribution ({title_suffix})",
                                color_discrete_sequence=px.colors.qualitative.Set3)
                fig_ep.update_traces(
                    textinfo='percent+value',
                    texttemplate='₹%{value:,.2f}<br>%{percent:.1%}',
                    hovertemplate="%{label}<br>Amount: ₹%{value:,.2f}<br>Percentage: %{percent:.1%}<extra></extra>"
                )
                st.plotly_chart(fig_ep, width='stretch', key=f"expenses_pie_{selected_year}_{selected_month_name}")
    
    
    
        # Variables needed for 60-day summary below
        if not df.empty:
            total_exp = df['amount'].sum()
            exp_grp = df.groupby('type')['amount'].sum().sort_values(ascending=False)
        else:
            total_exp = 0
            exp_grp = pd.Series(dtype=float)
    
        # ── NEW: EXPENSE TREND GRAPHS (RESTRUCTURED) ─────────────────────────
        st.divider()
        st.markdown("### 📈 Expense Trend Analysis")
        
        # Prepare date-time features
        df_exp = df_full.copy()
        df_exp['date_dt'] = pd.to_datetime(df_exp['date'])
        df_exp['hour'] = df_exp.apply(extract_hour_from_row, axis=1)
        df_exp['day_name'] = df_exp['date_dt'].dt.day_name()
        df_exp['month_str'] = df_exp['date_dt'].dt.strftime('%Y-%m')
        df_exp['year'] = df_exp['date_dt'].dt.year
        
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # 1. Hourly Distribution
        st.markdown("#### ⏰ Hourly Distribution")
        h_exp = df_exp.dropna(subset=['hour']).groupby('hour')['amount'].sum().reset_index()
        if not h_exp.empty:
            h_all = pd.DataFrame({'hour': range(24)})
            h_full = h_all.merge(h_exp, on='hour', how='left').fillna(0)
            h_full['hour_label'] = h_full['hour'].apply(lambda h: f"{h:02d}:00")
            fig_h = px.line(h_full, x='hour_label', y='amount', markers=True,
                           title="Expenses by Hour of Day",
                           labels={'hour_label': 'Hour', 'amount': 'Amount (₹)'},
                           color_discrete_sequence=['#f59e0b'])
            st.plotly_chart(fig_h, width='stretch', key="exp_hourly_line")
            
            if st.checkbox("Show trend for all activities (Category-wise)", key="exp_hour_all_activities"):
                h_cat_exp = df_exp.dropna(subset=['hour']).groupby(['hour', 'type'])['amount'].sum().reset_index()
                h_cat_exp['hour_label'] = h_cat_exp['hour'].apply(lambda h: f"{h:02d}:00")
                fig_h_cat = px.line(h_cat_exp, x='hour_label', y='amount', color='type', markers=True,
                               title="Hourly Expense Trend by Category",
                               labels={'hour_label': 'Hour', 'amount': 'Amount (₹)', 'type': 'Category'})
                st.plotly_chart(fig_h_cat, width='stretch', key="exp_hourly_trend_cat")
        else:
            st.caption("No hourly data available.")
    
        # 2. Weekday Distribution
        st.markdown("#### 📅 Weekday Distribution")
        d_exp = df_exp.groupby('day_name')['amount'].sum().reindex(days_order).reset_index().fillna(0)
        fig_d = px.line(d_exp, x='day_name', y='amount', markers=True,
                       title="Expenses by Day of Week",
                       labels={'day_name': 'Day', 'amount': 'Amount (₹)'},
                       color_discrete_sequence=['#3b82f6'])
        st.plotly_chart(fig_d, width='stretch', key="exp_daywise_line")
        
        if st.checkbox("Show trend for all activities (Category-wise)", key="exp_daywise_all_activities"):
            d_cat_exp = df_exp.groupby(['day_name', 'type'])['amount'].sum().reset_index()
            # To ensure the order is correct, we can convert day_name to categorical
            d_cat_exp['day_name'] = pd.Categorical(d_cat_exp['day_name'], categories=days_order, ordered=True)
            d_cat_exp = d_cat_exp.sort_values('day_name')
            fig_d_cat = px.line(d_cat_exp, x='day_name', y='amount', color='type', markers=True,
                           title="Expenses by Day of Week by Category",
                           labels={'day_name': 'Day', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_d_cat, width='stretch', key="exp_daywise_trend_cat")
    
        # 3. Daily Trend
        st.markdown("#### 📆 Daily Trend")
        daily_exp = df.groupby('date')['amount'].sum().reset_index().sort_values('date')
        fig_daily = px.line(daily_exp, x='date', y='amount', markers=True,
                           title="Daily Expense Trend",
                           labels={'date': 'Date', 'amount': 'Amount (₹)'},
                           color_discrete_sequence=['#10b981'])
        st.plotly_chart(fig_daily, width='stretch', key="exp_daily_trend")
        
        if st.checkbox("Show trend for all activities (Category-wise)", key="exp_daily_all_activities"):
            daily_cat_exp = df_exp.groupby(['date', 'type'])['amount'].sum().reset_index().sort_values('date')
            fig_daily_cat = px.line(daily_cat_exp, x='date', y='amount', color='type', markers=True,
                               title="Daily Expense Trend by Category",
                               labels={'date': 'Date', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_daily_cat, width='stretch', key="exp_daily_trend_cat")
    
        # 3.5 Monthly Trend
        st.markdown("#### 📅 Monthly Trend")
        monthly_exp = df_exp.groupby('month_str')['amount'].sum().reset_index().sort_values('month_str')
        fig_monthly = px.line(monthly_exp, x='month_str', y='amount', markers=True,
                             title="Monthly Expense Trend (Overall)",
                             labels={'month_str': 'Month', 'amount': 'Amount (₹)'},
                             color_discrete_sequence=['#f59e0b'])
        st.plotly_chart(fig_monthly, width='stretch', key="exp_monthly_trend_overall")
    
        show_all_activities = st.checkbox("Show trend for all activities (Category-wise)", key="exp_month_all_activities")
        if show_all_activities:
            month_cat_trend = df_exp.groupby(['month_str', 'type'])['amount'].sum().reset_index().sort_values('month_str')
            fig_monthly_cat = px.line(month_cat_trend, x='month_str', y='amount', color='type', markers=True,
                                     title="Monthly Expense Trend by Category",
                                     labels={'month_str': 'Month', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_monthly_cat, width='stretch', key="exp_monthly_trend_cat")
    
        # 4. Yearly Trend
        st.markdown("#### 📊 Yearly Trend")
        y_trend = df_exp.groupby('year')['amount'].sum().reset_index().sort_values('year')
        fig_y = px.line(y_trend, x='year', y='amount', markers=True,
                       title="Yearly Expense Trend",
                       labels={'year': 'Year', 'amount': 'Amount (₹)'},
                       color_discrete_sequence=['#8b5cf6'])
        st.plotly_chart(fig_y, width='stretch', key="exp_yearly_trend")
        
        if st.checkbox("Show trend for all activities (Category-wise)", key="exp_year_all_activities"):
            y_cat_trend = df_exp.groupby(['year', 'type'])['amount'].sum().reset_index().sort_values('year')
            fig_y_cat = px.line(y_cat_trend, x='year', y='amount', color='type', markers=True,
                           title="Yearly Expense Trend by Category",
                           labels={'year': 'Year', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_y_cat, width='stretch', key="exp_yearly_trend_cat")
    
        # Expense Summary Analysis
        st.divider()
        st.markdown(f"### 📊 Expense Analysis Summary ({current_year_str})")
        
        df_yearly = df_full[df_full['year_str'] == current_year_str]
        
        exp_stats_col1, exp_stats_col2, exp_stats_col3, exp_stats_col4 = st.columns(4)
        
        total_exp_yearly = df_yearly['amount'].sum()
        
        with exp_stats_col1:
            st.metric("Total Expenses", f"₹{total_exp_yearly:.0f}")
        with exp_stats_col2:
            avg_exp = df_yearly['amount'].mean()
            st.metric("Average Expense", f"₹{avg_exp:.0f}" if pd.notna(avg_exp) else "₹0")
        with exp_stats_col3:
            yearly_exp_grp = df_yearly.groupby('type')['amount'].sum().sort_values(ascending=False)
            max_category = yearly_exp_grp.idxmax() if not yearly_exp_grp.empty else "N/A"
            max_amount = yearly_exp_grp.max() if not yearly_exp_grp.empty else 0
            st.metric("Highest Category", max_category, f"₹{max_amount:.0f}")
        with exp_stats_col4:
            day_grp = df_yearly.groupby('date')['amount'].sum()
            highest_day = day_grp.idxmax() if not day_grp.empty else "N/A"
            highest_day_amount = day_grp.max() if not day_grp.empty else 0
            st.metric("Highest Spending Day", str(highest_day), f"₹{highest_day_amount:.0f}")
        
        # Daily average
        daily_avg = df_yearly.groupby('date')['amount'].sum().mean()
        st.info(f"📆 **Daily Average**: ₹{daily_avg:.0f}/day" if pd.notna(daily_avg) else "📆 **Daily Average**: ₹0/day")
        
        st.info("💡 Use the **Ask Esu** page to get personalized expense optimization and budgeting strategies.")
    
    
    else:
        st.info("No expenses recorded yet.")
    
    # ---------------- MANAGE USERS ----------------

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
from utils import *
from logic import *
import database
from smart_tips import generate_smart_work_tips, render_smart_work_section
import proposal

def render(USER, USER_CONFIG):
    import plotly.express as px
    conn = database.conn
    c = database.c
    st.title("📊 Productivity Analysis")
    
    import plotly.graph_objects as go
    
    df = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    if not df.empty:
        if 'start_time' not in df.columns: df['start_time'] = None
        df['start_time'] = df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        df['chapter'] = df['chapter'].apply(get_clean_chapter)
    
    # Dynamically build PRODUCTIVE and ESSENTIAL from custom activities
    try:
        cb_df = read_sql("SELECT name, activity_type FROM custom_boxes WHERE username=%s", (USER,))
        custom_productive = cb_df[cb_df['activity_type'] == 'Productive']['name'].tolist()
        custom_essential  = cb_df[cb_df['activity_type'] == 'Essential']['name'].tolist()
    except:
        custom_productive, custom_essential = [], []
    
    ALL_PRODUCTIVE = [a for a in (PRODUCTIVE_TYPES + custom_productive) if a != "UPSC App"]
    ALL_ESSENTIAL  = [a for a in (ESSENTIAL_TYPES + custom_essential) if a != "UPSC App"]
    
    # Define NEUTRAL_TYPES locally if not imported to avoid NameError
    try:
        ALL_NEUTRAL = NEUTRAL_TYPES
    except NameError:
        ALL_NEUTRAL = ["Sleep", "Powernap", "Napping"]
    
    tab_daily, tab_monthly, tab_yearly = st.tabs([
        "📅 Daily Productivity Analysis",
        "📆 Monthly Productivity Analysis",
        "📈 Yearly Productivity Analysis"
    ])
    
    # ════════════════════════════════════════════
    # TAB 1 — DAILY
    # ════════════════════════════════════════════
    with tab_daily:
        st.subheader("📅 Daily Productivity Analysis")
    
        # Keep only last 60 days for daily view
        if not df.empty:
            cutoff_date = (get_ist_now().date() - timedelta(days=60)).strftime('%Y-%m-%d')
            df_daily = df[df['date'] >= cutoff_date].copy()
        else:
            df_daily = df.copy()
    
        if df_daily.empty:
            st.info("No activity data found.")
        else:
            # Load sleep data for daily report
            try:
                hl_df = read_sql(
                    "SELECT date, sleep_time, wakeup_time, powernap FROM health_logs WHERE username=%s ORDER BY date ASC",
                    (USER,)
                )
                sleep_hours_dict = {}
                sleep_intervals_dict = {}
                powernap_dict = {}
                hl_map = {}
                if not hl_df.empty:
                    hl_map = {str(r['date']): r for _, r in hl_df.iterrows()}
                    for date_str in sorted(hl_map.keys()):
                        curr = hl_map[date_str]
                        prev_date = (pd.to_datetime(date_str) - timedelta(days=1)).strftime('%Y-%m-%d')
                        prev = hl_map.get(prev_date, {})
                        sleep_a = calculate_sleep_hours(prev.get('sleep_time'), curr.get('wakeup_time'))
                        sleep_b = 99.0
                        s_curr = curr.get('sleep_time', '')
                        if s_curr and "AM" in str(s_curr).upper():
                            sleep_b = calculate_sleep_hours(s_curr, curr.get('wakeup_time'))
                        sleep_hours_dict[date_str] = min(sleep_a, sleep_b)
                        powernap_dict[date_str] = curr.get('powernap', 0)
                        
                        # Store intervals for overlap logic
                        sleep_intervals_dict[date_str] = get_sleep_intervals(prev.get('sleep_time'), curr.get('wakeup_time'))
            except:
                sleep_hours_dict = {}
                sleep_intervals_dict = {}
                powernap_dict = {}
                hl_map = {}
            
            prod_df     = df_daily[df_daily['type'].isin(ALL_PRODUCTIVE)]
            essential_df= df_daily[df_daily['type'].isin(ALL_ESSENTIAL)]
            waste_df    = df_daily[~df_daily['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL + ALL_NEUTRAL)]
    
            # Metrics row
            m1, m2, m3 = st.columns(3)
            m1.metric("Productivity %", f"{productivity_score(df_daily, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict, sleep_intervals_dict=sleep_intervals_dict)}%")
            m2.metric("Study Streak",   f"{streak(df_daily)} days")
            m3.metric("Focus Score",    f"{focus_score(df_daily)}%")
    
            st.divider()
    
            # ── PRODUCTIVITY ANALYSIS ────────────────────────────────────
            st.markdown("### 📈 Productivity Analysis")
    
            # TABLE FIRST
            report_df = daily_report(df_daily, sleep_data=sleep_hours_dict, powernap_data=powernap_dict, sleep_intervals_dict=sleep_intervals_dict)
            if not report_df.empty:
                st.markdown("**📋 Daily Performance Report Table**")
                # Updated table prioritizing scores
                st.dataframe(report_df[['date', 'productivity_%', 'waste_%', 'productive_hours', 'waste_hours', 'essential_hours', 'sleep_hours', 'powernap']], 
                             column_config={
                                 "date": "Date",
                                 "productivity_%": st.column_config.ProgressColumn("Productivity (%)", min_value=0, max_value=100, format="%d%%"),
                                 "waste_%": st.column_config.ProgressColumn("Waste (%)", min_value=0, max_value=100, format="%d%%"),
                                 "productive_hours": st.column_config.NumberColumn("Prod (h)", format="%.1f"),
                                 "waste_hours": st.column_config.NumberColumn("Waste (h)", format="%.1f"),
                                 "essential_hours": st.column_config.NumberColumn("Ess (h)", format="%.1f"),
                                 "sleep_hours": st.column_config.NumberColumn("Sleep (h)", format="%.1f"),
                                 "powernap": st.column_config.NumberColumn("Nap (h)", format="%.1f")
                             },
                             width='stretch', hide_index=True)
    
    
            prod_total      = prod_df['duration'].sum()
            essential_total = essential_df['duration'].sum()
            waste_total     = waste_df['duration'].sum()
    
            # Line: Productive & Waste ONLY — Essential removed
            if not report_df.empty:
                trend_df_15 = report_df.tail(15)
                fig_trend_15 = go.Figure()
                fig_trend_15.add_trace(go.Scatter(x=trend_df_15['date'], y=trend_df_15['productive_hours'],
                    mode='lines+markers', name='Productive', line=dict(color='#22c55e', width=3)))
                fig_trend_15.add_trace(go.Scatter(x=trend_df_15['date'], y=trend_df_15['waste_hours'],
                    mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3)))
                fig_trend_15.update_layout(title="Last 15 Days Productive vs Waste Trend",
                                        xaxis_title="Date", yaxis_title="Hours")
                st.plotly_chart(fig_trend_15, width='stretch', key="daily_trend_line_15")
                
                trend_df_30 = report_df.tail(30)
                fig_trend_30 = go.Figure()
                fig_trend_30.add_trace(go.Scatter(x=trend_df_30['date'], y=trend_df_30['productive_hours'],
                    mode='lines+markers', name='Productive', line=dict(color='#22c55e', width=3)))
                fig_trend_30.add_trace(go.Scatter(x=trend_df_30['date'], y=trend_df_30['waste_hours'],
                    mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3)))
                fig_trend_30.update_layout(title="Last 30 Days Productive vs Waste Trend",
                                        xaxis_title="Date", yaxis_title="Hours")
                st.plotly_chart(fig_trend_30, width='stretch', key="daily_trend_line_30")
    
            st.divider()
            
            # --- TOP 10 RANKINGS ---
            st.markdown("### 🏆 Top 10 Productivity & Waste Rankings (All-Time)")
            # Generate all-time report
            try:
                hl_df_all = read_sql("SELECT date, sleep_time, wakeup_time, powernap FROM health_logs WHERE username=%s ORDER BY date ASC", (USER,))
                all_sleep_intervals_dict = {}
                if not hl_df_all.empty:
                    hl_map_all = {str(r['date']): r for _, r in hl_df_all.iterrows()}
                    for date_str in sorted(hl_map_all.keys()):
                        curr = hl_map_all[date_str]
                        prev_date = (pd.to_datetime(date_str) - timedelta(days=1)).strftime('%Y-%m-%d')
                        prev = hl_map_all.get(prev_date, {})
                        all_sleep_intervals_dict[date_str] = get_sleep_intervals(prev.get('sleep_time'), curr.get('wakeup_time'))
            except:
                all_sleep_intervals_dict = {}
                
            all_time_report = daily_report(df, sleep_intervals_dict=all_sleep_intervals_dict)
            
            if not all_time_report.empty:
                tab_days, tab_weeks, tab_months, tab_years, tab_streaks = st.tabs([
                    "📅 Days", "📆 Weeks", "🗓️ Months", "📈 Years", "🔥 Streaks"
                ])
                
                with tab_days:
                    st.markdown("#### Top 10 Days")
                    col_p, col_w = st.columns(2)
                    with col_p:
                        st.markdown("**Productive Days**")
                        st.dataframe(get_top_periods(all_time_report, 'Day', 'productive'), hide_index=True, width='stretch')
                    with col_w:
                        st.markdown("**Waste Days**")
                        st.dataframe(get_top_periods(all_time_report, 'Day', 'waste'), hide_index=True, width='stretch')
                
                with tab_weeks:
                    st.markdown("#### Top 10 Weeks")
                    col_p, col_w = st.columns(2)
                    with col_p:
                        st.markdown("**Productive Weeks**")
                        st.dataframe(get_top_periods(all_time_report, 'Week', 'productive'), hide_index=True, width='stretch')
                    with col_w:
                        st.markdown("**Waste Weeks**")
                        st.dataframe(get_top_periods(all_time_report, 'Week', 'waste'), hide_index=True, width='stretch')
                        
                with tab_months:
                    st.markdown("#### Top 10 Months")
                    col_p, col_w = st.columns(2)
                    with col_p:
                        st.markdown("**Productive Months**")
                        st.dataframe(get_top_periods(all_time_report, 'Month', 'productive'), hide_index=True, width='stretch')
                    with col_w:
                        st.markdown("**Waste Months**")
                        st.dataframe(get_top_periods(all_time_report, 'Month', 'waste'), hide_index=True, width='stretch')
                        
                with tab_years:
                    st.markdown("#### Top 10 Years")
                    col_p, col_w = st.columns(2)
                    with col_p:
                        st.markdown("**Productive Years**")
                        st.dataframe(get_top_periods(all_time_report, 'Year', 'productive'), hide_index=True, width='stretch')
                    with col_w:
                        st.markdown("**Waste Years**")
                        st.dataframe(get_top_periods(all_time_report, 'Year', 'waste'), hide_index=True, width='stretch')
                        
                with tab_streaks:
                    st.markdown("#### Top 10 Streaks")
                    col_p, col_w = st.columns(2)
                    with col_p:
                        st.markdown("**Productive Streaks**")
                        st.dataframe(get_top_streaks(all_time_report, 'productive'), hide_index=True, width='stretch')
                    with col_w:
                        st.markdown("**Waste Streaks**")
                        st.dataframe(get_top_streaks(all_time_report, 'waste'), hide_index=True, width='stretch')
    
            st.divider()
            st.markdown("### 📅 Day-wise Performance Trend")
            
            wd_prod = weekday_analysis(df_daily, ALL_PRODUCTIVE, sleep_intervals_dict=sleep_intervals_dict)
            _all_waste_types = [t for t in df_daily['type'].unique() if t not in ALL_PRODUCTIVE + ALL_ESSENTIAL + ALL_NEUTRAL]
            wd_waste = weekday_analysis(df_daily, _all_waste_types, sleep_intervals_dict=sleep_intervals_dict)
            
            if not wd_prod.empty or not wd_waste.empty:
                # Prepare combined dataframe
                if not wd_prod.empty: wd_prod['Category'] = 'Productive'
                if not wd_waste.empty: wd_waste['Category'] = 'Waste'
                
                wd_combined = pd.concat([df for df in [wd_prod, wd_waste] if not df.empty])
                
                fig_wd_combined = px.line(wd_combined, x='day_of_week', y='avg_hours', color='Category', markers=True,
                                         title="Avg Productivity vs Waste by Weekday",
                                         color_discrete_map={'Productive': '#22c55e', 'Waste': '#ef4444'})
                st.plotly_chart(fig_wd_combined, width='stretch', key="weekday_combined")
            else:
                st.caption("Not enough data for weekday trend.")
    
            st.divider()
            st.markdown("### 📱 Social Media & 📞 TalkOnCall Analytics")
            
            # Sub-activity Trends
            for act in ["Social Media", "TalkOnCall"]:
                st.markdown(f"#### {act} Analysis")
                trend_data = sub_activity_trend(df_daily, act, sleep_intervals_dict=sleep_intervals_dict)
                if not trend_data.empty:
                    # Date-wise multi-line graph
                    fig_sub_date = px.line(trend_data, x='date', y='duration', color='subject', markers=True,
                                          title=f"{act} Usage Trend (Date-wise)")
                    st.plotly_chart(fig_sub_date, width='stretch', key=f"trend_date_{act}")
                    
                    # Day-wise multi-line graph
                    trend_data['date_dt'] = pd.to_datetime(trend_data['date'])
                    trend_data['day_of_week'] = trend_data['date_dt'].dt.day_name()
                    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    
                    # Calculate average by day of week per subject
                    unique_dates_act = trend_data['date'].unique()
                    counts_act = pd.Series(pd.to_datetime(unique_dates_act)).dt.day_name().value_counts().to_dict()
                    
                    wd_sub = trend_data.groupby(['day_of_week', 'subject'])['duration'].sum().reset_index()
                    wd_sub['avg_hours'] = wd_sub.apply(lambda x: x['duration'] / counts_act.get(x['day_of_week'], 1), axis=1)
                    wd_sub['day_of_week'] = pd.Categorical(wd_sub['day_of_week'], categories=days_order, ordered=True)
                    wd_sub = wd_sub.sort_values('day_of_week')
                    
                    fig_sub_wd = px.line(wd_sub, x='day_of_week', y='avg_hours', color='subject', markers=True,
                                        title=f"{act} Avg Usage (Day-wise)")
                    st.plotly_chart(fig_sub_wd, width='stretch', key=f"trend_wd_{act}")
                else:
                    st.caption(f"No {act} data found.")
    
            st.divider()
            st.markdown("### ⚖️ Social Media vs TalkOnCall Comparison")
            
            # Combine both for comparison
            sm_data = df_daily[df_daily['type'] == "Social Media"].groupby('date')['duration'].sum().reset_index()
            tc_data = df_daily[df_daily['type'] == "TalkOnCall"].groupby('date')['duration'].sum().reset_index()
            
            if not sm_data.empty or not tc_data.empty:
                sm_data['Category'] = 'Social Media'
                tc_data['Category'] = 'TalkOnCall'
                comp_date = pd.concat([sm_data, tc_data])
                
                fig_comp_date = px.line(comp_date, x='date', y='duration', color='Category', markers=True,
                                        title="Social Media vs TalkOnCall (Date-wise)")
                st.plotly_chart(fig_comp_date, width='stretch', key="comp_date_sm_tc")
                
                # Weekday comparison
                comp_date['date_dt'] = pd.to_datetime(comp_date['date'])
                comp_date['day_of_week'] = comp_date['date_dt'].dt.day_name()
                
                unique_dates_comp = comp_date['date'].unique()
                counts_comp = pd.Series(pd.to_datetime(unique_dates_comp)).dt.day_name().value_counts().to_dict()
                
                wd_comp = comp_date.groupby(['day_of_week', 'Category'])['duration'].sum().reset_index()
                wd_comp['avg_hours'] = wd_comp.apply(lambda x: x['duration'] / counts_comp.get(x['day_of_week'], 1), axis=1)
                days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                wd_comp['day_of_week'] = pd.Categorical(wd_comp['day_of_week'], categories=days_order, ordered=True)
                wd_comp = wd_comp.sort_values('day_of_week')
                
                fig_comp_wd = px.line(wd_comp, x='day_of_week', y='avg_hours', color='Category', markers=True,
                                     title="Social Media vs TalkOnCall (Day-wise Avg)")
                st.plotly_chart(fig_comp_wd, width='stretch', key="comp_wd_sm_tc")
            else:
                st.caption("Not enough data for comparison.")
    
            import ai as _ai_d
            
            # ════════════════════════════════════════════════════════════════════════════════
            # PRODUCTIVITY SUMMARY & AI ANALYSIS
            # ════════════════════════════════════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("## 📊 Productivity Summary & AI Analysis")
            
            # Summary Metrics Display
            st.markdown("### 📈 Key Productivity Metrics")
            
            sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
            with sum_col1:
                st.metric("📚 Productive Hours", format_duration(prod_total), 
                         delta=f"{(prod_total/(prod_total+essential_total+waste_total)*100) if (prod_total+essential_total+waste_total)>0 else 0:.0f}%")
            with sum_col2:
                st.metric("⚡ Essential Hours", format_duration(essential_total),
                         delta=f"{(essential_total/(prod_total+essential_total+waste_total)*100) if (prod_total+essential_total+waste_total)>0 else 0:.0f}%")
            with sum_col3:
                st.metric("⚠️ Waste Hours", format_duration(waste_total),
                         delta=f"{(waste_total/(prod_total+essential_total+waste_total)*100) if (prod_total+essential_total+waste_total)>0 else 0:.0f}%")
            with sum_col4:
                st.metric("🎯 Overall Score", f"{productivity_score(df_daily, sleep_hours=sleep_hours_dict, sleep_intervals_dict=sleep_intervals_dict):.0f}%",
                         delta=f"Streak: {streak(df_daily)}d")
            
            # Time Allocation Analysis
            st.markdown("### 🔄 Time Allocation Breakdown")
            
            total_hours = prod_total + essential_total + waste_total
            if total_hours > 0:
                time_dist = pd.DataFrame({
                    'Category': ['Productive', 'Essential', 'Waste'],
                    'Hours': [prod_total, essential_total, waste_total],
                    'Percentage': [
                        round((prod_total/total_hours)*100, 1),
                        round((essential_total/total_hours)*100, 1),
                        round((waste_total/total_hours)*100, 1)
                    ]
                })
                
                col_stats, col_chart = st.columns([1, 1])
                with col_stats:
                    st.dataframe(time_dist, hide_index=True, width='stretch')
                with col_chart:
                    fig_dist = px.pie(time_dist, names='Category', values='Hours',
                                     color_discrete_map={'Productive':'#22c55e','Essential':'#3b82f6','Waste':'#ef4444'},
                                     title="Time Distribution")
                    st.plotly_chart(fig_dist, width='stretch', key="summary_pie")
                
                # Insights based on time allocation
                st.markdown("### 💡 Analysis Insights")
                
                prod_percent = (prod_total/total_hours)*100
                waste_percent = (waste_total/total_hours)*100
                
                insights_cols = st.columns(3)
                
                with insights_cols[0]:
                    if prod_percent >= 50:
                        st.success(f"✅ **Excellent Productivity** ({prod_percent:.0f}%)")
                        st.markdown(f"You're maintaining a high study ratio! Your top subjects are: **{', '.join(df_daily[df_daily['type'].isin(ALL_PRODUCTIVE)].groupby('subject')['duration'].sum().nlargest(2).index.tolist())}**.")
                        st.caption("🚀 *Tip: Try the **1-3-7 Revision Method** (revise after 1, 3, and 7 days) to lock in these gains.*")
                    elif prod_percent >= 35:
                        st.info(f"ℹ️ **Good Productivity** ({prod_percent:.0f}%)")
                        st.markdown("You're on the right track. Focus on more deep work sessions for your core subjects.")
                        st.caption("💡 *Tip: Use the **1-3-5 Rule**—complete 1 big, 3 medium, and 5 small tasks daily.*")
                    else:
                        st.warning(f"⚠️ **Low Productivity** ({prod_percent:.0f}%)")
                        st.markdown(f"Productivity is low. Most of your 'available' time is leaking into unlogged gaps or minor tasks.")
                        st.caption("🛠️ *Try: **Pomodoro 50/10**—50 mins deep work, 10 mins break. Start with just one session.*")
                
                with insights_cols[1]:
                    if waste_percent <= 15:
                        st.success(f"✅ **Excellent Waste Control** ({waste_percent:.0f}%)")
                        st.markdown("Minimal time leakage! You are very protective of your study hours.")
                    elif waste_percent <= 30:
                        st.info(f"ℹ️ **Moderate Waste** ({waste_percent:.0f}%)")
                        # Identify main waste triggers
                        waste_triggers = waste_df.groupby('type')['duration'].sum().nlargest(2).index.tolist()
                        trigger_str = f" (**{', '.join(waste_triggers)}**)" if waste_triggers else ""
                        st.markdown(f"Time is leaking{trigger_str}. Notice when you drift off.")
                        st.caption("💡 *Tip: Use the **2-Minute Rule**—if a task takes <2 mins, do it now. If not, schedule it.*")
                    else:
                        st.warning(f"⚠️ **High Waste Time** ({waste_percent:.0f}%)")
                        # Identifying the biggest culprit
                        culprits = waste_df.groupby('type')['duration'].sum().nlargest(2).index.tolist()
                        culprit_str = f" (Focus on **{', '.join(culprits)}**)" if culprits else ""
                        st.markdown(f"Critical time leakage detected{culprit_str}. Your unlogged gaps are considered waste.")
                        st.caption("🛠️ *Method: **Time Boxing**—Assign a specific hour only for {culprits[0] if culprits else 'social media'} to contain it.*")
                
                with insights_cols[2]:
                    f_score = focus_score(df_daily)
                    if f_score >= 75:
                        st.success(f"🎯 **Excellent Focus** ({f_score:.0f}%)")
                        st.markdown("Most of your study sessions are **Deep Work** (>= 2 hours long). Great concentration!")
                    elif f_score >= 50:
                        st.info(f"⚖️ **Balanced Focus** ({f_score:.0f}%)")
                        st.markdown("You have a mix of deep sessions and short bursts. Try to combine sessions for flow.")
                    else:
                        st.warning(f"🧊 **Fragmented Focus** ({f_score:.0f}%)")
                        st.markdown("Your sessions are mostly short (< 2 hours). It's hard to build context in short bursts.")
                    
                    with st.expander("❓ How is Focus Score calculated?"):
                        st.markdown("""
                        **Formula:** `(Deep Work Hours / Total Productive Hours) * 100`
                        
                        - **Deep Work**: Any session logged under 'Productive' types (Study, Revision, etc.) that lasts **2 hours or more** continuously.
                        - **Fragmented Work**: Sessions shorter than 2 hours.
                        
                        **💡 Tip to improve:** Instead of doing four 30-minute study sessions, try to combine them into one solid 2.5-hour block for a 100% focus score!
                        """)
                
                # Trend Analysis
                st.markdown("### 📉 Daily Trend Analysis")
                
                if not report_df.empty:
                    recent_days = min(7, len(report_df))
                    recent_report = report_df.tail(recent_days)
                    
                    trend_prod = recent_report['productive_hours'].mean()
                    trend_waste = recent_report['waste_hours'].mean()
                    trend_prod_pct = recent_report['productivity_%'].mean()
                    
                    trend_col1, trend_col2, trend_col3 = st.columns(3)
                    
                    with trend_col1:
                        st.info(f"""
                        📊 **Last {recent_days} Days Average**
                        
                        Productive: {format_duration(trend_prod)}/day
                        """)
                    
                    with trend_col2:
                        st.info(f"""
                        📊 **Waste Trend**
                        
                        Waste: {format_duration(trend_waste)}/day
                        """)
                    
                    with trend_col3:
                        st.info(f"""
                        📊 **Productivity Score**
                        
                        Average: {trend_prod_pct:.0f}%
                        """)
            
            st.divider()
            
            # AI Analysis Section
            st.markdown("### 🤖 AI Productivity Analysis")
            
            if st.button("🚀 Get Personalized Recommendations from Esu", key="gen_prod_insight"):
                with st.spinner("Esu is analyzing your productivity patterns..."):
                    # Prepare a period string
                    period_str = "all-time accumulated data"
                    insight = _ai_d.analyze_productivity(
                        prod_total, 
                        essential_total, 
                        waste_total, 
                        period_str, 
                        streak(df_daily)
                    )
                    st.markdown("---")
                    st.markdown(insight)
                    st.success("✅ Analysis complete!")
            else:
                st.markdown(f"""
                **📊 Quick Stats:**
                - **Productive**: {format_duration(prod_total)} | **Essential**: {format_duration(essential_total)} | **Waste**: {format_duration(waste_total)}
                - **Study Streak**: {streak(df_daily)} days
                
                *Click the button above to get personalized AI recommendations based on your data.*
                """)
    
            st.divider()
    
            # ── WASTE ANALYSIS ────────────────────────────────────────────
            st.markdown("### ⚠️ Waste Analysis")
    
            if waste_df.empty:
                st.success("No waste time logged! 🎉")
            else:
                # ── Activity Filter Dropdown (empty = show all) ──
                _all_waste_types = sorted(waste_df['type'].unique().tolist())
                _selected_waste_types = st.multiselect(
                    "🎯 Filter by Waste Activity (leave empty to show all)",
                    options=_all_waste_types,
                    default=[],
                    key="waste_activity_filter"
                )
    
                # Apply filter: if nothing selected → show all; otherwise → filter
                if _selected_waste_types:
                    _filtered_waste_df = waste_df[waste_df['type'].isin(_selected_waste_types)].copy()
                else:
                    _filtered_waste_df = waste_df.copy()
    
                # TABLE
                waste_tbl = _filtered_waste_df.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date', ascending=False)
                st.markdown("**📋 Waste Entries Table**")
                st.dataframe(waste_tbl.rename(columns={'date':'Date','type':'Activity','duration':'Hours'}),
                             width='stretch')
    
                # Show "Waste by Activity Type" bar only when no specific filter is applied
                if not _selected_waste_types:
                    w_grp = _filtered_waste_df.groupby('type')['duration'].sum().reset_index().sort_values('duration', ascending=False)
                    fig_wb = px.bar(w_grp, x='type', y='duration',
                                    labels={'type':'Activity','duration':'Hours'},
                                    color_discrete_sequence=['#ef4444'], title="Waste by Activity Type")
                    st.plotly_chart(fig_wb, width='stretch', key="daily_waste_bar")
    
                waste_trend = _filtered_waste_df.groupby('date')['duration'].sum().reset_index()
                fig_wl = go.Figure()
                fig_wl.add_trace(go.Scatter(x=waste_trend['date'], y=waste_trend['duration'],
                    mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3),
                    fill='tozeroy', fillcolor='rgba(239,68,68,0.1)'))
                fig_wl.update_layout(title="Daily Waste Trend", xaxis_title="Date", yaxis_title="Hours")
                st.plotly_chart(fig_wl, width='stretch', key="daily_waste_line")
    
                # ── Hourly Distribution ──
                st.markdown("#### ⏰ Hourly Distribution")
                _wdf_h = _filtered_waste_df.copy()
                _wdf_h['_hour'] = _wdf_h.apply(extract_hour_from_row, axis=1)
                _wdf_h_valid = _wdf_h.dropna(subset=['_hour'])
                if not _wdf_h_valid.empty:
                    _wh_grp = _wdf_h_valid.groupby('_hour')['duration'].sum().reset_index()
                    _wh_all = pd.DataFrame({'_hour': range(24)})
                    _wh_all['_hour_label'] = _wh_all['_hour'].apply(lambda h: f"{h:02d}:00")
                    _wh_full = _wh_all.merge(_wh_grp[['_hour', 'duration']], on='_hour', how='left').fillna(0)
                    _fig_wh = go.Figure()
                    _fig_wh.add_trace(go.Scatter(
                        x=_wh_full['_hour_label'], y=_wh_full['duration'],
                        mode='lines+markers', name='Waste',
                        line=dict(color='#f97316', width=3),
                        fill='tozeroy', fillcolor='rgba(249,115,22,0.15)',
                        marker=dict(size=6, color='#fb923c')
                    ))
                    _fig_wh.update_layout(
                        title="Hourly Waste Distribution",
                        xaxis_title="Hour of Day", yaxis_title="Hours",
                        template='plotly_dark', hovermode='x unified',
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(_fig_wh, width='stretch', key="daily_waste_hourly_dist")
                else:
                    st.caption("⏰ No time-stamped entries found. Log activities with **Time Range (From-To)** to see hourly data.")
    
    
    
    
    
            st.divider()
    
            # ── ESSENTIAL ANALYSIS ────────────────────────────────────────────
            st.markdown("### 🔵 Essential Work Analysis")
    
            if essential_df.empty:
                st.info("No essential time logged! ℹ️")
            else:
                # ── Activity Filter Dropdown (empty = show all) ──
                _all_essential_types = sorted(essential_df['type'].unique().tolist())
                _selected_essential_types = st.multiselect(
                    "🎯 Filter by Essential Activity (leave empty to show all)",
                    options=_all_essential_types,
                    default=[],
                    key="essential_activity_filter"
                )
    
                # Apply filter: if nothing selected → show all; otherwise → filter
                if _selected_essential_types:
                    _filtered_essential_df = essential_df[essential_df['type'].isin(_selected_essential_types)].copy()
                else:
                    _filtered_essential_df = essential_df.copy()
    
                # TABLE
                essential_tbl = _filtered_essential_df.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date', ascending=False)
                st.markdown("**📋 Essential Entries Table**")
                st.dataframe(essential_tbl.rename(columns={'date':'Date','type':'Activity','duration':'Hours'}),
                             width='stretch')
    
                # Show "Essential by Activity Type" bar only when no specific filter is applied
                if not _selected_essential_types:
                    e_grp = _filtered_essential_df.groupby('type')['duration'].sum().reset_index().sort_values('duration', ascending=False)
                    fig_eb = px.bar(e_grp, x='type', y='duration',
                                    labels={'type':'Activity','duration':'Hours'},
                                    color_discrete_sequence=['#3b82f6'], title="Essential by Activity Type")
                    st.plotly_chart(fig_eb, width='stretch', key="daily_essential_bar")
    
                essential_trend = _filtered_essential_df.groupby('date')['duration'].sum().reset_index()
                fig_el = go.Figure()
                fig_el.add_trace(go.Scatter(x=essential_trend['date'], y=essential_trend['duration'],
                    mode='lines+markers', name='Essential', line=dict(color='#3b82f6', width=3),
                    fill='tozeroy', fillcolor='rgba(59,130,246,0.1)'))
                fig_el.update_layout(title="Daily Essential Trend", xaxis_title="Date", yaxis_title="Hours")
                st.plotly_chart(fig_el, width='stretch', key="daily_essential_line")
    
                # ── Hourly Distribution ──
                st.markdown("#### ⏰ Hourly Distribution")
                _edf_h = _filtered_essential_df.copy()
                _edf_h['_hour'] = _edf_h.apply(extract_hour_from_row, axis=1)
                _edf_h_valid = _edf_h.dropna(subset=['_hour'])
                if not _edf_h_valid.empty:
                    _eh_grp = _edf_h_valid.groupby('_hour')['duration'].sum().reset_index()
                    _eh_all = pd.DataFrame({'_hour': range(24)})
                    _eh_all['_hour_label'] = _eh_all['_hour'].apply(lambda h: f"{h:02d}:00")
                    _eh_full = _eh_all.merge(_eh_grp[['_hour', 'duration']], on='_hour', how='left').fillna(0)
                    _fig_eh = go.Figure()
                    _fig_eh.add_trace(go.Scatter(
                        x=_eh_full['_hour_label'], y=_eh_full['duration'],
                        mode='lines+markers', name='Essential',
                        line=dict(color='#3b82f6', width=3),
                        fill='tozeroy', fillcolor='rgba(59,130,246,0.15)',
                        marker=dict(size=6, color='#60a5fa')
                    ))
                    _fig_eh.update_layout(
                        title="Hourly Essential Distribution",
                        xaxis_title="Hour of Day", yaxis_title="Hours",
                        template='plotly_dark', hovermode='x unified',
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(_fig_eh, width='stretch', key="daily_essential_hourly_dist")
                else:
                    st.caption("⏰ No time-stamped entries found. Log activities with **Time Range (From-To)** to see hourly data.")
    
    
    
            st.divider()
    
            # ════════════════════════════════════════════════════════════════════════════════
            # SECTION 1: SINGLE DATE ANALYSIS (24-Hour Breakdown for Selected Date)
            # ════════════════════════════════════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("## 📅 Single Date Analysis")
            st.markdown("*View hourly productivity breakdown for a specific date*")
            
            # Date picker for 24-hour analysis
            _tod_col1, _tod_col2 = st.columns([1, 4])
            with _tod_col1:
                selected_date_td = st.date_input("📅 Select Date", value=pd.to_datetime(list(df_daily['date'])[-1] if not df_daily.empty else date.today()).date() if not df_daily.empty else date.today(), key="24h_date_picker")
            
            # Filter data for selected date
            df_selected = df_daily[pd.to_datetime(df_daily['date']).dt.date == selected_date_td]
            
            # --- NEW: Get sleep intervals for the selected date ---
            sel_date_str = str(selected_date_td)
            curr_hl = hl_map.get(sel_date_str, {})
            prev_date_str = (pd.to_datetime(sel_date_str) - timedelta(days=1)).strftime('%Y-%m-%d')
            prev_hl = hl_map.get(prev_date_str, {})
            
            # We assume day-analysis shows sleep ending on that day
            # If they slept at 11 PM yesterday and woke up 6 AM today, we show 0-6 AM as sleep today.
            day_sleep_intervals = get_sleep_intervals(prev_hl.get('sleep_time'), curr_hl.get('wakeup_time'))
            
            tod_df = time_of_day_analysis_24h(df_selected, sleep_intervals=day_sleep_intervals)
            if not tod_df.empty:
                st.markdown(f"**📊 Hourly Performance Data - {selected_date_td.strftime('%A, %B %d, %Y')}**")
                # Updated table prioritizing % metrics and removing raw hours as requested
                st.dataframe(tod_df[['hour', 'productivity_%', 'waste_%', 'productive_hours', 'waste_hours']], 
                             column_config={
                                 "hour": "Hour",
                                 "productivity_%": st.column_config.ProgressColumn("Productivity (%)", min_value=0, max_value=100, format="%d%%"),
                                 "waste_%": st.column_config.ProgressColumn("Waste (%)", min_value=0, max_value=100, format="%d%%"),
                                 "productive_hours": st.column_config.NumberColumn("Prod (h)", format="%.2f"),
                                 "waste_hours": st.column_config.NumberColumn("Waste (h)", format="%.2f")
                             },
                             width='stretch', hide_index=True)
    
                # Combined Line chart: productivity % and waste % by hour
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=tod_df['hour'], y=tod_df['productivity_%'],
                                             mode='lines+markers', name='Productivity %',
                                             line=dict(color='#22c55e', width=3),
                                             marker=dict(size=8)))
                fig_line.add_trace(go.Scatter(x=tod_df['hour'], y=tod_df['waste_%'],
                                             mode='lines+markers', name='Waste %',
                                             line=dict(color='#ef4444', width=3, dash='dot'),
                                             marker=dict(size=6)))
                
                fig_line.update_layout(
                    title="Hourly Productivity vs Waste Trend",
                    yaxis_title="Percentage (%)", 
                    xaxis_title="Hour of Day",
                    hovermode='x unified',
                    height=450,
                    yaxis=dict(range=[0, 105]),
                    template='plotly_dark',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_line, width='stretch', key=f"daily_tod_line_{selected_date_td}")
                
            else:
                st.info(f"📝 No hourly data for {selected_date_td}.")
    
            # --- NEW: TOP 10 HOURLY SLOTS (OVERALL) ---
            st.markdown("### 🔝 Top 10 Productive & Waste Hours (Historical)")
            st.markdown("*Most productive and most wasted hours of the day based on your entire history*")
            
            t5_col1, t5_col2 = st.columns(2)
            with t5_col1:
                st.markdown("🎯 **Top 10 Productive Hours**")
                t5_prod = get_top_hours_all_time(df_daily, type='productive')
                if t5_prod:
                    t5_prod_df = pd.DataFrame(t5_prod)
                    st.dataframe(t5_prod_df[['time', 'duration']], 
                                 column_config={"time": "Hour Slot", "duration": "Total Hours Logged"},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No data yet.")
            
            with t5_col2:
                st.markdown("⚠️ **Top 10 Waste Hours**")
                t5_waste = get_top_hours_all_time(df_daily, type='waste')
                if t5_waste:
                    t5_waste_df = pd.DataFrame(t5_waste)
                    st.dataframe(t5_waste_df[['time', 'duration']], 
                                 column_config={"time": "Hour Slot", "duration": "Total Hours Logged"},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No data yet.")
    
    
    
    # ════════════════════════════════════════════
    # TAB 2 — MONTHLY
    # ════════════════════════════════════════════
    with tab_monthly:
        st.subheader("📆 Monthly Productivity Analysis")
    
        if df.empty:
            st.info("No activity data found.")
        else:
            import datetime as _dt
            now = _dt.date.today()
            sel_year_m  = st.number_input("Year",  value=now.year,  min_value=2020, max_value=2100, step=1, key="pa_year_m")
            sel_month_m = st.number_input("Month", value=now.month, min_value=1, max_value=12, step=1, key="pa_month_m")
    
            month_str = f"{int(sel_year_m)}-{int(sel_month_m):02d}"
            df['month_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
            month_df = df[df['month_str'] == month_str]
    
            if month_df.empty:
                st.warning(f"No data for {month_str}.")
            else:
                # Load sleep data for monthly report
                try:
                    hl_df = read_sql(
                        "SELECT date, sleep_time, wakeup_time, powernap FROM health_logs WHERE username=%s ORDER BY date ASC",
                        (USER,)
                    )
                    sleep_hours_dict = {}
                    sleep_intervals_dict = {}
                    powernap_dict = {}
                    if not hl_df.empty:
                        hl_map = {str(r['date']): r for _, r in hl_df.iterrows()}
                        for date_str in sorted(hl_map.keys()):
                            curr = hl_map[date_str]
                            prev_date = (pd.to_datetime(date_str) - timedelta(days=1)).strftime('%Y-%m-%d')
                            prev = hl_map.get(prev_date, {})
                            sleep_a = calculate_sleep_hours(prev.get('sleep_time'), curr.get('wakeup_time'))
                            sleep_b = 99.0
                            s_curr = curr.get('sleep_time', '')
                            if s_curr and "AM" in str(s_curr).upper():
                                sleep_b = calculate_sleep_hours(s_curr, curr.get('wakeup_time'))
                            sleep_hours_dict[date_str] = min(sleep_a, sleep_b)
                            powernap_dict[date_str] = curr.get('powernap', 0)
                            sleep_intervals_dict[date_str] = get_sleep_intervals(prev.get('sleep_time'), curr.get('wakeup_time'))
                except:
                    sleep_hours_dict = {}
                    sleep_intervals_dict = {}
                    powernap_dict = {}
                
                prod_m      = month_df[month_df['type'].isin(ALL_PRODUCTIVE)]
                essential_m = month_df[month_df['type'].isin(ALL_ESSENTIAL)]
                waste_m     = month_df[~month_df['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL + ALL_NEUTRAL)]
    
                pm1, pm2, pm3, pm4 = st.columns(4)
                pm1.metric("Productive Hrs", f"{round(prod_m['duration'].sum(),1)}h")
                pm2.metric("Essential Hrs",  f"{round(essential_m['duration'].sum(),1)}h")
                pm3.metric("Waste Hrs",      f"{round(waste_m['duration'].sum(),1)}h")
                pm4.metric("Productivity %", f"{productivity_score(month_df, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict, sleep_intervals_dict=sleep_intervals_dict)}%")
    
                st.divider()
    
                # ── PRODUCTIVITY ANALYSIS ────────────────────────────────────
                st.markdown("### 📈 Productivity Analysis")
    
                daily_m = daily_report(month_df, sleep_data=sleep_hours_dict, powernap_data=powernap_dict, sleep_intervals_dict=sleep_intervals_dict)
                if not daily_m.empty:
                    st.markdown("**📋 Day-by-Day Table**")
                    st.dataframe(daily_m[['date','productive_hours','essential_hours','waste_hours','sleep_hours','powernap','productivity_%']],
                                 width='stretch')
    
                m_bar_df = pd.DataFrame({
                    'Type': ['Productive', 'Essential', 'Waste'],
                    'Hours': [prod_m['duration'].sum(), essential_m['duration'].sum(), waste_m['duration'].sum()]
                })
                mc1, mc2 = st.columns(2)
                with mc1:
                    fig_mb = px.bar(m_bar_df, x='Type', y='Hours', color='Type',
                                    color_discrete_map={'Productive':'#22c55e','Essential':'#3b82f6','Waste':'#ef4444'},
                                    title=f"Time Distribution — {month_str}")
                    st.plotly_chart(fig_mb, width='stretch', key=f"monthly_bar_{month_str}")
                with mc2:
                    fig_mp = px.pie(m_bar_df, names='Type', values='Hours', color='Type',
                                    color_discrete_map={'Productive':'#22c55e','Essential':'#3b82f6','Waste':'#ef4444'},
                                    title=f"Time Share — {month_str}")
                    st.plotly_chart(fig_mp, width='stretch', key=f"monthly_pie_{month_str}")
    
                if not daily_m.empty:
                    # Line: Productive & Waste ONLY — Essential removed
                    fig_ml = go.Figure()
                    fig_ml.add_trace(go.Scatter(x=daily_m['date'], y=daily_m['productive_hours'],
                        mode='lines+markers', name='Productive', line=dict(color='#22c55e', width=3)))
                    fig_ml.add_trace(go.Scatter(x=daily_m['date'], y=daily_m['waste_hours'],
                        mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3)))
                    fig_ml.update_layout(title=f"Productive vs Waste Trend — {month_str}",
                                         xaxis_title="Date", yaxis_title="Hours")
                    st.plotly_chart(fig_ml, width='stretch', key=f"monthly_trend_line_{month_str}")
    
                    fig_mt = go.Figure()
                    fig_mt.add_trace(go.Bar(x=daily_m['date'], y=daily_m['productive_hours'],
                                            name='Productive', marker_color='#22c55e'))
                    fig_mt.add_trace(go.Bar(x=daily_m['date'], y=daily_m['essential_hours'],
                                            name='Essential', marker_color='#3b82f6'))
                    fig_mt.add_trace(go.Bar(x=daily_m['date'], y=daily_m['waste_hours'],
                                            name='Waste', marker_color='#ef4444'))
                    fig_mt.update_layout(barmode='stack', xaxis_title="Date", yaxis_title="Hours",
                                         title=f"Stacked Time per Day — {month_str}")
                    st.plotly_chart(fig_mt, width='stretch', key=f"monthly_stacked_{month_str}")
    
                study_m = prod_m[prod_m['type'].isin(['Study', 'Revision'])]
                if not study_m.empty:
                    st.markdown("**📚 Subject-wise Study & Revision Hours**")
                    subj_m_df = study_m.groupby('subject')['duration'].sum().sort_values(ascending=False).reset_index()
                    st.dataframe(subj_m_df.rename(columns={'subject':'Subject','duration':'Hours'}),
                                 width='stretch')
                    st.bar_chart(subj_m_df.set_index('subject')['duration'])
    
                import ai as _ai_m
                st.info("💡 Use the **Ask Esu** page to get personalized productivity tips.")
    
                st.divider()
    
                # ── WASTE ANALYSIS ────────────────────────────────────────────
                st.markdown("### ⚠️ Waste Analysis")
    
                if waste_m.empty:
                    st.success("No waste time this month! 🎉")
                else:
                    # ── Activity Filter Dropdown (empty = show all) ──
                    _all_waste_types_m = sorted(waste_m['type'].unique().tolist())
                    _selected_waste_types_m = st.multiselect(
                        "🎯 Filter by Waste Activity (leave empty to show all)",
                        options=_all_waste_types_m,
                        default=[],
                        key=f"waste_activity_filter_monthly_{month_str}"
                    )
    
                    # Apply filter: if nothing selected → show all; otherwise → filter
                    if _selected_waste_types_m:
                        _filtered_waste_m = waste_m[waste_m['type'].isin(_selected_waste_types_m)].copy()
                    else:
                        _filtered_waste_m = waste_m.copy()
    
                    waste_m_tbl = _filtered_waste_m.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date', ascending=False)
                    st.markdown("**📋 Waste Entries Table**")
                    st.dataframe(waste_m_tbl.rename(columns={'date':'Date','type':'Activity','duration':'Hours'}),
                                 width='stretch')
    
                    # Show "Waste by Activity Type" bar only when no specific filter is applied
                    if not _selected_waste_types_m:
                        wm_grp = _filtered_waste_m.groupby('type')['duration'].sum().reset_index().sort_values('duration', ascending=False)
                        fig_wm = px.bar(wm_grp, x='type', y='duration',
                                        labels={'type':'Activity','duration':'Hours'},
                                        color_discrete_sequence=['#ef4444'], title="Waste by Activity Type")
                        st.plotly_chart(fig_wm, width='stretch', key=f"monthly_waste_bar_{month_str}")
    
                    waste_daily_m = _filtered_waste_m.groupby('date')['duration'].sum().reset_index()
                    fig_wml = go.Figure()
                    fig_wml.add_trace(go.Scatter(x=waste_daily_m['date'], y=waste_daily_m['duration'],
                        mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3),
                        fill='tozeroy', fillcolor='rgba(239,68,68,0.1)'))
                    fig_wml.update_layout(title=f"Daily Waste Trend — {month_str}",
                                          xaxis_title="Date", yaxis_title="Hours")
                    st.plotly_chart(fig_wml, width='stretch', key=f"monthly_waste_line_{month_str}")
    
                    # ── Hourly Distribution ──
                    st.markdown("#### ⏰ Hourly Distribution")
                    _wdf_hm = _filtered_waste_m.copy()
                    _wdf_hm['_hour'] = _wdf_hm.apply(extract_hour_from_row, axis=1)
                    _wdf_hm_valid = _wdf_hm.dropna(subset=['_hour'])
                    if not _wdf_hm_valid.empty:
                        _whm_grp = _wdf_hm_valid.groupby('_hour')['duration'].sum().reset_index()
                        _whm_all = pd.DataFrame({'_hour': range(24)})
                        _whm_all['_hour_label'] = _whm_all['_hour'].apply(lambda h: f"{h:02d}:00")
                        _whm_full = _whm_all.merge(_whm_grp[['_hour', 'duration']], on='_hour', how='left').fillna(0)
                        _fig_whm = go.Figure()
                        _fig_whm.add_trace(go.Scatter(
                            x=_whm_full['_hour_label'], y=_whm_full['duration'],
                            mode='lines+markers', name='Waste',
                            line=dict(color='#f97316', width=3),
                            fill='tozeroy', fillcolor='rgba(249,115,22,0.15)',
                            marker=dict(size=6, color='#fb923c')
                        ))
                        _fig_whm.update_layout(
                            title=f"Hourly Waste Distribution — {month_str}",
                            xaxis_title="Hour of Day", yaxis_title="Hours",
                            template='plotly_dark', hovermode='x unified',
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(_fig_whm, width='stretch', key=f"monthly_waste_hourly_dist_{month_str}")
                    else:
                        st.caption("⏰ No time-stamped entries found. Log activities with **Time Range (From-To)** to see hourly data.")
    
                    st.info("💡 Use the **Ask Esu** page to get personalized waste reduction strategies.")
    
    
    
                st.divider()
                st.markdown(f"### 📈 Advanced Monthly Insights — {month_str}")
                
                # Top 10 Study Streaks in Month
                st.markdown("#### 🔥 Top 10 Study Streaks")
                m_streaks = calculate_top_streaks(month_df) # No need to pass year/month since month_df is already filtered
                if m_streaks:
                    st.dataframe(pd.DataFrame(m_streaks), 
                                 column_config={"start_date": "Start", "end_date": "End", "length": st.column_config.NumberColumn("Length (Days)", format="%d 🔥")},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No streaks found for this month.")
    
                # Top 10 Study Days in Month (Weekday vs Weekend)
                st.markdown("#### 🏆 Top Study Days & Content")
                wd_col, we_col = st.columns(2)
                with wd_col:
                    st.markdown("📅 **Top 10 Weekdays**")
                    top_wd = get_top_study_days(month_df, is_weekend=False)
                    if not top_wd.empty:
                        st.dataframe(top_wd[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekday study data.")
                
                with we_col:
                    st.markdown("Weekend **Top 10 Weekends**")
                    top_we = get_top_study_days(month_df, is_weekend=True)
                    if not top_we.empty:
                        st.dataframe(top_we[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekend study data.")
    
                # ════════════════════════════════════════════════════════════════════════════════
                # SECTION: MONTHLY CUMULATIVE TIME-OF-DAY ANALYSIS
                # ════════════════════════════════════════════════════════════════════════════════
                st.divider()
                st.markdown(f"## 🔍 Hourly Pattern Analysis — {month_str}")
                st.markdown(f"*Typical productivity vs waste distribution for the selected month*")
                
                try:
                    # Filter by the month selected in this tab
                    # Get all sleep intervals for unique dates in this month
                    all_m_sleep_intervals = []
                    unique_month_dates = month_df['date'].unique()
                    for d_str in unique_month_dates:
                        curr_h = hl_map.get(str(d_str), {})
                        prev_d = (pd.to_datetime(str(d_str)) - timedelta(days=1)).strftime('%Y-%m-%d')
                        prev_h = hl_map.get(prev_d, {})
                        intervals = get_sleep_intervals(prev_h.get('sleep_time'), curr_h.get('wakeup_time'))
                        all_m_sleep_intervals.extend(intervals)
    
                    cumul_24h = time_of_day_analysis_cumulative_24h(df, filter_month=month_str, all_sleep_intervals=all_m_sleep_intervals)
                except Exception as e:
                    st.error(f"Error analyzing monthly pattern: {e}")
                    cumul_24h = pd.DataFrame()
                
                if not cumul_24h.empty:
                    st.markdown(f"**📊 Average Hourly Trends — {month_str}**")
                    
                    # Cumulative Table
                    st.dataframe(cumul_24h[['hour', 'productivity_%', 'waste_%', 'avg_productive_h']], 
                                 column_config={
                                     "hour": "Hour",
                                     "productivity_%": st.column_config.ProgressColumn("Avg Productivity (%)", min_value=0, max_value=100, format="%d%%"),
                                     "waste_%": st.column_config.ProgressColumn("Avg Waste (%)", min_value=0, max_value=100, format="%d%%"),
                                     "avg_productive_h": st.column_config.NumberColumn("Avg Prod (h)", format="%.2f")
                                 },
                                 width='stretch', hide_index=True)
    
                    # Combined Line chart
                    fig_cumul_line = go.Figure()
                    fig_cumul_line.add_trace(go.Scatter(x=cumul_24h['hour'], y=cumul_24h['productivity_%'],
                                                 mode='lines+markers', name='Avg Productivity %',
                                                 line=dict(color='#8b5cf6', width=4),
                                                 marker=dict(size=8)))
                    fig_cumul_line.add_trace(go.Scatter(x=cumul_24h['hour'], y=cumul_24h['waste_%'],
                                                 mode='lines+markers', name='Avg Waste %',
                                                 line=dict(color='#f43f5e', width=3, dash='dot'),
                                                 marker=dict(size=6)))
                    
                    fig_cumul_line.update_layout(
                        title=f"Typica Pattern (Across {month_str})",
                        yaxis_title="Average Percentage (%)",
                        xaxis_title="Hour of Day",
                        hovermode='x unified',
                        height=500,
                        yaxis=dict(range=[0, 105]),
                        template='plotly_dark',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_cumul_line, width='stretch', key=f"monthly_tod_pattern_{month_str}")
                    
                    # Insights and Recommendations
                    st.markdown("### 💡 Monthly Insights & Recommendations")
                    
                    df_cumul_data = cumul_24h[cumul_24h['total_hours'] > 0]
                    if not df_cumul_data.empty:
                        try:
                            best_idx = df_cumul_data['productivity_%'].idxmax()
                            worst_idx = df_cumul_data['productivity_%'].idxmin()
                            
                            peak_hour = cumul_24h.loc[best_idx, 'hour']
                            peak_prod = cumul_24h.loc[best_idx, 'productivity_%']
                            low_hour = cumul_24h.loc[worst_idx, 'hour']
                            low_prod = cumul_24h.loc[worst_idx, 'productivity_%']
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.success(f"🏆 **Peak Hour**: {peak_hour}\n({peak_prod:.0f}% productive)")
                            with col2:
                                st.error(f"⏰ **Lowest Hour**: {low_hour}\n({low_prod:.0f}% productive)")
                            with col3:
                                st.info(f"📊 **Monthly Data**: {int(cumul_24h['total_hours'].sum())}h logged")
                            
                            # Esu's Analysis
                            st.divider()
                            st.markdown("### 🤖 Esu's Monthly Pattern Analysis")
                            
                            if st.button("✨ Generate Monthly Insights", key=f"gen_ai_monthly_{month_str}"):
                                with st.spinner("Analyzing..."):
                                    # Use data from the filtered month_df
                                    recent_json = month_df.tail(80).to_json(orient='records')
                                    hourly_json = cumul_24h[cumul_24h['productivity_%'] > 0][['hour', 'productivity_%', 'waste_%']].to_json(orient='records')
                                    
                                    prompt = (
                                        f"You are Esu, an elite productivity analyst. Analyze study patterns for {month_str}.\n\n"
                                        f"MONTHLY DATA (recent entries): {recent_json}\n\n"
                                        f"HOURLY PATTERNS: {hourly_json}\n\n"
                                        f"PEAK HOUR: {peak_hour} ({peak_prod:.0f}%) | LOWEST HOUR: {low_hour} ({low_prod:.0f}%)\n\n"
                                        f"RESPOND WITH:\n\n"
                                        f"## 📊 Monthly Performance Summary\n"
                                        f"| Metric | Value | Verdict |\n"
                                        f"|--------|-------|---------|\n"
                                        f"(fill: total hours, productive %, peak time, worst time, consistency)\n\n"
                                        f"## ⏰ Time Block Analysis\n"
                                        f"| Time Block | Productivity | Best For | Recommendation |\n"
                                        f"|------------|-------------|----------|----------------|\n"
                                        f"(Morning/Afternoon/Evening/Night — what's working, what's not)\n\n"
                                        f"## ⚡ Top 3 Actions for Next Month\n"
                                        f"Numbered list with specific, measurable actions.\n"
                                    )
                                    ai_response = _ai_m.get_ai_insight(prompt)
                                    st.markdown("---")
                                    st.markdown(ai_response)
                            
                            # Tactical tips
                            low_productive_hours = cumul_24h[cumul_24h['productivity_%'] < 20]['hour'].tolist()
                            low_hours_str = ', '.join(low_productive_hours[:3]) if low_productive_hours else 'Late night slots'
                            
                            tips_col1, tips_col2 = st.columns(2)
                            with tips_col1:
                                st.info(f"📍 **Focus Strategy**\nYour best hour is **{peak_hour}**. Protect this window for high-value tasks.")
                            with tips_col2:
                                st.warning(f"📍 **Waste Strategy**\nYour focus slumps at **{low_hours_str}**. Use these for chores or rest.")
                        except Exception as e:
                            st.error(f"Error generating insights: {e}")
                else:
                    st.info(f"📝 No hourly patterns found for {month_str}. Make sure you log activities with 'Time Range (From-To)'.")
    
    
    # ════════════════════════════════════════════
    # TAB 3 — YEARLY
    # ════════════════════════════════════════════
    with tab_yearly:
        st.subheader("📈 Yearly Productivity Analysis")
    
        if df.empty:
            st.info("No activity data found.")
        else:
            import datetime as _dt2
            import calendar as _cal
            sel_year_y = st.number_input("Year", value=_dt2.date.today().year, min_value=2020, max_value=2100, step=1, key="pa_year_y")
    
            df['year_str'] = pd.to_datetime(df['date']).dt.year
            year_df = df[df['year_str'] == int(sel_year_y)]
    
            if year_df.empty:
                st.warning(f"No data for {int(sel_year_y)}.")
            else:
                # Load sleep data for yearly report
                try:
                    hl_df = read_sql(
                        "SELECT date, sleep_time, wakeup_time, powernap FROM health_logs WHERE username=%s ORDER BY date ASC",
                        (USER,)
                    )
                    sleep_hours_dict = {}
                    sleep_intervals_dict = {}
                    powernap_dict = {}
                    if not hl_df.empty:
                        hl_map = {str(r['date']): r for _, r in hl_df.iterrows()}
                        for date_str in sorted(hl_map.keys()):
                            curr = hl_map[date_str]
                            prev_date = (pd.to_datetime(date_str) - timedelta(days=1)).strftime('%Y-%m-%d')
                            prev = hl_map.get(prev_date, {})
                            sleep_a = calculate_sleep_hours(prev.get('sleep_time'), curr.get('wakeup_time'))
                            sleep_b = 99.0
                            s_curr = curr.get('sleep_time', '')
                            if s_curr and "AM" in str(s_curr).upper():
                                sleep_b = calculate_sleep_hours(s_curr, curr.get('wakeup_time'))
                            sleep_hours_dict[date_str] = min(sleep_a, sleep_b)
                            powernap_dict[date_str] = curr.get('powernap', 0)
                            sleep_intervals_dict[date_str] = get_sleep_intervals(prev.get('sleep_time'), curr.get('wakeup_time'))
                except:
                    sleep_hours_dict = {}
                    sleep_intervals_dict = {}
                    powernap_dict = {}
                
                prod_y      = year_df[year_df['type'].isin(ALL_PRODUCTIVE)]
                essential_y = year_df[year_df['type'].isin(ALL_ESSENTIAL)]
                waste_y     = year_df[~year_df['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL + ALL_NEUTRAL)]
    
                py1, py2, py3, py4 = st.columns(4)
                py1.metric("Productive Hrs", f"{round(prod_y['duration'].sum(),1)}h")
                py2.metric("Essential Hrs",  f"{round(essential_y['duration'].sum(),1)}h")
                py3.metric("Waste Hrs",      f"{round(waste_y['duration'].sum(),1)}h")
                py4.metric("Productivity %", f"{productivity_score(year_df, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict, sleep_intervals_dict=sleep_intervals_dict)}%")
    
                st.divider()
    
                year_df = year_df.copy()
                year_df['month_num'] = pd.to_datetime(year_df['date']).dt.month
                month_rows = []
                for mn in range(1, 13):
                    mdata  = year_df[year_df['month_num'] == mn]
                    mlabel = _cal.month_abbr[mn]
                    if mdata.empty:
                        month_rows.append({'Month': mlabel, 'Productive': 0, 'Essential': 0, 'Waste': 0})
                    else:
                        # Use helper for sleep-adjusted sums
                        mp, me, mw = get_adjusted_sums(mdata, sleep_intervals_dict)
                        month_rows.append({'Month': mlabel, 'Productive': round(mp,1),
                                           'Essential': round(me,1), 'Waste': round(mw,1)})
                yr_monthly_df = pd.DataFrame(month_rows)
    
                # ── PRODUCTIVITY ANALYSIS ────────────────────────────────────
                st.markdown("### 📈 Productivity Analysis")
    
                st.markdown("**📋 Month-by-Month Summary Table**")
                st.dataframe(yr_monthly_df.iloc[::-1].set_index('Month'), width='stretch')
    
                fig_ym = go.Figure()
                fig_ym.add_trace(go.Bar(x=yr_monthly_df['Month'], y=yr_monthly_df['Productive'],
                                         name='Productive', marker_color='#22c55e'))
                fig_ym.add_trace(go.Bar(x=yr_monthly_df['Month'], y=yr_monthly_df['Essential'],
                                         name='Essential', marker_color='#3b82f6'))
                fig_ym.add_trace(go.Bar(x=yr_monthly_df['Month'], y=yr_monthly_df['Waste'],
                                         name='Waste', marker_color='#ef4444'))
                fig_ym.update_layout(barmode='group', xaxis_title="Month", yaxis_title="Hours",
                                      title=f"Monthly Breakdown — {int(sel_year_y)}")
                st.plotly_chart(fig_ym, width='stretch', key=f"yearly_bar_{int(sel_year_y)}")
    
                # Line: Productive & Waste ONLY — Essential removed
                fig_yl = go.Figure()
                fig_yl.add_trace(go.Scatter(x=yr_monthly_df['Month'], y=yr_monthly_df['Productive'],
                    mode='lines+markers', name='Productive', line=dict(color='#22c55e', width=3)))
                fig_yl.add_trace(go.Scatter(x=yr_monthly_df['Month'], y=yr_monthly_df['Waste'],
                    mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3)))
                fig_yl.update_layout(title=f"Productive vs Waste Trend — {int(sel_year_y)}",
                                      xaxis_title="Month", yaxis_title="Hours")
                st.plotly_chart(fig_yl, width='stretch', key=f"yearly_trend_{int(sel_year_y)}")
    
                study_y = prod_y[prod_y['type'].isin(['Study', 'Revision'])]
                if not study_y.empty:
                    st.markdown("**📚 Yearly Subject-wise Study & Revision Hours**")
                    subj_y_df = study_y.groupby('subject')['duration'].sum().sort_values(ascending=False).reset_index()
                    st.dataframe(subj_y_df.rename(columns={'subject':'Subject','duration':'Hours'}),
                                 width='stretch')
                    fig_ys = px.bar(subj_y_df, x='subject', y='duration',
                                    labels={'subject':'Subject','duration':'Hours'},
                                    color_discrete_sequence=['#22c55e'], title="Subject-wise Study Hours")
                    st.plotly_chart(fig_ys, width='stretch', key=f"yearly_subj_{int(sel_year_y)}")
    
                import ai as _ai_y
                st.info("💡 Use the **Ask Esu** page to get personalized productivity tips.")
    
                st.divider()
    
                # ── WASTE ANALYSIS ────────────────────────────────────────────
                st.markdown("### ⚠️ Waste Analysis")
    
                if waste_y.empty:
                    st.success("No waste time this year! 🎉")
                else:
                    # ── Activity Filter Dropdown (empty = show all) ──
                    _all_waste_types_y = sorted(waste_y['type'].unique().tolist())
                    _selected_waste_types_y = st.multiselect(
                        "🎯 Filter by Waste Activity (leave empty to show all)",
                        options=_all_waste_types_y,
                        default=[],
                        key=f"waste_activity_filter_yearly_{int(sel_year_y)}"
                    )
    
                    # Apply filter: if nothing selected → show all; otherwise → filter
                    if _selected_waste_types_y:
                        _filtered_waste_y = waste_y[waste_y['type'].isin(_selected_waste_types_y)].copy()
                    else:
                        _filtered_waste_y = waste_y.copy()
    
                    waste_y_tbl = _filtered_waste_y.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date', ascending=False)
                    st.markdown("**📋 All Waste Entries**")
                    st.dataframe(waste_y_tbl.rename(columns={'date':'Date','type':'Activity','duration':'Hours'}),
                                 width='stretch')
    
                    # Show "Waste by Activity Type" bar only when no specific filter is applied
                    if not _selected_waste_types_y:
                        wy_grp = _filtered_waste_y.groupby('type')['duration'].sum().sort_values(ascending=False).reset_index()
                        fig_yw = px.bar(wy_grp, x='type', y='duration',
                                        labels={'type':'Activity','duration':'Hours'},
                                        color_discrete_sequence=['#ef4444'], title="Waste by Activity Type")
                        st.plotly_chart(fig_yw, width='stretch', key=f"yearly_waste_bar_{int(sel_year_y)}")
    
                    waste_monthly = _filtered_waste_y.copy()
                    waste_monthly['month_num'] = pd.to_datetime(waste_monthly['date']).dt.month
                    wm_g = waste_monthly.groupby('month_num')['duration'].sum().reset_index()
                    wm_g['Month'] = wm_g['month_num'].apply(lambda x: _cal.month_abbr[x])
                    fig_ywl = go.Figure()
                    fig_ywl.add_trace(go.Scatter(x=wm_g['Month'], y=wm_g['duration'],
                        mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3),
                        fill='tozeroy', fillcolor='rgba(239,68,68,0.1)'))
                    fig_ywl.update_layout(title=f"Monthly Waste Trend — {int(sel_year_y)}",
                                          xaxis_title="Month", yaxis_title="Hours")
                    st.plotly_chart(fig_ywl, width='stretch', key=f"yearly_waste_line_{int(sel_year_y)}")
    
                    # ── Hourly Distribution ──
                    st.markdown("#### ⏰ Hourly Distribution")
                    _wdf_hy = _filtered_waste_y.copy()
                    _wdf_hy['_hour'] = _wdf_hy.apply(extract_hour_from_row, axis=1)
                    _wdf_hy_valid = _wdf_hy.dropna(subset=['_hour'])
                    if not _wdf_hy_valid.empty:
                        _why_grp = _wdf_hy_valid.groupby('_hour')['duration'].sum().reset_index()
                        _why_all = pd.DataFrame({'_hour': range(24)})
                        _why_all['_hour_label'] = _why_all['_hour'].apply(lambda h: f"{h:02d}:00")
                        _why_full = _why_all.merge(_why_grp[['_hour', 'duration']], on='_hour', how='left').fillna(0)
                        _fig_why = go.Figure()
                        _fig_why.add_trace(go.Scatter(
                            x=_why_full['_hour_label'], y=_why_full['duration'],
                            mode='lines+markers', name='Waste',
                            line=dict(color='#f97316', width=3),
                            fill='tozeroy', fillcolor='rgba(249,115,22,0.15)',
                            marker=dict(size=6, color='#fb923c')
                        ))
                        _fig_why.update_layout(
                            title=f"Hourly Waste Distribution — {int(sel_year_y)}",
                            xaxis_title="Hour of Day", yaxis_title="Hours",
                            template='plotly_dark', hovermode='x unified',
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(_fig_why, width='stretch', key=f"yearly_waste_hourly_dist_{int(sel_year_y)}")
                    else:
                        st.caption("⏰ No time-stamped entries found. Log activities with **Time Range (From-To)** to see hourly data.")
    
    
    
                st.divider()
                st.markdown(f"### 📈 Advanced Yearly Insights — {int(sel_year_y)}")
                
                # Top 10 Study Streaks in Year
                st.markdown("#### 🔥 Top 10 Study Streaks")
                y_streaks = calculate_top_streaks(year_df)
                if y_streaks:
                    st.dataframe(pd.DataFrame(y_streaks), 
                                 column_config={"start_date": "Start", "end_date": "End", "length": st.column_config.NumberColumn("Length (Days)", format="%d 🔥")},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No streaks found for this year.")
    
                # Top 10 Study Days in Year (Weekday vs Weekend)
                st.markdown("#### 🏆 Top Study Days & Content")
                ywd_col, ywe_col = st.columns(2)
                with ywd_col:
                    st.markdown("📅 **Top 10 Weekdays**")
                    top_ywd = get_top_study_days(year_df, is_weekend=False)
                    if not top_ywd.empty:
                        st.dataframe(top_ywd[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekday study data.")
                
                with ywe_col:
                    st.markdown("Weekend **Top 10 Weekends**")
                    top_ywe = get_top_study_days(year_df, is_weekend=True)
                    if not top_ywe.empty:
                        st.dataframe(top_ywe[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekend study data.")
    
                    st.info("💡 Use the **Ask Esu** page to get personalized waste reduction strategies.")
    
    if not df_daily.empty:
        st.divider()
        # ── SMART WORK TIPS (Productivity Analysis) ──
        _sw_streak_pa = streak(df_daily)
        _sw_focus_pa = focus_score(df_daily)
        _sw_prod_pct_pa = productivity_score(df_daily, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict, sleep_intervals_dict=sleep_intervals_dict)
        _sw_tips_pa = generate_smart_work_tips(
            prod_hours=prod_total,
            waste_hours=waste_total,
            essential_hours=essential_total,
            study_streak=_sw_streak_pa,
            focus_pct=_sw_focus_pa,
            subject_count=len(prod_df['subject'].unique()) if not prod_df.empty else 0,
            productivity_pct=_sw_prod_pct_pa,
            context="productivity"
        )
        st.markdown(render_smart_work_section(_sw_tips_pa, max_tips=12), unsafe_allow_html=True)
    

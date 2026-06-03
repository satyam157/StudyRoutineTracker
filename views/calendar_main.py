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
    conn = database.conn
    c = database.c
    st.title("📆 Calendars")
    
    cal_tab_month, cal_tab_year = st.tabs(["📅 Month Calendar", "📊 Year Calendar"])
    
    with cal_tab_month:
        import calendar as calmod
        import datetime
        
        today = get_ist_now().date()
        
        # Month/Year selection controls - single row
        col1, col2 = st.columns([1, 1])
        with col1:
            selected_year = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="cal_yr", step=1)
        with col2:
            selected_month = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="cal_mo", step=1)
        
        # Load activities data
        daily_prod = {}
        df = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
        if not df.empty:
            if 'start_time' not in df.columns: df['start_time'] = None
            df['start_time'] = df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
            df['chapter'] = df['chapter'].apply(get_clean_chapter)
            
            for d, g in df.groupby("date"):
                prod_hrs = g[g['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
                daily_prod[str(d)] = prod_hrs
            
            # Build daily description map (first non-empty description per date)
            daily_desc = {}
            for d, g in df.groupby("date"):
                for _, r in g.iterrows():
                    raw = r.get('description', '')
                    if raw and str(raw).strip() and str(raw).strip().lower() not in ('none', 'nan', 'null'):
                        daily_desc[str(d)] = str(raw).strip()
                        break
        
        # Load health logs
        try:
            hl_df = read_sql(
                "SELECT date, wakeup_time, sleep_time FROM health_logs WHERE username=%s",
                (USER,)
            )
            hl_map = {row['date']: row for _, row in hl_df.iterrows()}
        except Exception:
            hl_map = {}
        
        # Load social data from activities table
        try:
            sl_df = read_sql("""
                SELECT 
                    date, 
                    SUM(CASE WHEN type = 'Entertainment' THEN duration ELSE 0 END) as entertainment_hours,
                    SUM(CASE WHEN type = 'WentOutside' THEN duration ELSE 0 END) as went_outside_hours
                FROM activities 
                WHERE username=%s AND type IN ('Entertainment', 'WentOutside')
                GROUP BY date
            """, (USER,))
            sl_map = {str(row['date']): row for _, row in sl_df.iterrows()}
        except Exception:
            sl_map = {}
        
        # Generate calendar structure
        first_weekday, num_days = calmod.monthrange(int(selected_year), int(selected_month))
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        # Beautiful merged calendar HTML/CSS
        html = """
        <style>
        .merged-cal-grid { 
            display: grid; 
            grid-template-columns: repeat(7, 1fr); 
            gap: 10px; 
            margin: 15px 0 0 0;
        }
        .merged-cal-header { 
            font-weight: 900; 
            font-size: 15px; 
            text-align: center; 
            padding: 14px 8px; 
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%); 
            color: #e0e7ff;
            border-radius: 8px;
            border: 2px solid #475569;
            letter-spacing: 0.5px;
        }
        .merged-cal-cell {
            border: 2px solid #475569;
            border-radius: 12px;
            padding: 12px 10px;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            font-size: 12px;
            transition: all 0.25s ease, transform 0.2s ease;
            cursor: pointer;
            gap: 6px;
        }
        .merged-cal-cell:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
        }
        .merged-cal-cell.empty {
            background: transparent;
            border: none;
            cursor: default;
            min-height: auto;
        }
        .merged-cal-cell.empty:hover {
            transform: none;
            box-shadow: none;
            border-color: transparent;
        }
        .merged-cal-date {
            font-weight: 900;
            font-size: 22px;
            margin-bottom: 2px;
            line-height: 1;
        }
        .merged-cal-prod {
            font-size: 12px;
            font-weight: 700;
            padding: 5px 7px;
            border-radius: 5px;
            margin-bottom: 2px;
        }
        .merged-cal-health {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 6px;
            border-radius: 4px;
            line-height: 1.3;
        }
        .merged-cal-social {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 6px;
            border-radius: 4px;
            line-height: 1.3;
        }
        .merged-cal-desc {
            font-size: 10px;
            font-weight: 500;
            font-style: italic;
            padding: 3px 5px;
            border-radius: 4px;
            line-height: 1.3;
            opacity: 0.85;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        </style>
        <div class="merged-cal-grid">
        """
        
        # Day headers
        for day in day_names:
            html += f"<div class='merged-cal-header'>{day}</div>"
        
        # Empty cells before month starts
        for _ in range(first_weekday):
            html += "<div class='merged-cal-cell empty'></div>"
        
        today_str = str(today)
        
        # Color mapping for proper hex values and text colors
        color_map = {
            "black": ("#1a1a1a", "#ffffff"),    # (bg, text)
            "red": ("#dc2626", "#ffffff"),
            "lightblue": ("#38bdf8", "#000000"),
            "green": ("#22c55e", "#000000"),
            "gold": ("#fbbf24", "#000000"),
            "white": ("#ffffff", "#000000")
        }
        
        # Days of the month
        for day in range(1, num_days + 1):
            date_str = f"{int(selected_year)}-{int(selected_month):02d}-{day:02d}"
            weekday_idx = calmod.weekday(int(selected_year), int(selected_month), day)
            is_weekend = weekday_idx >= 5
            is_today = date_str == today_str
            is_future = datetime.date(int(selected_year), int(selected_month), day) > today
            
            # Get productive hours
            prod_hours = daily_prod.get(date_str, 0)
            
            # Get health/social data
            hl = hl_map.get(date_str, {})
            sl = sl_map.get(date_str, {})
            wu = hl.get('wakeup_time', '') or '–'
            st_ = hl.get('sleep_time', '') or '–'
            ent = sl.get('entertainment_hours', 0) or 0
            out = sl.get('went_outside_hours', 0) or 0
            
            # Get color based on productive hours
            if is_future:
                color_name = "white"
            else:
                color_name = get_study_color(date_str, prod_hours)
            
            bg_color, text_color = color_map.get(color_name, ("#0f172a", "#e2e8f0"))
            
            # Build cell content with proper styling
            cell_style = f"background-color: {bg_color}; color: {text_color}; border-color: {bg_color};"
            html += f"<div class='merged-cal-cell' style='{cell_style}'>"
            html += f"<div class='merged-cal-date'>{day}</div>"
            
            if prod_hours > 0 and not is_future:
                # Dark text for light backgrounds, light text for dark backgrounds
                text_for_prod = "#000000" if bg_color in ["#eab308", "#fbbf24", "#ffffff"] else "#ffffff"
                html += f"<div class='merged-cal-prod' style='background: rgba(255,255,255,0.2); color: {text_for_prod}'>⏱️ {format_duration(prod_hours)}</div>"
            
            # Add health & social data with high contrast
            if wu != '–' or st_ != '–':
                health_text = f"☀️ {wu}"
                if st_ != '–':
                    health_text += f" | 🌙 {st_}"
                html += f"<div class='merged-cal-health' style='background: rgba(255,255,255,0.2); color: {text_color}'>{health_text}</div>"
            
            if ent > 0 or out > 0:
                social_text = ""
                if ent > 0:
                    social_text += f"🎬 {format_duration(ent)}"
                if out > 0:
                    if social_text:
                        social_text += f" | 🚶 {format_duration(out)}"
                    else:
                        social_text = f"🚶 {format_duration(out)}"
                html += f"<div class='merged-cal-social' style='background: rgba(255,255,255,0.2); color: {text_color}'>{social_text}</div>"
            
            # Description (free-text note)
            day_desc = daily_desc.get(date_str, '') if not is_future else ''
            if day_desc:
                html += f"<div class='merged-cal-desc' style='background: rgba(255,255,255,0.1); color: {text_color}'>📝 {day_desc}</div>"
            
            html += "</div>"
        
        html += "</div>"
        
        # Display calendar at full width
        st.markdown(html, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        
        # Activities box below calendar with left/right halves
        st.markdown("""
        <style>
        .activities-box {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #4f46e5;
            border-radius: 14px;
            padding: 16px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .activities-box-title {
            font-size: 18px;
            font-weight: 700;
            color: #a78bfa;
            margin-bottom: 16px;
        }
        .activities-left-section {
            padding-right: 16px;
            border-right: 2px solid rgba(79, 70, 229, 0.3);
        }
        .activities-right-section {
            padding-left: 16px;
            overflow-y: auto;
            max-height: 500px;
        }
        </style>
        <div class='activities-box'>
        <div class='activities-box-title'>📝 View Activities by Date</div>
        """, unsafe_allow_html=True)
        
        # Get activities data first to calculate total_prod
        # Inner layout: left (date picker & study hrs) | right (results)
        act_left, act_right = st.columns([1, 1.5])
        
        with act_left:
            st.markdown("<div class='activities-left-section'>", unsafe_allow_html=True)
            st.markdown("**📅 Select Date:**", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Date picker
            selected_date = st.date_input(
                "Date",
                value=today,
                min_value=today - datetime.timedelta(days=730),
                max_value=today,
                key="merged_cal_datepicker_left",
                label_visibility="collapsed"
            )
            
            # Get activities data to calculate total_prod
            date_str = str(selected_date) if selected_date else None
            date_acts = read_sql("SELECT * FROM activities WHERE username=%s AND date=%s ORDER BY id DESC", (USER, date_str)) if date_str else pd.DataFrame()
            total_prod = date_acts[date_acts['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum() if not date_acts.empty else 0
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.metric("Study Hrs", format_duration(total_prod))
        
        with act_right:
            st.markdown("<div class='activities-right-section'>", unsafe_allow_html=True)
            
            if selected_date:
                if not date_acts.empty:
                    st.markdown(f"**📋 {date_str}**")
                    st.divider()
                    
                    for _, row in date_acts.iterrows():
                        _rid = int(row['id'])
                        act_type = row['type']
                        if act_type == 'WentOutside':
                            act_type = 'WentOut'
                        _parts = [act_type]
                        if row['subject']: _parts.append(str(row['subject']))
                        
                        ch_clean = get_clean_chapter(row['chapter'])
                        st_val = row.get('start_time')
                        if not st_val:
                            hr = extract_time_of_day(row['chapter'])
                            if hr is not None: st_val = f"{hr}:00"
                        
                        if ch_clean: _parts.append(ch_clean)
                        if st_val: _parts.append(f"[{st_val}]")
                        
                        _val = format_duration(row['duration']) if row['duration'] > 0 else (f"₹{row['amount']}" if row['amount'] > 0 else "")
                        if _val: _parts.append(_val)
                        
                        activity_text = ' | '.join(_parts)
                        
                        raw_desc = row.get('description')
                        desc_text = ""
                        if raw_desc and str(raw_desc).strip() and str(raw_desc).strip().lower() not in ('none', 'nan', 'null'):
                            desc_text = f"<br><span style='font-size:12px; color:#94a3b8; font-weight:normal;'>{str(raw_desc).strip()}</span>"
                        
                        # Create inline activity display with delete button
                        _act_container = st.container()
                        with _act_container:
                            _col_text, _col_del = st.columns([3.5, 1])
                            with _col_text:
                                st.markdown(f"**{activity_text}**{desc_text}", unsafe_allow_html=True)
                            with _col_del:
                                if st.button("🗑️", key=f"del_merged_{_rid}", help="Delete Activity", width='stretch'):
                                    st.session_state[f"confirm_merged_{_rid}"] = True
                        
                        if st.session_state.get(f"confirm_merged_{_rid}", False):
                            _confirm_col = st.container()
                            with _confirm_col:
                                st.warning(f"Delete?", icon="⚠️")
                                _yc, _nc = st.columns([1, 1])
                                with _yc:
                                    if st.button("✅ Yes", key=f"yes_merged_{_rid}", width='stretch'):
                                        c.execute("DELETE FROM activities WHERE id=%s", (_rid,))
                                        conn.commit()
                                        st.toast(f"🗑️ Activity deleted", icon="🗑️")
                                        st.session_state[f"confirm_merged_{_rid}"] = False
                                        st.rerun()
                                with _nc:
                                    if st.button("❌ No", key=f"no_merged_{_rid}", width='stretch'):
                                        st.session_state[f"confirm_merged_{_rid}"] = False
                                        st.rerun()
                        
                        st.caption("")  # Small spacing
                else:
                    st.info(f"No activities on {date_str}", icon="ℹ️")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with cal_tab_year:
        st.subheader("📊 Year Overview & Health/Social Heatmap")
        import calendar as calmod
    
        df = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
        if not df.empty:
            if 'start_time' not in df.columns: df['start_time'] = None
            df['start_time'] = df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
            df['chapter'] = df['chapter'].apply(get_clean_chapter)
        
        daily_prod = {}
        if not df.empty:
            for d, g in df.groupby("date"):
                prod_hrs = g[g['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
                daily_prod[str(d)] = prod_hrs
    
        # Year selection input
        year = st.number_input("Select Year", value=today.year, key="cal_tab_yr_sel", min_value=2020, max_value=2100, step=1)
    
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
        html = """
        <style>
        .year-grid { 
            display: grid; 
            grid-template-columns: 50px repeat(31, 1fr); 
            gap: 6px; 
            align-items: center; 
            margin: 20px 0;
            padding: 15px;
            background: #0f172a;
            border-radius: 12px;
            border: 1px solid #1e3a5f;
            overflow-x: auto;
        }
        .month-label { 
            font-weight: bold; 
            font-size: 12px; 
            text-align: right; 
            padding-right: 8px;
            color: #60a5fa;
            background: #1a1f3a;
            border-radius: 6px;
            padding: 6px 8px;
        }
        .day-circle { 
            width: 20px; 
            height: 20px; 
            border-radius: 50%; 
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 8px;
            font-weight: 600;
            border: 2px solid;
            transition: all 0.2s ease;
            cursor: pointer;
            color: white;
        }
        .day-circle:hover {
            transform: scale(1.15);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
        .day-header { 
            font-size: 11px; 
            text-align: center; 
            color: #94a3b8;
            font-weight: bold;
            background: #1e293b;
            padding: 6px 2px;
            border-radius: 4px;
        }
        .day-label {
            font-size: 9px;
            color: #64748b;
            text-align: center;
            margin-top: 2px;
        }
        </style>
        <div class='year-grid'>
        """
        
        html += "<div></div>"
        for d in range(1, 32):
            html += f"<div class='day-header'>{d}</div>"
            
        for month_idx, month_name in enumerate(months, start=1):
            html += f"<div class='month-label'>{month_name}</div>"
            
            _, num_days = calmod.monthrange(int(year), month_idx)
            
            for d in range(1, 32):
                if d <= num_days:
                    date_str = f"{int(year)}-{month_idx:02d}-{d:02d}"
                    weekday_idx = calmod.weekday(int(year), month_idx, d)
                    is_weekend = weekday_idx >= 5
                    
                    border_color = "#dc2626" if is_weekend else "#3b82f6"
                    
                    if date_str in daily_prod:
                        color = get_study_color(date_str, daily_prod[date_str])
                        hours_str = format_duration(daily_prod[date_str])
                    else:
                        color = "#1e293b"
                        hours_str = "–"
                    
                    title = f"{date_str}: {format_duration(daily_prod.get(date_str, 0))}"
                    html += f"<div style='display:flex; flex-direction:column; align-items:center;'><div class='day-circle' style='background-color: {color}; border-color: {border_color};' title='{title}'>{hours_str if daily_prod.get(date_str, 0) > 0 else ''}</div></div>"
                else:
                    html += "<div></div>"
                    
        html += "</div>"    
        st.markdown(html, unsafe_allow_html=True)
    
    # ---------------- SOCIAL LIFE ----------------

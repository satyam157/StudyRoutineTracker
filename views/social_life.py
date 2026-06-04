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
    st.title("🌟 Social Life")
    
    import calendar as calmod
    import datetime
    
    today = get_ist_now().date()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_year = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="sm_cal_yr", step=1)
    with col2:
        selected_month = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="sm_cal_mo", step=1)
    
    df = get_activities_df(USER)
    if not df.empty:
        if 'start_time' not in df.columns: df['start_time'] = None
        df['start_time'] = df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        df['chapter'] = df['chapter'].apply(get_clean_chapter)
    
    # Filter specific activities
    # WentOutside, Turf, Travelling, Office, Coaching, Test (D-Day Exam)
    sm_df = df[
        (df['type'].isin(['WentOutside', 'Turf', 'Travelling', 'Office', 'Coaching'])) |
        ((df['type'] == 'Test') & (df['subject'] == 'D-Day Exam'))
    ].copy() if not df.empty else pd.DataFrame()
    
    daily_sm = {}
    if not sm_df.empty:
        for d, g in sm_df.groupby("date"):
            daily_sm[str(d)] = g.to_dict('records')
            
    month_name = calmod.month_name[int(selected_month)]
    st.subheader(f"{month_name} {int(selected_year)}")
    
    cal = calmod.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(int(selected_year), int(selected_month))
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    _, num_days = calmod.monthrange(int(selected_year), int(selected_month))
    first_weekday = calmod.weekday(int(selected_year), int(selected_month), 1)
    
    html = """
    <style>
    .sm-cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        margin: 15px 0 0 0;
    }
    .sm-cal-header {
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
    .sm-cal-cell {
        border: 2px solid #475569;
        border-radius: 12px;
        padding: 12px 10px;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        font-size: 12px;
        transition: all 0.25s ease, transform 0.2s ease;
        cursor: pointer;
        gap: 4px;
        overflow: hidden;
    }
    .sm-cal-cell:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
    }
    .sm-cal-cell.empty {
        background: transparent !important;
        border: none !important;
        cursor: default;
        min-height: auto;
    }
    .sm-cal-cell.empty:hover {
        transform: none;
        box-shadow: none;
        border-color: transparent;
    }
    .sm-cal-date {
        font-weight: 900;
        font-size: 22px;
        margin-bottom: 2px;
        line-height: 1;
    }
    .sm-act-tag {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 5px;
        border-radius: 4px;
        margin-bottom: 2px;
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .sm-desc {
        font-size: 10px;
        margin-top: 2px;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    /* Tablet */
    @media (max-width: 900px) {
        .sm-cal-grid { grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .sm-cal-header { font-size: 13px; padding: 10px 6px; }
        .sm-cal-cell { min-height: 120px; padding: 10px 8px; }
        .sm-cal-date { font-size: 19px; }
        .sm-act-tag { font-size: 10px; }
    }
    /* Mobile */
    @media (max-width: 550px) {
        .sm-cal-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
        .sm-cal-header { font-size: 12px; padding: 8px 4px; }
        .sm-cal-cell { min-height: 100px; padding: 8px 6px; }
        .sm-cal-date { font-size: 16px; }
        .sm-act-tag { font-size: 9px; }
    }
    </style>
    <div class="sm-cal-grid">
    """
    
    for day in day_names:
        html += f"<div class='sm-cal-header'>{day}</div>"
        
    for _ in range(first_weekday):
        html += "<div class='sm-cal-cell empty'></div>"
        
    today_str = str(today)
    
    # Color priority for cell background (first match wins)
    _SM_COLOR_PRIORITY = {
        'WentOutside': ('#fbbf24', '#000000'),   # Golden Yellow
        'Travelling':  ('#fbbf24', '#000000'),   # Golden Yellow
        'Test':        ('#fbbf24', '#000000'),   # Golden Yellow (D-Day Exam)
        'Turf':        ('#dc2626', '#ffffff'),   # Red
        'Office':      ('#ec4899', '#ffffff'),   # Pink
        'Coaching':    ('#22c55e', '#000000'),   # Green
    }
    
    for day in range(1, num_days + 1):
        date_str = f"{int(selected_year)}-{int(selected_month):02d}-{day:02d}"
        
        is_today = date_str == today_str
        is_future = datetime.date(int(selected_year), int(selected_month), day) > today
        
        day_acts = daily_sm.get(date_str, [])
        
        # Determine cell background from primary activity
        cell_bg = "#0f172a"
        cell_text = "#e2e8f0"
        if day_acts and not is_future:
            for act in day_acts:
                at = act['type']
                if at in _SM_COLOR_PRIORITY:
                    cell_bg, cell_text = _SM_COLOR_PRIORITY[at]
                    break
        
        if is_future:
            cell_bg = "#0f172a"
            cell_text = "#e2e8f0"
        
        cell_border = f"border: 2px solid #eab308; box-shadow: 0 0 10px rgba(234, 179, 8, 0.3);" if is_today else f"border: 2px solid {cell_bg};"
        
        html += f"<div class='sm-cal-cell' style='background-color: {cell_bg}; color: {cell_text}; {cell_border}'>"
        html += f"<div class='sm-cal-date'>{day}</div>"
        
        for act in day_acts:
            act_type = act['type']
            
            # Display label overrides (cosmetic only, data unchanged)
            _DISPLAY_LABEL = {'WentOutside': 'WentOut'}
            display_type = _DISPLAY_LABEL.get(act_type, act_type)
            
            dur = act.get('duration', 0) or 0
            amt = act.get('amount', 0) or 0
            
            # Duration formatting
            if dur > 0:
                val = format_duration(dur)
            elif amt > 0:
                val = f"₹{amt}"
            else:
                val = ""
            
            desc = ""
            if act['subject'] and act['subject'] != 'D-Day Exam': desc += str(act['subject']) + " "
            if act['chapter']: desc += str(act['chapter'])
            raw_act_desc = act.get('description', '')
            if raw_act_desc and str(raw_act_desc).strip() and str(raw_act_desc).strip().lower() not in ('none', 'nan', 'null'):
                desc += (" " if desc else "") + str(raw_act_desc).strip()
            
            time_str = f"[{act['start_time']}] " if act.get('start_time') else ""
            
            main_text = f"{time_str}{display_type}"
            if val: main_text += f" ({val})"
            
            # Tag uses semi-transparent bg on colored cell
            tag_bg = "rgba(255,255,255,0.15)"
            tag_text = cell_text
            
            if act_type == 'WentOutside' and cell_bg != '#fbbf24':
                tag_text = '#fbbf24'

            
            tooltip = main_text
            if desc.strip(): tooltip += f" - {desc.strip()}"
            
            html += f"<div class='sm-act-tag' style='background: {tag_bg}; color: {tag_text};' title=\"{tooltip}\">"
            html += f"<div>{main_text}</div>"
            if desc.strip():
                html += f"<div class='sm-desc' style='color: {tag_text};'>{desc.strip()}</div>"
            html += "</div>"
            
        html += "</div>"
        
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
    .activities-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #fbbf24;
        border-radius: 14px;
        padding: 16px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .activities-box-title {
        font-size: 18px;
        font-weight: 700;
        color: #fbbf24;
        margin-bottom: 16px;
    }
    .activities-left-section {
        padding-right: 16px;
        border-right: 2px solid rgba(251, 191, 36, 0.3);
    }
    .activities-right-section {
        padding-left: 16px;
        overflow-y: auto;
        max-height: 500px;
    }
    </style>
    <div class='activities-box'>
    <div class='activities-box-title'>📝 View Social Life by Date</div>
    """, unsafe_allow_html=True)
    
    act_left, act_right = st.columns([1, 1.5])
    
    with act_left:
        st.markdown("<div class='activities-left-section'>", unsafe_allow_html=True)
        st.markdown("**📅 Select Date:**", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        selected_date = st.date_input(
            "Date",
            value=today,
            min_value=today - datetime.timedelta(days=730),
            max_value=today,
            key="sm_cal_datepicker_left",
            label_visibility="collapsed"
        )
        
        date_str = str(selected_date) if selected_date else None
        
        date_acts = sm_df[sm_df['date'] == date_str].sort_values('id', ascending=False) if (date_str and not sm_df.empty) else pd.DataFrame()
        total_sm_dur = date_acts['duration'].sum() if not date_acts.empty else 0
        total_sm_amt = date_acts['amount'].sum() if not date_acts.empty else 0
        
        st.markdown("<br>", unsafe_allow_html=True)
        if total_sm_dur > 0: st.metric("Total Hrs", format_duration(total_sm_dur))
        if total_sm_amt > 0: st.metric("Total Expense", f"₹{total_sm_amt:.1f}")
    
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
                    
                    _act_container = st.container()
                    with _act_container:
                        _col_text, _col_del = st.columns([3.5, 1])
                        with _col_text:
                            st.markdown(f"**{activity_text}**{desc_text}", unsafe_allow_html=True)
                        with _col_del:
                            if st.button("🗑️", key=f"del_sm_{_rid}", help="Delete Activity", width='stretch'):
                                st.session_state[f"confirm_sm_{_rid}"] = True
                    
                    if st.session_state.get(f"confirm_sm_{_rid}", False):
                        _confirm_col = st.container()
                        with _confirm_col:
                            st.warning(f"Delete?", icon="⚠️")
                            _yc, _nc = st.columns([1, 1])
                            with _yc:
                                if st.button("✅ Yes", key=f"yes_sm_{_rid}", width='stretch'):
                                    c.execute("DELETE FROM activities WHERE id=%s", (_rid,))
                                    conn.commit()
                                    st.toast(f"🗑️ Activity deleted", icon="🗑️")
                                    st.session_state[f"confirm_sm_{_rid}"] = False
                                    st.rerun()
                            with _nc:
                                if st.button("❌ No", key=f"no_sm_{_rid}", width='stretch'):
                                    st.session_state[f"confirm_sm_{_rid}"] = False
                                    st.rerun()
                    
                    st.caption("")
            else:
                st.info(f"No social life activities on {date_str}", icon="ℹ️")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # ---------------- STUDY CALENDAR ----------------

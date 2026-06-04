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
    st.title("📚 Study Calendar")
    
    import calendar as calmod
    import datetime
    
    today = get_ist_now().date()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_year = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="sc_cal_yr", step=1)
    with col2:
        selected_month = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="sc_cal_mo", step=1)
    
    # Activities to show on Study Calendar
    _SC_TYPES = ['Study', 'Test', 'Coaching', 'Revision', 'Book Reading', 'Answer Writing', 'Practice', 'Form Fillup', 'Strategy Planning', 'Resource Collection']
    # Activities whose text should render in golden
    _SC_GOLDEN_TEXT = ['Form Fillup', 'Strategy Planning', 'Resource Collection']
    
    df = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    if not df.empty:
        if 'start_time' not in df.columns: df['start_time'] = None
        df['start_time'] = df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        df['chapter'] = df['chapter'].apply(get_clean_chapter)
    
    # Filter to study activities only
    sc_df = df[df['type'].isin(_SC_TYPES)].copy() if not df.empty else pd.DataFrame()
    
    # Build daily productive hours (same logic as main calendar)
    daily_prod = {}
    if not sc_df.empty:
        for d, g in sc_df.groupby("date"):
            prod_hrs = g[g['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
            daily_prod[str(d)] = prod_hrs
    
    # Build daily activity details
    daily_sc = {}
    if not sc_df.empty:
        for d, g in sc_df.groupby("date"):
            agg = {}
            for _, r in g.iterrows():
                t = r['type']
                s = r.get('subject', '') or ''
                c = r.get('chapter', '') or ''
                dur = float(r.get('duration', 0) or 0)
                amt = float(r.get('amount', 0) or 0)
                
                if t not in ['Study', 'Revision', 'Coaching', 'Form Fillup', 'Strategy Planning', 'Resource Collection']:
                    k = (t, s, c, _)
                else:
                    k = (t, s, c)
                    
                if k not in agg:
                    agg[k] = {'type': t, 'subject': s, 'duration': 0.0, 'amount': 0.0, 'chapter_items': [], 'desc_items': []}
                
                agg[k]['duration'] += dur
                agg[k]['amount'] += amt
                if c:
                    agg[k]['chapter_items'].append(str(c))
                d_desc = r.get('description')
                if d_desc and str(d_desc).strip() and str(d_desc).strip().lower() not in ('none', 'nan', 'null'):
                    agg[k]['desc_items'].append(str(d_desc).strip())
                    
            final_acts = []
            for k, data in agg.items():
                t = data['type']
                ch_items = data['chapter_items']
                if t in ['Answer Writing', 'Practice']:
                    final_ch = ch_items[0] if ch_items else ""
                elif t == 'Test':
                    final_ch = ch_items[0] if ch_items else ""
                elif t == 'Book Reading':
                    final_ch = ch_items[0] if ch_items else ""
                else:
                    uniq = []
                    for ch in ch_items:
                        if ch and ch not in uniq: uniq.append(ch)
                    final_ch = ", ".join(uniq)
                
                
                data['chapter'] = final_ch
                
                uniq_desc = []
                for d_i in data.get('desc_items', []):
                    if d_i not in uniq_desc: uniq_desc.append(d_i)
                data['description'] = " | ".join(uniq_desc)
                
                final_acts.append(data)
                
            daily_sc[str(d)] = final_acts
    
    month_name = calmod.month_name[int(selected_month)]
    st.subheader(f"{month_name} {int(selected_year)}")
    
    _, num_days = calmod.monthrange(int(selected_year), int(selected_month))
    first_weekday = calmod.weekday(int(selected_year), int(selected_month), 1)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Same color map as main calendar
    color_map = {
        "black": ("#1a1a1a", "#ffffff"),
        "red": ("#dc2626", "#ffffff"),
        "lightblue": ("#38bdf8", "#000000"),
        "green": ("#22c55e", "#000000"),
        "gold": ("#fbbf24", "#000000"),
        "white": ("#ffffff", "#000000")
    }
    
    html = """
    <style>
    .sc-cal-wrapper {
        display: flex;
        flex-direction: column;
    }
    .sc-cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        margin: 15px 0 0 0;
    }
    .sc-cal-header {
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
    .sc-cal-cell {
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
        min-width: 0;
    }
    .sc-cal-cell:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
    }
    .sc-cal-cell.empty {
        background: transparent !important;
        border: none !important;
        cursor: default;
        min-height: auto;
    }
    .sc-cal-cell.empty:hover {
        transform: none;
        box-shadow: none;
        border-color: transparent;
    }
    .sc-cal-date {
        font-weight: 900;
        font-size: 22px;
        margin-bottom: 2px;
        line-height: 1;
    }
    .sc-cal-prod {
        font-size: 12px;
        font-weight: 700;
        padding: 5px 7px;
        border-radius: 5px;
        margin-bottom: 2px;
    }
    .sc-act-item {
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
    /* Tablet */
    @media (max-width: 900px) {
        .sc-cal-grid { grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .sc-cal-header { font-size: 13px; padding: 10px 6px; }
        .sc-cal-cell { min-height: 120px; padding: 10px 8px; }
        .sc-cal-date { font-size: 19px; }
        .sc-act-item { font-size: 10px; }
    }
    /* Mobile */
    @media (max-width: 550px) {
        .sc-cal-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
        .sc-cal-header { font-size: 12px; padding: 8px 4px; }
        .sc-cal-cell { min-height: 100px; padding: 8px 6px; }
        .sc-cal-date { font-size: 16px; }
        .sc-cal-prod { font-size: 10px; }
        .sc-act-item { font-size: 9px; }
    }
    </style>
    <div class="sc-cal-wrapper"><div class="sc-cal-grid">
    """
    
    for day in day_names:
        html += f"<div class='sc-cal-header'>{day}</div>"
        
    for _ in range(first_weekday):
        html += "<div class='sc-cal-cell empty'></div>"
        
    today_str = str(today)
    
    for day in range(1, num_days + 1):
        date_str = f"{int(selected_year)}-{int(selected_month):02d}-{day:02d}"
        is_today = date_str == today_str
        is_future = datetime.date(int(selected_year), int(selected_month), day) > today
        
        prod_hours = daily_prod.get(date_str, 0)
        
        if is_future:
            color_name = "white"
        else:
            color_name = get_study_color(date_str, prod_hours)
        
        bg_color, text_color = color_map.get(color_name, ("#0f172a", "#e2e8f0"))
        
        cell_border = f"border: 2px solid #eab308; box-shadow: 0 0 10px rgba(234, 179, 8, 0.3);" if is_today else f"border: 1px solid {bg_color};"
        
        html += f"<div class='sc-cal-cell' style='background-color: {bg_color}; color: {text_color}; {cell_border}'>"
        html += f"<div class='sc-cal-date'>{day}</div>"
        
        if prod_hours > 0 and not is_future:
            text_for_prod = "#000000" if bg_color in ["#fbbf24", "#ffffff", "#38bdf8", "#22c55e"] else "#ffffff"
            html += f"<div class='sc-cal-prod' style='background: rgba(255,255,255,0.2); color: {text_for_prod}'>⏱️ {format_duration(prod_hours)}</div>"
        
        day_acts = daily_sc.get(date_str, [])
        
        # Subject abbreviation map
        _SUBJ_SHORT = {
            'History': 'HIST', 'Ancient': 'Ancient', 'Medieval': 'Medieval',
            'Modern': 'Modern', 'Art&Culture': 'ANC',
            'Geography': 'Geo', 'Indian-Geography': 'Ind-Geo',
            'Physical-Geography': 'Phy-Geo', 'Human-Geography': 'Human-Geo',
            'Environment': 'ENV', 'Economics': 'ECO',
            'Post Independence': 'PostInd', 'Post-Independence': 'PostInd',
            'Post independence': 'PostInd', 'Post-independence': 'PostInd',
            'Sociology': 'Socio', 'bookstawa': 'Bstawa', 'Bookstawa': 'Bstawa'
        }
        
        for act in day_acts:
            act_type = act['type']
            act_sub = act.get('subject', '') or ''
            act_ch = act.get('chapter', '') or ''
            dur = act.get('duration', 0) or 0
            amt = act.get('amount', 0) or 0
            
            # Abbreviate subject
            act_sub_disp = _SUBJ_SHORT.get(act_sub, act_sub)
            
            # Determine text color for this activity item
            item_text_color = text_color
            is_dday = (act_type == 'Test' and act_sub == 'D-Day Exam')
            is_golden_text = act_type in _SC_GOLDEN_TEXT
            
            if is_dday or is_golden_text:
                if bg_color == "#fbbf24":
                    item_text_color = "#000000"  # Black on Golden background
                else:
                    item_text_color = "#eab308"  # Golden
            
            # Build label with truncated duration
            label_parts = []
            if act_sub_disp: 
                sub_str = str(act_sub_disp).replace('Bookstawa', 'Bstawa').replace('bookstawa', 'Bstawa')
                label_parts.append(sub_str)
            if act_ch: 
                ch_str = str(act_ch).replace('Bookstawa', 'Bstawa').replace('bookstawa', 'Bstawa')
                label_parts.append(ch_str)
            if dur > 0:
                val = format_duration(dur)
                label_parts.append(val)
            elif amt > 0:
                label_parts.append(f"₹{amt}")
            
            label = ' · '.join(label_parts)
            act_desc = act.get('description', '')
            
            tooltip = label
            if act_desc: tooltip += f" | {act_desc}"
            
            html += f"<div class='sc-act-item' style='color: {item_text_color}; background: rgba(255,255,255,0.1);' title=\"{tooltip}\">"
            html += f"<div>{label}</div>"
            if act_desc:
                html += f"<div style='display: inline-block; font-size: 8px; margin-top: 3px; padding: 1px 5px; border-radius: 8px; background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; box-sizing: border-box;'>💬 {act_desc}</div>"
            html += "</div>"
        
        html += "</div>"
    
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Detailed view below the calendar
    st.markdown("""
    <style>
    .sc-detail-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #4f46e5;
        border-radius: 14px;
        padding: 16px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .sc-detail-title {
        font-size: 18px;
        font-weight: 700;
        color: #a78bfa;
        margin-bottom: 16px;
    }
    </style>
    <div class='sc-detail-box'>
    <div class='sc-detail-title'>📝 View Study Activities by Date</div>
    """, unsafe_allow_html=True)
    
    sc_left, sc_right = st.columns([1, 1.5])
    
    with sc_left:
        st.markdown("**📅 Select Date:**")
        sc_sel_date = st.date_input(
            "Date",
            value=today,
            min_value=today - datetime.timedelta(days=730),
            max_value=today,
            key="sc_cal_datepicker",
            label_visibility="collapsed"
        )
        
        sc_date_str = str(sc_sel_date) if sc_sel_date else None
        sc_date_acts = sc_df[sc_df['date'] == sc_date_str].sort_values('id', ascending=False) if (sc_date_str and not sc_df.empty) else pd.DataFrame()
        sc_total_dur = sc_date_acts['duration'].sum() if not sc_date_acts.empty else 0
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.metric("Study Hrs", format_duration(sc_total_dur))
    
    with sc_right:
        if sc_sel_date:
            if not sc_date_acts.empty:
                st.markdown(f"**📋 {sc_date_str}**")
                st.divider()
                
                for _, row in sc_date_acts.iterrows():
                    _rid = int(row['id'])
                    _parts = [row['type']]
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
                        clean_desc = str(raw_desc).strip()
                        desc_text = f" <span style='display:inline-block; font-size:11px; color:#cbd5e1; background:rgba(255, 255, 255, 0.1); border: 1px solid rgba(255,255,255,0.15); padding:2px 8px; border-radius:12px; font-weight:normal; margin-left:6px; max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:middle;' title='{clean_desc}'>💬 {clean_desc}</span>"
                    
                    _act_container = st.container()
                    with _act_container:
                        _col_text, _col_del = st.columns([3.5, 1])
                        with _col_text:
                            st.markdown(f"**{activity_text}**{desc_text}", unsafe_allow_html=True)
                        with _col_del:
                            if st.button("🗑️", key=f"del_sc_{_rid}", help="Delete Activity", width='stretch'):
                                st.session_state[f"confirm_sc_{_rid}"] = True
                    
                    if st.session_state.get(f"confirm_sc_{_rid}", False):
                        _confirm_col = st.container()
                        with _confirm_col:
                            st.warning(f"Delete?", icon="⚠️")
                            _yc, _nc = st.columns([1, 1])
                            with _yc:
                                if st.button("✅ Yes", key=f"yes_sc_{_rid}", width='stretch'):
                                    c.execute("DELETE FROM activities WHERE id=%s", (_rid,))
                                    conn.commit()
                                    st.toast(f"🗑️ Activity deleted", icon="🗑️")
                                    st.session_state[f"confirm_sc_{_rid}"] = False
                                    st.rerun()
                            with _nc:
                                if st.button("❌ No", key=f"no_sc_{_rid}", width='stretch'):
                                    st.session_state[f"confirm_sc_{_rid}"] = False
                                    st.rerun()
                    
                    st.caption("")
            else:
                st.info(f"No study activities on {sc_date_str}", icon="ℹ️")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # ---------------- SET TARGET ----------------

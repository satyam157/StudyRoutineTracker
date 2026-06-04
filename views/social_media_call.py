import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
from utils import *
from logic import *
import database


def render(USER, USER_CONFIG):
    conn = database.conn
    c = database.c
    st.title("📱 Social Media & Calls Calendar")

    import calendar as calmod

    today = get_ist_now().date()

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_year = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="smc_yr", step=1)
    with col2:
        selected_month = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="smc_mo", step=1)

    # ── Activity types tracked on this calendar ──────────────────────────────
    _SM_TYPES    = ["Social Media"]
    _CALL_TYPES  = ["TalkOnCall"]
    _ALL_TYPES   = _SM_TYPES + _CALL_TYPES

    # Color per type for calendar cells
    _TYPE_COLOR = {
        "Social Media": "#f97316",   # orange
        "TalkOnCall":   "#818cf8",   # indigo
    }
    _TYPE_ICON = {
        "Social Media": "📱",
        "TalkOnCall":   "📞",
    }

    df_all = get_activities_df(USER)
    if not df_all.empty:
        if 'start_time' not in df_all.columns:
            df_all['start_time'] = None
        df_all['start_time'] = df_all.apply(
            lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time'])
                      else (f"{extract_time_of_day(r['chapter'])}:00"
                            if extract_time_of_day(r['chapter']) is not None else None),
            axis=1
        )
        df_all['chapter'] = df_all['chapter'].apply(get_clean_chapter)

    smc_df = df_all[df_all['type'].isin(_ALL_TYPES)].copy() if not df_all.empty else pd.DataFrame()

    # ── Build daily aggregates ───────────────────────────────────────────────
    # daily_hours:  { date_str -> { type -> total_hours } }
    # daily_acts:   { date_str -> [ {type, subject, chapter, start_time, duration, description} ] }
    daily_hours = {}
    daily_acts  = {}

    if not smc_df.empty:
        for d, g in smc_df.groupby("date"):
            date_str = str(d)
            hours_map = {}
            agg = {}
            for _, r in g.iterrows():
                t   = r['type']
                sub = str(r.get('subject', '') or '')
                ch  = str(r.get('chapter', '') or '')
                dur = float(r.get('duration', 0) or 0)
                raw_desc = r.get('description')
                desc = str(raw_desc).strip() if raw_desc and str(raw_desc).strip().lower() not in ('none','nan','null') else ''

                hours_map[t] = hours_map.get(t, 0.0) + dur

                if t not in agg:
                    agg[t] = {'type': t, 'duration': 0.0, 'items': []}

                agg[t]['duration'] += dur

                if desc:
                    agg[t]['items'].append(desc)

            final_acts = []
            for t, data in agg.items():
                final_acts.append({
                    'type': t,
                    'duration': data['duration'],
                    'description': " | ".join(data['items'])
                })
            daily_hours[date_str] = hours_map
            daily_acts[date_str] = final_acts
            
    # Calculate daily study (productive) hours
    prod_df = df_all[df_all['type'].isin(PRODUCTIVE_TYPES)].copy() if not df_all.empty else pd.DataFrame()
    daily_prod = {}
    if not prod_df.empty:
        for d, g in prod_df.groupby("date"):
            daily_prod[str(d)] = g['duration'].sum()

    # ── Calendar HTML ────────────────────────────────────────────────────────
    month_name_str = calmod.month_name[int(selected_month)]
    st.subheader(f"{month_name_str} {int(selected_year)}")

    _, num_days   = calmod.monthrange(int(selected_year), int(selected_month))
    first_weekday = calmod.weekday(int(selected_year), int(selected_month), 1)
    day_names     = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    html = """
    <style>
    .smc-cal-wrapper { display: flex; flex-direction: column; }
    .smc-cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        margin: 15px 0 0 0;
    }
    .smc-cal-header {
        font-weight: 900; font-size: 15px; text-align: center;
        padding: 14px 8px;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: #e0e7ff; border-radius: 8px; border: 2px solid #475569;
        letter-spacing: 0.5px;
    }
    .smc-cal-cell {
        border: 1px solid #334155; border-radius: 12px; padding: 10px 8px;
        min-height: 130px; display: flex; flex-direction: column;
        font-size: 12px; gap: 4px; overflow: hidden;
        background: #0f172a;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
    }
    .smc-cal-cell:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(249, 115, 22, 0.3);
    }
    .smc-cal-cell.empty {
        background: transparent !important; border: none !important;
        cursor: default; min-height: auto;
    }
    .smc-cal-cell.empty:hover { transform: none; box-shadow: none; }
    .smc-cal-cell.today-smc { border: 2px solid #eab308 !important; box-shadow: 0 0 10px rgba(234,179,8,0.35); }
    .smc-cal-cell.future-smc { opacity: 0.4; cursor: default; }
    .smc-cal-cell.golden-day {
        background: #eab308 !important;
        border: 2px solid #b45309 !important;
        box-shadow: 0 0 14px rgba(234,179,8,0.4) !important;
    }
    .smc-cal-cell.golden-day:hover {
        box-shadow: 0 8px 28px rgba(234,179,8,0.6) !important;
    }
    .smc-cal-cell.golden-day .smc-cal-date { color: #000000 !important; }
    .smc-golden-badge {
        font-size: 10px; font-weight: 800; color: #000000;
        background: rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);
        border-radius: 5px; padding: 2px 6px; margin-bottom: 3px;
        display: inline-block;
    }
    .smc-cal-date { font-weight: 900; font-size: 20px; margin-bottom: 3px; color: #e2e8f0; line-height: 1; }
    .smc-total-badge {
        font-size: 11px; font-weight: 700;
        padding: 3px 6px; border-radius: 5px; margin-bottom: 3px;
        background: rgba(255,255,255,0.07); color: #cbd5e1;
    }
    .smc-act-chip {
        font-size: 10px; font-weight: 600;
        padding: 3px 5px; border-radius: 4px; margin-bottom: 2px;
        line-height: 1.3; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis;
    }
    .smc-act-desc {
        font-size: 9px; opacity: 0.8; margin-top: 1px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    @media (max-width: 900px) {
        .smc-cal-grid { grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .smc-cal-cell { min-height: 110px; padding: 8px 6px; }
        .smc-cal-date { font-size: 17px; }
    }
    @media (max-width: 550px) {
        .smc-cal-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
        .smc-cal-cell { min-height: 95px; padding: 7px 5px; }
        .smc-cal-date { font-size: 14px; }
        .smc-act-chip { font-size: 9px; }
    }
    </style>
    <div class="smc-cal-wrapper"><div class="smc-cal-grid">
    """

    for day in day_names:
        html += f"<div class='smc-cal-header'>{day}</div>"

    for _ in range(first_weekday):
        html += "<div class='smc-cal-cell empty'></div>"

    today_str = str(today)

    for day in range(1, num_days + 1):
        date_str  = f"{int(selected_year)}-{int(selected_month):02d}-{day:02d}"
        is_today  = date_str == today_str
        is_future = dt_module.date(int(selected_year), int(selected_month), day) > today

        hours_map = daily_hours.get(date_str, {})
        acts_list = daily_acts.get(date_str, [])

        sm_hrs   = hours_map.get('Social Media', 0.0)
        call_hrs = hours_map.get('TalkOnCall', 0.0)
        total_waste = sm_hrs + call_hrs
        study_hrs = daily_prod.get(date_str, 0.0)
        
        # Golden day: SM ≤ 1h AND Calls ≤ 2h (even if 0)
        is_golden = (sm_hrs <= 1.0) and (call_hrs <= 2.0) and not is_future

        cell_cls = "smc-cal-cell"
        if is_golden:  cell_cls += " golden-day"
        if is_today:   cell_cls += " today-smc"
        if is_future:  cell_cls += " future-smc"

        # Color logic based on total waste vs study time
        bg_color, text_color = "#0f172a", "#e2e8f0"
        if not is_future and not is_golden:
            if total_waste > study_hrs:
                bg_color, text_color = "#1a1a1a", "#ffffff" # Black for exceeding study time
            else:
                if total_waste > 4:
                    bg_color, text_color = "#dc2626", "#ffffff" # Red
                elif total_waste > 2:
                    bg_color, text_color = "#38bdf8", "#000000" # Lightblue
                else:
                    bg_color, text_color = "#22c55e", "#000000" # Green

        # Only apply inline style if it's not golden (golden class handles its own background)
        style_attr = f"style='background-color: {bg_color}; color: {text_color};'" if not is_golden else ""

        html += f"<div class='{cell_cls}' {style_attr}>"
        html += f"<div class='smc-cal-date' style='color: {text_color if not is_golden else ""};'>{day}</div>"

        if not is_future:
            if is_golden:
                html += "<div class='smc-golden-badge'>⭐ Great Control</div>"
            
            if study_hrs > 0:
                html += f"<div style='font-size:10.5px; color:{text_color if not is_golden else '#000000'}; font-weight:700; margin-bottom:4px; opacity:0.9;'>📚 Study: {format_duration(study_hrs)}</div>"

            # Sort activities by duration descending
            acts_list.sort(key=lambda x: x['duration'], reverse=True)

            for act in acts_list:
                t      = act['type']
                dur    = act['duration']
                desc   = act['description']
                
                # Solid colors for chips to stand out against colored backgrounds
                _TYPE_BG = {"Social Media": "#1a1a1a", "TalkOnCall": "#1a1a1a"}
                _TYPE_TEXT = {"Social Media": "#ffffff", "TalkOnCall": "#ffffff"}
                
                bg = _TYPE_BG.get(t, '#334155')
                fg = _TYPE_TEXT.get(t, '#ffffff')
                icon = _TYPE_ICON.get(t, '•')

                parts = []
                if dur > 0: parts.append(format_duration(dur))
                chip_label = f"{icon} " + " · ".join(parts) if parts else f"{icon} {t}"

                tooltip = chip_label
                if desc: tooltip += f" | {desc}"

                html += (
                    f"<div class='smc-act-chip' "
                    f"style='background: {bg}; color: {fg}; box-shadow: 0 1px 3px rgba(0,0,0,0.3);' title='{tooltip}'>"
                    f"{chip_label}"
                )
                if desc:
                    html += f"<div class='smc-act-desc' style='color: rgba(255,255,255,0.85);'>{desc}</div>"
                html += "</div>"

        html += "</div>"

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Monthly Summary Stats ─────────────────────────────────────────────────
    month_str = f"{int(selected_year)}-{int(selected_month):02d}"
    if not smc_df.empty:
        smc_df['month_str'] = pd.to_datetime(smc_df['date']).dt.strftime('%Y-%m')
        month_smc = smc_df[smc_df['month_str'] == month_str]
    else:
        month_smc = pd.DataFrame()

    st.markdown("---")
    st.markdown(f"### 📊 {month_name_str} {int(selected_year)} — Summary")

    sm_total  = month_smc[month_smc['type'] == 'Social Media']['duration'].sum() if not month_smc.empty else 0.0
    call_total = month_smc[month_smc['type'] == 'TalkOnCall']['duration'].sum() if not month_smc.empty else 0.0
    combined  = sm_total + call_total

    c1, c2, c3 = st.columns(3)
    c1.metric("📱 Social Media", format_duration(sm_total))
    c2.metric("📞 Calls (TalkOnCall)", format_duration(call_total))
    c3.metric("🕐 Total This Month", format_duration(combined))

    if not smc_df.empty:
        st.markdown("#### 🔍 Breakdown by Platform / Person")
        
        b_c1, b_c2 = st.columns(2)
        with b_c1:
            br_yr = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="smc_br_yr", step=1)
        with b_c2:
            br_mo = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="smc_br_mo", step=1)
            
        breakdown_sel_month = f"{int(br_yr)}-{int(br_mo):02d}"
        breakdown_df = smc_df[smc_df['month_str'] == breakdown_sel_month].copy()
        
        if not breakdown_df.empty:
            breakdown = (
                breakdown_df.groupby(['type', 'subject'])['duration']
                .sum()
                .reset_index()
                .sort_values('duration', ascending=False)
            )
            breakdown['duration_fmt'] = breakdown['duration'].apply(format_duration)
            breakdown.rename(columns={'type': 'Activity', 'subject': 'Platform / Person', 'duration_fmt': 'Time'}, inplace=True)
            st.dataframe(breakdown[['Activity', 'Platform / Person', 'Time']], hide_index=True, width='stretch')
        else:
            st.info("No breakdown data found for the selected month.")

    # ── Monthly Activities Log ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Monthly Activities Log")
    
    if not smc_df.empty:
        l_c1, l_c2 = st.columns(2)
        with l_c1:
            log_yr = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="smc_log_yr", step=1)
        with l_c2:
            log_mo = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="smc_log_mo", step=1)
            
        log_sel_month = f"{int(log_yr)}-{int(log_mo):02d}"
        log_df = smc_df[smc_df['month_str'] == log_sel_month].copy()
        
        if not log_df.empty:
            log_df['Duration'] = log_df['duration'].apply(format_duration)
            log_df = log_df.sort_values(by=['date', 'start_time'], na_position='last')
            
            display_df = log_df[['date', 'type', 'subject', 'chapter', 'Duration', 'description']].copy()
            display_df.rename(columns={
                'date': 'Date',
                'type': 'Activity',
                'subject': 'Platform / Person',
                'chapter': 'Note',
                'description': 'Description'
            }, inplace=True)
            
            st.dataframe(display_df, hide_index=True, width='stretch')
        else:
            st.info(f"No entries found for the selected month.")
    else:
        st.info("No Social Media or Call entries recorded yet.")


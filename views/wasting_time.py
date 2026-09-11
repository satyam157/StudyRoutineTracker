import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
import calendar as calmod
from utils import *
from logic import *
import database


def render(USER, USER_CONFIG):
    conn = database.conn
    c = database.c

    today = get_ist_now().date()

    # ── Page Styles ──────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;900&display=swap');
    .wt-page-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #f87171 0%, #fb923c 50%, #fbbf24 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 4px;
    }
    .wt-page-subtitle { font-size: 13px; color: #94a3b8; margin-bottom: 20px; }
    .wt-legend { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; font-size: 12.5px; }
    .wt-legend-item { display: flex; align-items: center; gap: 6px; color: #cbd5e1; font-weight: 600; }
    .wt-legend-dot { width: 14px; height: 14px; border-radius: 4px; }
    .wt-cal-wrapper { display: flex; flex-direction: column; }
    .wt-cal-grid {
        display: grid; grid-template-columns: repeat(7, 1fr);
        gap: 8px; margin: 10px 0 0 0;
    }
    .wt-cal-header {
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
    .wt-cal-cell {
        border: 2px solid #475569;
        border-radius: 12px;
        padding: 12px 10px;
        min-height: 135px;
        display: flex;
        flex-direction: column;
        font-size: 12px;
        gap: 5px;
        overflow: hidden;
        transition: all 0.25s ease, transform 0.2s ease;
        cursor: pointer;
        position: relative;
    }
    .wt-cal-cell:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    .wt-cal-cell.empty { background: transparent !important; border: none !important; cursor: default; min-height: auto; }
    .wt-cal-cell.empty:hover { transform: none; box-shadow: none; }
    .wt-cal-cell.today-cell { border: 2px solid #eab308 !important; box-shadow: 0 0 12px rgba(234, 179, 8, 0.5) !important; }
    .wt-cal-cell.future-cell { opacity: 0.35; cursor: default; }
    .wt-cal-cell.green-cell { background: #22c55e; border: 2px solid #16a34a; color: #ffffff; }
    .wt-cal-cell.orange-cell { background: #f97316; border: 2px solid #ea580c; color: #ffffff; }
    .wt-cal-cell.red-cell { background: #991b1b; border: 2px solid #dc2626; color: #ffffff; }
    .wt-cal-cell.future-blank { background: #0f172a; border: 2px solid #1e293b; color: #64748b; }
    
    .wt-cal-date { font-weight: 900; font-size: 22px; line-height: 1; color: #ffffff; margin-bottom: 2px; }
    .wt-count-badge { font-size: 12px; font-weight: 800; padding: 5px 8px; border-radius: 5px; margin-top: 2px; background: rgba(0, 0, 0, 0.25); color: #ffffff !important; display: inline-block; letter-spacing: 0.2px; text-shadow: 0 1px 2px rgba(0,0,0,0.3); }
    .wt-time-badge { font-size: 11.5px; font-weight: 700; padding: 4px 7px; border-radius: 5px; margin-top: 2px; background: rgba(0, 0, 0, 0.35); color: #ffffff !important; display: inline-block; text-shadow: 0 1px 2px rgba(0,0,0,0.3); }
    .wt-clean-badge { font-size: 12px; font-weight: 700; padding: 5px 8px; border-radius: 5px; margin-top: 4px; background: rgba(0, 0, 0, 0.2); color: #ffffff !important; display: inline-block; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
    @media (max-width: 900px) {
        .wt-cal-grid { grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .wt-cal-header { font-size: 13px; padding: 10px 6px; }
        .wt-cal-cell { min-height: 115px; padding: 10px 8px; }
        .wt-cal-date { font-size: 19px; }
    }
    @media (max-width: 550px) {
        .wt-cal-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
        .wt-cal-header { font-size: 12px; padding: 8px 4px; }
        .wt-cal-cell { min-height: 100px; padding: 8px 6px; }
        .wt-cal-date { font-size: 16px; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='wt-page-title'>🚫 WastingTime</div>", unsafe_allow_html=True)
    st.markdown("<div class='wt-page-subtitle'>Social Media & Calls — WatchingP Activity Calendar</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='wt-legend'>
        <div class='wt-legend-item'><div class='wt-legend-dot' style='background:#22c55e; border:1px solid #16a34a;'></div>0 times — Clean day ✅</div>
        <div class='wt-legend-item'><div class='wt-legend-dot' style='background:#f97316; border:1px solid #ea580c;'></div>1 time — Watch out ⚠️</div>
        <div class='wt-legend-item'><div class='wt-legend-dot' style='background:#991b1b; border:1px solid #dc2626;'></div>2+ times — Danger 🚨</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Month / Year selector ─────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_year = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="wt_yr", step=1)
    with col2:
        selected_month = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="wt_mo", step=1)

    # ── WatchingP activity type variants (case-insensitive match) ─────────────
    _WATCHINGP_LOWER = {"watchingp", "watching p", "watching_p", "watchp", "watchingporn"}

    # ── Load data ─────────────────────────────────────────────────────────────
    df_all = get_activities_df(USER)

    if not df_all.empty:
        _wp_mask = df_all['type'].str.strip().str.lower().isin(_WATCHINGP_LOWER)
        wp_df = df_all[_wp_mask].copy()
    else:
        wp_df = pd.DataFrame()

    # ── Build daily aggregates ────────────────────────────────────────────────
    daily_stats = {}
    if not wp_df.empty:
        for d, g in wp_df.groupby("date"):
            date_str = str(d)
            count = len(g)
            total_hours = float(g['duration'].sum())
            daily_stats[date_str] = {'count': count, 'total_hours': total_hours}

    # ── Calendar HTML ─────────────────────────────────────────────────────────
    month_name_str = calmod.month_name[int(selected_month)]
    st.subheader(f"📅 {month_name_str} {int(selected_year)}")

    _, num_days = calmod.monthrange(int(selected_year), int(selected_month))
    first_weekday = calmod.weekday(int(selected_year), int(selected_month), 1)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_str = str(today)

    html = "<div class='wt-cal-wrapper'><div class='wt-cal-grid'>"

    for day in day_names:
        html += f"<div class='wt-cal-header'>{day}</div>"

    for _ in range(first_weekday):
        html += "<div class='wt-cal-cell empty'></div>"

    for day in range(1, num_days + 1):
        date_str = f"{int(selected_year)}-{int(selected_month):02d}-{day:02d}"
        is_today = date_str == today_str
        is_future = dt_module.date(int(selected_year), int(selected_month), day) > today

        stats = daily_stats.get(date_str, {'count': 0, 'total_hours': 0.0})
        count = stats['count']
        total_hours = stats['total_hours']

        if is_future:
            cell_cls = "wt-cal-cell future-blank future-cell"
        elif count == 0:
            cell_cls = "wt-cal-cell green-cell"
        elif count == 1:
            cell_cls = "wt-cal-cell orange-cell"
        else:
            cell_cls = "wt-cal-cell red-cell"

        if is_today:
            cell_cls += " today-cell"

        html += f"<div class='{cell_cls}'>"
        html += f"<div class='wt-cal-date'>{day}</div>"

        if not is_future:
            if count == 0:
                html += "<div class='wt-clean-badge'>✅ Clean</div>"
            else:
                html += f"<div class='wt-count-badge'>🔁 x{count}</div>"
                if total_hours > 0:
                    html += f"<div class='wt-time-badge'>⏱️ {format_duration(total_hours)}</div>"

        html += "</div>"

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Monthly Summary ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 📊 {month_name_str} {int(selected_year)} — Summary")

    month_str = f"{int(selected_year)}-{int(selected_month):02d}"
    if not wp_df.empty:
        wp_df['_month'] = pd.to_datetime(wp_df['date']).dt.strftime('%Y-%m')
        month_wp = wp_df[wp_df['_month'] == month_str]
    else:
        month_wp = pd.DataFrame()

    total_count = len(month_wp) if not month_wp.empty else 0
    total_time = month_wp['duration'].sum() if not month_wp.empty else 0.0

    clean_days = 0
    danger_days = 0
    warn_days = 0
    _, nm = calmod.monthrange(int(selected_year), int(selected_month))
    for d in range(1, nm + 1):
        ds = f"{int(selected_year)}-{int(selected_month):02d}-{d:02d}"
        if dt_module.date(int(selected_year), int(selected_month), d) > today:
            continue
        cnt = daily_stats.get(ds, {}).get('count', 0)
        if cnt == 0:
            clean_days += 1
        elif cnt == 1:
            warn_days += 1
        else:
            danger_days += 1

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🔁 Total Occurrences", total_count)
    m2.metric("⏱️ Total Time", format_duration(total_time))
    m3.metric("✅ Clean Days", clean_days)
    m4.metric("⚠️ Warning Days", warn_days)
    m5.metric("🚨 Danger Days", danger_days)

    # ── Monthly Log ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Monthly Log")

    if not wp_df.empty and not month_wp.empty:
        log_df = month_wp.copy()
        log_df['Duration'] = log_df['duration'].apply(format_duration)
        log_df = log_df.sort_values(by='date')
        display_cols = [c for c in ['date', 'type', 'subject', 'chapter', 'Duration', 'description'] if c in log_df.columns]
        log_df = log_df[display_cols].copy()
        log_df.rename(columns={
            'date': 'Date', 'type': 'Activity', 'subject': 'Detail',
            'chapter': 'Note', 'description': 'Description'
        }, inplace=True)
        st.dataframe(log_df, hide_index=True, use_container_width=True)
    else:
        st.info(f"No WatchingP entries found for {month_name_str} {int(selected_year)}.", icon="ℹ️")

    # ── All-time yearly breakdown ─────────────────────────────────────────────
    if daily_stats:
        st.markdown("---")
        st.markdown("### 🗺️ All-Time WatchingP Breakdown")
        heat_data = []
        for ds, s in sorted(daily_stats.items()):
            try:
                dt_obj = dt_module.date.fromisoformat(ds)
                heat_data.append({'year': dt_obj.year, 'count': s['count'], 'hours': s['total_hours']})
            except:
                pass

        if heat_data:
            heat_df = pd.DataFrame(heat_data)
            yearly = heat_df.groupby('year').agg(
                total_count=('count', 'sum'),
                danger_days=('count', lambda x: (x > 1).sum()),
                warn_days=('count', lambda x: (x == 1).sum()),
            ).reset_index()

            for _, yr_row in yearly.iterrows():
                yr = int(yr_row['year'])
                tc = int(yr_row['total_count'])
                dd = int(yr_row['danger_days'])
                wd = int(yr_row['warn_days'])
                st.markdown(f"""
                <div style="background: linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155;
                    border-radius:10px; padding:12px 16px; margin-bottom:10px;
                    display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span style="font-weight:800; font-size:16px; color:#e2e8f0;">{yr}</span>
                    <span style="color:#fca5a5;">🚨 {dd} danger days</span>
                    <span style="color:#fdba74;">⚠️ {wd} warning days</span>
                    <span style="color:#a78bfa;">🔁 {tc} total occurrences</span>
                </div>
                """, unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
from logic import PRODUCTIVE_TYPES, get_ist_now, get_adjusted_sums

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TIER DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════
HOUR_TIERS = [
    {"min": 0.0,  "max": 3.0,  "name": "Beginner",   "color": "#94a3b8", "fill": "rgba(148, 163, 184, 0.28)"},
    {"min": 3.0,  "max": 6.0,  "name": "Consistent", "color": "#4ade80", "fill": "rgba(74, 222, 128, 0.28)"},
    {"min": 6.0,  "max": 8.0,  "name": "Specialist", "color": "#2dd4bf", "fill": "rgba(45, 212, 191, 0.28)"},
    {"min": 8.0,  "max": 10.0, "name": "Expert",     "color": "#60a5fa", "fill": "rgba(96, 165, 250, 0.28)"},
    {"min": 10.0, "max": 12.0, "name": "Master",     "color": "#c084fc", "fill": "rgba(192, 132, 252, 0.28)"},
    {"min": 12.0, "max": 24.0, "name": "Grandmaster","color": "#f87171", "fill": "rgba(248, 113, 113, 0.28)"},
]

PCT_TIERS = [
    {"min": 0,   "max": 40,  "name": "Developing",  "color": "#94a3b8", "fill": "rgba(148, 163, 184, 0.28)"},
    {"min": 40,  "max": 60,  "name": "Consistent",  "color": "#4ade80", "fill": "rgba(74, 222, 128, 0.28)"},
    {"min": 60,  "max": 75,  "name": "Specialist",  "color": "#2dd4bf", "fill": "rgba(45, 212, 191, 0.28)"},
    {"min": 75,  "max": 85,  "name": "Expert",      "color": "#60a5fa", "fill": "rgba(96, 165, 250, 0.28)"},
    {"min": 85,  "max": 95,  "name": "Master",      "color": "#c084fc", "fill": "rgba(192, 132, 252, 0.28)"},
    {"min": 95,  "max": 100, "name": "Grandmaster", "color": "#f87171", "fill": "rgba(248, 113, 113, 0.28)"},
]

def get_tier_info(val, is_pct=False):
    tiers = PCT_TIERS if is_pct else HOUR_TIERS
    for t in tiers:
        if t["min"] <= val <= t["max"]:
            return t
    return tiers[-1] if val > tiers[-1]["max"] else tiers[0]

def _render_html(html_str):
    """
    Renders clean raw HTML without letting Streamlit markdown parser
    interpret leading indentation spaces as code blocks.
    """
    clean_lines = [line.strip() for line in html_str.strip().splitlines() if line.strip() and not line.strip().startswith("<!--")]
    clean_html = "".join(clean_lines)
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE & TIER GRAPH (HOURS & OTHER METRICS)
# ══════════════════════════════════════════════════════════════════════════════
def render_codeforces_performance_graph(daily_df, metric_col="productive_no_test_hours", metric_label="Productive Hours (Excl. Test)"):
    """
    Renders performance graph with hours and other metrics across performance tiers.
    Features horizontal colored tier bands, golden line, circular data points,
    and a highlighted red ring marker at the peak performance point.
    """
    if daily_df.empty:
        st.info("No daily data available to plot performance graph.")
        return

    today = get_ist_now().date()
    plot_df = daily_df.copy()
    if 'date_dt' not in plot_df.columns:
        plot_df['date_dt'] = pd.to_datetime(plot_df['date'])
    # Guard: Strictly exclude any dates beyond today
    plot_df = plot_df[plot_df['date_dt'].dt.date <= today]
    plot_df = plot_df.sort_values('date_dt').reset_index(drop=True)

    if metric_col not in plot_df.columns:
        if metric_col == "productive_no_test_hours" and "productive_hours" in plot_df.columns:
            if "test_hours" in plot_df.columns:
                plot_df["productive_no_test_hours"] = (plot_df["productive_hours"] - plot_df["test_hours"]).clip(lower=0)
            else:
                plot_df["productive_no_test_hours"] = plot_df["productive_hours"]
        else:
            st.warning(f"Metric '{metric_col}' not found in data.")
            return

    is_pct = "%" in metric_label or "Score" in metric_label or "pct" in metric_col.lower()
    tiers = PCT_TIERS if is_pct else HOUR_TIERS

    y_vals = plot_df[metric_col].fillna(0).tolist()
    x_vals = plot_df['date_dt'].tolist()
    date_strs = plot_df['date'].astype(str).tolist()

    if not y_vals:
        st.info("No points to plot.")
        return

    max_val = max(y_vals) if y_vals else 0
    peak_idx = int(np.argmax(y_vals)) if y_vals else 0
    peak_date = date_strs[peak_idx] if date_strs else ""
    peak_val = y_vals[peak_idx] if y_vals else 0

    if is_pct:
        y_upper = 100.0
        d_tick = 10
    else:
        if max_val <= 4.0:
            y_upper = max(5.0, float(np.ceil(max_val + 1.0)))
            d_tick = 1
        elif max_val <= 8.0:
            y_upper = max(9.0, float(np.ceil(max_val + 1.0)))
            d_tick = 1
        else:
            y_upper = max(14.0, float(np.ceil(max_val + 1.5)))
            d_tick = 2

    # Rating Header (Current Rating evaluated strictly as per previous completed day)
    completed_df = plot_df[plot_df['date_dt'].dt.date < today]
    if not completed_df.empty:
        curr_val = float(completed_df[metric_col].fillna(0).iloc[-1])
        curr_date = str(completed_df['date'].iloc[-1])
    else:
        curr_val = y_vals[-1] if y_vals else 0
        curr_date = date_strs[-1] if date_strs else ""

    curr_tier = get_tier_info(curr_val, is_pct)
    peak_tier = get_tier_info(peak_val, is_pct)

    unit_str = "%" if is_pct else "hrs"
    try:
        curr_date_fmt = pd.to_datetime(curr_date).strftime('%d %b %Y')
    except:
        curr_date_fmt = curr_date

    try:
        peak_date_fmt = pd.to_datetime(peak_date).strftime('%d %b %Y')
    except:
        peak_date_fmt = peak_date

    rating_banner_html = (
        f'<div style="display:flex;flex-wrap:wrap;gap:20px 32px;align-items:center;padding:14px 20px;background:#0f172a;border-radius:10px;border:1px solid #1e293b;margin:6px 0 14px 0;">'
        f'<div>'
        f'<div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">Current Rating (Previous Completed Day)</div>'
        f'<div style="font-size:22px;font-weight:700;color:#f8fafc;margin-top:2px;display:flex;align-items:center;gap:8px;">'
        f'<span>{curr_val:.2f} {unit_str}</span>'
        f'<span style="font-size:13px;font-weight:700;color:{curr_tier["color"]};background:{curr_tier["fill"]};padding:2px 8px;border-radius:6px;border:1px solid {curr_tier["color"]}40;">{curr_tier["name"]}</span>'
        f'<span style="font-size:12px;color:#94a3b8;font-weight:400;">({curr_date_fmt})</span>'
        f'</div>'
        f'</div>'
        f'<div style="width:1px;height:36px;background:#1e293b;"></div>'
        f'<div>'
        f'<div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">Highest Rating Achieved</div>'
        f'<div style="font-size:22px;font-weight:700;color:#f8fafc;margin-top:2px;display:flex;align-items:center;gap:8px;">'
        f'<span>{peak_val:.2f} {unit_str}</span>'
        f'<span style="font-size:13px;font-weight:700;color:{peak_tier["color"]};background:{peak_tier["fill"]};padding:2px 8px;border-radius:6px;border:1px solid {peak_tier["color"]}40;">{peak_tier["name"]}</span>'
        f'<span style="font-size:12px;color:#94a3b8;font-weight:400;">({peak_date_fmt})</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    _render_html(rating_banner_html)

    fig = go.Figure()

    # 1. Add horizontal tier bands
    for t in tiers:
        if t["min"] >= y_upper:
            continue
        b_max = min(t["max"], y_upper)
        fig.add_hrect(
            y0=t["min"],
            y1=b_max,
            fillcolor=t["fill"],
            line_width=0,
            layer="below"
        )

    # 2. Add connecting golden line
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode='lines+markers',
        name=metric_label,
        line=dict(color="#f59e0b", width=2.5),
        marker=dict(
            color="#fbbf24",
            size=6,
            line=dict(color="#ffffff", width=1.2)
        ),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>" +
            f"{metric_label}: <b>%{{y:.2f}}</b>" + ("%" if is_pct else " hrs") + "<br>" +
            "Tier: <span style='color:%{customdata[2]};'><b>%{customdata[1]}</b></span><extra></extra>"
        ),
        customdata=[
            [
                d_str,
                get_tier_info(v, is_pct)["name"],
                get_tier_info(v, is_pct)["color"]
            ]
            for d_str, v in zip(date_strs, y_vals)
        ]
    ))

    # 3. Add highlighted red ring marker for all-time peak
    if peak_val > 0:
        peak_tier = get_tier_info(peak_val, is_pct)
        fig.add_trace(go.Scatter(
            x=[x_vals[peak_idx]],
            y=[peak_val],
            mode='markers',
            name="Peak Performance",
            marker=dict(
                color="#ef4444",
                size=12,
                symbol="circle",
                line=dict(color="#ffffff", width=2.5)
            ),
            hovertemplate=(
                f"👑 <b>All-Time Peak</b><br>Date: {peak_date}<br>" +
                f"{metric_label}: <b>{peak_val:.2f}</b>" + ("%" if is_pct else " hrs") + "<br>" +
                f"Tier: <span style='color:{peak_tier['color']};'><b>{peak_tier['name']}</b></span><extra></extra>"
            )
        ))

    # Layout styling
    fig.update_layout(
        title=dict(
            text=f"<b>Performance Timeline</b> — {metric_label}",
            font=dict(size=17, color="#f8fafc")
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.15)",
            zeroline=False,
            showline=True,
            linecolor="rgba(148, 163, 184, 0.4)",
            tickformat="%b %Y",
            dtick="M1"
        ),
        yaxis=dict(
            title=f"{metric_label}" + (" (%)" if is_pct else " (Hours)"),
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.15)",
            zeroline=False,
            range=[0, y_upper],
            tickmode="linear",
            dtick=d_tick
        ),
        hovermode="x unified",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0", family="Inter, system-ui, sans-serif"),
        margin=dict(l=40, r=30, t=55, b=40),
        height=380,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, key=f"cf_perf_graph_{metric_col}")


# ══════════════════════════════════════════════════════════════════════════════
# STATS CALCULATIONS (2x3 & 4-STREAK CARD LAYOUT)
# ══════════════════════════════════════════════════════════════════════════════
def calculate_cf_stats(df, activity_type="All", year=None):
    """
    Calculates metrics:
    Row 1: [All-time hours], [Year hours], [Last month / 30-day hours]
    Row 2: [Current active streak], [Max streak all-time], [Max streak selected year], [Max streak last 30 days]
    """
    now = get_ist_now()
    curr_year = now.year if year is None or year == "All" or year == "Last 365 Days" else int(year)
    today = now.date()
    month_ago = today - timedelta(days=30)

    if df.empty:
        return {
            "all_time_hrs": 0.0, "year_hrs": 0.0, "month_hrs": 0.0,
            "current_streak": 0, "all_time_streak": 0, "year_streak": 0, "month_streak": 0,
            "target_year": curr_year, "activity_type": activity_type
        }

    # Filter by activity type and guard against future dates
    work_df = df.copy()
    if 'date_dt' not in work_df.columns:
        work_df['date_dt'] = pd.to_datetime(work_df['date'])
    work_df = work_df[work_df['date_dt'].dt.date <= today]

    if activity_type == "Study":
        act_df = work_df[work_df['type'].isin(['Study', 'Study during trip'])].copy()
    elif activity_type == "Revision":
        act_df = work_df[work_df['type'] == 'Revision'].copy()
    elif activity_type == "Test":
        act_df = work_df[work_df['type'].isin(['Test', 'test'])].copy()
    elif activity_type == "All 3 Combined":
        act_df = work_df[work_df['type'].isin(['Study', 'Study during trip', 'Revision', 'Test', 'test'])].copy()
    else:
        act_df = work_df[work_df['type'].isin(PRODUCTIVE_TYPES)].copy()

    # Aggregate by date
    if act_df.empty:
        return {
            "all_time_hrs": 0.0, "year_hrs": 0.0, "month_hrs": 0.0,
            "current_streak": 0, "all_time_streak": 0, "year_streak": 0, "month_streak": 0,
            "target_year": curr_year, "activity_type": activity_type
        }

    daily_totals = act_df.groupby('date')['duration'].sum()
    all_dates = pd.to_datetime(daily_totals.index)
    
    # 1. Hours calculations
    all_time_hrs = round(float(daily_totals.sum()), 1)
    
    year_mask = (all_dates.year == curr_year)
    year_hrs = round(float(daily_totals[year_mask].sum()), 1)
    
    month_mask = (all_dates.date >= month_ago) & (all_dates.date <= today)
    month_hrs = round(float(daily_totals[month_mask].sum()), 1)

    # 2. Max Streak calculations (consecutive calendar days with hours > 0)
    def compute_max_streak(dates_series):
        if dates_series.empty:
            return 0
        sorted_dates = sorted(list(set(dates_series.dt.date)))
        if not sorted_dates:
            return 0
        max_s = 1
        curr_s = 1
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] == sorted_dates[i-1] + timedelta(days=1):
                curr_s += 1
                max_s = max(max_s, curr_s)
            elif sorted_dates[i] == sorted_dates[i-1]:
                continue
            else:
                curr_s = 1
        return max_s

    all_time_streak = compute_max_streak(pd.Series(all_dates))
    year_streak = compute_max_streak(pd.Series(all_dates[year_mask]))
    month_streak = compute_max_streak(pd.Series(all_dates[month_mask]))

    # 3. Current active streak (ending today or yesterday if today is in progress)
    daily_dict = daily_totals.to_dict()
    hrs_today = daily_dict.get(today.strftime('%Y-%m-%d'), 0)
    hrs_yesterday = daily_dict.get((today - timedelta(days=1)).strftime('%Y-%m-%d'), 0)

    if hrs_today > 0:
        check_date = today
    elif hrs_yesterday > 0:
        check_date = today - timedelta(days=1)
    else:
        check_date = None

    current_streak = 0
    if check_date:
        while True:
            d_str = check_date.strftime('%Y-%m-%d')
            if daily_dict.get(d_str, 0) > 0:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break

    return {
        "all_time_hrs": all_time_hrs,
        "year_hrs": year_hrs,
        "month_hrs": month_hrs,
        "current_streak": current_streak,
        "all_time_streak": all_time_streak,
        "year_streak": year_streak,
        "month_streak": month_streak,
        "target_year": curr_year,
        "activity_type": activity_type
    }


def render_codeforces_stats_cards(stats, unit="hours"):
    """
    Renders statistics cards below the heatmap:
    Row 1: Hours (All time, Selected Year, Last 30 days)
    Row 2: Streaks (Current Active Streak, Max Streak All-time, Max Streak for Year, Max Streak for Last Month)
    """
    yr = stats.get("target_year", "the year")
    act_type = stats.get("activity_type", "Study")
    cur_s = stats.get("current_streak", 0)
    all_s = stats.get("all_time_streak", 0)
    yr_s = stats.get("year_streak", 0)
    m_s = stats.get("month_streak", 0)

    cards_html = (
        f'<div style="margin:16px 0 10px 0;padding:20px 24px;background:#0f172a;border-radius:12px;border:1px solid #1e293b;box-shadow:0 4px 12px rgba(0,0,0,0.25);">'
        f'<div style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px;">'
        f'<span>📊 {act_type} Performance Summary & Streaks</span>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:16px 24px;padding-bottom:18px;border-bottom:1px solid #1e293b;">'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f8fafc;line-height:1.15;letter-spacing:-0.02em;">{stats["all_time_hrs"]:g} {unit}</div><div style="font-size:13px;color:#94a3b8;margin-top:5px;">logged for all time</div></div>'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f8fafc;line-height:1.15;letter-spacing:-0.02em;">{stats["year_hrs"]:g} {unit}</div><div style="font-size:13px;color:#94a3b8;margin-top:5px;">logged in {yr}</div></div>'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f8fafc;line-height:1.15;letter-spacing:-0.02em;">{stats["month_hrs"]:g} {unit}</div><div style="font-size:13px;color:#94a3b8;margin-top:5px;">logged in last 30 days</div></div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:16px 24px;padding-top:16px;">'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f59e0b;line-height:1.15;letter-spacing:-0.02em;display:flex;align-items:center;gap:6px;"><span>🔥 {cur_s}</span> <span style="font-size:16px;color:#e2e8f0;">{"day" if cur_s == 1 else "days"}</span></div><div style="font-size:13px;color:#cbd5e1;margin-top:5px;font-weight:600;">current active streak</div></div>'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f8fafc;line-height:1.15;letter-spacing:-0.02em;">{all_s} {"day" if all_s == 1 else "days"}</div><div style="font-size:13px;color:#94a3b8;margin-top:5px;">in a row max.</div></div>'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f8fafc;line-height:1.15;letter-spacing:-0.02em;">{yr_s} {"day" if yr_s == 1 else "days"}</div><div style="font-size:13px;color:#94a3b8;margin-top:5px;">in a row for {yr}</div></div>'
        f'<div style="display:flex;flex-direction:column;"><div style="font-size:26px;font-weight:700;color:#f8fafc;line-height:1.15;letter-spacing:-0.02em;">{m_s} {"day" if m_s == 1 else "days"}</div><div style="font-size:13px;color:#94a3b8;margin-top:5px;">in a row for last month</div></div>'
        f'</div>'
        f'</div>'
    )
    _render_html(cards_html)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTIVITY CALENDAR HEATMAP (SVG IMPLEMENTATION)
# ══════════════════════════════════════════════════════════════════════════════



def _build_heatmap_grid(df, activity_type, year, today):
    """Build a 7xN_weeks grid for the Plotly heatmap."""
    from datetime import date as date_cls
    if year == "Last 365 Days":
        end_date = today
        start_date = end_date - timedelta(days=364)
    else:
        try:
            sel_yr = int(year)
            start_date = date(sel_yr, 1, 1)
            end_date = min(today, date(sel_yr, 12, 31)) if sel_yr == today.year else date(sel_yr, 12, 31)
        except Exception:
            end_date = today
            start_date = end_date - timedelta(days=364)

    work_df = df.copy() if not df.empty else pd.DataFrame()
    if not work_df.empty:
        if "date_dt" not in work_df.columns:
            work_df["date_dt"] = pd.to_datetime(work_df["date"])
        work_df = work_df[work_df["date_dt"].dt.date <= today]
        if activity_type == "Study":
            f_df = work_df[work_df["type"].isin(["Study", "Study during trip"])].copy()
        elif activity_type == "Revision":
            f_df = work_df[work_df["type"] == "Revision"].copy()
        elif activity_type == "Test":
            f_df = work_df[work_df["type"].isin(["Test", "test"])].copy()
        elif activity_type == "All 3 Combined":
            f_df = work_df[work_df["type"].isin(["Study", "Study during trip", "Revision", "Test", "test"])].copy()
        else:
            f_df = work_df[work_df["type"].isin(PRODUCTIVE_TYPES)].copy()
    else:
        f_df = pd.DataFrame()

    daily_hrs = {}
    daily_details = {}
    if not f_df.empty:
        for d_val, g_val in f_df.groupby("date"):
            d_str = str(d_val)
            daily_hrs[d_str] = float(g_val["duration"].sum())
            subs = [str(s) for s in g_val["subject"].dropna().unique() if str(s).strip()]
            daily_details[d_str] = ", ".join(subs[:3]) if subs else ""

    # Monday-aligned calendar
    cal_start = start_date - timedelta(days=start_date.weekday())
    cal_end   = end_date + timedelta(days=(6 - end_date.weekday()) % 7)

    curr = cal_start
    weeks_data = []
    curr_week = []

    while curr <= cal_end:
        row_idx = curr.weekday()   # 0=Mon ... 6=Sun
        d_str = curr.strftime("%Y-%m-%d")
        in_range = start_date <= curr <= end_date
        is_future = curr > today
        hrs = daily_hrs.get(d_str, 0.0) if (in_range and not is_future) else 0.0
        det = daily_details.get(d_str, "") if in_range else ""
        curr_week.append({
            "date_str": d_str,
            "display": curr.strftime("%d %b %Y"),
            "row": row_idx,
            "hrs": hrs,
            "details": det,
            "in_range": in_range,
            "is_future": is_future,
        })
        if row_idx == 6:
            weeks_data.append(curr_week)
            curr_week = []
        curr += timedelta(days=1)
    if curr_week:
        weeks_data.append(curr_week)

    n_cols = len(weeks_data)
    z_grid    = [[float("nan")] * n_cols for _ in range(7)]
    text_grid = [[""] * n_cols for _ in range(7)]
    month_ticks = {}
    prev_month = None

    for col_idx, wk in enumerate(weeks_data):
        for day in wk:
            row = day["row"]
            if day["in_range"] and not day["is_future"]:
                z_grid[row][col_idx] = day["hrs"]
                det_part = ("\n\u2728 " + day["details"]) if day["details"] else ""
                text_grid[row][col_idx] = (
                    "\U0001f4c5 " + day["display"] + "\n\u23f1 " + f"{day['hrs']:.1f} hrs logged" + det_part
                    if day["hrs"] > 0 else "\U0001f4c5 " + day["display"] + "\n\u2014 No activity"
                )
        # Month label: first in-range day of each new month
        for day in wk:
            if day["in_range"] and not day["is_future"]:
                try:
                    import datetime as _dt
                    m = _dt.datetime.strptime(day["date_str"], "%Y-%m-%d").month
                    if m != prev_month:
                        month_ticks[col_idx] = _dt.datetime.strptime(day["date_str"], "%Y-%m-%d").strftime("%b")
                        prev_month = m
                except Exception:
                    pass
                break

    return z_grid, text_grid, n_cols, list(month_ticks.keys()), list(month_ticks.values()), daily_hrs


def render_github_codeforces_heatmap(df, activity_type="All 3 Combined", year="Last 365 Days"):
    """
    Renders a Codeforces/GitHub-style activity calendar heatmap using Plotly.

    Color themes:
      Study / All Combined -> GitHub green
      Revision             -> Teal/cyan
      Test                 -> Amber/orange

    Layout: 7 rows (Mon-Sun) x 52-53 week columns.
    Stats cards rendered below.
    """
    now   = get_ist_now()
    today = now.date()
    DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    z_grid, text_grid, n_cols, m_tick_vals, m_tick_text, daily_hrs = (
        _build_heatmap_grid(df, activity_type, year, today)
    )

    max_val = max((v for v in daily_hrs.values() if v > 0), default=1.0)

    if activity_type == "Test":
        colorscale = [
            [0.00, "#1e293b"], [0.01, "#451a03"], [0.25, "#92400e"],
            [0.55, "#d97706"], [0.80, "#f59e0b"], [1.00, "#fde68a"],
        ]
        bar_title = "hrs (Test)"
    elif activity_type == "Revision":
        colorscale = [
            [0.00, "#1e293b"], [0.01, "#042f2e"], [0.25, "#0f766e"],
            [0.55, "#14b8a6"], [0.80, "#2dd4bf"], [1.00, "#99f6e4"],
        ]
        bar_title = "hrs (Revision)"
    else:
        # Study / All 3 Combined -> GitHub green
        colorscale = [
            [0.00, "#161b22"], [0.01, "#0e4429"], [0.25, "#006d32"],
            [0.55, "#26a641"], [0.80, "#39d353"], [1.00, "#6bff8a"],
        ]
        bar_title = "hrs (Study)"

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z_grid,
        text=text_grid,
        hovertemplate="%{text}<extra></extra>",
        colorscale=colorscale,
        zmin=0,
        zmax=max_val,
        showscale=True,
        colorbar=dict(
            title=dict(text=bar_title, side="right", font=dict(color="#94a3b8", size=11)),
            thickness=10,
            len=0.6,
            x=1.01,
            tickfont=dict(color="#94a3b8", size=10),
            bgcolor="rgba(0,0,0,0)",
            outlinewidth=0,
        ),
        xgap=2,
        ygap=2,
        name="",
    ))

    fig.update_layout(
        xaxis=dict(
            tickvals=m_tick_vals,
            ticktext=m_tick_text,
            tickfont=dict(color="#94a3b8", size=10),
            showgrid=False,
            zeroline=False,
            tickangle=0,
        ),
        yaxis=dict(
            tickvals=list(range(7)),
            ticktext=DAY_LABELS,
            tickfont=dict(color="#94a3b8", size=10),
            showgrid=False,
            zeroline=False,
            autorange="reversed",
        ),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(family="Inter, system-ui, sans-serif", color="#e2e8f0"),
        margin=dict(l=45, r=60, t=10, b=30),
        height=175,
        dragmode=False,
    )

    chart_key = ("heatmap_" + activity_type + "_" + year).replace(" ", "_")
    st.plotly_chart(fig, use_container_width=True, key=chart_key,
                    config={"displayModeBar": False})

    stats = calculate_cf_stats(df, activity_type=activity_type, year=year)
    render_codeforces_stats_cards(stats, unit="hours")

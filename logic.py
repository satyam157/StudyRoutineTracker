import pandas as pd
from datetime import datetime, timedelta
import re

study_subjects = [
    "Polity","Ancient","Medieval","Modern","Art&Culture","Economics",
    "Physical-Geography","Human-Geography","Environment","Ethics",
    "Sociology","IR","Society","Governance"
]

ent_types = ["Movie","Sports","friendMeetup"]
movie_modes = ["Room","Outside"]
social_platform = ["YouTube","Instagram"]
content_type = ["Stories/Chat","DoomScrolling"]
food_sources = ["Swiggy","Zomato","Outside"]
transport_services = ["Uber","Ola","Rapido"]

test_types = ["Mock Test","Sectional","PYQ"]

PRODUCTIVE_TYPES = ["Study","Revision","Test", "Book Reading", "Answer Writing", "Practice"]
ESSENTIAL_TYPES = ["Coaching", "Office", "WFH"]


def calculate_sleep_hours(sleep_time_str, wakeup_time_str):
    """
    Calculate sleep duration in hours.
    Case 1: Sleep at PM (e.g. 11 PM) -> (24 - sleep_hour) + wakeup_hour
    Case 2: Sleep at AM (e.g. 1 AM) -> wakeup_hour - sleep_hour
    """
    try:
        # Parse Wakeup Time (Morning of the day)
        if not wakeup_time_str or not str(wakeup_time_str).strip():
            return 0
        w_dt = datetime.strptime(str(wakeup_time_str).strip(), "%I:%M %p")
        w_h = w_dt.hour + w_dt.minute / 60.0
        
        # Parse Sleep Time (Night or early morning)
        if not sleep_time_str or not str(sleep_time_str).strip():
            return w_h  # Fallback: assume slept at midnight
            
        s_dt = datetime.strptime(str(sleep_time_str).strip(), "%I:%M %p")
        s_h = s_dt.hour + s_dt.minute / 60.0
        
        if "PM" in str(sleep_time_str).upper():
            # e.g. 11 PM (23.0) to 6 AM (6.0) -> (24 - 23) + 6 = 7.0
            duration = (24 - s_h) + w_h
        else:
            # e.g. 1 AM (1.0) to 6 AM (6.0) -> 6 - 1 = 5.0
            duration = w_h - s_h
            
        return max(0, min(duration, 24))
        
    except Exception:
        return 0

def get_study_color(date_str, hours):
    try:
        dt = pd.to_datetime(date_str)
        is_weekend = dt.weekday() >= 5 # 5=Sat, 6=Sun
    except:
        is_weekend = False

    if hours < 1: return "black"
    
    if is_weekend:
        if hours < 5: return "red"
        elif hours < 8: return "lightblue"
        elif hours < 14: return "green"
        else: return "gold"
    else:
        if hours < 3: return "red"
        elif hours < 6: return "lightblue"
        elif hours < 8: return "green"
        else: return "gold"



def completion_percent(total, done):
    return round((done/total)*100,1) if total>0 else 0


def productivity_score(df: pd.DataFrame, sleep_hours=None, powernap_hours=None):
    """
    Calculate productivity percentage. 
    Formula: (productive_hours / available_hours) * 100
    Where: available_hours = SUM(day_limit) - total_sleep_hours - total_essential_hours
    For past days, day_limit = 24. For current day, day_limit = time passed till now.
    """
    if df.empty: 
        return 0
    
    productive = df[df['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
    essential = df[df['type'].isin(ESSENTIAL_TYPES)]['duration'].sum()
    
    # Get unique dates in the dataframe
    unique_dates = pd.to_datetime(df['date']).unique()
    
    # Current time info
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_hour = now.hour + now.minute / 60.0
    
    total_day_limit = 0
    total_sleep_hours = 0
    
    for date in unique_dates:
        if hasattr(date, 'date'): date_str = str(date.date())
        elif isinstance(date, str): date_str = date
        else: date_str = str(date)[:10]
        
        # Determine day limit
        if date_str == today_str:
            day_limit = current_hour
        else:
            day_limit = 24.0
        
        total_day_limit += day_limit
        
        # Calculate sleep hours for this date
        if sleep_hours is not None:
            if isinstance(sleep_hours, dict):
                total_sleep_hours += sleep_hours.get(date_str, 0)
            elif isinstance(sleep_hours, (int, float)):
                total_sleep_hours += sleep_hours

    # Calculate available hours: (total_day_limit - sleep - essential)
    available_hours = total_day_limit - total_sleep_hours - essential
    
    if available_hours <= 0:
        return 0
    
    return round((productive / available_hours) * 100, 2)


def streak(df: pd.DataFrame):
    try:
        if df.empty:
            return 0

        df = df.sort_values('date', ascending=False)
        count = 0

        # safe iteration (no slicing on groupby)
        grouped = list(df.groupby('date', sort=False))

        for d, g in grouped:
            prod = g[g['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
            if prod > 0:
                count += 1
            else:
                break

        return count

    except Exception as e:
        # suppress error and return safe value
        return 0

# -------- NEW: DAILY REPORT --------
def daily_report(df, sleep_data=None, powernap_data=None):
    """
    Generate daily productivity report.
    Uses time passed till now for the current date.
    
    Args:
        df: DataFrame with activity data
        sleep_data: Optional dict mapping dates to sleep hours
        powernap_data: Optional dict mapping dates to powernap hours
    
    Returns:
        DataFrame with daily report including productivity_% excluding sleep and essential hours
    """
    if df.empty:
        return pd.DataFrame()
    
    if sleep_data is None:
        sleep_data = {}
    if powernap_data is None:
        powernap_data = {}

    report = []
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_hour = now.hour + now.minute / 60.0

    for d, g in df.groupby('date'):
        productive = g[g['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
        essential = g[g['type'].isin(ESSENTIAL_TYPES)]['duration'].sum()
        
        # Get sleep and powernap hours
        date_str = str(d)
        sleep_hours = sleep_data.get(date_str, 0)
        powernap_hours = powernap_data.get(date_str, 0)
        
        # Determine day limit: current hour if today, else 24
        day_limit = current_hour if date_str == today_str else 24.0
        
        # Calculate available hours: day_limit - sleep - essential
        available_hours = day_limit - sleep_hours - essential
        
        # Waste is everything that is NOT productive, NOT essential, and NOT sleep up to day_limit.
        waste = max(0, day_limit - sleep_hours - essential - productive)
        
        # Calculate productivity score
        if available_hours > 0:
            score = round((productive / available_hours) * 100, 2)
            waste_score = round((waste / available_hours) * 100, 2)
        else:
            score = 0
            waste_score = 0

        report.append({
            "date": d,
            "productivity_%": score,
            "waste_%": waste_score,
            "productive_hours": round(productive, 2),
            "waste_hours": round(waste, 2),
            "essential_hours": round(essential, 2),
            "sleep_hours": round(sleep_hours, 2),
            "powernap": round(powernap_hours, 2),
            "day_limit": round(day_limit, 2) # helpful for debugging
        })

    return pd.DataFrame(report)


# -------- NEW: FOCUS SCORE --------
def focus_score(df):
    if df.empty:
        return 0

    # deep work = sessions >= 2 hours
    deep_work = df[(df['type'].isin(PRODUCTIVE_TYPES)) & (df['duration'] >= 2)]['duration'].sum()
    total = df[df['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()

    return round((deep_work/total)*100,2) if total>0 else 0

# -------- NEW: TIME OF DAY ANALYSIS --------
def extract_time_of_day(chapter_str):
    """Extract hour from chapter string like 'Chapter 5 [14:30]' or just return None"""
    try:
        if not chapter_str:
            return None
        chapter_str = str(chapter_str)
        if '[' in chapter_str and ']' in chapter_str:
            time_part = chapter_str.split('[')[1].split(']')[0]
            hour = int(time_part.split(':')[0])
            return hour
        return None
    except:
        return None

def extract_hour_from_row(row):
    """
    Enhanced hour extraction:
    1. Check 'start_time' column if it exists and has 'HH:MM'
    2. Fallback to extracting from 'chapter' string brackets '[HH:MM]'
    """
    if 'start_time' in row and row['start_time'] and ':' in str(row['start_time']):
        try:
            return int(str(row['start_time']).split(':')[0])
        except:
            pass
    return extract_time_of_day(row.get('chapter'))

def get_clean_chapter(ch):
    """Remove timestamp suffix like ' [14:30]' and strip whitespace."""
    if not ch: return ""
    s = str(ch)
    if ' [' in s:
        return s.split(' [')[0].strip()
    # Catch cases where it might only be a timestamp
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        return ""
    return s


def is_numeric_entry(ch_val):
    """Check if the chapter value is a numeric progress entry like 'Pages: 50' or just '50'."""
    if not ch_val:
        return False
    # Matches with or without prefix
    return bool(re.match(r'^(?:Pages:|Pg:|Q:|Ch:)?\s*\d+', str(ch_val).strip(), re.IGNORECASE))


def parse_numeric(ch_val):
    """Extract integer from 'Pages: 50', 'Q:25', or just '50'."""
    if not ch_val:
        return None
    # Matches with or without prefix
    m = re.match(r'^(?:Pages:|Pg:|Q:|Ch:)?\s*(\d+)', str(ch_val).strip(), re.IGNORECASE)
    return int(m.group(1)) if m else None

def classify_time_period(hour):
    """Classify hour into time period (0-23 hour format)"""
    if hour is None:
        return "Unknown"
    if 6 <= hour < 12:
        return "Morning (6-12)"
    elif 12 <= hour < 17:
        return "Afternoon (12-5 PM)"
    elif 17 <= hour < 21:
        return "Evening (5-9 PM)"
    else:  # 21-6
        return "Night (9 PM-6 AM)"

def extract_float_hour(row):
    """Extract hour and minute as a float (e.g., 14:30 -> 14.5)"""
    # 1. Check start_time column
    st = row.get('start_time')
    if st and ':' in str(st):
        try:
            parts = str(st).split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return h + m/60.0
        except:
            pass
    
    # 2. Check chapter brackets [HH:MM]
    ch = row.get('chapter')
    if ch and '[' in str(ch) and ']' in str(ch):
        try:
            time_part = str(ch).split('[')[1].split(']')[0]
            parts = time_part.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return h + m/60.0
        except:
            pass
    return None

def get_sleep_intervals(sleep_time_str, wakeup_time_str):
    """
    Returns list of (start_float, end_float) intervals for sleep.
    Handles midnight crossing by splitting into two if necessary.
    """
    try:
        if not wakeup_time_str or not str(wakeup_time_str).strip():
            return []
        w_dt = datetime.strptime(str(wakeup_time_str).strip(), "%I:%M %p")
        w_h = w_dt.hour + w_dt.minute / 60.0
        
        if not sleep_time_str or not str(sleep_time_str).strip():
            return [(0, w_h)] # Assume sleep from midnight to wakeup
            
        s_dt = datetime.strptime(str(sleep_time_str).strip(), "%I:%M %p")
        s_h = s_dt.hour + s_dt.minute / 60.0
        
        if "PM" in str(sleep_time_str).upper():
            # e.g. 11 PM (23.0) to 6 AM (6.0)
            # This spans across midnight. Since we analyze day-by-day:
            # On 'today' (the day user woke up), sleep was 00:00 to 06:00
            # On 'yesterday', sleep started at 23:00 and goes to 24:00
            # For a single day's 24h analysis, 'Sleep' is usually the morning part.
            return [(0, w_h)]
        else:
            # e.g. 1 AM (1.0) to 6 AM (6.0)
            return [(s_h, w_h)]
    except:
        return []

def distribute_duration_across_hours(df, denom_days=1, sleep_intervals_list=None):
    """
    Distributes duration of each activity across the hours it spans.
    Returns 5 arrays of size 24 (prod, waste, essential, sleep, slot_caps).
    
    NEW: If time is not logged as Prod, Ess, or Sleep, it is added to Waste.
    Slot caps are adjusted for the current day.
    """
    prod_hrs = [0.0] * 24
    waste_hrs = [0.0] * 24
    essential_hrs = [0.0] * 24
    sleep_hrs = [0.0] * 24
    total_hrs_logged = [0.0] * 24
    
    # 1. Mark Sleep intervals
    if sleep_intervals_list:
        for start_f, end_f in sleep_intervals_list:
            curr = start_f
            rem = end_f - start_f
            while rem > 0 and curr < 24:
                idx = int(curr)
                space = (idx+1) - curr
                fill = min(rem, space)
                sleep_hrs[idx] += fill
                curr += fill
                rem -= fill

    # 2. Mark activities
    for _, row in df.iterrows():
        start_f = extract_float_hour(row)
        if start_f is None:
            continue
            
        duration = float(row.get('duration', 0))
        if duration <= 0:
            continue
            
        is_prod = row['type'] in PRODUCTIVE_TYPES
        is_essential = row['type'] in ESSENTIAL_TYPES
        
        remaining = duration
        current_time = start_f
        
        while remaining > 0 and current_time < 24:
            hour_idx = int(current_time)
            space_in_slot = (hour_idx + 1) - current_time
            to_fill = min(remaining, space_in_slot)
            
            if is_prod:
                prod_hrs[hour_idx] += to_fill
            elif is_essential:
                essential_hrs[hour_idx] += to_fill
            else:
                # Logged waste (e.g. Entertainment)
                waste_hrs[hour_idx] += to_fill
            
            total_hrs_logged[hour_idx] += to_fill
            
            remaining -= to_fill
            current_time += to_fill

    # 3. Calculate slot caps and fill gaps as Waste (Unlogged time)
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_hour_f = now.hour + now.minute / 60.0
    
    unique_date_strs = []
    if not df.empty:
        unique_dates = pd.to_datetime(df['date']).unique()
        unique_date_strs = [str(d.date()) if hasattr(d, 'date') else str(d)[:10] for d in unique_dates]
    
    slot_caps = [0.0] * 24
    final_waste_hrs = [0.0] * 24
    
    for h in range(24):
        current_slot_cap = 0.0
        if not unique_date_strs:
            # Fallback if no dates in df
            current_slot_cap = float(denom_days)
        else:
            for d_str in unique_date_strs:
                if d_str == today_str:
                    if h < int(current_hour_f):
                        current_slot_cap += 1.0
                    elif h == int(current_hour_f):
                        current_slot_cap += (current_hour_f - h)
                else:
                    current_slot_cap += 1.0
        
        slot_caps[h] = current_slot_cap
        
        # Fill gaps as waste
        filled = prod_hrs[h] + essential_hrs[h] + waste_hrs[h] + sleep_hrs[h]
        unlogged = max(0, current_slot_cap - filled)
        final_waste_hrs[h] = (waste_hrs[h] + unlogged)
        
    return prod_hrs, final_waste_hrs, essential_hrs, sleep_hrs, slot_caps

def time_of_day_analysis(df):
    """
    Analyze productivity by time of day.
    Returns DataFrame with productive/waste hours for each time period.
    """
    if df.empty:
        return pd.DataFrame()
    
    report = []
    df_copy = df.copy()
    
    # Extract hours from start_time column or chapter brackets
    df_copy['hour'] = df_copy.apply(extract_hour_from_row, axis=1)
    df_copy['time_period'] = df_copy['hour'].apply(classify_time_period)
    
    # Group by time period
    for period in ["Morning (6-12)", "Afternoon (12-5 PM)", "Evening (5-9 PM)", "Night (9 PM-6 AM)"]:
        period_data = df_copy[df_copy['time_period'] == period]
        
        if not period_data.empty:
            productive = period_data[period_data['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
            waste = period_data[~period_data['type'].isin(PRODUCTIVE_TYPES + ESSENTIAL_TYPES)]['duration'].sum()
            total = period_data['duration'].sum()
            
            if total > 0:
                prod_percent = round((productive / total) * 100, 1)
            else:
                prod_percent = 0
            
            report.append({
                "time_period": period,
                "productive_hours": round(productive, 1),
                "waste_hours": round(waste, 1),
                "total_hours": round(total, 1),
                "productivity_%": prod_percent
            })
    
    if not report:
        return pd.DataFrame()
    
    return pd.DataFrame(report)


def time_of_day_analysis_24h(df, sleep_intervals=None):
    """
    Analyze productivity by hour of day (24-hour granularity) for a single date.
    Returns DataFrame with percentage-based metrics.
    """
    if df.empty and not sleep_intervals:
        return pd.DataFrame()
    
    prod_hrs, waste_hrs, essential_hrs, sleep_hrs, slot_caps = distribute_duration_across_hours(df, denom_days=1, sleep_intervals_list=sleep_intervals)
    
    report = []
    for hour in range(24):
        # For a single day, the denominator for % is slot_caps[hour] (usually 1.0 or fraction if today)
        cap = slot_caps[hour]
        
        if cap > 0:
            # Ensure we cap values at the slot limit for % calculation in case of overlaps
            p_val = min(cap, prod_hrs[hour])
            w_val = min(cap, waste_hrs[hour])
            
            p_pct = round((p_val / cap) * 100, 1)
            w_pct = round((w_val / cap) * 100, 1)
        else:
            p_pct = 0.0
            w_pct = 0.0
        
        report.append({
            "hour": f"{hour:02d}:00",
            "hour_num": hour,
            "productive_hours": round(prod_hrs[hour], 2),
            "waste_hours": round(waste_hrs[hour], 2),
            "essential_hours": round(essential_hrs[hour], 2),
            "productivity_%": p_pct,
            "waste_%": w_pct
        })
    
    return pd.DataFrame(report)


def time_of_day_analysis_cumulative_24h(df, filter_month=None, all_sleep_intervals=None):
    """
    Analyze productivity by hour of day across multiple dates.
    Returns DataFrame with average percentage-based metrics per day.
    """
    if df.empty:
        return pd.DataFrame()
    
    analysis_df = df.copy()
    if filter_month:
        analysis_df['month_str'] = pd.to_datetime(analysis_df['date']).dt.strftime('%Y-%m')
        analysis_df = analysis_df[analysis_df['month_str'] == filter_month]
        
    if analysis_df.empty:
        return pd.DataFrame()
    
    unique_dates_count = pd.to_datetime(analysis_df['date']).nunique()
    if unique_dates_count == 0:
        unique_dates_count = 1
        
    prod_hrs, waste_hrs, essential_hrs, sleep_hrs, slot_caps = distribute_duration_across_hours(analysis_df, denom_days=unique_dates_count, sleep_intervals_list=all_sleep_intervals)
    
    report = []
    for hour in range(24):
        cap = slot_caps[hour]
        
        # average hours per day in this slot
        if cap > 0:
            p_avg = min(1.0, prod_hrs[hour] / cap)
            w_avg = min(1.0, waste_hrs[hour] / cap)
            e_avg = min(1.0, essential_hrs[hour] / cap)
            s_avg = min(1.0, sleep_hrs[hour] / cap)
            p_pct = round(p_avg * 100, 1)
            w_pct = round(w_avg * 100, 1)
        else:
            p_avg = w_avg = e_avg = s_avg = p_pct = w_pct = 0.0
        
        report.append({
            "hour": f"{hour:02d}:00",
            "hour_num": hour,
            "productive_hours": round(prod_hrs[hour], 2),
            "waste_hours": round(waste_hrs[hour], 2),
            "essential_hours": round(essential_hrs[hour], 2),
            "sleep_hours": round(sleep_hrs[hour], 2),
            "avg_productive_h": round(p_avg, 2),
            "productivity_%": p_pct,
            "waste_%": w_pct,
            "total_hours": round((prod_hrs[hour] + waste_hrs[hour] + essential_hrs[hour] + sleep_hrs[hour]), 2)
        })
    
    return pd.DataFrame(report)

# -------- NEW: ADVANCED ANALYTICS --------

def calculate_top_streaks(df: pd.DataFrame, year=None, month=None):
    """
    Calculate top 5 longest streaks within a given month or year.
    A streak is a series of consecutive days with productive hours > 0.
    """
    if df.empty:
        return []

    temp_df = df.copy()
    temp_df['date_dt'] = pd.to_datetime(temp_df['date'])
    
    if year:
        temp_df = temp_df[temp_df['date_dt'].dt.year == year]
    if month:
        temp_df = temp_df[temp_df['date_dt'].dt.month == month]
    
    if temp_df.empty:
        return []

    # Get daily productive hours
    daily_prod = temp_df.groupby('date_dt').apply(
        lambda g: g[g['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
    ).reset_index(name='prod_hrs')
    daily_prod = daily_prod.sort_values('date_dt')

    # Find all days in the range to account for gaps
    if not daily_prod.empty:
        all_days = pd.date_range(start=daily_prod['date_dt'].min(), end=daily_prod['date_dt'].max())
        daily_prod = daily_prod.set_index('date_dt').reindex(all_days, fill_value=0).reset_index()
        daily_prod.columns = ['date_dt', 'prod_hrs']

    streaks = []
    current_streak = 0
    start_date = None

    for _, row in daily_prod.iterrows():
        if row['prod_hrs'] > 0:
            if current_streak == 0:
                start_date = row['date_dt']
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append({
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': (row['date_dt'] - timedelta(days=1)).strftime('%Y-%m-%d'),
                    'length': current_streak
                })
                current_streak = 0
    
    # Check if last day was part of a streak
    if current_streak > 0:
        streaks.append({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': daily_prod.iloc[-1]['date_dt'].strftime('%Y-%m-%d'),
            'length': current_streak
        })

    # Sort streaks by length descending and take top 5
    streaks.sort(key=lambda x: x['length'], reverse=True)
    return streaks[:5]


def get_top_hours_all_time(df: pd.DataFrame, type='productive'):
    """Find top 5 hours (0-23) with highest aggregate productive or waste time."""
    if df.empty:
        return []
    
    prod_hrs, waste_hrs, _, _, _ = distribute_duration_across_hours(df)
    target_hrs = prod_hrs if type == 'productive' else waste_hrs
    
    hourly_stats = []
    for h in range(24):
        if target_hrs[h] > 0:
            hourly_stats.append({
                'hour': h,
                'time': f"{h:02d}:00",
                'duration': round(target_hrs[h], 2)
            })
    
    hourly_stats.sort(key=lambda x: x['duration'], reverse=True)
    return hourly_stats[:5]


def get_top_study_days(df: pd.DataFrame, year=None, month=None, is_weekend=None):
    """
    Find top 5 days with most study time.
    Separable by weekend/weekday.
    Returns day, hours, and what was read.
    """
    if df.empty:
        return pd.DataFrame()

    temp_df = df.copy()
    temp_df['date_dt'] = pd.to_datetime(temp_df['date'])
    
    if year:
        temp_df = temp_df[temp_df['date_dt'].dt.year == year]
    if month:
        temp_df = temp_df[temp_df['date_dt'].dt.month == month]
    
    if is_weekend is not None:
        if is_weekend:
            # Saturday=5, Sunday=6
            temp_df = temp_df[temp_df['date_dt'].dt.weekday >= 5]
        else:
            # Mon-Fri are 0-4
            temp_df = temp_df[temp_df['date_dt'].dt.weekday < 5]
            
    if temp_df.empty:
        return pd.DataFrame()

    results = []
    # Sort by date for clean grouping
    for d, g in temp_df.groupby('date'):
        prod_g = g[g['type'].isin(PRODUCTIVE_TYPES)]
        total_hrs = prod_g['duration'].sum()
        
        if total_hrs > 0:
            # Consolidate what was read
            reading_summary = []
            for _, row in prod_g.iterrows():
                parts = []
                if row['subject']: parts.append(str(row['subject']))
                ch_clean = get_clean_chapter(row['chapter'])
                if ch_clean: parts.append(ch_clean)
                if parts:
                    reading_summary.append(" - ".join(parts))
            
            # Unique entries to avoid duplicates
            summary_str = "; ".join(list(dict.fromkeys(reading_summary)))
            
            # Determine if it's weekend or weekday for labeling
            day_dt = pd.to_datetime(d)
            category = "Weekend" if day_dt.weekday() >= 5 else "Weekday"
            
            results.append({
                'date': d,
                'day_name': day_dt.strftime('%A'),
                'category': category,
                'hours': round(total_hrs, 2),
                'readings': summary_str
            })

    report_df = pd.DataFrame(results)
    if not report_df.empty:
        report_df = report_df.sort_values('hours', ascending=False).head(5)
    
    return report_df


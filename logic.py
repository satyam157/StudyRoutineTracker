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
NEUTRAL_TYPES = ["Sleep", "Powernap", "Napping"]


def calculate_sleep_hours(sleep_time_str, wakeup_time_str):
    """
    Calculate sleep duration in hours.
    Case 1: Sleep at PM (e.g. 11 PM) -> (24 - sleep_hour) + wakeup_hour
    Case 2: Sleep at AM (e.g. 1 AM) -> wakeup_hour - sleep_hour
    """
    def _parse(t_str):
        if not t_str or not str(t_str).strip():
            return None
        s = str(t_str).strip().upper()
        # Handle '0:35 AM' -> '12:35 AM' because %I (12-hr) expects 1-12
        if s.startswith("0:"):
            s = "12:" + s[2:]
        return datetime.strptime(s, "%I:%M %p")

    try:
        # Parse Wakeup Time (Morning of the day)
        w_dt = _parse(wakeup_time_str)
        if not w_dt:
            return 0
        w_h = w_dt.hour + w_dt.minute / 60.0
        
        # Parse Sleep Time (Night or early morning)
        s_dt = _parse(sleep_time_str)
        if not s_dt:
            return w_h  # Fallback: assume slept at midnight
            
        s_h = s_dt.hour + s_dt.minute / 60.0
        
        if "PM" in str(sleep_time_str).upper():
            # e.g. 11 PM (23.0) to 6 AM (6.0) -> (24 - 23) + 6 = 7.0
            duration = (24 - s_h) + w_h
        else:
            # e.g. 1 AM (1.0) to 6 AM (6.0) -> 6 - 1 = 5.0
            # or 12:30 AM (0.5) to 6 AM (6.0) -> 6 - 0.5 = 5.5
            if s_h > w_h: # Slept at say 11 AM and woke at 6 AM? (Unlikely but handle)
                 duration = (24 - s_h) + w_h
            else:
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
    neutral = df[df['type'].isin(NEUTRAL_TYPES)]['duration'].sum()
    
    # Get unique dates in the dataframe
    unique_dates = pd.to_datetime(df['date']).unique()
    
    # Current time info
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_hour = now.hour + now.minute / 60.0
    
    total_day_limit = 0
    total_sleep_hours = 0
    total_powernap_hours = 0
    
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

        # Calculate powernap hours for this date
        if powernap_hours is not None:
            if isinstance(powernap_hours, dict):
                total_powernap_hours += powernap_hours.get(date_str, 0)
            elif isinstance(powernap_hours, (int, float)):
                total_powernap_hours += powernap_hours

    # Previous Logic: available_hours = (total_day_limit - sleep - essential)
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
        neutral = g[g['type'].isin(NEUTRAL_TYPES)]['duration'].sum()
        
        # Get sleep and powernap hours
        date_str = str(d)
        sleep_hours = sleep_data.get(date_str, 0)
        powernap_hours = powernap_data.get(date_str, 0)
        
        # Determine day limit: current hour if today, else 24
        day_limit = current_hour if date_str == today_str else 24.0
        
        # Previous logic for scores: available = day_limit - sleep - essential
        available_for_score = day_limit - sleep_hours - essential
        
        # New logic for waste hours: calculated strictly as (day_limit - sleep - essential - productive)
        waste = max(0, day_limit - sleep_hours - essential - productive)
        
        # Calculate productivity score based on PREVIOUS logic
        if available_for_score > 0:
            score = round((productive / available_for_score) * 100, 2)
            waste_score = round((waste / available_for_score) * 100, 2)
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

    return pd.DataFrame(report).sort_values('date', ascending=False)


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
    def _parse(t_str):
        if not t_str or not str(t_str).strip():
            return None
        s = str(t_str).strip().upper()
        if s.startswith("0:"):
            s = "12:" + s[2:]
        try:
            return datetime.strptime(s, "%I:%M %p")
        except:
            return None

    try:
        w_dt = _parse(wakeup_time_str)
        if not w_dt:
            return []
        w_h = w_dt.hour + w_dt.minute / 60.0
        
        s_dt = _parse(sleep_time_str)
        if not s_dt:
            return [(0, w_h)] # Assume sleep from midnight to wakeup
            
        s_h = s_dt.hour + s_dt.minute / 60.0
        
        if "PM" in str(sleep_time_str).upper():
            # e.g. 11 PM (23.0) to 6 AM (6.0)
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
        is_neutral = row['type'] in NEUTRAL_TYPES
        
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
                # Logged waste and neutral go to waste
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
        cap = slot_caps[hour]
        
        # Calculate available time for this hour (excluding sleep and essential)
        available_for_hour = max(0.0, cap - sleep_hrs[hour] - essential_hrs[hour])
        
        if available_for_hour > 0:
            p_val_capped = min(available_for_hour, prod_hrs[hour])
            w_val_capped = min(available_for_hour, waste_hrs[hour])
            
            p_pct = round((p_val_capped / available_for_hour) * 100, 1)
            w_pct = round((w_val_capped / available_for_hour) * 100, 1)
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
        
        # calculate available time across all days for this slot
        available_for_hour = max(0.0, cap - sleep_hrs[hour] - essential_hrs[hour])
        
        if available_for_hour > 0:
            p_val_capped = min(available_for_hour, prod_hrs[hour])
            w_val_capped = min(available_for_hour, waste_hrs[hour])
            
            p_pct = round((p_val_capped / available_for_hour) * 100, 1)
            w_pct = round((w_val_capped / available_for_hour) * 100, 1)
        else:
            p_pct = 0.0
            w_pct = 0.0
            
        if cap > 0:
            p_avg = min(1.0, prod_hrs[hour] / cap)
            w_avg = min(1.0, waste_hrs[hour] / cap)
            e_avg = min(1.0, essential_hrs[hour] / cap)
            s_avg = min(1.0, sleep_hrs[hour] / cap)
        else:
            p_avg = w_avg = e_avg = s_avg = 0.0
        
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
    Calculate top 10 longest streaks within a given month or year.
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

    # Sort streaks by length descending and take top 10
    streaks.sort(key=lambda x: x['length'], reverse=True)
    top_streaks = streaks[:10]
    
    # Sort the top 10 by end_date descending (latest first)
    top_streaks.sort(key=lambda x: x['end_date'], reverse=True)
    return top_streaks


def get_top_hours_all_time(df: pd.DataFrame, type='productive'):
    """Find top 10 hours (0-23) with highest aggregate productive or waste time."""
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
    return hourly_stats[:10]


def get_top_study_days(df: pd.DataFrame, year=None, month=None, is_weekend=None):
    """
    Find top 10 days with most study time.
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
        report_df = report_df.sort_values('hours', ascending=False).head(10)
        report_df = report_df.sort_values('date', ascending=False)
    
    return report_df


# ════════════════════════════════════════════════════════════════════════
# SMART WORK TIPS ENGINE — Data-driven, no AI calls needed
# ════════════════════════════════════════════════════════════════════════

def generate_smart_work_tips(prod_hours=0, waste_hours=0, essential_hours=0,
                              study_streak=0, focus_pct=0, subject_count=0,
                              productivity_pct=0, context="general"):
    """
    Generate contextual smart work tips based on user's actual data.
    
    Args:
        prod_hours: Total productive study hours
        waste_hours: Total waste hours
        essential_hours: Total essential (work/coaching) hours
        study_streak: Current study streak in days
        focus_pct: Focus score (% of deep work sessions ≥ 2h)
        subject_count: Number of subjects studied
        productivity_pct: Overall productivity percentage
        context: 'productivity' | 'target' | 'ask_esu' | 'general'
    
    Returns:
        List of tip dicts: [{icon, category, tip, priority}]
    """
    tips = []
    
    # ── TECHNIQUE TIPS (always useful) ──
    core_techniques = [
        {"icon": "🍅", "category": "Pomodoro Technique",
         "tip": "**25 min focus → 5 min break → repeat 4x → 30 min long break.** Best for subjects you find boring. Use a physical timer to avoid phone distraction."},
        {"icon": "🧠", "category": "Active Recall",
         "tip": "**Close the book and write everything you remember.** Then check what you missed. This builds 3x stronger memory than passive reading."},
        {"icon": "📆", "category": "Spaced Repetition",
         "tip": "**Revise on Day 1 → Day 3 → Day 7 → Day 21 → Day 45.** Mark revision dates in your calendar. Without this, you'll forget 80% within a week."},
        {"icon": "🎯", "category": "Eat The Frog",
         "tip": "**Do your hardest/most boring subject FIRST in the morning** when willpower is highest. Save easier subjects for evening when energy dips."},
        {"icon": "📝", "category": "Feynman Technique",
         "tip": "**Explain the topic as if teaching a 10-year-old.** Where you struggle to simplify = where you don't truly understand. Go back and study those gaps."},
    ]
    
    # ── DATA-DRIVEN TIPS ──
    
    # Waste time analysis
    if waste_hours > 0:
        daily_waste = waste_hours  # Assume this is per-period
        if daily_waste > 3:
            tips.append({"icon": "🚫", "category": "Waste Recovery",
                "tip": f"**You have {waste_hours:.0f}h of waste time.** Use the '2-Minute Rule': if tempted by distraction, tell yourself 'just 2 more minutes of study.' Your brain usually forgets the distraction. Install app blockers during study hours.",
                "priority": 1})
        elif daily_waste > 1:
            tips.append({"icon": "⏰", "category": "Time Boxing",
                "tip": f"**{waste_hours:.0f}h waste is recoverable.** Schedule specific 'guilt-free' leisure slots (e.g., 7-8 PM). Outside those slots, phone stays in another room. This eliminates 60-70% of casual waste.",
                "priority": 2})
    
    # Focus score tips
    if focus_pct < 30:
        tips.append({"icon": "🔬", "category": "Deep Work",
            "tip": "**Your deep work sessions (≥2h unbroken) are low.** Try 'Cave Mode': pick one subject, set a 2-hour timer, put phone in airplane mode, and work in complete silence. Even 1 deep session/day transforms results.",
            "priority": 1})
    elif focus_pct > 60:
        tips.append({"icon": "💪", "category": "Deep Work Master",
            "tip": f"**Your focus score is {focus_pct:.0f}% — excellent.** Protect your peak focus hours. Consider adding interleaving: switch between 2 related subjects within a deep session to strengthen cross-connections.",
            "priority": 3})
    
    # Study streak tips
    if study_streak == 0:
        tips.append({"icon": "🔥", "category": "Start a Streak",
            "tip": "**Study even 30 minutes today to start a streak.** Consistency > intensity. A 30-day streak of 3h/day beats sporadic 10h marathon sessions. The brain needs daily repetition to form neural pathways.",
            "priority": 1})
    elif study_streak >= 7:
        tips.append({"icon": "🔥", "category": "Streak Power",
            "tip": f"**{study_streak}-day streak! 🔥** You've built momentum. Now add 'Progressive Overload': increase daily hours by 15 minutes every week. Small increments compound into massive results.",
            "priority": 3})
    
    # Productivity tips
    if productivity_pct > 0:
        if productivity_pct < 30:
            tips.append({"icon": "📊", "category": "Productivity Boost",
                "tip": f"**{productivity_pct:.0f}% productivity — room for growth.** Use the 'MIT Method': identify your 3 Most Important Tasks each morning. Complete those BEFORE anything else. Even finishing 2/3 MITs will double your output.",
                "priority": 1})
        elif productivity_pct > 60:
            tips.append({"icon": "🏆", "category": "High Performer",
                "tip": f"**{productivity_pct:.0f}% productivity — strong!** Now optimize quality: for every 2 hours of new learning, spend 30 min on revision. The 80/20 rule: 20% of topics account for 80% of exam marks — focus there.",
                "priority": 3})
    
    # Work-life balance tips (if essential hours exist)
    if essential_hours > 0:
        tips.append({"icon": "⚖️", "category": "Work + Study Balance",
            "tip": f"**You have {essential_hours:.0f}h of work/coaching.** Use 'Sandwich Technique': study 1h BEFORE work (peak brain), then 2-3h AFTER work. During lunch break, do 15-min flashcard revision. Commute = podcast/audio notes.",
            "priority": 2})
    
    # Subject count tips
    if subject_count > 5:
        tips.append({"icon": "🔄", "category": "Subject Rotation",
            "tip": f"**{subject_count} subjects — use a 3-day rotation.** Day 1: 3 subjects (2 hard + 1 easy). Day 2: next 3 subjects. Day 3: remaining + revision of Day 1. This ensures every subject gets attention weekly.",
            "priority": 2})
    
    # ── CONTEXT-SPECIFIC TIPS ──
    if context == "productivity":
        tips.append({"icon": "📈", "category": "Energy Management",
            "tip": "**Track energy, not just time.** Your brain has 2-3 peak hours/day (usually 9-11 AM or 2-4 PM). Use these for hardest subjects. Reserve low-energy slots for revision, notes, or current affairs.",
            "priority": 2})
        tips.append({"icon": "😴", "category": "Sleep = Memory",
            "tip": "**7-8 hours sleep is non-negotiable.** During deep sleep, your brain consolidates everything studied that day. Cutting sleep to study more actually REDUCES what you retain. Sleep before midnight for best quality.",
            "priority": 2})
    
    elif context == "target":
        tips.append({"icon": "🎯", "category": "Target Acceleration",
            "tip": "**Falling behind? Use 'Sprint Weeks.'** Pick the target closest to deadline, block 4-5h/day for just that subject for 5 days. Intense focused bursts are more effective than slow, scattered effort.",
            "priority": 2})
        tips.append({"icon": "✅", "category": "Micro-Goals",
            "tip": "**Break each target into daily micro-goals.** Instead of 'Complete 10 chapters in 30 days,' set 'Finish Chapter 5, pages 45-80 today.' Specific = actionable = achievable.",
            "priority": 2})
    
    elif context == "ask_esu":
        tips.append({"icon": "🗞️", "category": "Current Affairs Strategy",
            "tip": "**30 min daily: The Hindu/Indian Express.** Don't just read — link every news item to a GS paper. Environment → GS3, Policy → GS2, History connection → GS1. Make a 1-line note for each. Monthly compilation = revision-ready.",
            "priority": 2})
        tips.append({"icon": "✍️", "category": "Answer Writing",
            "tip": "**Write 2 answers daily from Day 1.** Use UPSC structure: Intro (2 lines) → Body (points + examples) → Conclusion (way forward). Even bad answers improve fast with daily practice. Get them evaluated weekly.",
            "priority": 2})
    
    # Always add core techniques
    for i, t in enumerate(core_techniques):
        t["priority"] = 4 + i  # Lower priority than data-driven tips
        tips.append(t)
    
    # Sort by priority (lower = more relevant)
    tips.sort(key=lambda x: x.get("priority", 99))
    
    return tips


def render_smart_work_section(tips, max_tips=6):
    """
    Returns HTML for rendering the smart work tips section in Streamlit.
    Call with st.markdown(html, unsafe_allow_html=True)
    
    Args:
        tips: List of tip dicts from generate_smart_work_tips()
        max_tips: Max number of tips to show
    """
    if not tips:
        return ""
    
    display_tips = tips[:max_tips]
    
    # Build cards HTML
    cards_html = ""
    for t in display_tips:
        cards_html += f"""
        <div style="
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155; border-radius: 14px;
            padding: 16px 20px; margin-bottom: 10px;
            border-left: 4px solid #8b5cf6;
            transition: transform 0.2s ease, border-color 0.2s ease;
        ">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="font-size: 20px;">{t['icon']}</span>
                <span style="font-size: 13px; font-weight: 700; color: #a78bfa; text-transform: uppercase; letter-spacing: 0.5px;">
                    {t['category']}
                </span>
            </div>
            <div style="font-size: 14px; color: #e2e8f0; line-height: 1.6;">
                {t['tip']}
            </div>
        </div>
        """
    
    html = f"""
    <div style="
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%);
        padding: 20px 22px 10px 22px; border-radius: 16px;
        border: 1px solid #4f46e5; margin: 20px 0;
        box-shadow: 0 8px 32px rgba(79, 70, 229, 0.15);
    ">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
            <span style="font-size: 26px;">⚡</span>
            <h3 style="margin: 0; color: #e0e7ff; font-weight: 800; letter-spacing: -0.3px;">Smart Work Tips</h3>
            <span style="font-size: 12px; color: #818cf8; background: rgba(129,140,248,0.15); padding: 3px 10px; border-radius: 20px; font-weight: 600;">
                Based on your data
            </span>
        </div>
        {cards_html}
    </div>
    """
    return html


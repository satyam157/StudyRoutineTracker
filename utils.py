import os
import streamlit as st
import re
import glob
import pandas as pd
import database
supabase_client = database.supabase_client
STORAGE_BUCKET = database.STORAGE_BUCKET
get_allowed_recipients = database.get_allowed_recipients
set_allowed_recipients = database.set_allowed_recipients
get_user_config = database.get_user_config
update_user_config = database.update_user_config


def read_sql(query, params=None):
    """Execute a SELECT query via the psycopg2 cursor and return a pandas DataFrame.
    Avoids the UserWarning pandas raises when a raw DBAPI2 connection is passed.
    On failure, retries with a fresh throw-away connection (never crashes on lost connection)."""
    import time as _t
    database.ensure_connection()
    conn = database.conn

    try:
        if conn is None or getattr(conn, 'closed', 1) != 0:
            raise Exception("Connection unavailable")
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        # Retry with a fresh independent connection so we never crash on a dead conn
        try:
            tmp_conn, tmp_cur = database.get_fresh_cursor()
            if tmp_conn is None or tmp_cur is None:
                return pd.DataFrame()
            tmp_cur.execute(query, params)
            rows = tmp_cur.fetchall()
            cols = [desc[0] for desc in tmp_cur.description]
            tmp_cur.close()
            tmp_conn.close()
            return pd.DataFrame(rows, columns=cols)
        except Exception as e2:
            print(f"read_sql retry failed: {e2}")
            return pd.DataFrame()


def get_activities_df(user, force_refresh=False):
    """Return the full activities DataFrame for the user, cached in session_state for 60s.
    Raw data — caller must apply start_time/chapter preprocessing if needed.
    Call invalidate_activities_cache(user) after any write to the activities table."""
    import time as _t
    _cache_key = f"_act_df_{user}"
    _ts_key = f"_act_df_ts_{user}"
    now = _t.time()
    is_stale = (now - st.session_state.get(_ts_key, 0)) > 60
    if force_refresh or _cache_key not in st.session_state or is_stale:
        df = read_sql("SELECT * FROM activities WHERE username=%s", (user,))
        st.session_state[_cache_key] = df
        st.session_state[_ts_key] = now
    return st.session_state[_cache_key].copy()


def invalidate_activities_cache(user):
    """Invalidate the activities cache so the next get_activities_df call re-queries the DB.
    Call this after any INSERT / UPDATE / DELETE on the activities table."""
    st.session_state.pop(f"_act_df_ts_{user}", None)

def get_user_subjects(user):
    """Return the user-specific subject list from user_subjects table.
    On first call seeds the table with the default study_subjects."""
    from logic import study_subjects
    try:
        subj_df = read_sql(
            "SELECT subject FROM user_subjects WHERE username=%s ORDER BY subject", (user,)
        )
        if not subj_df.empty:
            return subj_df['subject'].tolist()
        
        # First time for this user – seed with defaults
        conn = database.conn
        c = database.c
        for s in study_subjects:
            try:
                c.execute(
                    "INSERT INTO user_subjects (username, subject) VALUES (%s, %s) "
                    "ON CONFLICT (username, subject) DO NOTHING",
                    (user, s)
                )
            except Exception:
                pass
        conn.commit()
        return study_subjects[:]
    except Exception:
        from logic import study_subjects
        return study_subjects[:]

def get_user_defaults(username):
    """Retrieve saved default values for all activities for the user."""
    try:
        df = read_sql("SELECT activity, default_sub1, default_sub2 FROM user_defaults WHERE username=%s", (username,))
        return {row['activity']: (row['default_sub1'] or "", row['default_sub2'] or "") for _, row in df.iterrows()}
    except Exception:
        return {}

def get_all_songs(force_refresh=False):
    # Find all supported audio files in the music directory
    supported_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
    all_files = []
    
    # Check if music directory exists, else fallback to root
    search_dir = "music/**/*" if os.path.exists("music") else "**/*"
    
    for ext in supported_exts:
        all_files.extend(glob.glob(f"{search_dir}{ext}", recursive=True))
    
    # Filter out anything in common hidden/ignored folders if searching root
    local_songs = [f for f in all_files if not any(x in f for x in ['.git', '__pycache__', 'venv', 'env'])]
    
    # Normalize paths to use forward slashes for consistency
    local_songs = [f.replace("\\", "/") for f in local_songs]

    if not supabase_client:
        return sorted(list(set(local_songs)))
    
    try:
        res = supabase_client.storage.from_(STORAGE_BUCKET).list()
        if isinstance(res, list):
            cloud_songs = [f['name'] for f in res if f['name'].lower().endswith(supported_exts)]
            return sorted(list(set(local_songs + cloud_songs)))
        return sorted(list(set(local_songs)))
    except Exception as e:
        print(f"Error listing Supabase songs: {e}")
        return sorted(list(set(local_songs)))

def get_song_url(filename):
    # Check if file exists locally first
    if os.path.exists(filename):
        return filename
    
    if not supabase_client:
        return filename
        
    try:
        return supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(filename)
    except Exception:
        return filename

def clean_song_name(filename):
    # Get basename if it's a path
    name = os.path.basename(filename)
    # Remove any supported extension
    for ext in (".mp3", ".m4a", ".webm", ".wav", ".ogg"):
        name = name.replace(ext, "")
    name = name.replace(".mp3", "") # Fallback for edge cases
    name = re.sub(r' \d+ [Kk]bps| Youngistaan', '', name)
    name = name.replace("_", " ").replace("-", " ")
    name = " ".join(name.split()).title()
    icons = {"Perfect": "💍", "Tum Se Hi": "✨", "Phir Bhi": "💖", "Suno Na": "🎵", "Ishq": "🔥", "Rang": "🎨", "Waalian": "🎧"}
    for key, icon in icons.items():
        if key.lower() in name.lower():
            return f"{name} {icon}"
    return f"{name} 🎵"

def get_song_lists():
    if "all_mp3s" not in st.session_state or st.session_state.get("_refresh_music"):
        st.session_state.all_mp3s = get_all_songs()
        st.session_state._refresh_music = False

    all_mp3s = st.session_state.all_mp3s

    if "Perfect.mp3" in all_mp3s:
        temp_list = list(all_mp3s)
        temp_list.remove("Perfect.mp3")
        temp_list.sort()
        temp_list.insert(0, "Perfect.mp3")
        all_mp3s = temp_list
    else:
        all_mp3s = sorted(all_mp3s)

    song_options_dict = {}
    if all_mp3s:
        for f in all_mp3s:
            clean = clean_song_name(f)
            if clean in song_options_dict:
                parent = os.path.basename(os.path.dirname(f))
                if parent:
                    clean = f"{clean} [{parent}]"
                else:
                    clean = f"{clean} ({f})"
            song_options_dict[clean] = f

    song_names_list = list(song_options_dict.keys())
    return all_mp3s, song_options_dict, song_names_list

def format_duration(dur):
    if dur is None or dur <= 0:
        return ""
    try:
        dur = float(dur)
    except:
        return ""
    hours = int(dur)
    minutes = int(round((dur - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    if hours > 0 and minutes > 0:
        return f"{hours}Hr{minutes}M"
    elif hours > 0:
        return f"{hours}Hr"
    else:
        return f"{minutes}M"



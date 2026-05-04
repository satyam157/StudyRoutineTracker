import mimetypes
mimetypes.init()
mimetypes.types_map['.js'] = 'application/javascript'
mimetypes.types_map['.css'] = 'text/css'

import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from datetime import timedelta, date
import shutil
import os
import sys
import subprocess
import tempfile
import time



# --- Isolated Music Player Styling (ONLY affects the music player, nothing else) ---
st.markdown("""
<style>
    /* =========================================================
       MUSIC PLAYER ISOLATION
       All rules below are scoped to the sidebar music section
       using :has(#sidebar-music-marker) so they CANNOT bleed
       into any other part of the UI.
    ========================================================= */

    /* --- Prev/Next/Mode Buttons --- */
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container button {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
        border: 1px solid #21262d !important;
        border-radius: 8px !important;
        transition: background-color 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container button:hover {
        background-color: #161b22 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }

    /* --- Auto-switch checkbox dark card --- */
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stCheckbox"] {
        background-color: #161b22 !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
        margin-bottom: 6px !important;
    }
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stCheckbox"] label p,
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stCheckbox"] label span {
        color: #e2e8f0 !important;
        font-size: 0.82rem !important;
    }

    /* --- Audio player — invert so it's clearly visible on dark --- */
    audio {
        filter: invert(100%) hue-rotate(180deg) brightness(1.4);
        height: 40px;
        width: 100%;
        border-radius: 10px;
    }

    /* --- Song Selectbox (Premium Dark Look) --- */
    /* Sidebar Scoped */
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stSelectbox"] [data-baseweb="select"]:hover > div {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 1px #38bdf8 !important;
    }
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stSelectbox"] svg {
        fill: #38bdf8 !important;
    }
    [data-testid="stSidebar"] .element-container:has(#sidebar-music-marker) ~ .element-container div[data-testid="stSelectbox"] [data-testid="stMarkdownContainer"] p {
        color: #8b949e !important;
        font-size: 0.75rem !important;
    }

    /* Media Player Page Scoped */
    .element-container:has(#media-player-marker) ~ .element-container div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 5px 10px !important;
    }
    .element-container:has(#media-player-marker) ~ .element-container div[data-testid="stSelectbox"] [data-baseweb="select"]:hover > div {
        border-color: #38bdf8 !important;
    }

    /* --- Dropdown Menu (Global but specific to BaseWeb popovers) --- */
    /* Note: Streamlit portals popovers to the body, making them hard to isolate. 
       We apply a dark theme to all popovers which fits the 'Premium' aesthetic. */
    div[data-baseweb="popover"] {
        background-color: transparent !important;
    }
    div[data-baseweb="popover"] ul {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 8px !important;
    }
    div[data-baseweb="popover"] li {
        background-color: transparent !important;
        color: #c9d1d9 !important;
        border-radius: 6px !important;
        margin: 2px 0 !important;
        transition: all 0.2s ease !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #161b22 !important;
        color: #38bdf8 !important;
    }
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: rgba(56, 189, 248, 0.1) !important;
        color: #38bdf8 !important;
    }

    /* =========================================================
       SIDEBAR VERTICAL PAGE BUTTON STYLING
       Converts page navigation lists into tactile, highly-responsive buttons
       ========================================================= */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 10px !important;
        padding: 5px 0 !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        position: relative !important;
        background: rgba(255, 255, 255, 0.05) !important;
        padding: 14px 20px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        cursor: pointer !important;
        user-select: none !important;
        touch-action: manipulation !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important; /* Centered horizontal alignment */
        text-align: center !important;
        -webkit-tap-highlight-color: transparent !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15), 0 2px 4px -2px rgba(0, 0, 0, 0.1) !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        color: #60a5fa !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(96, 165, 250, 0.4) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
        color: white !important;
        border-color: transparent !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        transform: scale(1.02) !important;
    }
    /* Stretch the native invisible touch target to cover 100% of the sidebar label button */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child { 
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        opacity: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
        z-index: 2 !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:last-child {
        position: relative !important;
        z-index: 3 !important;
        pointer-events: none !important;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar Header: User Emoji, Username and Logout button below
import database
from database import get_fresh_cursor, reconnect, save_esu_response, get_esu_responses, delete_esu_response, ensure_connection, get_ist_now
import importlib
import logic
importlib.reload(logic)
from logic import *

# Initialize or ensure connection at startup
database.ensure_connection()
conn = database.conn
c = database.c
from streamlit_calendar import calendar


def read_sql(query, params=None):
    """Execute a SELECT query via the psycopg2 cursor and return a pandas DataFrame.
    Avoids the UserWarning pandas raises when a raw DBAPI2 connection is passed."""
    global conn, c
    import database
    database.ensure_connection()
    conn = database.conn
    c = database.c
    
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        # One-time retry on failure
        database.reconnect()
        conn = database.conn
        c = database.c
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        return pd.DataFrame(rows, columns=cols)


def get_user_subjects(user):
    """Return the user-specific subject list from user_subjects table.
    On first call seeds the table with the default study_subjects."""
    try:
        subj_df = read_sql(
            "SELECT subject FROM user_subjects WHERE username=%s ORDER BY subject", (user,)
        )
        if not subj_df.empty:
            return subj_df['subject'].tolist()
        # First time for this user – seed with defaults
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
        return study_subjects[:]


def get_user_defaults(username):
    """Retrieve saved default values for all activities for the user."""
    try:
        df = read_sql("SELECT activity, default_sub1, default_sub2 FROM user_defaults WHERE username=%s", (username,))
        return {row['activity']: (row['default_sub1'] or "", row['default_sub2'] or "") for _, row in df.iterrows()}
    except Exception:
        return {}


if conn is None:
    st.error("🚨 CRITICAL: PostgreSQL Database Connection Failed! Please ensure PostgreSQL is installed, running locally, and credentials match the .env configuration. The app cannot proceed without a database.")
    st.stop()

if "username" not in st.session_state:
    if "usr" in st.query_params:
        st.session_state["username"] = st.query_params["usr"]
    else:
        st.session_state["username"] = None

if st.session_state["username"] is None:
    st.title("🔐 Login to Study Routine Tracker")
    with st.form("login_form"):
        usr = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                # Use a fresh connection to avoid stale PgBouncer/Supabase pool timeouts
                tmp_conn, tmp_cur = get_fresh_cursor()
                if tmp_cur is None:
                    st.error("Could not connect to database. Please try again.")
                else:
                    tmp_cur.execute("SELECT password FROM users WHERE username=%s", (usr.strip(),))
                    res = tmp_cur.fetchone()
                    tmp_cur.close()
                    tmp_conn.close()
                    if res and res[0] == pwd:
                        # Record last login
                        try:
                            from database import get_ist_now, get_fresh_cursor
                            upd_conn, upd_cur = get_fresh_cursor()
                            upd_cur.execute("UPDATE users SET last_login = %s WHERE username = %s", (get_ist_now(), usr.strip()))
                            upd_conn.commit()
                            upd_cur.close()
                            upd_conn.close()
                        except Exception as log_err:
                            st.sidebar.error(f"Login log failed: {log_err}")
                            
                        st.session_state["username"] = usr.strip()
                        st.query_params["usr"] = usr.strip()
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            except Exception as e:
                st.error(f"Database error: {e}")
    st.stop()

USER = st.session_state["username"]

# Sidebar Header: User Emoji, Username and Logout button below
st.sidebar.markdown(f"### 👤 {USER}")
if st.sidebar.button("Logout", key="logout_btn", width='stretch'):
    st.session_state["username"] = None
    if "usr" in st.query_params:
        del st.query_params["usr"]
    st.rerun()

st.sidebar.divider()

menu_options = [
    "Daily Entry","Calendar","Study Calendar","Social Life","Set Target","Study Target Manager","Productivity Analysis","Ask Esu","Expenses"
]
# --- PERMISSIONS & CONFIG ---
from database import get_user_config, update_user_config, get_allowed_recipients, set_allowed_recipients
USER_CONFIG = get_user_config(USER)

# --- GLOBAL SIDEBAR MUSIC PLAYER ---

# We need to defer the actual rendering until after the menu is selected,
# but we initialise music state now so it persists across pages.
import os
import re
import random as _rand
from database import supabase_client, STORAGE_BUCKET

# Helper to get songs from Supabase Storage + Local fallback
# Helper to get songs from Supabase Storage + Local fallback
def get_all_songs(force_refresh=False):
    import glob
    # Find all supported audio files in the current directory and all subdirectories
    supported_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
    all_files = []
    for ext in supported_exts:
        all_files.extend(glob.glob(f"**/*{ext}", recursive=True))
    
    # Filter out anything in common hidden/ignored folders
    local_songs = [f for f in all_files if not any(x in f for x in ['.git', '__pycache__', 'venv', 'env'])]
    
    # Normalize paths to use forward slashes for consistency
    local_songs = [f.replace("\\", "/") for f in local_songs]

    if not supabase_client:
        return sorted(list(set(local_songs)))
    
    try:
        # We don't cache this at the Streamlit level by default, 
        # but we could if the bucket is very large.
        res = supabase_client.storage.from_(STORAGE_BUCKET).list()
        if isinstance(res, list):
            supported_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
            cloud_songs = [f['name'] for f in res if f['name'].lower().endswith(supported_exts)]
            # Combine and remove duplicates
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
    except:
        return filename

# Initial load
if "all_mp3s" not in st.session_state or st.session_state.get("_refresh_music"):
    st.session_state.all_mp3s = get_all_songs()
    st.session_state._refresh_music = False

all_mp3s = st.session_state.all_mp3s

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

if "Perfect.mp3" in all_mp3s:
    # Use a copy to avoid modifying the session state list directly if needed
    temp_list = list(all_mp3s)
    temp_list.remove("Perfect.mp3")
    temp_list.sort()
    temp_list.insert(0, "Perfect.mp3")
    all_mp3s = temp_list
else:
    all_mp3s = sorted(all_mp3s)

# Dictionary of {CleanName: Filename}
# Use full path as value to ensure correct playback, handle collisions
song_options_dict = {}
if all_mp3s:
    for f in all_mp3s:
        clean = clean_song_name(f)
        if clean in song_options_dict:
            # Collision! Append parent folder or a bit of the hash
            parent = os.path.basename(os.path.dirname(f))
            if parent:
                clean = f"{clean} [{parent}]"
            else:
                # If both in root (shouldn't happen with set()), just use full name
                clean = f"{clean} ({f})"
        song_options_dict[clean] = f

song_names_list = list(song_options_dict.keys())

if "music_idx" not in st.session_state:
    st.session_state.music_idx = 0
if "music_shuffle" not in st.session_state:
    st.session_state.music_shuffle = False
if "music_autoswitch" not in st.session_state:
    st.session_state.music_autoswitch = True
if "music_playing" not in st.session_state:
    st.session_state.music_playing = False
if "music_stop_triggered" not in st.session_state:
    st.session_state.music_stop_triggered = False
if "music_play_triggered" not in st.session_state:
    st.session_state.music_play_triggered = False

def _render_music_player(is_mylove=False):
    """Render the sidebar music player with warm light-colored scrollable song list."""
    if not song_names_list:
        st.sidebar.info("🎵 No audio files found in Cloud Storage or Local Directory.")
        st.sidebar.divider()
        return

    st.sidebar.markdown('<div id="sidebar-music-marker"></div>', unsafe_allow_html=True)

    st.sidebar.markdown("""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                    padding: 12px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 15px;
                    display: flex; justify-content: space-between; align-items: center;">
            <h3 style="color: #38bdf8; margin: 0; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                <span>🎵</span> Media Box
            </h3>
        </div>
    """, unsafe_allow_html=True)


    def next_song():
        if not song_names_list: return
        st.session_state.music_playing = True
        if st.session_state.music_shuffle:
            idx = _rand.randint(0, len(song_names_list)-1)
            if len(song_names_list) > 1 and idx == st.session_state.music_idx:
                idx = (idx + 1) % len(song_names_list)
            st.session_state.music_idx = idx
        else:
            st.session_state.music_idx = (st.session_state.music_idx + 1) % len(song_names_list)

    def prev_song():
        if not song_names_list: return
        st.session_state.music_playing = True
        if st.session_state.music_shuffle:
            idx = _rand.randint(0, len(song_names_list)-1)
            if len(song_names_list) > 1 and idx == st.session_state.music_idx:
                idx = (idx - 1) % len(song_names_list)
            st.session_state.music_idx = idx
        else:
            st.session_state.music_idx = (st.session_state.music_idx - 1) % len(song_names_list)

    # Controls row
    def stop_song():
        st.session_state.music_playing = False
        st.session_state.music_stop_triggered = True

    def play_song():
        st.session_state.music_playing = True
        st.session_state.music_play_triggered = True

    ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.sidebar.columns([1, 1, 1, 1])
    ctrl_c1.button("⏮️", on_click=prev_song, width='stretch', key="music_prev_btn", help="Previous Song")
    # Stop button always shown; Play button hidden on MyLove Special (it autoplays)
    if is_mylove or st.session_state.music_playing:
        ctrl_c2.button("⏹️", on_click=stop_song, width='stretch', key="music_stop_btn", help="Stop")
    else:
        ctrl_c2.button("▶️", on_click=play_song, width='stretch', key="music_play_btn", help="Play")
    ctrl_c3.button("⏭️", on_click=next_song, width='stretch', key="music_next_btn", help="Next Song")
    mode_icon = "🔀" if st.session_state.music_shuffle else "🔁"
    if ctrl_c4.button(mode_icon, width='stretch', key="music_mode_toggle", help="Toggle Shuffle / In Order"):
        st.session_state.music_shuffle = not st.session_state.music_shuffle
        st.rerun()

    st.session_state.music_autoswitch = st.sidebar.checkbox(
        "⏩ Auto-switch at end",
        value=st.session_state.music_autoswitch,
        key="music_auto_chk"
    )

    mode_label = "🔀 Shuffle" if st.session_state.music_shuffle else "🔁 In Order"
    st.sidebar.markdown(f"""
        <div style="font-size: 0.75rem; color: #8b949e; margin-bottom: 10px; display: flex; justify-content: space-between;">
            <span>Mode:</span>
            <span style="color: #38bdf8; font-weight: 600;">{mode_label}</span>
        </div>
    """, unsafe_allow_html=True)

    # Clamp index
    if st.session_state.music_idx >= len(song_names_list):
        st.session_state.music_idx = 0

    # --- Song Selector Dropdown ---
    def _on_sidebar_sel_change():
        if st.session_state.sidebar_song_selector in song_names_list:
            st.session_state.music_idx = song_names_list.index(st.session_state.sidebar_song_selector)
            st.session_state.music_playing = True

    st.sidebar.selectbox(
        "Select Song",
        options=song_names_list,
        index=st.session_state.music_idx,
        key="sidebar_song_selector",
        on_change=_on_sidebar_sel_change,
        label_visibility="collapsed"
    )

    current_song_path = song_options_dict[song_names_list[st.session_state.music_idx]]
    st.sidebar.markdown(f"""
        <div style="background-color: #161b22; padding: 10px; border-radius: 8px; border-left: 3px solid #38bdf8; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px;">Current Track</p>
            <p style="margin: 0; font-size: 0.9rem; color: #f0f6fc; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {song_names_list[st.session_state.music_idx]}
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Auto-play only on MyLove Special or if already started by user
    should_autoplay = is_mylove or st.session_state.music_playing
    st.sidebar.audio(get_song_url(current_song_path), format="audio/mp3", autoplay=should_autoplay)

    # --- JS: actually stop or start the audio element in the browser ---
    if st.session_state.get("music_stop_triggered"):
        st.session_state.music_stop_triggered = False
        st.html("""
        <script>
        (function stopAllAudio() {
            var attempts = 0;
            function tryStop() {
                try {
                    var audios = window.parent.document.querySelectorAll('audio');
                    audios.forEach(function(a) {
                        a.pause();
                        a.currentTime = 0;
                    });
                } catch(e) {}
                if (++attempts < 5) setTimeout(tryStop, 200);
            }
            tryStop();
        })();
        </script>
        """, unsafe_allow_javascript=True)
    elif st.session_state.get("music_play_triggered"):
        st.session_state.music_play_triggered = False
        st.html("""
        <script>
        (function playAudio() {
            var attempts = 0;
            function tryPlay() {
                try {
                    var sidebarAudio = window.parent.document.querySelector('[data-testid="stSidebar"] audio');
                    var audio = sidebarAudio || window.parent.document.querySelector('audio');
                    if (audio) { audio.play(); }
                } catch(e) {}
                if (++attempts < 5) setTimeout(tryPlay, 200);
            }
            tryPlay();
        })();
        </script>
        """, unsafe_allow_javascript=True)

    if st.session_state.music_autoswitch:
        st.html("""
        <script>
        (function() {
            setInterval(() => {
                try {
                    function getItems(win) {
                        let res = { audios: [], buttons: [] };
                        try {
                            res.audios = Array.from(win.document.querySelectorAll('audio'));
                            res.buttons = Array.from(win.document.querySelectorAll('button'));
                            let fs = win.document.querySelectorAll('iframe');
                            for (let i=0; i<fs.length; i++) {
                                try {
                                    let s = getItems(fs[i].contentWindow);
                                    res.audios = res.audios.concat(s.audios);
                                    res.buttons = res.buttons.concat(s.buttons);
                                } catch(e) {}
                            }
                        } catch(e) {}
                        return res;
                    }
                    const all = getItems(window.top);
                    all.audios.forEach(a => {
                        const isDone = a.ended || (a.duration > 0 && a.currentTime >= a.duration - 0.5);
                        if (isDone && !a.dataset.nextTriggered) {
                            a.dataset.nextTriggered = "true";
                            let b = all.buttons.find(btn => (btn.title && btn.title.toLowerCase().includes('next')) || 
                                                            (btn.innerText && btn.innerText.includes('⏭')));
                            if (b) { b.click(); }
                        }
                        if (a.currentTime < 0.2) a.dataset.nextTriggered = "";
                    });
                } catch(e) {}
            }, 500);
        })();
        </script>
        """, unsafe_allow_javascript=True)

    # --- Quick "Media Player" link for users with music access ---
    if USER_CONFIG.get("can_access_music") or USER == "admin":
        if st.sidebar.button("🎵 Media Player", key="music_media_player_btn", width='stretch', help="Go to Media Player page"):
            st.session_state["_jump_to_media_player"] = True
            st.rerun()

    # --- Reset to default song for MyLove Special ---
    if is_mylove:
        _default_song = USER_CONFIG.get("mylove_default_song", "Perfect.mp3")
        _default_song_clean = clean_song_name(_default_song) if _default_song else "Perfect 💍"
        if st.sidebar.button(f"🔄 Reset to Default ({_default_song_clean})", key="music_reset_mylove_btn", width='stretch'):
            st.session_state.music_playing = True
            for i, name in enumerate(song_names_list):
                if _default_song and _default_song.replace('.mp3', '').lower() in name.lower():
                    st.session_state.music_idx = i
                    break
            else:
                # Fallback to Perfect if configured song not found
                for i, name in enumerate(song_names_list):
                    if "perfect" in name.lower():
                        st.session_state.music_idx = i
                        break
            st.rerun()

    st.sidebar.markdown('<div id="sidebar-music-end-marker"></div>', unsafe_allow_html=True)
    st.sidebar.divider()


# --- SIDEBAR NOTIFICATIONS ALERT ---
import proposal
if USER_CONFIG.get("can_receive_love_notifications") or USER == 'admin':
    notifs = proposal.get_latest_love_notifications(USER)
    if notifs:
        st.sidebar.markdown("### 🔔 New Messages")
        for n_id, msg, ts, sender, is_hidden in notifs:
            if f"toasted_{n_id}" not in st.session_state:
                st.toast(f"New Message: {msg}", icon="💖")
                st.session_state[f"toasted_{n_id}"] = True
                
            col_msg, col_x = st.sidebar.columns([6, 1])
            with col_msg:
                st.markdown(f"""
                    <div style="background-color: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; padding: 10px; border-radius: 12px; margin-bottom: 5px;">
                        <p style="font-size: 0.85rem; margin: 0;"><b>{sender}:</b> {msg[:30]}...</p>
                    </div>
                """, unsafe_allow_html=True)
            with col_x:
                if st.button("✖", key=f"dismiss_notif_{n_id}"):
                    proposal.mark_notification_read(n_id)
                    st.rerun()

if USER == "admin":
    menu_options.append("Manage Users")
    menu_options.append("Love Management")

if USER_CONFIG.get("can_access_music") or USER == "admin":
    menu_options.append("Media Player")

menu_options.append("Chat")

if USER_CONFIG.get("can_view_mylove_special"):
    menu_options.append("MyLove Special")

# --- MENU SELECTION ---
if "menu" not in st.session_state:
    st.session_state.menu = menu_options[0]

# If we were previously on a menu that is no longer available (e.g. logout/config change), 
# default to the first available option.
if st.session_state.menu not in menu_options:
    st.session_state.menu = menu_options[0]

# Handle "Media Player" jump from sidebar music player button
if st.session_state.get("_jump_to_media_player"):
    st.session_state["_jump_to_media_player"] = False
    st.session_state.menu = "Media Player"

def _on_menu_change():
    st.session_state.menu = st.session_state.main_menu_radio

# Find current index for the radio button
try:
    menu_index = menu_options.index(st.session_state.menu)
except ValueError:
    menu_index = 0

menu = st.sidebar.radio(
    "Menu", 
    menu_options, 
    index=menu_index,
    key="main_menu_radio",
    on_change=_on_menu_change
)

# Sync back to menu variable for the rest of the script
menu = st.session_state.menu

# --- Auto-Scroll to Top on Page Change ---
if st.session_state.get("_prev_menu") != menu:
    st.html("<script>window.parent.window.scrollTo(0,0);</script>", unsafe_allow_javascript=True)

# Auto-select configured default song when first entering MyLove Special
if menu == "MyLove Special":
    if st.session_state.get("_prev_menu") != "MyLove Special":
        _default_song = USER_CONFIG.get("mylove_default_song", "Perfect.mp3")
        _found_default = False
        if _default_song:
            _default_base = _default_song.replace('.mp3', '').lower()
            for i, name in enumerate(song_names_list):
                if _default_base in name.lower():
                    st.session_state.music_idx = i
                    _found_default = True
                    break
        if not _found_default:
            for i, name in enumerate(song_names_list):
                if "perfect" in name.lower():
                    st.session_state.music_idx = i
                    break
st.session_state["_prev_menu"] = menu

# --- Render sidebar music player ---
# MyLove Special: ALWAYS show (controls background music for the page)
# Media Player: NEVER show (page has its own built-in player)
# Other pages: show if user has can_access_music or is admin
_show_sidebar_player = False
if menu == "MyLove Special":
    _show_sidebar_player = True
elif menu != "Media Player" and (USER_CONFIG.get("can_access_music") or USER == "admin"):
    _show_sidebar_player = True

if _show_sidebar_player:
    _render_music_player(is_mylove=(menu == "MyLove Special"))

if menu == "Chat":
    st.title("💌 Love Chat & Inbox")
    
    import proposal
    
    # Determine if the user should see the Note Activity tab
    _show_note_activity = USER == 'admin' or USER_CONFIG.get("can_receive_love_notifications", False)
    
    if _show_note_activity:
        tab_notes, tab_send, tab_alerts, tab_activity = st.tabs([
            "📥 Personal Notes", "🚀 Send a Note", "🔔 System Alerts", "📝 Note Activity"
        ])
    else:
        tab_notes, tab_send, tab_alerts = st.tabs([
            "📥 Personal Notes", "🚀 Send a Note", "🔔 System Alerts"
        ])
    
    with tab_notes:
        proposal.show_admin_notifications(USER, mode='personal')
        
    with tab_alerts:
        proposal.show_admin_notifications(USER, mode='system')
    
    # Note Activity tab — shows all personal note notifications sent to admin/privileged users
    if _show_note_activity:
        with tab_activity:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                padding: 16px 22px; border-radius: 14px; border: 1px solid #334155;
                margin-bottom: 18px;
            ">
                <div style="font-size: 16px; color: #e2e8f0; font-weight: 700; margin-bottom: 4px;">
                    📝 Note Activity Monitor
                </div>
                <div style="font-size: 13px; color: #94a3b8;">
                    Real-time feed of personal notes sent between users.
                    You receive these because you have notification privileges.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Fetch notifications that are note-activity style (contain "📝" prefix)
            all_notifs = proposal.get_all_love_notifications(USER)
            activity_notifs = [n for n in all_notifs if "📝" in n[1]]
            
            if not activity_notifs:
                st.info("No note activity yet. When users send personal notes to each other, you'll see it here. 🔍")
            else:
                from collections import OrderedDict
                # Group by sender
                activity_grouped = OrderedDict()
                for n_id, msg, ts, sender, is_hidden in activity_notifs:
                    if sender not in activity_grouped:
                        activity_grouped[sender] = []
                    activity_grouped[sender].append((n_id, msg, ts, sender, is_hidden))
                
                st.markdown(f"""
                <div style="
                    display: flex; gap: 12px; margin-bottom: 14px; flex-wrap: wrap;
                ">
                    <div style="background: #1e293b; padding: 10px 18px; border-radius: 10px; border: 1px solid #334155;">
                        <span style="color: #94a3b8; font-size: 12px;">Total Activity</span><br>
                        <span style="color: #38bdf8; font-size: 20px; font-weight: 700;">{len(activity_notifs)}</span>
                    </div>
                    <div style="background: #1e293b; padding: 10px 18px; border-radius: 10px; border: 1px solid #334155;">
                        <span style="color: #94a3b8; font-size: 12px;">Active Senders</span><br>
                        <span style="color: #a78bfa; font-size: 20px; font-weight: 700;">{len(activity_grouped)}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                _activity_can_delete = USER == 'admin' or USER_CONFIG.get("can_delete_system_alerts", False)
                
                for sender_name, notes in activity_grouped.items():
                    with st.expander(f"📝 {sender_name} — {len(notes)} event{'s' if len(notes) != 1 else ''}", expanded=False):
                        for n_id, msg, ts, sender, is_hidden in notes:
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, #f0f4ff 0%, #ffffff 100%);
                                padding: 16px;
                                border-radius: 16px;
                                margin-bottom: 5px;
                                border-left: 4px solid #6366f1;
                                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
                            ">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span style="font-size: 13px; font-weight: 600; color: #6366f1;">📝 {sender}</span>
                                    <span style="font-size: 11px; color: #999;">⏰ {ts}</span>
                                </div>
                                <div style="font-size: 15px; color: #333; line-height: 1.5;">
                                    {msg}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if _activity_can_delete:
                                if st.checkbox(f"🗑️ Delete #{n_id}?", key=f"act_del_{n_id}"):
                                    if st.button("✅ Confirm Delete", key=f"act_y_{n_id}", type="primary"):
                                        proposal.delete_notification(n_id)
                                        st.rerun()
                            
                            proposal.mark_notification_read(n_id)
                
                # Clear all activity
                if _activity_can_delete:
                    st.divider()
                    if st.button("🗑️ Clear All Note Activity", width='stretch', key="clear_note_activity"):
                        from database import get_fresh_cursor
                        tmp_conn, tmp_c = get_fresh_cursor()
                        if tmp_c:
                            try:
                                ids_to_delete = [n[0] for n in activity_notifs]
                                if ids_to_delete:
                                    tmp_c.execute("DELETE FROM system_notifications WHERE id = ANY(%s)", (ids_to_delete,))
                                    tmp_conn.commit()
                                tmp_c.close()
                                tmp_conn.close()
                                st.success("Activity history cleared! ✨")
                                import time; time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        
    with tab_send:
        if USER_CONFIG.get("can_send_love_messages") or USER == 'admin':
            st.markdown("### 💝 Love Express")
            st.write("Send a romantic note or a quick surprise!")
            
            if USER == 'admin':
                if st.button("❤️ Quick 'I Love You' to Her"):
                    proposal.send_love_notification("admin", "I love you too, my princess! 💖🌹", "foryou")
                    proposal.notify_admins_personal_note("admin", "I love you too, my princess! 💖🌹", "foryou")
                    st.toast("Love message sent! 💌", icon="❤️")
            
            with st.container():
                love_msg = st.text_area("Message", placeholder="Write your heart out...", height=150)
                
                # Determine allowed recipients
                if USER == "admin":
                    try:
                        allowed_users_df = read_sql("SELECT username FROM user_config WHERE can_receive_love_messages = TRUE AND username != 'admin'")
                        allowed_users = allowed_users_df['username'].tolist()
                    except:
                        allowed_users = ["foryou", "love", "rishika"]
                else:
                    allowed_users = get_allowed_recipients(USER)
                
                if not allowed_users:
                    st.info("No recipients assigned yet. Check with admin! 🕊️")
                else:
                    target_usr = st.selectbox("Send to", allowed_users)
                    if st.button("🚀 Send Love"):
                        if love_msg.strip():
                            proposal.send_love_notification(USER, love_msg.strip(), target_usr)
                            # Notify admin/privileged users about this note activity
                            proposal.notify_admins_personal_note(USER, love_msg.strip(), target_usr)
                            st.success(f"Your message took flight to {target_usr}! ✨")
                            st.balloons()
                        else:
                            st.warning("You can't send an empty heart!")
        else:
            st.warning("You don't have permission to send messages. Ask admin! 🕊️")
    st.stop()


if menu == "Love Management" and USER == "admin":
    st.title("💖 Love & Permission Management")
    st.markdown("Control which users have access to romantic features.")
    
    ALL_PAGES = ["Daily Entry","Calendar","Set Target","Study Target Manager","Productivity Analysis","Ask Esu","Expenses","Chat","MyLove Special","Media Player"]
    
    try:
        users_df = read_sql("SELECT u.username, c.can_view_mylove_special, c.can_send_love_messages, c.can_receive_love_messages, c.can_receive_love_notifications, c.can_delete_messages, c.can_delete_system_alerts, c.can_access_music, c.music_pages, c.mylove_default_song, c.can_hide_personal_notes FROM users u LEFT JOIN user_config c ON u.username = c.username WHERE u.username != 'admin'")
        all_potential_recipients = users_df['username'].tolist() + ["admin"]
        
        for index, row in users_df.iterrows():
            with st.expander(f"👤 {row['username']}"):
                col1, col2 = st.columns(2)
                v1 = col1.checkbox("MyLove Page", value=row['can_view_mylove_special'], key=f"v_{row['username']}")
                v2 = col2.checkbox("Send Chats/Msgs", value=row['can_send_love_messages'], key=f"s_{row['username']}")
                v3 = col1.checkbox("Receive Chats/Msgs", value=row['can_receive_love_messages'], key=f"m_{row['username']}")
                v4 = col2.checkbox("Receive MyLove Page Notifs", value=row['can_receive_love_notifications'], key=f"n_{row['username']}")
                v5 = col1.checkbox("Delete Personal Notes", value=row['can_delete_messages'], key=f"d_note_{row['username']}")
                v6 = col2.checkbox("Delete System Alerts", value=row['can_delete_system_alerts'], key=f"d_sys_{row['username']}")
                v7 = col1.checkbox("Use Music Player", value=row['can_access_music'], key=f"d_mus_{row['username']}")
                v10 = col2.checkbox("🔒 Hide Personal Notes", value=row.get('can_hide_personal_notes', False), key=f"hide_notes_{row['username']}")
                
                # Per-page music player controls
                if v7:
                    current_pages = row.get('music_pages', 'all') or 'all'
                    use_all = st.checkbox("Music on ALL pages", value=(current_pages == 'all'), key=f"mus_all_{row['username']}")
                    if use_all:
                        v8 = "all"
                    else:
                        current_list = [p.strip() for p in current_pages.split(",") if p.strip()] if current_pages != "all" else ALL_PAGES
                        selected_pages = st.multiselect(
                            f"Music Player Pages for {row['username']}",
                            ALL_PAGES,
                            default=[p for p in current_list if p in ALL_PAGES],
                            key=f"mus_pages_{row['username']}"
                        )
                        v8 = ",".join(selected_pages) if selected_pages else "all"
                else:
                    v8 = row.get('music_pages', 'all') or 'all'
                
                # Recipients selection
                current_allowed = get_allowed_recipients(row['username'])
                # Filter out self from recipients list for this specific user
                other_users = [u for u in all_potential_recipients if u != row['username']]
                selected_recipients = st.multiselect(f"Allowed Recipients for {row['username']}", other_users, default=current_allowed, key=f"recip_{row['username']}")
                
                # --- MyLove Special default song selector ---
                if v1:  # Only show if MyLove Special page is enabled
                    _current_default = row.get('mylove_default_song', 'Perfect.mp3') or 'Perfect.mp3'
                    _audio_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
                    _mp3_files = [f for f in os.listdir(".") if f.lower().endswith(_audio_exts)]
                    _mp3_files.sort()
                    _default_idx = _mp3_files.index(_current_default) if _current_default in _mp3_files else 0
                    v9 = st.selectbox(
                        f"🎵 Default MyLove Song for {row['username']}",
                        options=_mp3_files,
                        index=_default_idx,
                        format_func=clean_song_name,
                        key=f"mlsong_{row['username']}",
                        help="The song that auto-plays when this user opens MyLove Special"
                    )
                else:
                    v9 = row.get('mylove_default_song', 'Perfect.mp3') or 'Perfect.mp3'

                if st.button("Save Changes", key=f"save_{row['username']}"):
                    success = update_user_config(row['username'], v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
                    success_recip = set_allowed_recipients(row['username'], selected_recipients)
                    if success and success_recip:
                        st.success(f"Permissions updated for {row['username']}!")
                        st.rerun()
                    else:
                        st.error("Failed to update.")
    except Exception as e:
        st.error(f"Error loading management UI: {e}")
    st.stop()

# ---------------- MEDIA PLAYER ----------------
if menu == "Media Player" and (USER_CONFIG.get("can_access_music") or USER == "admin"):
    st.markdown('<div id="media-player-marker"></div>', unsafe_allow_html=True)
    
    # Global Frame Explorer for Media Player
    if st.session_state.music_autoswitch:
        st.html("""
        <script>
        (function() {
            setInterval(() => {
                try {
                    function getItems(win) {
                        let res = { audios: [], buttons: [] };
                        try {
                            res.audios = Array.from(win.document.querySelectorAll('audio'));
                            res.buttons = Array.from(win.document.querySelectorAll('button'));
                            let fs = win.document.querySelectorAll('iframe');
                            for (let i=0; i<fs.length; i++) {
                                try {
                                    let s = getItems(fs[i].contentWindow);
                                    res.audios = res.audios.concat(s.audios);
                                    res.buttons = res.buttons.concat(s.buttons);
                                } catch(e) {}
                            }
                        } catch(e) {}
                        return res;
                    }
                    const all = getItems(window.top);
                    all.audios.forEach(a => {
                        const isDone = a.ended || (a.duration > 0 && a.currentTime >= a.duration - 0.5);
                        if (isDone && !a.dataset.nextTriggered) {
                            a.dataset.nextTriggered = "true";
                            let b = all.buttons.find(btn => (btn.title && btn.title.toLowerCase().includes('next')) || 
                                                            (btn.innerText && btn.innerText.includes('⏭')));
                            if (b) { b.click(); }
                        }
                        if (a.currentTime < 0.2) a.dataset.nextTriggered = "";
                    });
                } catch(e) {}
            }, 500);
        })();
        </script>
        """, unsafe_allow_javascript=True)

    st.title("🎵 Media Player")
    st.markdown("Your music hub — play, download, upload & manage your song library.")

    # ── Built-in Now Playing section (sidebar player hidden on this page) ──
    if song_names_list:
        if st.session_state.music_idx >= len(song_names_list):
            st.session_state.music_idx = 0

        _np_header, _np_controls = st.columns([3, 2])
        with _np_header:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        border: 1px solid #334155;
                        border-radius: 16px; padding: 22px 26px; color: white;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                        margin-bottom: 10px;">
                <div style="font-size:11px; font-weight:600; color:#38bdf8; margin-bottom:6px;
                            letter-spacing:1.8px; text-transform:uppercase; opacity:0.9;">✨ NOW PLAYING</div>
                <div style="font-size:22px; font-weight:700; letter-spacing:0.2px; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                    {song_names_list[st.session_state.music_idx]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            _current_mp_path = song_options_dict[song_names_list[st.session_state.music_idx]]
            st.audio(get_song_url(_current_mp_path), format="audio/mp3", autoplay=st.session_state.music_playing)

        with _np_controls:
            def _mp_next():
                st.session_state.music_playing = True
                if st.session_state.music_shuffle:
                    idx = _rand.randint(0, len(song_names_list)-1)
                    if len(song_names_list) > 1 and idx == st.session_state.music_idx:
                        idx = (idx + 1) % len(song_names_list)
                    st.session_state.music_idx = idx
                else:
                    st.session_state.music_idx = (st.session_state.music_idx + 1) % len(song_names_list)

            def _mp_prev():
                st.session_state.music_playing = True
                if st.session_state.music_shuffle:
                    idx = _rand.randint(0, len(song_names_list)-1)
                    if len(song_names_list) > 1 and idx == st.session_state.music_idx:
                        idx = (idx - 1) % len(song_names_list)
                    st.session_state.music_idx = idx
                else:
                    st.session_state.music_idx = (st.session_state.music_idx - 1) % len(song_names_list)

            def _mp_on_sel():
                if st.session_state._mp_song_sel in song_names_list:
                    st.session_state.music_idx = song_names_list.index(st.session_state._mp_song_sel)
                    st.session_state.music_playing = True

            st.selectbox("Select Song", options=song_names_list,
                         index=st.session_state.music_idx,
                         key="_mp_song_sel", on_change=_mp_on_sel,
                         label_visibility="collapsed")

            def _mp_stop():
                st.session_state.music_playing = False
                st.session_state.music_stop_triggered = True

            def _mp_play():
                st.session_state.music_playing = True
                st.session_state.music_play_triggered = True

            _mc1, _mc2, _mc3, _mc4 = st.columns(4)
            _mc1.button("⏮️", on_click=_mp_prev, width='stretch', key="_mp_prev", help="Previous")
            if st.session_state.music_playing:
                _mc2.button("⏹️", on_click=_mp_stop, width='stretch', key="_mp_stop", help="Stop")
            else:
                _mc2.button("▶️", on_click=_mp_play, width='stretch', key="_mp_play", help="Play")
            _mc3.button("⏭️", on_click=_mp_next, width='stretch', key="_mp_next", help="Next")
            _mode_lbl = "🔀" if st.session_state.music_shuffle else "🔁"
            if _mc4.button(_mode_lbl, width='stretch', key="_mp_mode", help="Toggle Shuffle / In Order"):
                st.session_state.music_shuffle = not st.session_state.music_shuffle
                st.rerun()

            _mode_txt = "🔀 Shuffle" if st.session_state.music_shuffle else "🔁 In Order"
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; gap: 10px; 
                            background: #111827; padding: 8px; border-radius: 8px; border: 1px solid #374151;
                            margin-bottom: 10px;">
                    <span style="color: #9ca3af; font-size: 0.8rem;">Playback:</span>
                    <span style="color: #38bdf8; font-size: 0.9rem; font-weight: 600;">{_mode_txt}</span>
                </div>
            """, unsafe_allow_html=True)
            
            st.session_state.music_autoswitch = st.checkbox(
                "⏩ Auto-switch at end",
                value=st.session_state.music_autoswitch,
                key="music_auto_chk"
            )

        # --- JS: actually stop or play audio on Media Player page ---
        if st.session_state.get("music_stop_triggered"):
            st.session_state.music_stop_triggered = False
            st.html("""
            <script>
            (function stopAllAudio() {
                var attempts = 0;
                function tryStop() {
                    try {
                        var audios = window.parent.document.querySelectorAll('audio');
                        audios.forEach(function(a) {
                            a.pause();
                            a.currentTime = 0;
                        });
                    } catch(e) {}
                    if (++attempts < 5) setTimeout(tryStop, 200);
                }
                tryStop();
            })();
            </script>
            """, unsafe_allow_javascript=True)
        elif st.session_state.get("music_play_triggered"):
            st.session_state.music_play_triggered = False
            st.html("""
            <script>
            (function playAudio() {
                var attempts = 0;
                function tryPlay() {
                    try {
                        var audio = window.parent.document.querySelector('audio');
                        if (audio) { audio.play(); }
                    } catch(e) {}
                    if (++attempts < 5) setTimeout(tryPlay, 200);
                }
                tryPlay();
            })();
            </script>
            """, unsafe_allow_javascript=True)

        # Autoswitch JS was moved to top of block for persistence
    else:
        st.info("🎵 No audio files found. Try downloading or uploading one above!")

    st.divider()

    tab_yt, tab_upload, tab_manage = st.tabs(["🔗 YouTube Download", "📤 Upload MP3", "📋 Manage Songs"])
    
    with tab_yt:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                    border: 1px solid #38bdf8; border-radius: 14px;
                    padding: 18px 20px; margin-bottom: 18px;">
            <div style="font-size:16px; font-weight:600; color:#38bdf8; margin-bottom:8px;">
                🔗 YouTube Downloader
            </div>
            <div style="font-size:13px; color:#94a3b8;">
                Paste a link below to fetch new tracks. They will appear in your library automatically.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        yt_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        custom_name = st.text_input("Custom filename (optional)", placeholder="Leave blank to use video title")
        
        # --- Advanced Settings for bypassing blocks ---
        with st.expander("🛠️ Advanced Settings (Bypass 403 Forbidden)"):
            st.markdown("""
            YouTube often blocks requests from cloud servers. If you get a **403 Forbidden** error:
            1. Use a **Cookies** file (Netscape format). Use 'Get cookies.txt' extension.
            2. Or try a different video.
            """)
            cookie_text = st.text_area("Paste Cookies Content", height=100, help="Paste the content of your cookies.txt here.")
            force_update = st.checkbox("Force update yt-dlp & ffmpeg before download", value=False)
            col_client, col_mobile = st.columns(2)
            with col_client:
                # Changed default to android (index 1) as it often handles challenges better
                player_client = st.selectbox("Player Client", ["android", "ios", "web", "mweb", "tv"], index=0, help="Changing this can help if a video is blocked or signature fails.")
            with col_mobile:
                use_mobile_client = st.checkbox("Use Advanced Client Strategy", value=True)
            
            st.info("💡 **Tip:** If you see 'n challenge solving failed', ensure you have **Node.js** installed on your server/computer. I've added it to `packages.txt` for Streamlit Cloud.")

        if st.button("⬇️ Download as MP3", type="primary", width='stretch'):
            if yt_url.strip():
                # Update only if forced or if it's the first time
                if force_update:
                    with st.spinner("🎵 Updating downloader tools..."):
                        try:
                            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "static-ffmpeg"], check=True, capture_output=True)
                        except Exception as e:
                            st.warning(f"Update failed: {e}")
                
                # 1. Try to find ffmpeg (System first, then static-ffmpeg)
                ffmpeg_location = shutil.which("ffmpeg")
                if not ffmpeg_location:
                    try:
                        import static_ffmpeg
                        pkg_dir = os.path.dirname(static_ffmpeg.__file__)
                        potential_bins = [
                            os.path.join(pkg_dir, "bin", "win32"),
                            os.path.join(pkg_dir, "bin"),
                            os.path.join(pkg_dir, "static_ffmpeg", "bin", "win32")
                        ]
                        ffmpeg_exe = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
                        for pb in potential_bins:
                            target_exe = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
                            target = os.path.join(pb, target_exe)
                            if os.path.exists(target):
                                ffmpeg_location = target
                                break
                    except:
                        pass
                
                # Ultimate fallback for Streamlit Cloud (Linux) if static_ffmpeg doesn't work out of the box
                if not ffmpeg_location and os.name != 'nt':
                    if os.path.exists("/usr/bin/ffmpeg"):
                        ffmpeg_location = "/usr/bin/ffmpeg"

                # 2. Check for Node.js (required for 'n challenge' signature decryption)
                # Streamlit Cloud usually has nodejs if added to packages.txt
                node_available = shutil.which("node") or shutil.which("nodejs")
                if not node_available:
                    with st.spinner("🔧 Providing JavaScript runtime for bypass..."):
                        try:
                            # Try nodejs-bin as fallback
                            subprocess.run([sys.executable, "-m", "pip", "install", "nodejs-bin"], capture_output=True)
                            import nodejs_bin
                            node_dir = os.path.dirname(nodejs_bin.__file__)
                            # Exhaustive search for the node binary
                            for sub in ["bin", "node_bin", "scripts", "Scripts", ""]:
                                bp = os.path.abspath(os.path.join(node_dir, sub))
                                for exe in ["node", "node.exe", "nodejs"]:
                                    if os.path.exists(os.path.join(bp, exe)):
                                        if bp not in os.environ["PATH"]:
                                            os.environ["PATH"] = bp + os.pathsep + os.environ["PATH"]
                                        node_available = os.path.join(bp, exe)
                                        break
                                if node_available: break
                        except: pass

                with st.spinner("🎵 Downloading and converting to MP3..."):
                    try:
                        output_template = f"{custom_name.strip()}.%(ext)s" if custom_name.strip() else "%(title)s.%(ext)s"
                        
                        # Create temporary cookie file if provided
                        cookie_file_path = None
                        final_cookie_text = cookie_text.strip()
                        
                        # Fallback to Streamlit Secrets for cookies if available
                        if not final_cookie_text and "YOUTUBE_COOKIES" in st.secrets:
                            final_cookie_text = st.secrets["YOUTUBE_COOKIES"]
                            
                        if final_cookie_text:
                            fd, cookie_file_path = tempfile.mkstemp(suffix=".txt")
                            with os.fdopen(fd, 'w') as tmp:
                                tmp.write(final_cookie_text)

                        # Build the command
                        cmd = [
                            sys.executable, "-m", "yt_dlp",
                            "-x",
                            "--audio-format", "mp3",
                            "--audio-quality", "192K",
                            "-o", output_template,
                            "--no-playlist",
                            "--no-check-certificate",
                            "--prefer-free-formats",
                            "--format", "bestaudio/best",
                            "--add-header", "Accept-Language:en-US,en;q=0.9"
                        ]
                        
                        # Add cookies if available
                        if cookie_file_path:
                            cmd.extend(["--cookies", cookie_file_path])
                        elif os.name == 'nt':
                            try: cmd.extend(["--cookies-from-browser", "chrome+edge"])
                            except: pass
                            
                        # Strategy helper
                        def get_cmd_for_strat(base_cmd, strat):
                            c = base_cmd.copy()
                            # ios and android_music are best for bypassing n-challenge
                            c.extend(["--extractor-args", f"youtube:player_client={strat}"])
                            if "ios" in strat:
                                c.extend(["--user-agent", "com.google.ios.youtube/19.12.3 (iPhone16,2; U; CPU iOS 17_4_1 like Mac OS X; en_US) gzip"])
                            elif "android" in strat:
                                c.extend(["--user-agent", "com.google.android.youtube/19.12.39 (Linux; U; Android 14; en_US) gzip"])
                            elif "tv" in strat:
                                c.extend(["--user-agent", "Mozilla/5.0 (Chromecast; Google TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"])
                            
                            # Add referer to look less like a direct bot request
                            c.extend(["--referer", "https://www.youtube.com/"])
                            return c

                        # Set initial strategy to Android VR (currently the most resilient against n-challenge without JS)
                        # We also try android_music and ios.
                        initial_strat = "android,android_music,ios"
                        full_cmd = get_cmd_for_strat(cmd, initial_strat)
                        
                        # Add these to completely bypass the need for a JS runtime in yt-dlp
                        full_cmd.extend(["--extractor-args", "youtube:player_skip=js;youtube:player_client=android"])
                        
                        # Set ffmpeg location if we found a non-system one
                        if ffmpeg_location and not shutil.which("ffmpeg"):
                            full_cmd.extend(["--ffmpeg-location", ffmpeg_location])
                        
                        full_cmd.extend([
                            "--restrict-filenames" if not custom_name.strip() else "--no-restrict-filenames",
                            yt_url.strip()
                        ])
                        
                        # --- TRY 1 ---
                        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=300, env=os.environ)
                        
                        # --- AUTOMATIC RETRY IF BLOCKED OR SIGNATURE FAILS ---
                        is_blocked = "403" in result.stderr or "forbidden" in result.stderr.lower()
                        is_challenge = "signature" in result.stderr.lower() or "n challenge" in result.stderr.lower()
                        is_bot = "confirm you're not a bot" in result.stderr.lower()
                        
                        if result.returncode != 0 and (is_blocked or is_challenge or is_bot):
                            st.info("🔄 Issue detected. Attempting deep bypass and recursive retries...")
                            try:
                                # Update and clear cache
                                subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True)
                                subprocess.run([sys.executable, "-m", "yt_dlp", "--rm-cache-dir"], capture_output=True)
                            except: pass
                                
                            # Expanded Strategy Pool
                            strategies = [
                                "ios", "android_music", "android", "web,tv", 
                                "mweb,ios", "web_creator", "tv,android", "mweb"
                            ]
                            
                            for strat in strategies:
                                st.caption(f"Recursive retry attempt using strategy: {strat}...")
                                retry_cmd = get_cmd_for_strat(cmd, strat)
                                if ffmpeg_location and not shutil.which("ffmpeg"):
                                    retry_cmd.extend(["--ffmpeg-location", ffmpeg_location])
                                
                                # Add deep bypass flags
                                retry_cmd.extend(["--geo-bypass", "--no-check-certificate"])
                                retry_cmd.extend([
                                    "--restrict-filenames" if not custom_name.strip() else "--no-restrict-filenames",
                                    yt_url.strip()
                                ])
                                
                                result = subprocess.run(retry_cmd, capture_output=True, text=True, timeout=300, env=os.environ)
                                if result.returncode == 0:
                                    st.success(f"✅ Success! Bypass found with {strat} strategy.")
                                    break
                                elif "429" in result.stderr:
                                    st.warning(f"⚠️ Rate limited on {strat}. Pausing...")
                                    time.sleep(2)
                        
                        # Cleanup cookie file and any leftover webm/m4a files
                        if cookie_file_path and os.path.exists(cookie_file_path):
                            try: os.remove(cookie_file_path)
                            except: pass
                        
                        # Only cleanup temp files, not supported audio
                        for f in os.listdir("."):
                            if f.endswith(".part") or f.endswith(".ytdl"):
                                try: os.remove(f)
                                except: pass
                        
                        if result.returncode == 0:
                            # Upload to Supabase if available
                            downloaded_file = None
                            # Find all matching mp3s and pick the most recent one
                            matches = []
                            _audio_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
                            for f in os.listdir("."):
                                if f.lower().endswith(_audio_exts):
                                    if not custom_name.strip() or custom_name.strip() in f:
                                        matches.append(f)
                            
                            if matches:
                                matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                                downloaded_file = matches[0]
                             
                            if downloaded_file and supabase_client:
                                with st.spinner("☁️ Uploading to Supabase Storage..."):
                                    try:
                                        with open(downloaded_file, "rb") as f:
                                            supabase_client.storage.from_(STORAGE_BUCKET).upload(
                                                path=downloaded_file,
                                                file=f,
                                                file_options={"content-type": "audio/mpeg"}
                                            )
                                        os.remove(downloaded_file) # Clean up local
                                        st.success("✅ Uploaded to Supabase!")
                                    except Exception as upload_err:
                                        st.warning(f"Local download ok, but Supabase upload failed: {upload_err}")

                            st.success("✅ Download complete! Adding to library...")
                            st.balloons()
                            import time
                            time.sleep(2)
                            st.rerun()
                        else:
                            err_msg = result.stderr
                            if "403: Forbidden" in err_msg:
                                st.error("❌ **YouTube blocked the request (403 Forbidden).**\n\nYouTube has flagged this server's IP. To fix this:\n1. Expand 'Advanced Settings' above.\n2. Paste your **YouTube Cookies** (Netscape format).\n3. Try again.\n\n*Changing the 'Player Client' in Advanced Settings also helps.*")
                            elif "n challenge" in err_msg.lower() or "signature" in err_msg.lower():
                                st.error("❌ **Signature Challenge Failed even after automatic retries.**\n\nYouTube is using a new security measure that requires a JavaScript runtime. I've attempted to automatically install a Node.js runtime and retry with different strategies, but it still failed. To fix this definitively:\n1. Expand **Advanced Settings** above.\n2. Paste your **YouTube Cookies** (Netscape format).\n3. Try again. This bypasses the signature challenge entirely.")
                            elif "Requested format is not available" in err_msg:
                                st.error("❌ **Format not available.**\n\nYouTube is hiding the audio formats for this video from this server. Try using **Cookies** or changing the **Player Client** to **Android**.")
                            elif "ffmpeg" in err_msg.lower():
                                st.error("❌ **ffmpeg not found.**\n\nConversion to MP3 failed. I've attempted to install it. Please try again.")
                            else:
                                st.error(f"Download failed:\n```\n{err_msg[-500:]}\n```")
                    except subprocess.TimeoutExpired:
                        st.error("⏱️ Download timed out (5 min limit). Try a shorter video.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter a YouTube URL.")
    
    with tab_upload:
        st.markdown("### 📤 Upload an audio file directly")
        uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "m4a", "webm", "wav", "ogg"])
        if uploaded_file is not None:
            save_name = st.text_input("Save as (filename)", value=uploaded_file.name, key="upload_save_name")
            # Auto-append .mp3 only if no supported extension is present
            _audio_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
            if not any(save_name.lower().endswith(ext) for ext in _audio_exts):
                save_name += ".mp3"
            if st.button("💾 Save Song", key="save_upload_btn"):
                if supabase_client:
                    with st.spinner("☁️ Uploading to Supabase..."):
                        try:
                            supabase_client.storage.from_(STORAGE_BUCKET).upload(
                                path=save_name,
                                file=uploaded_file.getbuffer().tobytes(),
                                file_options={"content-type": "audio/mpeg"}
                            )
                            st.success(f"✅ Uploaded **{save_name}** to Supabase!")
                        except Exception as e:
                            st.error(f"Supabase upload failed: {e}")
                else:
                    with open(save_name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ Saved locally as **{save_name}**")
                
                st.balloons()
                import time; time.sleep(1)
                st.rerun()
    
    with tab_manage:
        st.markdown("### 📋 Current Song Library")
        
        # Add refresh button in management tab too
        _refresh_col, _debug_col = st.columns([1, 1])
        with _refresh_col:
            if st.button("🔄 Rescan Library", key="rescan_btn", width='stretch'):
                st.session_state._refresh_music = True
                st.rerun()
        
        with _debug_col:
            with st.expander("🛠️ Library Debug"):
                st.write(f"**CWD:** `{os.getcwd()}`")
                st.write(f"**Total Songs Found:** {len(all_mp3s)}")
                st.write("**Local Paths Scanned:**")
                st.json(all_mp3s)
            
        current_mp3s = all_mp3s # Use the already computed list
        if not current_mp3s:
            st.info("No songs found.")
        else:
            st.caption(f"**{len(current_mp3s)}** songs in library")
            for mp3 in sorted(current_mp3s):
                # Try to get size from supabase or local
                try:
                    if supabase_client:
                        # Listing already gave us some info but let's keep it simple
                        file_size_mb = 0 # Difficult to get size for each without extra calls
                    else:
                        file_size_mb = os.path.getsize(mp3) / (1024 * 1024)
                except:
                    file_size_mb = 0

                mc1, mc2, mc3 = st.columns([3, 1, 1])
                mc1.markdown(f"🎵 **{clean_song_name(mp3)}**")
                if file_size_mb > 0:
                    mc2.caption(f"{file_size_mb:.1f} MB")
                else:
                    mc2.caption("Cloud")
                
                if mc3.button("🗑️", key=f"del_song_{mp3}", help=f"Delete {mp3}"):
                    st.session_state[f"confirm_del_song_{mp3}"] = True
                
                if st.session_state.get(f"confirm_del_song_{mp3}", False):
                    st.warning(f"⚠️ Delete **{mp3}**? This cannot be undone.")
                    yc, nc = st.columns(2)
                    if yc.button("✅ Yes, Delete", key=f"yes_del_song_{mp3}"):
                        try:
                            if supabase_client:
                                supabase_client.storage.from_(STORAGE_BUCKET).remove([mp3])
                            if os.path.exists(mp3):
                                os.remove(mp3)
                            st.toast(f"🗑️ '{mp3}' deleted.", icon="🗑️")
                            st.session_state[f"confirm_del_song_{mp3}"] = False
                            import time; time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting file: {e}")
                    if nc.button("❌ No, Keep", key=f"no_del_song_{mp3}"):
                        st.session_state[f"confirm_del_song_{mp3}"] = False
                        st.rerun()
    st.stop()

if menu == "MyLove Special":
    import proposal
    proposal.show_proposal(USER)
    st.stop()

if menu == "Notifications":
    import proposal
    proposal.show_admin_notifications(USER)
    st.stop()

# ---------------- DAILY ENTRY ----------------
if menu == "Daily Entry":
    st.title("📅 Smart Entry")

    date = st.date_input("Date")

    # Persistent Tab Navigation
    st.markdown("""
        <style>
        /* Container for radio to look like tabs - Scoped specifically to Daily Entry */
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) > div {
            background-color: rgba(255, 255, 255, 0.05) !important;
            padding: 6px !important;
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            gap: 10px !important;
            margin-bottom: 20px !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
            justify-content: space-between !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            -ms-overflow-style: none !important;  /* IE and Edge */
            scrollbar-width: none !important;  /* Firefox */
        }
        /* Hide scrollbar for Chrome, Safari and Opera */
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) > div::-webkit-scrollbar {
            display: none !important;
        }
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) label {
            position: relative !important;
            background: transparent !important;
            padding: 12px 24px !important;
            border-radius: 10px !important;
            transition: all 0.2s ease-in-out !important;
            color: #94a3b8 !important;
            font-weight: 600 !important;
            border: none !important;
            cursor: pointer !important;
            user-select: none !important;
            touch-action: manipulation !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex: 1 1 0% !important; /* Equal distribution for huge touch targets */
            text-align: center !important;
            -webkit-tap-highlight-color: transparent !important;
            white-space: nowrap !important; /* Force text to remain strictly horizontal */
        }
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) label:hover {
            color: #60a5fa !important;
            background: rgba(96, 165, 250, 0.08) !important;
        }
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) label[data-checked="true"] {
            background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        }
        /* Hide the radio group main label */
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) div[data-testid="stWidgetLabel"] { 
            display: none !important; 
        }
        /* Stretch the native touch target to cover the entire label bounding box for instant mobile response */
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) div[role="radiogroup"] > label > div:first-child { 
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            opacity: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            cursor: pointer !important;
            z-index: 2 !important;
        }
        /* Keep text above the absolute overlay so it remains readable and crisp */
        div[data-testid="stRadio"]:has(input[id*="daily_tab_persist"]) div[role="radiogroup"] > label > div:last-child {
            position: relative !important;
            z-index: 3 !important;
            pointer-events: none !important;
            white-space: nowrap !important; /* Force text strictly horizontal */
        }
        </style>
    """, unsafe_allow_html=True)
    
    selected_tab = st.radio("Tab Selection", ["📝 Log Activities", "🌙 Sleep & Wake Log", "⚙️ Manage Defaults"], 
                            horizontal=True, label_visibility="collapsed", key="daily_tab_persist")

    if selected_tab == "📝 Log Activities":
        _user_defaults = get_user_defaults(USER)
        base_activities = [
            "Study", "Revision", "Book Reading", "Answer Writing", "Practice", "Test",
            "Entertainment", "Social Media", "TalkOnCall", "Food", "Transport",
            "Office", "WFH", "Coaching", "WatchingMatch", "WentOutside",
            "Turf", "Travelling", "Powernap"
        ]

        # Activities that share user-managed subjects
        _SUBJ_ACTS = ["Study", "Revision", "Answer Writing", "Practice"]

        try:
            custom_df = read_sql("SELECT name, activity_type, tracking_type FROM custom_boxes WHERE username=%s", (USER,))
            custom = custom_df['name'].tolist()
            custom_type_map = dict(zip(custom_df['name'], custom_df['activity_type']))
            custom_track_map = dict(zip(custom_df['name'], custom_df['tracking_type']))
        except:
            custom = []
            custom_type_map = {}
            custom_track_map = {}

        # Activity selection with inline delete
        _act_col, _del_col = st.columns([3, 1])
        with _act_col:
            activity = st.selectbox("Activity", base_activities + custom + ["+ Add New"])
        
        with _del_col:
            if activity in custom:
                if st.button("🗑️", key=f"del_act_{activity}", help="Delete Activity"):
                    st.session_state[f"confirm_del_act_{activity}"] = True
                if st.session_state.get(f"confirm_del_act_{activity}", False):
                    st.markdown(f"⚠️ Delete **{activity}**?", unsafe_allow_html=True)
                    _yc, _nc = st.columns([1, 1])
                    with _yc:
                        if st.button("✅ Yes", key=f"yes_del_act_{activity}"):
                            c.execute("DELETE FROM custom_boxes WHERE name=%s AND username=%s", (activity, USER))
                            conn.commit()
                            st.toast(f"🗑️ Activity '{activity}' deleted.", icon="🗑️")
                            st.session_state[f"confirm_del_act_{activity}"] = False
                            st.rerun()
                    with _nc:
                        if st.button("❌ No", key=f"no_del_act_{activity}"):
                            st.session_state[f"confirm_del_act_{activity}"] = False
                            st.rerun()
            elif activity != "+ Add New":
                st.caption("Base activity", help="Base activities cannot be deleted")

        if activity == "+ Add New":
            new_act_col1, new_act_col2, new_act_col3 = st.columns([2, 1, 1])
            with new_act_col1:
                new = st.text_input("New Activity Name")
            with new_act_col2:
                new_act_type = st.selectbox("Activity Type", ["Productive", "Essential", "Waste"], index=2)
            with new_act_col3:
                _new_track_mode = st.selectbox("Tracking Mode", ["Hours only", "Expense + Hours"])
            
            new_track_type = "Expense (₹)" if _new_track_mode == "Expense + Hours" else "Hours"
            if st.button("Save Activity"):
                if new.strip():
                    c.execute("INSERT INTO custom_boxes(name, username, activity_type, tracking_type) VALUES(%s, %s, %s, %s)", (new.strip(), USER, new_act_type, new_track_type))
                    conn.commit()
                    st.toast(f"✅ Activity '{new.strip()}' added!", icon="✅")
                    import time; time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Please enter an activity name.")

        sub1 = sub2 = ""
        if activity in _SUBJ_ACTS:
            _user_subjs = get_user_subjects(USER)
            
            # Ensure "Current Affairs" exists in user_subjects
            if "Current Affairs" not in _user_subjs:
                try:
                    c.execute("INSERT INTO user_subjects (username, subject) VALUES (%s, %s) ON CONFLICT DO NOTHING", (USER, "Current Affairs"))
                    conn.commit()
                    _user_subjs = get_user_subjects(USER)
                except Exception:
                    pass

            if activity == "Study":
                # Find default study mode
                _def_sub1, _def_sub2 = _user_defaults.get("Study", ("", ""))
                _def_mode_idx = 1 if _def_sub1 == "Current Affairs" else 0
                
                _study_mode = st.radio("Study Mode", ["Static GS Syllabus", "Current Affairs"], index=_def_mode_idx, horizontal=True, key="de_study_mode")
                if _study_mode == "Current Affairs":
                    sub1 = "Current Affairs"
                    
                    # Find default CA source
                    _ca_options = ["Newspaper (The Hindu / Indian Express)", "Monthly Compilation", "PIB / PRS / Yojana", "Editorial Analysis", "Custom Topic"]
                    _def_ca_idx = 0
                    if _def_sub2 in _ca_options:
                        _def_ca_idx = _ca_options.index(_def_sub2)
                    elif _def_sub2:
                        _def_ca_idx = 4 # Default to custom topic if some value exists but not in pre-filled list
                        
                    _ca_source = st.selectbox("Source / Topic", _ca_options, index=_def_ca_idx, key="de_ca_source")
                    if _ca_source == "Custom Topic":
                        _custom_val = _def_sub2 if _def_sub2 not in _ca_options[:-1] else ""
                        sub2 = st.text_input("Custom Topic Name", value=_custom_val, placeholder="e.g. G20 Summit, DPI", key="de_ca_custom_topic")
                    else:
                        sub2 = _ca_source
                else:
                    # Static GS Syllabus - show standard subject selector (excluding Current Affairs to avoid confusion)
                    _static_subjs = [s for s in _user_subjs if s != "Current Affairs"]
                    _subj_col, _subj_del_col = st.columns([3, 1])
                    with _subj_col:
                        _def_subj_idx = 0
                        if _def_sub1 in _static_subjs:
                            _def_subj_idx = _static_subjs.index(_def_sub1)
                        sub1 = st.selectbox("Subject", _static_subjs + ["+ Add New"], index=_def_subj_idx, key="de_subject_sel")
                    with _subj_del_col:
                        if sub1 in _user_subjs:
                            if st.button("🗑️", key=f"del_subj_{sub1}"):
                                st.session_state[f"confirm_del_subj_{sub1}"] = True
                        if sub1 in _user_subjs and st.session_state.get(f"confirm_del_subj_{sub1}", False):
                            st.markdown(f"⚠️ Delete **{sub1}**?")
                            _yc, _nc = st.columns([1, 1])
                            with _yc:
                                if st.button("✅ Yes", key=f"yes_del_subj_{sub1}"):
                                    c.execute("DELETE FROM user_subjects WHERE username=%s AND subject=%s", (USER, sub1))
                                    conn.commit()
                                    st.session_state[f"confirm_del_subj_{sub1}"] = False
                                    st.toast(f"🗑️ Subject '{sub1}' deleted.", icon="🗑️")
                                    st.rerun()
                            with _nc:
                                if st.button("❌ No", key=f"no_del_subj_{sub1}"):
                                    st.session_state[f"confirm_del_subj_{sub1}"] = False
                                    st.rerun()
                    
                    if sub1 == "+ Add New":
                        _new_subj_col, _ = st.columns([3, 1])
                        with _new_subj_col:
                            _new_subj = st.text_input("Subject Name", key="de_new_subj")
                            if st.button("➕ Add Subject", key="de_add_subj_btn"):
                                _ns = _new_subj.strip()
                                if _ns:
                                    c.execute("INSERT INTO user_subjects (username, subject) VALUES (%s, %s) ON CONFLICT DO NOTHING", (USER, _ns))
                                    conn.commit()
                                    st.toast(f"✅ Subject '{_ns}' added!", icon="✅")
                                    import time; time.sleep(1)
                                    st.rerun()
            else:
                # Other subject-based activities: Revision, Answer Writing, Practice
                _def_sub1, _def_sub2 = _user_defaults.get(activity, ("", ""))
                _def_subj_idx = 0
                if _def_sub1 in _user_subjs:
                    _def_subj_idx = _user_subjs.index(_def_sub1)
                _subj_col, _subj_del_col = st.columns([3, 1])
                with _subj_col:
                    sub1 = st.selectbox("Subject", _user_subjs + ["+ Add New"], index=_def_subj_idx, key="de_subject_sel")
                with _subj_del_col:
                    if sub1 in _user_subjs:
                        if st.button("🗑️", key=f"del_subj_{sub1}"):
                            st.session_state[f"confirm_del_subj_{sub1}"] = True
                    if sub1 in _user_subjs and st.session_state.get(f"confirm_del_subj_{sub1}", False):
                        st.markdown(f"⚠️ Delete **{sub1}**?")
                        _yc, _nc = st.columns([1, 1])
                        with _yc:
                            if st.button("✅ Yes", key=f"yes_del_subj_{sub1}"):
                                c.execute("DELETE FROM user_subjects WHERE username=%s AND subject=%s", (USER, sub1))
                                conn.commit()
                                st.session_state[f"confirm_del_subj_{sub1}"] = False
                                st.toast(f"🗑️ Subject '{sub1}' deleted.", icon="🗑️")
                                st.rerun()
                        with _nc:
                            if st.button("❌ No", key=f"no_del_subj_{sub1}"):
                                st.session_state[f"confirm_del_subj_{sub1}"] = False
                                st.rerun()
                
                if sub1 == "+ Add New":
                    _new_subj_col, _ = st.columns([3, 1])
                    with _new_subj_col:
                        _new_subj = st.text_input("Subject Name", key="de_new_subj")
                        if st.button("➕ Add Subject", key="de_add_subj_btn"):
                            _ns = _new_subj.strip()
                            if _ns:
                                c.execute("INSERT INTO user_subjects (username, subject) VALUES (%s, %s) ON CONFLICT DO NOTHING", (USER, _ns))
                                conn.commit()
                                st.toast(f"✅ Subject '{_ns}' added!", icon="✅")
                                import time; time.sleep(1)
                                st.rerun()

        # Activity specific fields
        if activity == "Study":
            if "de_study_mode" in st.session_state and st.session_state["de_study_mode"] == "Current Affairs":
                pass
            else:
                _def_sub1, _def_sub2 = _user_defaults.get("Study", ("", ""))
                _def_ch = _def_sub2 if _def_sub1 != "Current Affairs" else ""
                sub2 = st.text_input("Chapter / Topic", value=_def_ch, max_chars=50, placeholder="Enter chapter/topic...", key="de_study_static_ch")
        elif activity == "Revision":
            _def_sub1, _def_sub2 = _user_defaults.get("Revision", ("", ""))
            sub2 = st.text_input("Chapter/Pages Revised", value=_def_sub2, key="de_rev_ch")
        elif activity == "Book Reading":
            _def_sub1, _def_sub2 = _user_defaults.get("Book Reading", ("", ""))
            sub1 = st.text_input("Book Title", value=_def_sub1, key="de_book_title")
            sub2 = st.text_input("Chapters/Pages", value=_def_sub2, key="de_book_detail")
        elif activity in ["Answer Writing", "Practice"]:
            _def_sub1, _def_sub2 = _user_defaults.get(activity, ("", ""))
            _def_q = 0
            if _def_sub2 and _def_sub2.startswith("Q:"):
                try:
                    _def_q = int(_def_sub2.split(":")[1])
                except:
                    pass
            _q_solved = st.number_input("Questions Solved", min_value=0, value=_def_q, step=1, key=f"de_q_{activity}")
            sub2 = f"Q:{int(_q_solved)}" if _q_solved > 0 else ""
        elif activity == "Test":
            _def_sub1, _def_sub2 = _user_defaults.get("Test", ("", ""))
            _def_test_idx = 0
            if _def_sub1 in test_types:
                _def_test_idx = test_types.index(_def_sub1)
            sub1 = st.selectbox("Test Type", test_types, index=_def_test_idx)
            if sub1 == "D-Day Exam":
                sub2 = ""
            else:
                sub2 = st.text_input("#Questions", value=_def_sub2)
        elif activity == "Office":
            _def_sub1, _def_sub2 = _user_defaults.get("Office", ("", ""))
            sub1 = st.text_input("Work Notes", value=_def_sub1, key="de_office_notes")
        elif activity == "Coaching":
            _def_sub1, _def_sub2 = _user_defaults.get("Coaching", ("", ""))
            sub1 = st.text_input("Subject", value=_def_sub1, key="de_coaching_topic")
            sub2 = st.text_input("Notes", value=_def_sub2, key="de_coaching_notes")
        elif activity == "WFH":
            _def_sub1, _def_sub2 = _user_defaults.get("WFH", ("", ""))
            sub1 = st.text_input("Work Notes", value=_def_sub1, key="de_wfh_notes")
        elif activity == "Entertainment":
            _def_sub1, _def_sub2 = _user_defaults.get("Entertainment", ("", ""))
            _def_ent_idx = 0
            if _def_sub1 in ent_types:
                _def_ent_idx = ent_types.index(_def_sub1)
            sub1 = st.selectbox("Type", ent_types, index=_def_ent_idx)
            if sub1 == "Movie":
                _def_mode_idx = 0
                if _def_sub2 in movie_modes:
                    _def_mode_idx = movie_modes.index(_def_sub2)
                sub2 = st.selectbox("Mode", movie_modes, index=_def_mode_idx)
        elif activity == "Social Media":
            _def_sub1, _def_sub2 = _user_defaults.get("Social Media", ("", ""))
            _def_plat_idx = 0
            if _def_sub1 in social_platform:
                _def_plat_idx = social_platform.index(_def_sub1)
            _def_cont_idx = 0
            if _def_sub2 in content_type:
                _def_cont_idx = content_type.index(_def_sub2)
            sub1 = st.selectbox("Platform", social_platform, index=_def_plat_idx)
            sub2 = st.selectbox("Content", content_type, index=_def_cont_idx)
        elif activity == "TalkOnCall":
            _def_sub1, _def_sub2 = _user_defaults.get("TalkOnCall", ("", ""))
            _def_whom_idx = 0
            if _def_sub1 in talkoncall_withwhom:
                _def_whom_idx = talkoncall_withwhom.index(_def_sub1)
            sub1 = st.selectbox("With Whom", talkoncall_withwhom, index=_def_whom_idx)
            sub2 = st.text_input("Topic / Notes", value=_def_sub2, key="de_talk_notes")
        elif activity == "Food":
            _def_sub1, _def_sub2 = _user_defaults.get("Food", ("", ""))
            _def_food_idx = 0
            if _def_sub1 in food_sources:
                _def_food_idx = food_sources.index(_def_sub1)
            sub1 = st.selectbox("Source", food_sources, index=_def_food_idx)
        elif activity == "Transport":
            _def_sub1, _def_sub2 = _user_defaults.get("Transport", ("", ""))
            _def_trans_idx = 0
            if _def_sub1 in transport_services:
                _def_trans_idx = transport_services.index(_def_sub1)
            sub1 = st.selectbox("Service", transport_services, index=_def_trans_idx)
        elif activity == "WentOutside":
            _def_sub1, _def_sub2 = _user_defaults.get("WentOutside", ("", ""))
            sub1 = st.text_input("Location", value=_def_sub1, key="de_went_outside")
        elif activity == "Turf":
            _def_sub1, _def_sub2 = _user_defaults.get("Turf", ("", ""))
            sub1 = st.text_input("Sport", value=_def_sub1, key="de_turf_sport")
            sub2 = st.text_input("Details", value=_def_sub2, key="de_turf_detail")
        elif activity == "Travelling":
            _def_sub1, _def_sub2 = _user_defaults.get("Travelling", ("", ""))
            _travel_modes = ["✈️ Flight", "🚂 Railway", "🚗 Other"]
            _def_travel_idx = 2
            if _def_sub1 in _travel_modes:
                _def_travel_idx = _travel_modes.index(_def_sub1)
            sub1 = st.selectbox("Mode", _travel_modes, index=_def_travel_idx, key="de_travel_mode")
            sub2 = st.text_input("Destination", value=_def_sub2, key="de_travel_dest")

        _track_both = activity in ["Food", "Transport", "WentOutside", "Turf", "Travelling", "Office", "WFH", "Coaching", "Test"]
        _track_by_expense = activity in ["Food", "Transport"]
        if activity in custom:
            _track_both = (custom_track_map.get(activity) == "Expense (₹)")
            _track_by_expense = False

        description = st.text_input("📝 Description (Optional)", key=f"de_desc_{activity}")

        _duration_mode = st.radio("⏱️ Duration Input", ["Hours", "Time Range (From-To)"], index=1, horizontal=True, key=f"de_dur_mode_{activity}")
        
        duration = 0.0
        amount = 0.0
        start_time = ""
        is_midnight_crossing = False
        duration_today = duration_tomorrow = 0.0
        from_h = from_m = to_h = to_m = 0

        def parse_time_value(raw):
            try:
                if ":" in str(raw):
                    h, m = str(raw).split(":", 1)
                    return int(h), int(m)
                return int(raw), 0
            except: return None

        if _duration_mode == "Hours":
            if _track_both:
                c1, c2 = st.columns(2)
                with c1: duration = st.number_input("⏱️ Hours", min_value=0.0, step=0.5, value=0.0, key=f"de_hours_{activity}")
                with c2: amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=0.0, key=f"de_amount_{activity}")
            elif _track_by_expense:
                amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=0.0)
            else:
                duration = st.number_input("⏱️ Hours", min_value=0.0, step=0.5, value=0.0)
        else:
            c1, c2 = st.columns(2)
            with c1: from_time_raw = st.text_input("From Time", key=f"de_from_{activity}", placeholder="2:30 PM")
            with c2: to_time_raw = st.text_input("To Time", key=f"de_to_{activity}", placeholder="4:45 PM")
            if from_time_raw and to_time_raw:
                f_p, t_p = parse_time_value(from_time_raw), parse_time_value(to_time_raw)
                if f_p and t_p:
                    from_h, from_m = f_p
                    to_h, to_m = t_p
                    start_time = f"{from_h}:{from_m:02d}"
                    f_mins, t_mins = from_h * 60 + from_m, to_h * 60 + to_m
                    if t_mins < f_mins:
                        is_midnight_crossing = True
                        duration_today = (1440 - f_mins) / 60
                        duration_tomorrow = t_mins / 60
                        duration = duration_today + duration_tomorrow
                    else: duration = (t_mins - f_mins) / 60
                    st.caption(f"Duration: **{duration:.1f} hours**" + (" (spans midnight ⏰)" if is_midnight_crossing else ""))
            if _track_both: amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=0.0, key=f"de_amt_tr_{activity}")
        if st.button("💾 Save Activity", key="save_main_activity"):
            if duration > 0 or amount > 0:
                if is_midnight_crossing:
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date), activity, sub1, sub2, duration_today, amount, USER, f"{from_h}:{from_m:02d}", description))
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date + timedelta(days=1)), activity, sub1, sub2, duration_tomorrow, 0, USER, f"{to_h}:{to_m:02d}", description))
                else:
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date), activity, sub1, sub2, duration, amount, USER, start_time, description))
                conn.commit()
                if activity.strip().lower() == "powernap":
                    try:
                        if is_midnight_crossing:
                            c.execute("INSERT INTO health_logs (username, date, powernap) VALUES (%s, %s, %s) ON CONFLICT (username, date) DO UPDATE SET powernap = COALESCE(health_logs.powernap, 0) + EXCLUDED.powernap", (USER, str(date), duration_today))
                            c.execute("INSERT INTO health_logs (username, date, powernap) VALUES (%s, %s, %s) ON CONFLICT (username, date) DO UPDATE SET powernap = COALESCE(health_logs.powernap, 0) + EXCLUDED.powernap", (USER, str(date + timedelta(days=1)), duration_tomorrow))
                        else:
                            c.execute("INSERT INTO health_logs (username, date, powernap) VALUES (%s, %s, %s) ON CONFLICT (username, date) DO UPDATE SET powernap = COALESCE(health_logs.powernap, 0) + EXCLUDED.powernap", (USER, str(date), duration))
                        conn.commit()
                    except: pass
                st.toast(f"✅ Activity saved!", icon="✅")
                import time; time.sleep(1); st.rerun()
            else: st.warning("Enter duration/amount.")

        st.divider()
        st.markdown("### 📋 Activities Logged")
        _today_df = read_sql("SELECT id, type, subject, chapter, duration, amount, start_time, description FROM activities WHERE date=%s AND username=%s ORDER BY id", (str(date), USER))
        if _today_df.empty: st.caption("No activities logged for this date.")
        else:
            for _, _row in _today_df.iterrows():
                rid = int(_row['id'])
                parts = [_row['type']]
                if _row['subject']: parts.append(str(_row['subject']))
                ch = get_clean_chapter(_row['chapter'])
                st_v = _row.get('start_time') or ""
                if ch: parts.append(ch)
                if st_v: parts.append(f"[{st_v}]")
                val = f"{_row['duration']}h" if _row['duration'] > 0 else (f"₹{_row['amount']}" if _row['amount'] > 0 else "")
                if val: parts.append(val)
                l, r = st.columns([5, 1])
                
                raw_desc = _row.get('description')
                desc_text = ""
                if raw_desc and str(raw_desc).strip() and str(raw_desc).strip().lower() not in ('none', 'nan', 'null'):
                    desc_text = f"<br><span style='font-size:12px; color:#94a3b8;'>{str(raw_desc).strip()}</span>"
                l.markdown(f"• **{' | '.join(parts)}**{desc_text}", unsafe_allow_html=True)
                
                if r.button("🗑️", key=f"del_daily_{rid}"):
                    st.session_state[f"confirm_daily_del_{rid}"] = True
                
                if st.session_state.get(f"confirm_daily_del_{rid}", False):
                    st.warning("Delete this entry?", icon="⚠️")
                    yc, nc = st.columns([1, 1])
                    with yc:
                        if st.button("✅ Yes", key=f"yes_daily_del_{rid}", width='stretch'):
                            c.execute("DELETE FROM activities WHERE id=%s AND username=%s", (rid, USER))
                            conn.commit()
                            st.session_state[f"confirm_daily_del_{rid}"] = False
                            st.rerun()
                    with nc:
                        if st.button("❌ No", key=f"no_daily_del_{rid}", width='stretch'):
                            st.session_state[f"confirm_daily_del_{rid}"] = False
                            st.rerun()

    elif selected_tab == "🌙 Sleep & Wake Log":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%); border: 1.5px solid #2563eb; border-radius: 14px; padding: 18px 20px 10px 20px; margin-bottom: 18px;">
            <div style="font-size:17px; font-weight:700; color:#60a5fa; margin-bottom:10px;">🌙 Sleep & Wake Log</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display current values
        hl_res = read_sql("SELECT wakeup_time, sleep_time FROM health_logs WHERE username=%s AND date=%s", (USER, str(date)))
        curr_wu = hl_res.iloc[0]['wakeup_time'] if not hl_res.empty else ""
        curr_sl = hl_res.iloc[0]['sleep_time'] if not hl_res.empty else ""
        if curr_wu or curr_sl:
            st.info(f"Current Log: ☀️ Wake: **{curr_wu or 'N/A'}** | 🌙 Sleep: **{curr_sl or 'N/A'}**")

        def parse_time_sw(raw, always_am=False):
            raw = str(raw).strip()
            if not raw: return None, None
            try:
                if ":" in raw: h, m = map(int, raw.split(":", 1))
                else: h, m = int(raw), 0
                period = "AM" if always_am else ("PM" if 7 <= h <= 11 else "AM")
                if h == 0: h = 12
                return f"{h}:{m:02d} {period}", None
            except: return None, "Invalid format"

        c1, c2 = st.columns(2)
        with c1:
            wu_raw = st.text_input("⏰ Wakeup", key="wu_raw", placeholder="6:00")
            wu_f, wu_e = parse_time_sw(wu_raw, True)
            if wu_raw: 
                if wu_e: st.error(wu_e)
                else: st.caption(f"→ **{wu_f}** AM")
            if st.button("💾 Save Wakeup", key="save_wu"):
                if wu_f:
                    c.execute("""
                        INSERT INTO health_logs (username, date, wakeup_time)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (username, date) DO UPDATE SET 
                            wakeup_time = EXCLUDED.wakeup_time
                    """, (USER, str(date), wu_f))
                    conn.commit()
                    st.toast(f"✅ Wakeup saved!", icon="✅")
                    import time; time.sleep(1); st.rerun()
                else: st.warning("Enter wakeup time.")

        with c2:
            sl_raw = st.text_input("😴 Sleep", key="sl_raw", placeholder="11:00")
            sl_f, sl_e = parse_time_sw(sl_raw, False)
            if sl_raw:
                if sl_e: st.error(sl_e)
                else: st.caption(f"→ **{sl_f}**")
            if st.button("💾 Save Sleep", key="save_sl"):
                if sl_f:
                    c.execute("""
                        INSERT INTO health_logs (username, date, sleep_time)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (username, date) DO UPDATE SET 
                            sleep_time = EXCLUDED.sleep_time
                    """, (USER, str(date), sl_f))
                    conn.commit()
                    st.toast(f"✅ Sleep saved!", icon="✅")
                    import time; time.sleep(1); st.rerun()
                else: st.warning("Enter sleep time.")

    elif selected_tab == "⚙️ Manage Defaults":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%); border: 1.5px solid #2563eb; border-radius: 14px; padding: 18px 20px 10px 20px; margin-bottom: 18px;">
            <div style="font-size:17px; font-weight:700; color:#60a5fa; margin-bottom:4px;">⚙️ Manage Activity Defaults</div>
            <div style="font-size:13px; color:#94a3b8;">Set default subactivities, subjects, or notes for each activity type to auto-fill them during log entry and save time.</div>
        </div>
        """, unsafe_allow_html=True)

        _base_acts = [
            "Study", "Revision", "Book Reading", "Answer Writing", "Practice", "Test",
            "Entertainment", "Social Media", "TalkOnCall", "Food", "Transport",
            "Office", "WFH", "Coaching", "WentOutside", "Turf", "Travelling"
        ]
        # Query custom activities
        _custom_acts_df = read_sql("SELECT name FROM custom_boxes WHERE username=%s", (USER,))
        _custom_acts = _custom_acts_df['name'].tolist() if not _custom_acts_df.empty else []
        
        all_config_acts = _base_acts + _custom_acts
        
        # Load existing defaults
        _current_defaults = get_user_defaults(USER)
        
        selected_config_act = st.selectbox("Select Activity to Configure", all_config_acts, key="cfg_act_sel")
        
        # Display inputs based on selected activity
        def_sub1_val, def_sub2_val = _current_defaults.get(selected_config_act, ("", ""))
        
        new_def_sub1 = ""
        new_def_sub2 = ""
        
        st.markdown(f"### Configure **{selected_config_act}** Defaults")
        
        if selected_config_act == "Study":
            _study_mode = st.radio("Default Study Mode", ["Static GS Syllabus", "Current Affairs"], 
                                   index=1 if def_sub1_val == "Current Affairs" else 0, horizontal=True, key="cfg_study_mode")
            if _study_mode == "Current Affairs":
                new_def_sub1 = "Current Affairs"
                _ca_options = ["Newspaper (The Hindu / Indian Express)", "Monthly Compilation", "PIB / PRS / Yojana", "Editorial Analysis", "Custom Topic"]
                _def_ca_idx = 0
                if def_sub2_val in _ca_options:
                    _def_ca_idx = _ca_options.index(def_sub2_val)
                elif def_sub2_val:
                    _def_ca_idx = 4
                _ca_source = st.selectbox("Default Source", _ca_options, index=_def_ca_idx, key="cfg_ca_source")
                if _ca_source == "Custom Topic":
                    _custom_val = def_sub2_val if def_sub2_val not in _ca_options[:-1] else ""
                    new_def_sub2 = st.text_input("Default Custom Topic Name", value=_custom_val, key="cfg_ca_custom_topic")
                else:
                    new_def_sub2 = _ca_source
            else:
                _user_subjs = get_user_subjects(USER)
                _static_subjs = [s for s in _user_subjs if s != "Current Affairs"]
                _def_subj_idx = 0
                if def_sub1_val in _static_subjs:
                    _def_subj_idx = _static_subjs.index(def_sub1_val)
                new_def_sub1 = st.selectbox("Default Subject", _static_subjs, index=_def_subj_idx if _static_subjs else 0, key="cfg_subject_sel")
                
                # pre-fill default chapter/topic
                _def_ch = def_sub2_val if def_sub1_val != "Current Affairs" else ""
                new_def_sub2 = st.text_input("Default Chapter / Topic", value=_def_ch, placeholder="e.g. Fundamental Rights", key="cfg_study_ch")
                
        elif selected_config_act in ["Revision", "Answer Writing", "Practice"]:
            _user_subjs = get_user_subjects(USER)
            _def_subj_idx = 0
            if def_sub1_val in _user_subjs:
                _def_subj_idx = _user_subjs.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default Subject", _user_subjs, index=_def_subj_idx if _user_subjs else 0, key="cfg_subject_sel")
            
            if selected_config_act == "Revision":
                new_def_sub2 = st.text_input("Default Chapter/Pages Revised", value=def_sub2_val, key="cfg_rev_ch")
            elif selected_config_act in ["Answer Writing", "Practice"]:
                _def_q = 0
                if def_sub2_val and def_sub2_val.startswith("Q:"):
                    try:
                        _def_q = int(def_sub2_val.split(":")[1])
                    except:
                        pass
                _q_solved = st.number_input("Default Questions Solved", min_value=0, value=_def_q, step=1, key="cfg_q_solved")
                new_def_sub2 = f"Q:{int(_q_solved)}" if _q_solved > 0 else ""
                
        elif selected_config_act == "Book Reading":
            new_def_sub1 = st.text_input("Default Book Title", value=def_sub1_val, key="cfg_book_title")
            new_def_sub2 = st.text_input("Default Chapters/Pages", value=def_sub2_val, key="cfg_book_detail")
            
        elif selected_config_act == "Social Media":
            _plat_idx = 0
            if def_sub1_val in social_platform:
                _plat_idx = social_platform.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default Platform", social_platform, index=_plat_idx, key="cfg_sm_platform")
            
            _cont_idx = 0
            if def_sub2_val in content_type:
                _cont_idx = content_type.index(def_sub2_val)
            new_def_sub2 = st.selectbox("Default Content Type", content_type, index=_cont_idx, key="cfg_sm_content")
            
        elif selected_config_act == "TalkOnCall":
            _whom_idx = 0
            if def_sub1_val in talkoncall_withwhom:
                _whom_idx = talkoncall_withwhom.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default With Whom", talkoncall_withwhom, index=_whom_idx, key="cfg_talk_whom")
            new_def_sub2 = st.text_input("Default Topic / Notes", value=def_sub2_val, key="cfg_talk_notes")
            
        elif selected_config_act == "Entertainment":
            _ent_idx = 0
            if def_sub1_val in ent_types:
                _ent_idx = ent_types.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default Entertainment Type", ent_types, index=_ent_idx, key="cfg_ent_type")
            if new_def_sub1 == "Movie":
                _mode_idx = 0
                if def_sub2_val in movie_modes:
                    _mode_idx = movie_modes.index(def_sub2_val)
                new_def_sub2 = st.selectbox("Default Movie Mode", movie_modes, index=_mode_idx, key="cfg_movie_mode")
                
        elif selected_config_act == "Food":
            _food_idx = 0
            if def_sub1_val in food_sources:
                _food_idx = food_sources.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default Food Source", food_sources, index=_food_idx, key="cfg_food_src")
            
        elif selected_config_act == "Transport":
            _trans_idx = 0
            if def_sub1_val in transport_services:
                _trans_idx = transport_services.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default Service", transport_services, index=_trans_idx, key="cfg_trans_srv")
            
        elif selected_config_act == "Travelling":
            _travel_modes = ["✈️ Flight", "🚂 Railway", "🚗 Other"]
            _travel_idx = 2
            if def_sub1_val in _travel_modes:
                _travel_idx = _travel_modes.index(def_sub1_val)
            new_def_sub1 = st.selectbox("Default Travel Mode", _travel_modes, index=_travel_idx, key="cfg_travel_mode")
            new_def_sub2 = st.text_input("Default Destination", value=def_sub2_val, key="cfg_travel_dest")
            
        elif selected_config_act == "Turf":
            new_def_sub1 = st.text_input("Default Sport", value=def_sub1_val, key="cfg_turf_sport")
            new_def_sub2 = st.text_input("Default Details", value=def_sub2_val, key="cfg_turf_detail")
            
        else:
            # Custom/Default general activities (Office, WFH, Coaching, WentOutside, Custom activities, etc.)
            new_def_sub1 = st.text_input("Default Detail 1 (e.g. Location, Subject, Notes)", value=def_sub1_val, key="cfg_custom_sub1")
            new_def_sub2 = st.text_input("Default Detail 2 (e.g. Details, Notes)", value=def_sub2_val, key="cfg_custom_sub2")

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("💾 Save Activity Defaults", use_container_width=True, key="save_cfg_defaults"):
            try:
                c.execute("""
                    INSERT INTO user_defaults (username, activity, default_sub1, default_sub2)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username, activity) DO UPDATE SET
                        default_sub1 = EXCLUDED.default_sub1,
                        default_sub2 = EXCLUDED.default_sub2
                """, (USER, selected_config_act, new_def_sub1, new_def_sub2))
                conn.commit()
                st.toast(f"✅ Defaults for **{selected_config_act}** saved successfully!", icon="✅")
                import time; time.sleep(1)
                st.rerun()
            except Exception as ex:
                st.error(f"Error saving defaults: {ex}")

    # ── SMART WORK TIPS (Daily Entry Page) ──
    _de_df_all = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    if not _de_df_all.empty:
        _de_prod = _de_df_all[_de_df_all['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
        _de_waste = _de_df_all[~_de_df_all['type'].isin(PRODUCTIVE_TYPES + ESSENTIAL_TYPES + NEUTRAL_TYPES)]['duration'].sum()
        _de_ess = _de_df_all[_de_df_all['type'].isin(ESSENTIAL_TYPES)]['duration'].sum()
        _de_tips = generate_smart_work_tips(
            prod_hours=_de_prod, waste_hours=_de_waste, essential_hours=_de_ess,
            study_streak=streak(_de_df_all), focus_pct=focus_score(_de_df_all),
            subject_count=len(_de_df_all[_de_df_all['type'].isin(PRODUCTIVE_TYPES)]['subject'].unique()) if not _de_df_all.empty else 0,
            productivity_pct=0, context="general"
        )
        with st.expander("⚡ Smart Work Tips & UPSC Strategies", expanded=False):
            st.markdown(render_smart_work_section(_de_tips, max_tips=12), unsafe_allow_html=True)

# ---------------- CALENDAR ----------------
elif menu == "Calendar":
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
                html += f"<div class='merged-cal-prod' style='background: rgba(255,255,255,0.2); color: {text_for_prod}'>⏱️ {prod_hours:.1f}h</div>"
            
            # Add health & social data with high contrast
            if wu != '–' or st_ != '–':
                health_text = f"☀️ {wu}"
                if st_ != '–':
                    health_text += f" | 🌙 {st_}"
                html += f"<div class='merged-cal-health' style='background: rgba(255,255,255,0.2); color: {text_color}'>{health_text}</div>"
            
            if ent > 0 or out > 0:
                social_text = ""
                if ent > 0:
                    social_text += f"🎬 {ent:.1f}h"
                if out > 0:
                    if social_text:
                        social_text += f" | 🚶 {out:.1f}h"
                    else:
                        social_text = f"🚶 {out:.1f}h"
                html += f"<div class='merged-cal-social' style='background: rgba(255,255,255,0.2); color: {text_color}'>{social_text}</div>"
            
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
            st.metric("Study Hrs", f"{total_prod:.1f}h")
        
        with act_right:
            st.markdown("<div class='activities-right-section'>", unsafe_allow_html=True)
            
            if selected_date:
                if not date_acts.empty:
                    st.markdown(f"**📋 {date_str}**")
                    st.divider()
                    
                    for _, row in date_acts.iterrows():
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
                        
                        _val = f"{row['duration']}h" if row['duration'] > 0 else (f"₹{row['amount']}" if row['amount'] > 0 else "")
                        if _val: _parts.append(_val)
                        
                        activity_text = ' | '.join(_parts)
                        
                        # Create inline activity display with delete button
                        _act_container = st.container()
                        with _act_container:
                            _col_text, _col_del = st.columns([3.5, 1])
                            with _col_text:
                                st.caption(f"**{activity_text}**")
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
                        hours_str = f"{int(daily_prod[date_str])}h"
                    else:
                        color = "#1e293b"
                        hours_str = "–"
                    
                    title = f"{date_str}: {daily_prod.get(date_str, 0):.1f} hrs"
                    html += f"<div style='display:flex; flex-direction:column; align-items:center;'><div class='day-circle' style='background-color: {color}; border-color: {border_color};' title='{title}'>{hours_str if daily_prod.get(date_str, 0) > 0 else ''}</div></div>"
                else:
                    html += "<div></div>"
                    
        html += "</div>"    
        st.markdown(html, unsafe_allow_html=True)

# ---------------- SOCIAL LIFE ----------------
elif menu == "Social Life":
    st.title("🌟 Social Life")
    
    import calendar as calmod
    import datetime
    
    today = get_ist_now().date()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_year = st.number_input("Year", value=today.year, min_value=2020, max_value=2100, key="sm_cal_yr", step=1)
    with col2:
        selected_month = st.number_input("Month", value=today.month, min_value=1, max_value=12, key="sm_cal_mo", step=1)
    
    df = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
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
                dur_rounded = round(dur, 2)
                val = f"{dur_rounded:.2f}".rstrip('0').rstrip('.') + "h"
            elif amt > 0:
                val = f"₹{amt}"
            else:
                val = ""
            
            desc = ""
            if act['subject'] and act['subject'] != 'D-Day Exam': desc += str(act['subject']) + " "
            if act['chapter']: desc += str(act['chapter'])
            
            time_str = f"[{act['start_time']}] " if act.get('start_time') else ""
            
            main_text = f"{time_str}{act_type}"
            if val: main_text += f" ({val})"
            
            # Tag uses semi-transparent bg on colored cell
            tag_bg = "rgba(255,255,255,0.15)"
            tag_text = cell_text
            
            html += f"<div class='sm-act-tag' style='background: {tag_bg}; color: {tag_text};'>"
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
        if total_sm_dur > 0: st.metric("Total Hrs", f"{total_sm_dur:.1f}h")
        if total_sm_amt > 0: st.metric("Total Expense", f"₹{total_sm_amt:.1f}")
    
    with act_right:
        st.markdown("<div class='activities-right-section'>", unsafe_allow_html=True)
        
        if selected_date:
            if not date_acts.empty:
                st.markdown(f"**📋 {date_str}**")
                st.divider()
                
                for _, row in date_acts.iterrows():
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
                    
                    _val = f"{row['duration']}h" if row['duration'] > 0 else (f"₹{row['amount']}" if row['amount'] > 0 else "")
                    if _val: _parts.append(_val)
                    
                    activity_text = ' | '.join(_parts)
                    
                    _act_container = st.container()
                    with _act_container:
                        _col_text, _col_del = st.columns([3.5, 1])
                        with _col_text:
                            st.caption(f"**{activity_text}**")
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
elif menu == "Study Calendar":
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
                    agg[k] = {'type': t, 'subject': s, 'duration': 0.0, 'amount': 0.0, 'chapter_items': []}
                
                agg[k]['duration'] += dur
                agg[k]['amount'] += amt
                if c:
                    agg[k]['chapter_items'].append(str(c))
                    
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
            html += f"<div class='sc-cal-prod' style='background: rgba(255,255,255,0.2); color: {text_for_prod}'>⏱️ {prod_hours:.1f}h</div>"
        
        day_acts = daily_sc.get(date_str, [])
        
        # Subject abbreviation map
        _SUBJ_SHORT = {
            'History': 'HIST', 'Ancient': 'Ancient', 'Medieval': 'Medieval',
            'Modern': 'Modern', 'Art&Culture': 'ANC',
            'Geography': 'Geo', 'Indian-Geography': 'Ind-Geo',
            'Physical-Geography': 'Phy-Geo', 'Human-Geography': 'Human-Geo',
            'Environment': 'ENV', 'Economics': 'ECO',
            'Post Independence': 'PostIndep', 'Post-Independence': 'PostIndep',
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
                dur_rounded = round(dur, 2)
                val = f"{dur_rounded:.2f}h".rstrip('0').rstrip('.') + 'h' if '.' in f"{dur_rounded}" else f"{int(dur_rounded)}h"
                label_parts.append(val)
            elif amt > 0:
                label_parts.append(f"₹{amt}")
            
            label = ' · '.join(label_parts)
            
            html += f"<div class='sc-act-item' style='color: {item_text_color}; background: rgba(255,255,255,0.1);' title='{label}'>{label}</div>"
        
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
        st.metric("Study Hrs", f"{sc_total_dur:.1f}h")
    
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
                    
                    _val = f"{row['duration']}h" if row['duration'] > 0 else (f"₹{row['amount']}" if row['amount'] > 0 else "")
                    if _val: _parts.append(_val)
                    
                    activity_text = ' | '.join(_parts)
                    
                    _act_container = st.container()
                    with _act_container:
                        _col_text, _col_del = st.columns([3.5, 1])
                        with _col_text:
                            st.caption(f"**{activity_text}**")
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
elif menu == "Set Target":
    st.title("📚 Set Target")

    import datetime as _sm_dt
    GOAL_TYPES = ["Chapters", "Pages", "Questions Solved", "Topics / Units", "Problems", "Pomodoros", "Hours", "Custom"]

    st.markdown("### ➕ Set a New Target")
    with st.form("new_target_form"):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            subj_choice = st.selectbox("Subject / Topic", get_user_subjects(USER) + ["➕ Custom Subject"])
        with f_col2:
            goal_type = st.selectbox("Goal Type", GOAL_TYPES)

        custom_subject_input = ""
        custom_unit_input    = ""
        fc1, fc2 = st.columns(2)
        with fc1:
            if subj_choice == "➕ Custom Subject":
                custom_subject_input = st.text_input("Enter Custom Subject Name", placeholder="e.g. Current Affairs")
        with fc2:
            if goal_type == "Custom":
                custom_unit_input = st.text_input("Custom Unit Name", placeholder="e.g. Flashcards")

        fe1, fe2 = st.columns(2)
        with fe1:
            unit_label = custom_unit_input if (goal_type == "Custom" and custom_unit_input) else goal_type
            total_ch = st.number_input(f"Goal Amount ({unit_label})", min_value=0, step=1)
        with fe2:
            deadline = st.date_input("Deadline")

        if st.form_submit_button("💾 Save New Target"):
            final_subject = custom_subject_input.strip() if subj_choice == "➕ Custom Subject" else subj_choice
            final_unit    = custom_unit_input.strip() if goal_type == "Custom" else goal_type
            if not final_subject:
                st.error("Please enter a subject name.")
            else:
                date_created = str(_sm_dt.date.today())
                c.execute(
                    """INSERT INTO targets(subject,total_chapters,deadline,username,date_created,ai_feedback,goal_type,goal_unit,custom_subject)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (final_subject, int(total_ch), str(deadline), USER, date_created, "", goal_type, final_unit, custom_subject_input.strip())
                )
                # Also add custom subject to user_subjects table so it's available everywhere
                if subj_choice == "➕ Custom Subject":
                    c.execute("INSERT INTO user_subjects (username, subject) VALUES (%s, %s) ON CONFLICT DO NOTHING", (USER, final_subject))
                conn.commit()
                st.toast(f"✅ Target for '{final_subject}' saved!", icon="✅")
                st.rerun()

    st.divider()
    tgt_df = read_sql("SELECT * FROM targets WHERE username=%s", (USER,))
    act_df = read_sql("SELECT * FROM activities WHERE username=%s AND type IN ('Study', 'Revision', 'Test')", (USER,))
    if not act_df.empty:
        if 'start_time' not in act_df.columns: act_df['start_time'] = None
        act_df['start_time'] = act_df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        act_df['chapter'] = act_df['chapter'].apply(get_clean_chapter)

    if tgt_df.empty:
        st.info("No targets yet. Use the form above to add your first target.")
    else:
        st.subheader("🎯 Target Overview")
        display_data = []
        for _, t in tgt_df.iterrows():
            sub      = t['subject']
            sub_acts = act_df[act_df['subject'] == sub]
            hours_taken = round(sub_acts['duration'].sum(), 2)
            days_taken  = sub_acts['date'].nunique()
            # Use clean chapter names to count unique chapters
            valid_items = [get_clean_chapter(ch) for ch in sub_acts['chapter'].unique()]
            goal_unit = t.get('goal_unit', 'Chapters') or 'Chapters'
            
            # Refined filter: if goal is Chapters/Topics, count non-empty unique entries
            # but still filter out entries that are explicitly Pages or Questions
            valid_items = [
                ch for ch in valid_items 
                if ch and str(ch).strip() and not (
                    goal_unit in ["Chapters", "Topics / Units"] and 
                    is_numeric_entry(ch) and 
                    (str(ch).lower().startswith('pages:') or str(ch).lower().startswith('pg:') or str(ch).lower().startswith('q:'))
                )
            ]
            done  = len(valid_items)
            total = t['total_chapters']
            goal_unit = t.get('goal_unit', 'Chapters') or 'Chapters'
            percent = round(min((done / total) * 100, 100), 1) if total > 0 else (0 if done == 0 else 100)
            display_data.append({
                "Subject":         sub,
                "Goal Type":       goal_unit,
                f"Goal ({goal_unit})": total,
                f"Done ({goal_unit})": done,
                "Achieved %":      f"{percent}%",
                "Deadline":        t['deadline'],
                "Days Studied":    days_taken,
                "Hours Logged":    hours_taken,
            })
        st.dataframe(pd.DataFrame(display_data), width='stretch')
        
        st.divider()
        
        # Target Summary and Analytics
        st.markdown("### 📊 Target Performance Summary")
        
        # Calculate metrics
        total_targets = len(tgt_df)
        display_df = pd.DataFrame(display_data)
        
        achieved_targets = len(display_df[display_df['Achieved %'].str.rstrip('%').astype(float) == 100])
        in_progress = len(display_df[display_df['Achieved %'].str.rstrip('%').astype(float) < 100]) 
        avg_completion = display_df['Achieved %'].str.rstrip('%').astype(float).mean()
        
        sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
        with sum_col1:
            st.metric("🎯 Total Targets", total_targets)
        with sum_col2:
            st.metric("✅ Completed", achieved_targets, delta=f"{(achieved_targets/total_targets*100):.0f}%")
        with sum_col3:
            st.metric("⏳ In Progress", in_progress)
        with sum_col4:
            st.metric("📈 Avg Completion", f"{avg_completion:.0f}%")

        # ── NEW: CIRCULAR PROGRESS FOR ACTIVE TARGETS ────────────────────────
        st.markdown("#### 🔄 Active Targets Completion %")
        active_df = display_df[display_df['Achieved %'].str.rstrip('%').astype(float) < 100]
        if not active_df.empty:
            gauge_cols = st.columns(min(len(active_df), 4))
            for i, (_, row) in enumerate(active_df.head(4).iterrows()):
                with gauge_cols[i % 4]:
                    p_val = float(row['Achieved %'].rstrip('%'))
                    fig_g = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = p_val,
                        title = {'text': row['Subject'], 'font': {'size': 14}},
                        number = {'suffix': "%", 'font': {'size': 16}},
                        gauge = {
                            'axis': {'range': [0, 100], 'tickwidth': 1},
                            'bar': {'color': "#3b82f6"},
                            'bgcolor': "#1e1b4b",
                            'steps': [{'range': [0, 100], 'color': '#1e1b4b'}]
                        }
                    ))
                    fig_g.update_layout(height=140, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_g, width='stretch', key=f"active_gauge_{i}")
        else:
            st.success("All targets completed! 🎉")
        
        # Target category breakdown
        st.markdown("### 📑 Target Category Analysis")
        
        goal_type_dist = display_df['Goal Type'].value_counts()
        goal_type_completion = display_df.groupby('Goal Type')['Achieved %'].apply(lambda x: float(x.str.rstrip('%').astype(float).mean()))

        
        cat_col1, cat_col2 = st.columns(2)
        
        with cat_col1:
            st.subheader("Goal Types Distribution")
            for goal_type, count in goal_type_dist.items():
                completion = goal_type_completion[goal_type]
                st.info(f"""
                **{goal_type}**: {int(count)} targets
                - Average Completion: {completion:.0f}%
                """)
        
        with cat_col2:
            st.subheader("Progress Status")
            status_data = {
                "Completed": achieved_targets,
                "In Progress": in_progress,
                "Not Started": len(display_df[display_df['Days Studied'] == 0])
            }
            fig_status = px.pie(values=list(status_data.values()), names=list(status_data.keys()),
                              color_discrete_map={'Completed':'#22c55e', 'In Progress':'#3b82f6', 'Not Started':'#ef4444'},
                              title="Target Status Distribution")
            st.plotly_chart(fig_status, width='stretch', key="target_status_pie")
        
        # Time efficiency analysis
        st.markdown("### ⏱️ Study Efficiency Analysis")
        
        hours_to_goals = []
        for idx, row in display_df.iterrows():
            goal_unit = row['Goal Type']
            done_col = f"Done ({goal_unit})"
            
            if done_col in display_df.columns:
                done_val = row[done_col]
                hours = row['Hours Logged']
                
                if pd.notna(done_val) and done_val > 0:
                    efficiency = hours / done_val
                    hours_to_goals.append({
                        'Subject': row['Subject'],
                        'Goal Type': goal_unit,
                        'Chapters Done': done_val,
                        'Total Hours': hours,
                        'Hours per Chapter': round(efficiency, 2)
                    })
        
        if hours_to_goals:
            eff_df = pd.DataFrame(hours_to_goals)
            st.dataframe(eff_df, hide_index=True, width='stretch')
        
        st.divider()
        
        # Show detailed target progress data
        st.markdown("### 📊 Target Progress Data (Set Date → Achievement Date)")
        for _, t in tgt_df.iterrows():
            sub = t['subject']
            # Get dates from target
            today = get_ist_now().date()
            set_date = pd.to_datetime(t.get('set_date', t['deadline'])).date() if 'set_date' in t and pd.notna(t.get('set_date')) else (today - timedelta(days=365))
            achieve_date = pd.to_datetime(t.get('achieve_date', today)).date() if 'achieve_date' in t and pd.notna(t.get('achieve_date')) else today
            
            # Filter activities between set_date and achieve_date
            sub_acts = act_df[(act_df['subject'] == sub) & 
                              (pd.to_datetime(act_df['date']).dt.date >= set_date) & 
                              (pd.to_datetime(act_df['date']).dt.date <= achieve_date)]
            
            with st.expander(f"📈 {sub} - {set_date} to {achieve_date}"):
                if not sub_acts.empty:
                    # Summary stats
                    total_hours = round(sub_acts['duration'].sum(), 2)
                    days_studied = sub_acts['date'].nunique()
                    
                    # Clean chapters first then count unique
                    clean_chs = sub_acts['chapter'].apply(get_clean_chapter)
                    chapters_covered = len([ch for ch in clean_chs.unique() if ch and str(ch).strip()])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Hours", f"{total_hours}h")
                    with col2:
                        st.metric("Days Studied", days_studied)
                    with col3:
                        st.metric("Chapters", chapters_covered)
                    
                    # Detailed table
                    st.write("**Detailed Activity Log:**")
                    detail_data = sub_acts[['date', 'type', 'chapter', 'duration', 'amount']].copy()
                    detail_data = detail_data.sort_values('date', ascending=False)
                    st.dataframe(detail_data, width='stretch')
                else:
                    st.info(f"No activities logged for {sub} between {set_date} and {achieve_date}.")

        st.divider()
        # ════════════════════════════════════════════════════════
        # SECTION: DELETE TARGET
        # ════════════════════════════════════════════════════════
        st.subheader("🗑️ Delete a Target")
        del_sub = st.selectbox("Select target to delete", [t['subject'] for _, t in tgt_df.iterrows()], key="del_tgt_sel")
        del_row = tgt_df[tgt_df['subject'] == del_sub].iloc[0]
        del_cols = st.columns([2,1,1])
        with del_cols[0]:
            if st.button("🗑️ Delete Target", key="del_tgt_btn"):
                st.session_state["confirm_del_tgt"] = True
        if st.session_state.get("confirm_del_tgt", False):
            st.warning(f"Delete target for **{del_sub}**? This cannot be undone.")
            yc, nc = st.columns(2)
            with yc:
                if st.button("✅ Yes, Delete", key="yes_del_tgt"):
                    c.execute("DELETE FROM targets WHERE id=%s AND username=%s", (int(del_row['id']), USER))
                    conn.commit()
                    st.session_state["confirm_del_tgt"] = False
                    st.toast(f"🗑️ Target '{del_sub}' deleted.", icon="🗑️")
                    st.rerun()
            with nc:
                if st.button("❌ No, Keep", key="no_del_tgt"):
                    st.session_state["confirm_del_tgt"] = False
                    st.rerun()

    # ── SMART WORK TIPS (Set Target Page) ──
    _st_tips = generate_smart_work_tips(
        prod_hours=0, waste_hours=0, essential_hours=0,
        study_streak=0, focus_pct=0, subject_count=0,
        productivity_pct=0, context="target"
    )
    with st.expander("⚡ Smart Work Tips & Target Strategies", expanded=False):
        st.markdown(render_smart_work_section(_st_tips, max_tips=10), unsafe_allow_html=True)

# ---------------- STUDY TARGET MANAGER ----------------
elif menu == "Study Target Manager":
    st.title("📊 Study Target Manager")
    import ai as _ai_ta
    import datetime as _ta_dt
    import re as _re

    tgt_df = read_sql("SELECT * FROM targets WHERE username=%s", (USER,))
    act_df = read_sql(
        "SELECT * FROM activities WHERE username=%s "
        "AND type IN ('Study','Revision','Test','Answer Writing','Practice','Book Reading')",
        (USER,)
    )
    if not act_df.empty:
        if 'start_time' not in act_df.columns: act_df['start_time'] = None
        act_df['start_time'] = act_df.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        act_df['chapter'] = act_df['chapter'].apply(get_clean_chapter)

    if tgt_df.empty:
        st.info("No targets yet. Go to **Set Target** to create one.")
    else:
        # Goal-type buckets
        _ITEM_TYPES  = {"Chapters", "Topics / Units", "Custom", "Pomodoros"}
        _CUMUL_TYPES = {"Pages", "Questions Solved", "Problems"}
        _HOURS_TYPE  = "Hours"

        def _filter_period(df, date_created, end_date=None):
            df = df.copy()
            df['_date'] = pd.to_datetime(df['date']).dt.date
            if date_created:
                df = df[df['_date'] >= pd.to_datetime(date_created).date()]
            if end_date:
                df = df[df['_date'] <= pd.to_datetime(end_date).date()]
            return df

        def _compute_progress(t, all_act_df):
            """Return (done, total, percent) by goal_type."""
            sub       = t['subject']
            goal_unit = (t.get('goal_unit') or 'Chapters')
            total     = int(t['total_chapters'])
            sub_acts  = _filter_period(all_act_df[all_act_df['subject'] == sub], t.get('date_created')).copy()
            
            # Use cleaned chapter names for unique counting
            sub_acts['clean_ch'] = sub_acts['chapter'].apply(get_clean_chapter)
            
            if goal_unit in _ITEM_TYPES:
                # Count unique chapters/items
                # If unit is Chapters/Topics, we are more lenient but still filter out explicit Pages/Questions entries
                done = len([
                    ch for ch in sub_acts['clean_ch'].unique()
                    if ch and str(ch).strip() and not (
                        goal_unit in ["Chapters", "Topics / Units"] and 
                        is_numeric_entry(ch) and 
                        (str(ch).lower().startswith('pages:') or str(ch).lower().startswith('pg:') or str(ch).lower().startswith('q:'))
                    )
                ])
            elif goal_unit == _HOURS_TYPE:
                done = round(sub_acts['duration'].sum(), 2)
            elif goal_unit in _CUMUL_TYPES:
                # Still use raw chapter to parse numeric values like 'Pg: 50'
                done = sum(n for n in ((parse_numeric(ch) for ch in sub_acts['chapter'])) if n is not None)
            else:
                done = len([ch for ch in sub_acts['clean_ch'].unique() if ch and str(ch).strip()])
            
            percent = round(min((done / total) * 100, 100), 1) if total > 0 else (0 if done == 0 else 100)
            return done, total, percent

        def _detail_table(sub, date_created, achieved_date, all_act_df, goal_unit):
            """Return (primary_df, secondary_df) for the goal type."""
            sub_acts = _filter_period(
                all_act_df[all_act_df['subject'] == sub], date_created, achieved_date
            )
            sub_acts = sub_acts[
                sub_acts['chapter'].notna() & (sub_acts['chapter'].astype(str).str.strip() != '')
            ]
            if sub_acts.empty:
                return None, None
            if goal_unit in _ITEM_TYPES:
                sub_acts['clean_ch'] = sub_acts['chapter'].apply(get_clean_chapter)
                # Group by chapters, being lenient with numeric names but filtering out explicit Pages/Questions
                named = sub_acts[
                    (sub_acts['clean_ch'] != "") & 
                    ~((goal_unit in ["Chapters", "Topics / Units"]) & 
                      sub_acts['chapter'].apply(is_numeric_entry) & 
                      (sub_acts['chapter'].str.lower().str.startswith('pages:') | 
                       sub_acts['chapter'].str.lower().str.startswith('pg:') | 
                       sub_acts['chapter'].str.lower().str.startswith('q:')))
                ]
                if named.empty:
                    return None, None
                summary = (
                    named.groupby('clean_ch').agg({
                        'duration': 'sum',
                        'id': 'count'
                    }).reset_index()
                    .rename(columns={
                        'clean_ch': 'Chapter / Topic',
                        'duration': 'Total Hours',
                        'id': 'Sessions'
                    })
                    .sort_values('Chapter / Topic')
                )
                detail = (
                    named.groupby(['clean_ch', '_date'], as_index=False)['duration'].sum()
                    .rename(columns={'clean_ch': 'Chapter / Topic', '_date': 'Date', 'duration': 'Hours'})
                    .sort_values(['Chapter / Topic', 'Date'], ascending=[True, False])
                )
                return summary, detail
            elif goal_unit == _HOURS_TYPE:
                daily = (
                    sub_acts.groupby('_date')['duration'].sum().reset_index()
                    .rename(columns={'_date': 'Date', 'duration': 'Hours'})
                    .sort_values('Date')
                )
                daily['Cumulative Hours'] = daily['Hours'].cumsum().round(2)
                daily = daily.sort_values('Date', ascending=False)
                return daily, None
            elif goal_unit in _CUMUL_TYPES:
                col = 'Pages' if goal_unit == 'Pages' else 'Questions'
                rows = [{'Date': r['_date'], col: parse_numeric(r['chapter']), 'Activity': r['type']}
                        for _, r in sub_acts.iterrows() if parse_numeric(r['chapter']) is not None]
                if not rows:
                    return None, None
                daily = pd.DataFrame(rows).groupby('Date')[col].sum().reset_index().sort_values('Date')
                daily[f'Cumulative {col}'] = daily[col].cumsum()
                daily = daily.sort_values('Date', ascending=False)
                return daily, None
            else:
                tbl = (
                    sub_acts.groupby(['chapter', '_date'], as_index=False)['duration'].sum()
                    .rename(columns={'chapter': 'Chapter / Item', '_date': 'Date', 'duration': 'Hours'})
                    .sort_values('Date', ascending=False)
                )
                return tbl, None

        # ── Classify targets ──────────────────────────────────────────────
        active_targets   = []
        achieved_targets = []
        for _, t in tgt_df.iterrows():
            done, total, percent = _compute_progress(t, act_df)
            entry = dict(t)
            entry['_done']      = done
            entry['_percent']   = percent
            entry['_goal_unit'] = (t.get('goal_unit') or 'Chapters')
            if percent >= 100:
                achieved_targets.append(entry)
            else:
                active_targets.append(entry)

        # Shared card renderer
        def _render_card(t, achieved_on=None, expanded=True):
            sub       = t['subject']
            tid       = t['id']
            goal_unit = t['_goal_unit']
            done      = t['_done']
            total     = int(t['total_chapters'])
            percent   = t['_percent']
            stored_insight = t.get('ai_feedback', '') or ''

            sub_acts    = act_df[act_df['subject'] == sub].copy()
            sub_acts['clean_ch'] = sub_acts['chapter'].apply(get_clean_chapter)
            
            hours_taken = round(sub_acts['duration'].sum(), 2)
            days_taken  = sub_acts['date'].nunique()
            _ch_active  = sub_acts[sub_acts['clean_ch'] != ""]
            max_item    = _ch_active.groupby('clean_ch')['duration'].sum().idxmax() if not _ch_active.empty else "N/A"

            label  = f"{round(done,1)}" if goal_unit == _HOURS_TYPE else str(done)
            icon   = "✅" if percent >= 100 else "🔵"
            header = f"{icon} {sub} — {percent}% ({label}/{total} {goal_unit})"
            if achieved_on:
                header += "  🎉"

            with st.expander(header, expanded=expanded):
                mc1, mc2, mc3, mc4, mc5 = st.columns([1.5, 1, 1, 1, 1.5])
                
                with mc1:
                    # Circular Completion Indicator
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = percent,
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        number = {'suffix': "%", 'font': {'size': 20, 'color': 'white'}},
                        gauge = {
                            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                            'bar': {'color': "#22c55e" if percent >= 100 else "#3b82f6"},
                            'bgcolor': "#1e1b4b",
                            'borderwidth': 2,
                            'bordercolor': "gray",
                            'steps': [
                                {'range': [0, 100], 'color': '#1e1b4b'}
                            ],
                        }
                    ))
                    fig_gauge.update_layout(
                        height=150, margin=dict(l=10, r=10, t=30, b=10),
                        paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}
                    )
                    st.plotly_chart(fig_gauge, width='stretch', key=f"gauge_{tid}")

                mc2.metric("Goal",     f"{total} {goal_unit}")
                mc3.metric("Done",     f"{label} {goal_unit}")
                # mc4 was previously mc3 (Progress)
                mc4.metric("Total Time", f"{hours_taken}h")
                if achieved_on:
                    mc5.metric("Completed On", str(achieved_on))
                else:
                    mc5.metric("Deadline", str(t['deadline']))

                if goal_unit in _ITEM_TYPES:
                    exp_label = "📋 Chapter / Topic Summary & Hours Breakdown"
                elif goal_unit == _HOURS_TYPE:
                    exp_label = "📋 Daily Hours Log (Cumulative)"
                else:
                    col_n = 'Pages' if goal_unit == 'Pages' else 'Questions'
                    exp_label = f"📋 Daily {col_n} Log (Cumulative)"

                with st.expander(exp_label, expanded=False):
                    primary, secondary = _detail_table(
                        sub, t.get('date_created'), achieved_on, act_df, goal_unit
                    )
                    if primary is None:
                        st.caption("No matching entries logged yet for this target.")
                    else:
                        st.dataframe(primary, width='stretch', hide_index=True)
                        if secondary is not None:
                            st.markdown("**📅 Date-wise Breakdown**")
                            st.dataframe(secondary, width='stretch', hide_index=True)

                if stored_insight:
                    st.markdown("---")
                    st.info(f"🤖 **AI Analysis:** {stored_insight}")

        # ════════════════════════════════════════════════════════
        # SECTION: TARGET ACHIEVED
        # ════════════════════════════════════════════════════════
        st.subheader("🏆 Target Achieved")

        st.markdown("#### 🔵 Active Targets")
        if not active_targets:
            st.info("No active targets. All targets are completed! 🎉")
        else:
            for t in active_targets:
                _render_card(t, achieved_on=None, expanded=True)

        st.markdown("#### ✅ Completed Targets")
        if not achieved_targets:
            st.info("No targets have reached 100% yet. Keep going! 💪")
        else:
            for t in achieved_targets:
                sub      = t['subject']
                sub_acts = act_df[act_df['subject'] == sub]
                achieved_on = None
                if not sub_acts.empty:
                    dated = sub_acts[
                        sub_acts['chapter'].notna() &
                        (sub_acts['chapter'].astype(str).str.strip() != '')
                    ]
                    if not dated.empty:
                        achieved_on = pd.to_datetime(dated['date']).max().date()
                _render_card(t, achieved_on=achieved_on, expanded=False)

        # ── WEAK SUBJECTS (bottom) ────────────────────────────────────────────
        st.subheader("📉 Weak Subjects (Least Studied & Revised)")
        study_acts = act_df[act_df['type'].isin(['Study', 'Revision'])]
        if study_acts.empty:
            st.info("No study entries yet.")
        else:
            subj_hours = study_acts.groupby('subject')['duration'].sum().sort_values()
            
            # Summary Metrics
            st.markdown("### 📊 Study & Revision Hours by Subject")
            st.dataframe(subj_hours.reset_index().rename(columns={'subject':'Subject','duration':'Hours'}),
                         width='stretch')
            st.bar_chart(subj_hours)
            
            # Analysis Section
            st.markdown("### 💡 Weak Subjects Analysis")
            
            total_study_hours = subj_hours.sum()
            num_subjects = len(subj_hours)
            
            analysis_cols = st.columns(3)
            with analysis_cols[0]:
                st.metric("📚 Total Subjects", num_subjects)
            with analysis_cols[1]:
                st.metric("⏱️ Total Productive Hours", f"{total_study_hours:.1f}h")
            with analysis_cols[2]:
                avg_hours = total_study_hours / num_subjects if num_subjects > 0 else 0
                st.metric("📊 Average per Subject", f"{avg_hours:.1f}h")
            
            # ════════════════════════════════════════════════════════════════
            # SMART STUDY TECHNIQUES & METHODS — UPSC CSE Focused
            # ════════════════════════════════════════════════════════════════
            st.divider()
            
            # Load PYQ data for subject-technique mapping
            import json as _json_tm
            try:
                with open('pyq_data.json', 'r') as _f_tm:
                    _pyq_tm = _json_tm.load(_f_tm)
                    _prelims_subjects = _pyq_tm.get('prelims', [])
                    _mains_subjects = _pyq_tm.get('mains', [])
            except Exception:
                _prelims_subjects = []
                _mains_subjects = []
            
            # Import upsc_strategy_data
            try:
                import upsc_strategy_data as _usd
                _all_subjects_data = _usd.ALL_SUBJECTS
            except ImportError:
                _all_subjects_data = {}
            
            # Build subject importance map
            _subj_importance = {}
            for s in _prelims_subjects:
                _subj_importance[s['subject']] = {
                    'score': s['importance_score'],
                    'topics': s['important_topics'],
                    'chapters': s['important_chapters'],
                    'strategy': s['revision_strategy']
                }
            
            st.markdown('<div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#1e3a5f 100%);padding:24px 28px 16px 28px;border-radius:16px;border:1px solid #4f46e5;margin-bottom:20px;box-shadow:0 8px 32px rgba(79,70,229,0.15);"><div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;"><span style="font-size:28px;">\U0001f4da</span><h2 style="margin:0;color:#e0e7ff;font-weight:800;">Smart Study Techniques &amp; Methods</h2></div><p style="margin:0;color:#a5b4fc;font-size:14px;">Proven study &amp; productivity techniques mapped to your UPSC subjects based on PYQ trends and syllabus weight.</p></div>', unsafe_allow_html=True)
            
            # ── TAB LAYOUT ──
            # Inject CSS to make tab content panels scrollable so all subjects are visible
            st.markdown("""
            <style>
                /* Make the tab content panels scrollable across all tabs */
                div[data-testid="stTabs"] > div[data-baseweb="tab-panel"] {
                    max-height: 75vh;
                    overflow-y: auto;
                    overflow-x: hidden;
                    padding-right: 8px;
                }
                /* Custom scrollbar styling for the tab panels */
                div[data-testid="stTabs"] > div[data-baseweb="tab-panel"]::-webkit-scrollbar {
                    width: 6px;
                }
                div[data-testid="stTabs"] > div[data-baseweb="tab-panel"]::-webkit-scrollbar-track {
                    background: #0f172a;
                    border-radius: 6px;
                }
                div[data-testid="stTabs"] > div[data-baseweb="tab-panel"]::-webkit-scrollbar-thumb {
                    background: #334155;
                    border-radius: 6px;
                }
                div[data-testid="stTabs"] > div[data-baseweb="tab-panel"]::-webkit-scrollbar-thumb:hover {
                    background: #475569;
                }
            </style>
            """, unsafe_allow_html=True)
            
            _tech_tab1, _tech_tab2, _tech_tab3 = st.tabs([
                "🧠 Study Techniques", "⚡ Productivity Methods", "🎯 Subject-wise Strategy"
            ])
            
            # ═══════════════════════════════════════════
            # TAB 1 — STUDY TECHNIQUES
            # ═══════════════════════════════════════════
            with _tech_tab1:
                st.markdown('<div style="background:#0f172a;border:1px solid #334155;border-radius:14px;padding:18px 22px;margin-bottom:16px;"><div style="font-size:13px;color:#94a3b8;margin-bottom:8px;">\U0001f4a1 Each technique below has been mapped to specific UPSC subjects where it works best.</div></div>', unsafe_allow_html=True)
                
                import re as _re_md
                def _md(text):
                    """Convert **bold** markdown to <strong> HTML tags."""
                    return _re_md.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', str(text))
                
                _study_techniques = [
                    {
                        "name": "Active Recall",
                        "icon": "🧠",
                        "what": "Close the book and write/speak everything you remember. Then check gaps.",
                        "how": "After reading 1 chapter, close it. Write all key points from memory on blank paper. Compare with book — your gaps are your weak spots.",
                        "when": "Every study session — spend last 15 min of each hour on recall.",
                        "subjects": "**Polity** (Articles, Amendments), **History** (Dates, Movements), **Economics** (Concepts, Data)",
                        "impact": "3x better retention than re-reading. Builds neural pathways for exam recall under pressure.",
                        "color": "#8b5cf6"
                    },
                    {
                        "name": "Spaced Repetition",
                        "icon": "📆",
                        "what": "Revise at increasing intervals: Day 1 → Day 3 → Day 7 → Day 21 → Day 45.",
                        "how": "After completing a chapter, mark revision dates in calendar. Use Anki flashcards for facts. Keep a 'Revision Register' with dates.",
                        "when": "Daily 30-min revision slot (morning or before sleep). Sunday = full revision day.",
                        "subjects": "**All subjects** — especially fact-heavy: **Environment** (species, acts), **Geography** (data, maps), **Current Affairs**",
                        "impact": "Without this, you forget 80% in 7 days. With it, you retain 90%+ for months.",
                        "color": "#06b6d4"
                    },
                    {
                        "name": "Feynman Technique",
                        "icon": "📝",
                        "what": "Explain the topic as if teaching a 10-year-old. Where you struggle = where you don't understand.",
                        "how": "Pick a topic (e.g., 'Separation of Powers'). Write a 5-line explanation in simple Hindi/English. If you can't simplify it, re-study that part.",
                        "when": "2 topics/day. Best done during evening revision sessions.",
                        "subjects": "**Polity** (Constitutional concepts), **Economics** (Fiscal/Monetary policy), **Ethics** (case studies)",
                        "impact": "Converts surface-level reading into deep understanding. Essential for Mains answer writing.",
                        "color": "#f59e0b"
                    },
                    {
                        "name": "Mind Mapping",
                        "icon": "🗺️",
                        "what": "Create visual diagrams connecting related concepts, chapters, and themes.",
                        "how": "Central topic in middle → branches for sub-topics → leaves for facts/dates. Use colors for different categories. One A4 sheet per chapter.",
                        "when": "After completing a subject/unit. Revise using maps instead of full chapters.",
                        "subjects": "**History** (connect movements, leaders, dates), **Geography** (physical features, climate), **Environment** (ecosystem linkages)",
                        "impact": "Visual memory is 6x stronger. Mind maps compress 50 pages into 1 page for quick revision.",
                        "color": "#10b981"
                    },
                    {
                        "name": "PYQ-First Approach",
                        "icon": "📋",
                        "what": "Study Previous Year Questions BEFORE reading the chapter. Know what UPSC asks, then study accordingly.",
                        "how": "Download last 10 years PYQs topic-wise. Before starting any chapter, solve its PYQs. Mark which topics repeat. Study those FIRST.",
                        "when": "Before starting each new chapter/topic. Weekly PYQ practice sessions.",
                        "subjects": "**All subjects** — Prelims PYQ trends: Polity (96/100), History (95/100), Geography (92/100), Economics (88/100)",
                        "impact": "80% of Prelims questions come from 20% of topics. PYQ analysis reveals those 20%.",
                        "color": "#ef4444"
                    },
                    {
                        "name": "SQ3R Method",
                        "icon": "📖",
                        "what": "Survey → Question → Read → Recite → Review. Structured reading method for textbooks.",
                        "how": "**Survey**: Scan headings for 2 min. **Question**: Convert headings to questions. **Read**: Read to answer your questions. **Recite**: Close book, answer. **Review**: Summarize in notes.",
                        "when": "Every time you open NCERT, Laxmikanth, or any standard book.",
                        "subjects": "**NCERT 6-12** (all subjects), **Laxmikanth** (Polity), **Spectrum** (History), **Shankar IAS** (Environment)",
                        "impact": "Prevents passive reading. Forces comprehension. Ideal for first-time reading of any textbook.",
                        "color": "#6366f1"
                    },
                    {
                        "name": "Answer Writing Practice",
                        "icon": "✍️",
                        "what": "Write 2-3 Mains-style answers daily. Structure: Intro → Body (points + examples) → Conclusion.",
                        "how": "Pick a PYQ or mock question. Set 7-minute timer for 150-word answer. Use diagrams, flowcharts where possible. Get evaluated weekly.",
                        "when": "Daily 30-45 min. Start from Day 1 of preparation — don't wait for 'completion'.",
                        "subjects": "**GS1** (History, Geography, Society), **GS2** (Polity, IR, Governance), **GS3** (Economy, Environment, Security), **GS4** (Ethics)",
                        "impact": "Mains = 1750 marks. Without daily writing, you can't finish papers in time. Start early, improve fast.",
                        "color": "#ec4899"
                    },
                    {
                        "name": "Interleaving",
                        "icon": "🔄",
                        "what": "Mix different subjects/topics in a single study session instead of studying one subject for hours (blocked practice).",
                        "how": "Study Polity for 45 min → switch to Geography for 45 min → then Economics for 45 min. Your brain constantly re-engages, building stronger retrieval paths.",
                        "when": "Every study session. Especially effective during revision phases when you have multiple subjects to cover.",
                        "subjects": "**All subjects** — particularly effective when mixing related subjects: **Polity + Governance**, **History + Art & Culture**, **Geography + Environment**",
                        "impact": "Research shows 43% better long-term retention vs blocked practice. Feels harder but produces superior results for exam performance.",
                        "color": "#14b8a6"
                    },
                    {
                        "name": "Elaborative Interrogation",
                        "icon": "❓",
                        "what": "After reading any fact, ask yourself 'WHY is this true?' and 'HOW does this work?' — then find the answer.",
                        "how": "Read: 'Article 356 allows President's Rule.' Ask: WHY was it included? HOW has it been misused? WHAT did Sarkaria Commission say? Forces deeper processing.",
                        "when": "While reading any new chapter. Write 3-5 'WHY/HOW' questions per topic in margins or separate notebook.",
                        "subjects": "**Polity** (WHY articles exist), **Economics** (HOW policies work), **History** (WHY events happened), **Ethics** (WHY values matter)",
                        "impact": "Transforms passive reading into active analysis. Builds the 'analytical thinking' muscle UPSC Mains rewards. 2.5x better than highlighting.",
                        "color": "#f97316"
                    },
                    {
                        "name": "Dual Coding Theory",
                        "icon": "🎨",
                        "what": "Combine verbal information (text/notes) with visual information (diagrams, charts, maps) for every topic.",
                        "how": "For every chapter, create BOTH a written summary AND a visual aid (flowchart, diagram, table, map). Brain stores them in 2 separate channels, doubling recall routes.",
                        "when": "After finishing any chapter. Spend 15-20 min creating a visual companion to your text notes.",
                        "subjects": "**Geography** (maps + data), **Polity** (flowcharts for amendment process), **History** (timelines + event maps), **Science & Tech** (diagrams)",
                        "impact": "Creates 2 independent memory pathways. Even if you forget the text, the visual cue triggers recall. Essential for Mains diagrams that fetch extra marks.",
                        "color": "#a855f7"
                    },
                    {
                        "name": "Cornell Note-Taking System",
                        "icon": "📓",
                        "what": "Divide your page into 3 sections: Notes (right), Cues/Questions (left), Summary (bottom). Structured notes that double as revision material.",
                        "how": "**Right column (70%)**: Detailed notes during study. **Left column (30%)**: Key questions/keywords after session. **Bottom**: 2-3 line summary. Cover right → test with left cues.",
                        "when": "Every time you take notes from any source. Weekly revision using only the cue column.",
                        "subjects": "**All subjects** — especially for NCERT reading, **Polity** (article-wise notes), **Economics** (concept notes), **Current Affairs** (daily notes)",
                        "impact": "Combines note-taking with built-in self-testing. Your notes become a complete revision tool. Reduces revision time by 60%.",
                        "color": "#0ea5e9"
                    },
                    {
                        "name": "Leitner System (Flashcard Method)",
                        "icon": "🗃️",
                        "what": "Organize flashcards into 5 boxes based on how well you know each card. Wrong → move back; Right → advance forward.",
                        "how": "**Box 1**: Review daily. **Box 2**: Every 2 days. **Box 3**: Weekly. **Box 4**: Bi-weekly. **Box 5**: Monthly. Wrong answer → card goes back to Box 1.",
                        "when": "Daily 20-30 min session. Create cards as you study new topics. Use physical cards or Anki app.",
                        "subjects": "**Environment** (species, acts, conventions), **Art & Culture** (facts, GI tags), **Polity** (articles, schedules), **Geography** (data, places)",
                        "impact": "Most efficient system for memorizing 1000+ facts. Focuses energy on weak spots. UPSC Prelims is 50% fact recall — this covers it.",
                        "color": "#84cc16"
                    },
                    {
                        "name": "Teach-Back Method",
                        "icon": "👨‍🏫",
                        "what": "Teach the topic to a study partner, family member, or even to a wall/mirror. Teaching forces you to organize and simplify knowledge.",
                        "how": "After studying a chapter, explain it to someone for 10 min without notes. Record yourself if alone. Note where you stumble — those are your gaps.",
                        "when": "After completing each major topic. Weekly study group sessions where everyone teaches one topic.",
                        "subjects": "**Polity** (explain articles in simple terms), **Economics** (explain schemes to non-students), **Ethics** (discuss case studies), **History** (narrate events)",
                        "impact": "The 'Protégé Effect' — you learn 90% of what you teach vs 10% of what you read. The ultimate comprehension test.",
                        "color": "#e11d48"
                    },
                    {
                        "name": "Chunking",
                        "icon": "🧩",
                        "what": "Break large amounts of information into smaller, meaningful groups (chunks) that are easier to remember and process.",
                        "how": "Instead of 50 Articles individually, group: **Fundamental Rights** (14-32), **DPSPs** (36-51), **Duties** (51A). Create acronyms like LEPS for Lok Sabha functions.",
                        "when": "When facing overwhelming data. Before creating flashcards. During first reading of fact-heavy chapters.",
                        "subjects": "**Polity** (group articles by theme), **Environment** (group species by biome), **Geography** (group rivers by drainage), **History** (group events by era)",
                        "impact": "Working memory holds only 4-7 items. Chunking compresses 50 items into 7-10 chunks. Essential for Prelims elimination strategy.",
                        "color": "#7c3aed"
                    },
                    {
                        "name": "Deliberate Practice",
                        "icon": "🎯",
                        "what": "Focus specifically on your weakest areas with targeted, uncomfortable practice rather than revising what you already know.",
                        "how": "Analyze mock test scores → Identify bottom 3 subjects → Spend 70% of time on THOSE. If you score 40% in Economy, do 2 extra hours of Economy before Polity.",
                        "when": "After every mock test or weekly review. Adjust study schedule based on data, not comfort.",
                        "subjects": "**Your weakest subjects first** — check tracker data. Common weak areas: **Economics** (conceptual), **Science & Tech** (application), **Environment** (factual)",
                        "impact": "Elite performers spend 80% of practice on weaknesses. Studying strengths feels good but doesn't improve scores. Uncomfortable practice = real growth.",
                        "color": "#dc2626"
                    },
                ]
                
                # ── PAGINATION for Study Techniques ──
                _ST_PER_PAGE = 5
                _total_st = len(_study_techniques)
                _total_st_pages = max(1, (_total_st + _ST_PER_PAGE - 1) // _ST_PER_PAGE)
                
                if "stm_tech_page" not in st.session_state:
                    st.session_state.stm_tech_page = 1
                if st.session_state.stm_tech_page > _total_st_pages:
                    st.session_state.stm_tech_page = _total_st_pages
                if st.session_state.stm_tech_page < 1:
                    st.session_state.stm_tech_page = 1
                
                _cur_st_page = st.session_state.stm_tech_page
                _st_start = (_cur_st_page - 1) * _ST_PER_PAGE
                _st_end = min(_st_start + _ST_PER_PAGE, _total_st)
                _page_techniques = _study_techniques[_st_start:_st_end]
                
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:10px 18px;margin-bottom:14px;">
                    <span style="font-size:13px;color:#94a3b8;">Showing techniques <strong style="color:#38bdf8;">{_st_start+1}–{_st_end}</strong> of <strong style="color:#38bdf8;">{_total_st}</strong></span>
                    <span style="font-size:13px;color:#a78bfa;font-weight:600;">Page {_cur_st_page} of {_total_st_pages}</span>
                </div>
                """, unsafe_allow_html=True)
                
                for tech in _page_techniques:
                    _t_html = f'<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border:1px solid #334155;border-radius:16px;padding:20px 24px;margin-bottom:14px;border-left:5px solid {tech["color"]};">' \
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;"><span style="font-size:24px;">{tech["icon"]}</span><span style="font-size:18px;font-weight:800;color:#e2e8f0;">{tech["name"]}</span></div>' \
                        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;color:#cbd5e1;line-height:1.6;">' \
                        f'<div><div style="color:{tech["color"]};font-weight:700;font-size:11px;text-transform:uppercase;margin-bottom:4px;">\U0001f4cc What It Is</div>{_md(tech["what"])}</div>' \
                        f'<div><div style="color:{tech["color"]};font-weight:700;font-size:11px;text-transform:uppercase;margin-bottom:4px;">\U0001f527 How to Apply</div>{_md(tech["how"])}</div>' \
                        f'<div><div style="color:{tech["color"]};font-weight:700;font-size:11px;text-transform:uppercase;margin-bottom:4px;">\u23f0 When to Use</div>{_md(tech["when"])}</div>' \
                        f'<div><div style="color:{tech["color"]};font-weight:700;font-size:11px;text-transform:uppercase;margin-bottom:4px;">\U0001f4da Best For Subjects</div>{_md(tech["subjects"])}</div>' \
                        f'</div><div style="margin-top:10px;padding:8px 14px;background:rgba(139,92,246,0.08);border-radius:8px;font-size:12px;color:#a78bfa;">\U0001f4a1 <strong>Impact:</strong> {_md(tech["impact"])}</div></div>'
                    st.markdown(_t_html, unsafe_allow_html=True)
                
                # ── Pagination controls for Study Techniques ──
                _st_c1, _st_c2, _st_c3, _st_c4, _st_c5 = st.columns([1, 1, 2, 1, 1])
                with _st_c1:
                    if st.button("⏮ First", key="stm_tech_first", disabled=(_cur_st_page <= 1), use_container_width=True):
                        st.session_state.stm_tech_page = 1
                        st.rerun()
                with _st_c2:
                    if st.button("◀ Prev", key="stm_tech_prev", disabled=(_cur_st_page <= 1), use_container_width=True):
                        st.session_state.stm_tech_page = _cur_st_page - 1
                        st.rerun()
                with _st_c3:
                    _new_st_page = st.selectbox(
                        "Page",
                        options=list(range(1, _total_st_pages + 1)),
                        index=_cur_st_page - 1,
                        key="stm_tech_page_select",
                        label_visibility="collapsed",
                        format_func=lambda x: f"📄 Page {x} of {_total_st_pages}"
                    )
                    if _new_st_page != _cur_st_page:
                        st.session_state.stm_tech_page = _new_st_page
                        st.rerun()
                with _st_c4:
                    if st.button("Next ▶", key="stm_tech_next", disabled=(_cur_st_page >= _total_st_pages), use_container_width=True):
                        st.session_state.stm_tech_page = _cur_st_page + 1
                        st.rerun()
                with _st_c5:
                    if st.button("Last ⏭", key="stm_tech_last", disabled=(_cur_st_page >= _total_st_pages), use_container_width=True):
                        st.session_state.stm_tech_page = _total_st_pages
                        st.rerun()
            
            # ═══════════════════════════════════════════
            # TAB 2 — PRODUCTIVITY METHODS
            # ═══════════════════════════════════════════
            with _tech_tab2:
                _prod_methods = [
                    {
                        "name": "Pomodoro Technique",
                        "icon": "🍅",
                        "what": "25 min focused work → 5 min break → repeat 4 times → 30 min long break.",
                        "routine": "**Morning**: 4 Pomodoros (hard subject) → Break → 4 Pomodoros (medium subject). **Evening**: 4 Pomodoros (revision/CA). Total = ~6h deep study.",
                        "apply": "Use for subjects you find boring or hard to start. Physical timer > phone timer (avoid distraction). Track Pomodoro count daily.",
                        "color": "#ef4444"
                    },
                    {
                        "name": "Eat The Frog",
                        "icon": "🐸",
                        "what": "Do the hardest/most boring task FIRST thing in the morning when willpower is at its peak.",
                        "routine": "**6:00-8:00 AM**: Your weakest UPSC subject (the 'frog'). No phone, no excuses. **After 8 AM**: Easier subjects feel effortless because the hard part is done.",
                        "apply": "If Polity bores you — do Polity first. If Economics confuses you — do Economics first. Rotate the 'frog' based on what you're avoiding.",
                        "color": "#22c55e"
                    },
                    {
                        "name": "Time Blocking",
                        "icon": "📅",
                        "what": "Pre-assign every hour of your day to a specific activity. No 'free time' that becomes waste.",
                        "routine": "**6-8 AM**: Hard subject | **9-11 AM**: Medium subject | **11:30-1 PM**: Current Affairs + Notes | **2:30-4:30 PM**: Revision/PYQs | **5-6 PM**: Answer Writing | **8-9 PM**: Light reading/newspaper",
                        "apply": "Block in Google Calendar or physical planner. Include meals, walk, sleep. The key: treat each block as a meeting you can't skip.",
                        "color": "#3b82f6"
                    },
                    {
                        "name": "2-Minute Rule",
                        "icon": "⚡",
                        "what": "If a task takes < 2 minutes, do it NOW. For bigger tasks: commit to just 2 minutes to overcome inertia.",
                        "routine": "Can't start studying? Open the book and read just 2 minutes. By then, momentum kicks in and you continue. Works for revision, notes, and answer writing too.",
                        "apply": "Use when procrastinating. Also: reply to that message in 2 min instead of letting it become a 30-min distraction later.",
                        "color": "#f59e0b"
                    },
                    {
                        "name": "90-Minute Deep Work Cycles",
                        "icon": "🔬",
                        "what": "90 min of unbroken focus (phone off, door closed) → 20 min break. Aligned with your brain's ultradian rhythm.",
                        "routine": "**2 cycles in morning** (3h study) + **2 cycles in afternoon** (3h study) = 6h of elite-level deep work. More effective than 10h of distracted study.",
                        "apply": "Reserve for new chapter reading, answer writing, or mock test analysis. Never use for passive activities. Put phone in airplane mode.",
                        "color": "#8b5cf6"
                    },
                    {
                        "name": "Weekly Review & Planning",
                        "icon": "📊",
                        "what": "Every Sunday: review what you studied, what you skipped, and plan next week's targets.",
                        "routine": "**Sunday 1h**: Check tracker data → What subjects got neglected? → What PYQs scored low? → Plan next 7 days with specific chapters/topics per day.",
                        "apply": "Use your Study Routine Tracker data! Check productivity %, waste hours, and subject distribution. Adjust next week's plan based on actual data.",
                        "color": "#06b6d4"
                    },
                    {
                        "name": "Environment Design",
                        "icon": "🏠",
                        "what": "Design your physical space to make studying easy and distractions hard.",
                        "routine": "**Study desk**: Only books + notes + water. **Phone**: In another room or locked drawer. **Study playlist**: Instrumental/lo-fi (no lyrics). **Lighting**: Bright white light.",
                        "apply": "Remove all choice from your environment. When you sit at your desk, the ONLY thing you can do is study. Willpower is finite — environment design is permanent.",
                        "color": "#ec4899"
                    },
                    {
                        "name": "Eisenhower Matrix",
                        "icon": "📐",
                        "what": "Categorize every task into 4 quadrants: Urgent+Important (DO), Important+Not Urgent (SCHEDULE), Urgent+Not Important (DELEGATE), Neither (ELIMINATE).",
                        "routine": "**Morning 5 min**: List today's tasks → Assign to quadrants. **Quadrant 2** (Important, Not Urgent) is where UPSC prep lives — schedule it FIRST. Never let Quadrant 3 eat your study time.",
                        "apply": "Current Affairs = Q1 (daily urgency). Syllabus study = Q2 (most important, schedule it). Social media = Q4 (eliminate). Random YouTube = Q3 (delegate to break time only).",
                        "color": "#0891b2"
                    },
                    {
                        "name": "Accountability Partner System",
                        "icon": "🤝",
                        "what": "Partner with another serious UPSC aspirant. Share daily targets, report progress every night, and call each other out on slacking.",
                        "routine": "**Morning**: Share today's study plan with partner. **Night**: Report what you actually did. **Weekly**: Compare study hours from trackers. The social pressure makes skipping feel costly.",
                        "apply": "Find 1-2 serious aspirants (in-person or online group). Use WhatsApp/Telegram for daily check-ins. Share screenshots of your Study Routine Tracker data weekly.",
                        "color": "#7c3aed"
                    },
                    {
                        "name": "Digital Detox Windows",
                        "icon": "📵",
                        "what": "Designate 3-4 hour blocks where ALL screens (except study material) are OFF. No phone, no social media, no notifications.",
                        "routine": "**6-10 AM**: Phone in airplane mode, study only. **2-5 PM**: Second detox window. **Before bed**: No screens 30 min before sleep. Use physical books during detox windows.",
                        "apply": "Install app blockers (Forest, Freedom). Delete Instagram/YouTube from phone during prep months. The average person checks their phone 96 times/day — each check costs 23 min of focus recovery.",
                        "color": "#dc2626"
                    },
                    {
                        "name": "Energy Management (Not Time Management)",
                        "icon": "🔋",
                        "what": "Match task difficulty to your energy levels throughout the day. Hard subjects when energy is HIGH, easy review when energy is LOW.",
                        "routine": "**Peak hours (6-11 AM for most)**: New chapters, answer writing, conceptual subjects. **Low hours (2-4 PM)**: Revision, flashcards, current affairs reading. **Recovery (evening)**: Light notes, mind maps.",
                        "apply": "Track your energy for 1 week — note when you feel most alert vs. drowsy. Schedule your weakest/hardest subject during peak energy. Never waste peak hours on easy tasks.",
                        "color": "#16a34a"
                    },
                    {
                        "name": "Task Batching",
                        "icon": "📦",
                        "what": "Group similar tasks together and do them in one go. Context-switching between different types of work kills productivity.",
                        "routine": "**Batch 1**: All newspaper/CA reading in one 1h slot. **Batch 2**: All note-making in one session. **Batch 3**: All PYQ solving together. **Batch 4**: All revision flashcards in one session.",
                        "apply": "Don't read 1 article, then solve 1 PYQ, then make 1 note. Instead: read ALL articles → make ALL notes → solve ALL PYQs. Each context switch costs 15-25 min of refocusing.",
                        "color": "#ca8a04"
                    },
                    {
                        "name": "Reflection Journaling",
                        "icon": "📔",
                        "what": "Spend 10 minutes before bed writing: What went well today? What didn't? What will I do differently tomorrow?",
                        "routine": "**3 questions nightly**: (1) Best study moment today? (2) Biggest time waste? (3) Tomorrow's #1 priority. Review weekly. Patterns emerge that data alone can't show.",
                        "apply": "Use a physical notebook — handwriting engages deeper processing. Be brutally honest. Track patterns: if 'phone distraction' appears 5/7 days, you have a systemic problem to solve.",
                        "color": "#9333ea"
                    },
                    {
                        "name": "Habit Stacking",
                        "icon": "🔗",
                        "what": "Link a new habit to an existing one: 'After I [CURRENT HABIT], I will [NEW HABIT].' Uses existing neural pathways to anchor new behaviors.",
                        "routine": "**After brushing teeth** → Read 1 editorial. **After morning tea** → 30 min active recall. **After lunch** → 15 min flashcard review. **After dinner** → Write 1 Mains answer.",
                        "apply": "Start with 2-minute mini-habits. Don't say 'I'll study 3 hours after waking up.' Say 'After I drink water, I'll open my book for 2 minutes.' The habit, not the duration, matters initially.",
                        "color": "#059669"
                    },
                    {
                        "name": "Implementation Intentions (If-Then Planning)",
                        "icon": "🎪",
                        "what": "Pre-decide your response to common obstacles: 'IF [obstacle occurs], THEN I will [specific action].' Removes decision fatigue in the moment.",
                        "routine": "**IF** I feel like checking my phone → **THEN** I will do 5 deep breaths and continue studying. **IF** I feel sleepy after lunch → **THEN** I will walk for 5 min and switch to an interesting subject.",
                        "apply": "Write 5-7 IF-THEN statements for your most common productivity killers. Stick them on your study desk. Research shows this doubles follow-through rates compared to motivation alone.",
                        "color": "#b91c1c"
                    },
                ]
                
                # ── PAGINATION for Productivity Methods ──
                _PM_PER_PAGE = 5
                _total_pm = len(_prod_methods)
                _total_pm_pages = max(1, (_total_pm + _PM_PER_PAGE - 1) // _PM_PER_PAGE)
                
                if "stm_prod_page" not in st.session_state:
                    st.session_state.stm_prod_page = 1
                if st.session_state.stm_prod_page > _total_pm_pages:
                    st.session_state.stm_prod_page = _total_pm_pages
                if st.session_state.stm_prod_page < 1:
                    st.session_state.stm_prod_page = 1
                
                _cur_pm_page = st.session_state.stm_prod_page
                _pm_start = (_cur_pm_page - 1) * _PM_PER_PAGE
                _pm_end = min(_pm_start + _PM_PER_PAGE, _total_pm)
                _page_methods = _prod_methods[_pm_start:_pm_end]
                
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:10px 18px;margin-bottom:14px;">
                    <span style="font-size:13px;color:#94a3b8;">Showing methods <strong style="color:#38bdf8;">{_pm_start+1}–{_pm_end}</strong> of <strong style="color:#38bdf8;">{_total_pm}</strong></span>
                    <span style="font-size:13px;color:#a78bfa;font-weight:600;">Page {_cur_pm_page} of {_total_pm_pages}</span>
                </div>
                """, unsafe_allow_html=True)
                
                for method in _page_methods:
                    _m_html = f'<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border:1px solid #334155;border-radius:16px;padding:20px 24px;margin-bottom:14px;border-left:5px solid {method["color"]};">' \
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;"><span style="font-size:24px;">{method["icon"]}</span><span style="font-size:18px;font-weight:800;color:#e2e8f0;">{method["name"]}</span></div>' \
                        f'<div style="font-size:13px;color:#cbd5e1;line-height:1.6;">' \
                        f'<div style="margin-bottom:10px;"><span style="color:{method["color"]};font-weight:700;font-size:11px;text-transform:uppercase;">\U0001f4cc What It Is: </span>{_md(method["what"])}</div>' \
                        f'<div style="margin-bottom:10px;"><span style="color:{method["color"]};font-weight:700;font-size:11px;text-transform:uppercase;">\U0001f4c5 Daily Routine: </span>{_md(method["routine"])}</div>' \
                        f'<div><span style="color:{method["color"]};font-weight:700;font-size:11px;text-transform:uppercase;">\U0001f527 How to Apply: </span>{_md(method["apply"])}</div>' \
                        f'</div></div>'
                    st.markdown(_m_html, unsafe_allow_html=True)
                
                # ── Pagination controls for Productivity Methods ──
                _pm_c1, _pm_c2, _pm_c3, _pm_c4, _pm_c5 = st.columns([1, 1, 2, 1, 1])
                with _pm_c1:
                    if st.button("⏮ First", key="stm_prod_first", disabled=(_cur_pm_page <= 1), use_container_width=True):
                        st.session_state.stm_prod_page = 1
                        st.rerun()
                with _pm_c2:
                    if st.button("◀ Prev", key="stm_prod_prev", disabled=(_cur_pm_page <= 1), use_container_width=True):
                        st.session_state.stm_prod_page = _cur_pm_page - 1
                        st.rerun()
                with _pm_c3:
                    _new_pm_page = st.selectbox(
                        "Page",
                        options=list(range(1, _total_pm_pages + 1)),
                        index=_cur_pm_page - 1,
                        key="stm_prod_page_select",
                        label_visibility="collapsed",
                        format_func=lambda x: f"📄 Page {x} of {_total_pm_pages}"
                    )
                    if _new_pm_page != _cur_pm_page:
                        st.session_state.stm_prod_page = _new_pm_page
                        st.rerun()
                with _pm_c4:
                    if st.button("Next ▶", key="stm_prod_next", disabled=(_cur_pm_page >= _total_pm_pages), use_container_width=True):
                        st.session_state.stm_prod_page = _cur_pm_page + 1
                        st.rerun()
                with _pm_c5:
                    if st.button("Last ⏭", key="stm_prod_last", disabled=(_cur_pm_page >= _total_pm_pages), use_container_width=True):
                        st.session_state.stm_prod_page = _total_pm_pages
                        st.rerun()
            
            # ═══════════════════════════════════════════
            # TAB 3 — SUBJECT-WISE STRATEGY (from PYQ data)
            # ═══════════════════════════════════════════
            with _tech_tab3:
                if not _prelims_subjects:
                    st.info("PYQ data not available. Please ensure pyq_data.json exists.")
                else:
                    st.markdown('<div style="background:#0f172a;border:1px solid #334155;border-radius:14px;padding:16px 20px;margin-bottom:16px;"><div style="font-size:14px;color:#e2e8f0;font-weight:700;margin-bottom:4px;">\U0001f3af Subject Priority \u2014 Based on UPSC PYQ Analysis (Last 10 Years)</div><div style="font-size:12px;color:#94a3b8;">Click on any subject to expand full strategy, books, chapters, revision plan &amp; proven techniques.</div></div>', unsafe_allow_html=True)
                    
                    # Map pyq_data subject names → upsc_strategy_data keys
                    _pyq_to_strategy_key = {
                        "Current Affairs": "current_affairs",
                        "Polity & Constitution": "polity",
                        "Modern History": "history",
                        "Ancient History": "history",
                        "Medieval History": "history",
                        "Art & Culture": "art_culture",
                        "Geography": "geography",
                        "Economics": "economy",
                        "Environment & Ecology": "environment",
                        "Indian Society": "society",
                        "Governance": "polity",
                        "International Relations": "international_relations",
                        "Science & Technology": "science_tech",
                        "Ethics": "ethics",
                        "Internal Security": "internal_security",
                        "Sociology (Optional)": "sociology",
                    }
                    
                    # Sort prelims_subjects by frequency_rank (already integers 1-16)
                    _sorted_subjects = sorted(_prelims_subjects, key=lambda x: x.get('frequency_rank', 999))

                    # ── Render all subjects as expanders (no pagination needed) ──
                    for _idx, _pyq_subj in enumerate(_sorted_subjects):
                        _s_name = _pyq_subj['subject']
                        _s_score = _pyq_subj['importance_score']
                        _s_rank = _pyq_subj['frequency_rank']
                        _s_chapters_pyq = _pyq_subj.get('important_chapters', '')
                        _s_topics_pyq = _pyq_subj.get('important_topics', '')
                        _s_revision_pyq = _pyq_subj.get('revision_strategy', '')
                        
                        # Get rich data from upsc_strategy_data
                        _strat_key = _pyq_to_strategy_key.get(_s_name, '')
                        _strat_data = _all_subjects_data.get(_strat_key, {}) if _strat_key else {}
                        
                        # Badge/color
                        if _s_score >= 95:
                            _badge = "🔴 CRITICAL"
                            _badge_color = "#ef4444"
                        elif _s_score >= 90:
                            _badge = "🟡 HIGH"
                            _badge_color = "#f59e0b"
                        elif _s_score >= 85:
                            _badge = "🟠 IMPORTANT"
                            _badge_color = "#f97316"
                        else:
                            _badge = "🟢 MODERATE"
                            _badge_color = "#22c55e"
                        
                        _exp_label = f"#{_s_rank} {_s_name}  —  {_s_score}/100  {_badge}"
                        
                        with st.expander(_exp_label, expanded=False):
                            # ── Score bar ──
                            st.markdown(f'<div style="background:#1e293b;border-radius:8px;height:10px;margin-bottom:16px;overflow:hidden;"><div style="background:linear-gradient(90deg,{_badge_color},{_badge_color}88);width:{_s_score}%;height:100%;border-radius:8px;"></div></div>', unsafe_allow_html=True)
                            
                            # ── SECTION 1: High-Frequency Topics & Focus Chapters from PYQ data ──
                            _sec1_c1, _sec1_c2 = st.columns(2)
                            with _sec1_c1:
                                st.markdown(f'**🎯 High-Frequency Topics (PYQ)**')
                                if _s_topics_pyq:
                                    for _tp in _s_topics_pyq.split(', '):
                                        st.markdown(f'- {_tp.strip()}')
                                else:
                                    st.caption("N/A")
                            with _sec1_c2:
                                st.markdown(f'**📋 Focus Chapters (PYQ)**')
                                if _s_chapters_pyq:
                                    for _ch in _s_chapters_pyq.split(', '):
                                        st.markdown(f'- {_ch.strip()}')
                                else:
                                    st.caption("N/A")
                            
                            st.divider()
                            
                            # ── SECTION 2: Standard Books (in order) ──
                            st.markdown('**📚 Standard Books (Follow in This Order)**')
                            _book_str = _strat_data.get('book', '')
                            if _book_str:
                                _books_list = [b.strip() for b in _book_str.replace(' + ', ', ').replace(' / ', ', ').split(',') if b.strip()]
                                for _bi, _bk in enumerate(_books_list, 1):
                                    st.markdown(f'{_bi}. **{_bk}**')
                            else:
                                st.caption("NCERT + Standard reference books")
                            
                            # Weight & avg questions
                            _weight = _strat_data.get('weight', '')
                            _avg_qs = _strat_data.get('avg_qs', '')
                            if _weight or _avg_qs:
                                st.markdown(f'> **Prelims Weight:** {_weight} | **Avg Questions/Year:** {_avg_qs}')
                            
                            st.divider()
                            
                            # ── SECTION 3: Step-by-Step Study Strategy ──
                            st.markdown('**🧠 Step-by-Step Study Strategy**')
                            _revision_str = _strat_data.get('revision', '')
                            _short_notes = _strat_data.get('short_notes', '')
                            
                            # Build step-by-step from strategy data
                            _steps = []
                            _steps.append(f"**Step 1 — Foundation Read:** Read the standard book ({_strat_data.get('book', 'NCERT').split('+')[0].split('/')[0].strip()}) cover-to-cover. Make basic notes. Don't try to memorize — focus on understanding concepts.")
                            if _short_notes:
                                _steps.append(f"**Step 2 — Short Notes:** {_short_notes}")
                            _steps.append(f"**Step 3 — PYQ Analysis:** Solve last 10 years PYQs topic-wise. Identify which areas UPSC focuses on. Mark topics you got wrong.")
                            if _revision_str:
                                _steps.append(f"**Step 4 — Revision Cycle:** {_revision_str}")
                            _steps.append("**Step 5 — Current Affairs Integration:** Link every static topic to recent news/schemes/events. Maintain a running CA-static linkage sheet.")
                            _steps.append("**Step 6 — Mock Tests:** Take subject-wise sectional tests. Analyze every wrong answer. Maintain an error journal.")
                            
                            for _step in _steps:
                                st.markdown(f'- {_step}')
                            
                            st.divider()
                            
                            # ── SECTION 4: Chapter-wise Breakdown (from strategy data) ──
                            _chapters_data = _strat_data.get('chapters', [])
                            if _chapters_data:
                                st.markdown('**📖 Chapter-wise Study Plan**')
                                # Group by priority
                                _critical = [c for c in _chapters_data if c.get('priority') == 'Critical']
                                _high = [c for c in _chapters_data if c.get('priority') == 'High']
                                _medium = [c for c in _chapters_data if c.get('priority') == 'Medium']
                                
                                if _critical:
                                    st.markdown('🔴 **CRITICAL (Do First — Highest PYQ frequency)**')
                                    for _ch in _critical:
                                        _focus_str = ', '.join(_ch.get('focus', [])[:4])
                                        st.markdown(f'- **{_ch["ch"]}** — Revisions: {_ch.get("revisions", 3)}x | PYQ: {_ch.get("pyq", "N/A")} | Focus: {_focus_str}')
                                
                                if _high:
                                    st.markdown('🟡 **HIGH PRIORITY**')
                                    for _ch in _high:
                                        _focus_str = ', '.join(_ch.get('focus', [])[:4])
                                        st.markdown(f'- **{_ch["ch"]}** — Revisions: {_ch.get("revisions", 3)}x | PYQ: {_ch.get("pyq", "N/A")} | Focus: {_focus_str}')
                                
                                if _medium:
                                    st.markdown('🟢 **MODERATE**')
                                    for _ch in _medium:
                                        _focus_str = ', '.join(_ch.get('focus', [])[:3])
                                        st.markdown(f'- **{_ch["ch"]}** — Revisions: {_ch.get("revisions", 2)}x | PYQ: {_ch.get("pyq", "N/A")} | Focus: {_focus_str}')
                            
                            st.divider()
                            
                            # ── SECTION 5: Revision Method ──
                            st.markdown('**🔄 Revision Method After Completing**')
                            if _revision_str:
                                st.markdown(f'> {_revision_str}')
                            st.markdown(f'''
- **1st Revision (After 1 day):** Re-read short notes + attempt 20 MCQs on the topic
- **2nd Revision (After 7 days):** Active recall — close book, write key points from memory, then compare
- **3rd Revision (After 30 days):** Rapid scan of short notes only (should take 50% less time)
- **4th Revision (Before exam):** Quick flashcard/keyword scan — if you can't recall in 5 sec, re-read that section
- **Error Journal Review:** After every mock test, revise ONLY the topics you got wrong
''')
                            
                            st.divider()
                            
                            # ── SECTION 6: Proven Technique (detailed) ──
                            st.markdown('**🔧 Proven Study Technique — How to Implement**')
                            _tips_list = _strat_data.get('tips', [])
                            
                            # PYQ-based revision strategy
                            if _s_revision_pyq:
                                st.markdown(f'**📌 PYQ-Based Strategy:** {_s_revision_pyq}')
                            
                            # Tips from strategy data
                            if _tips_list:
                                st.markdown('**💡 Expert Tips:**')
                                for _tip in _tips_list:
                                    st.markdown(f'- ✅ {_tip}')
                            
                            # Current Affairs link
                            _gs_paper = _strat_data.get('gs', '')
                            if _gs_paper:
                                st.markdown(f'**🔗 GS Paper Link:** {_gs_paper}')
            
            # ── SMART WORK TIPS (Study Target Manager) ──
            st.divider()
            _sw_tips_tm = generate_smart_work_tips(
                prod_hours=subj_hours.sum(),
                waste_hours=0,
                essential_hours=0,
                study_streak=0,
                focus_pct=0,
                subject_count=num_subjects,
                productivity_pct=0,
                context="target"
            )
            st.markdown(render_smart_work_section(_sw_tips_tm, max_tips=10), unsafe_allow_html=True)


# ---------------- PRODUCTIVITY ANALYSIS ----------------
elif menu == "Productivity Analysis":
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
                st.metric("📚 Productive Hours", f"{prod_total:.1f}h", 
                         delta=f"{(prod_total/(prod_total+essential_total+waste_total)*100) if (prod_total+essential_total+waste_total)>0 else 0:.0f}%")
            with sum_col2:
                st.metric("⚡ Essential Hours", f"{essential_total:.1f}h",
                         delta=f"{(essential_total/(prod_total+essential_total+waste_total)*100) if (prod_total+essential_total+waste_total)>0 else 0:.0f}%")
            with sum_col3:
                st.metric("⚠️ Waste Hours", f"{waste_total:.1f}h",
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
                        
                        Productive: {trend_prod:.1f}h/day
                        """)
                    
                    with trend_col2:
                        st.info(f"""
                        📊 **Waste Trend**
                        
                        Waste: {trend_waste:.1f}h/day
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
                - **Productive**: {prod_total:.1f}h | **Essential**: {essential_total:.1f}h | **Waste**: {waste_total:.1f}h
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

elif menu == "Ask Esu":
    # Pre-load saved responses from database
    if "saved_esu_responses_db" not in st.session_state:
        st.session_state["saved_esu_responses_db"] = get_esu_responses(USER)
    
    import ai as _ai_esu
    
    # ── Hero Banner ──
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%);
        padding: 28px 30px 20px 30px; border-radius: 16px;
        border: 1px solid #4f46e5; margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(79, 70, 229, 0.15);
    ">
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">
            <span style="font-size: 32px;">🤖</span>
            <h2 style="margin: 0; color: #e0e7ff; font-weight: 800; letter-spacing: -0.5px;">Ask Esu</h2>
        </div>
        <p style="margin: 0; color: #a5b4fc; font-size: 14px; line-height: 1.5;">
            Your AI study mentor — ask anything about UPSC strategy, timetable, subject planning, or productivity.<br>
            <span style="color: #818cf8;">💡 Mention your weak/strong subjects in the question for personalized answers.</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get all data for analysis
    df_all = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    if not df_all.empty:
        if 'start_time' not in df_all.columns: df_all['start_time'] = None
        df_all['start_time'] = df_all.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        df_all['chapter'] = df_all['chapter'].apply(get_clean_chapter)
    chapter_data = read_sql("SELECT * FROM chapters WHERE username=%s", (USER,))
    
    # Load UPSC PYQ data (used by AI behind the scenes, not shown in UI)
    import json
    try:
        with open('pyq_data.json', 'r') as f:
            pyq_json_data = json.load(f)
            pyq_data_prelims = pyq_json_data.get('prelims', [])
            pyq_data_mains = pyq_json_data.get('mains', [])
    except Exception:
        pyq_data_prelims = []
        pyq_data_mains = []
    
    # Calculate key metrics
    if not df_all.empty:
        prod_df = df_all[df_all['type'].isin(['Study', 'Revision', 'Book Reading', 'Answer Writing', 'Practice', 'Test'])]
        essential_df = df_all[df_all['type'].isin(['Office', 'WFH', 'Coaching'])]
        waste_df_esu = df_all[df_all['type'].isin(['Entertainment', 'Social Media'])]
        
        prod_total_esu = prod_df['duration'].sum() if not prod_df.empty else 0
        essential_total_esu = essential_df['duration'].sum() if not essential_df.empty else 0
        waste_total_esu = waste_df_esu['duration'].sum() if not waste_df_esu.empty else 0
        
        # Subject-wise data
        subj_data = prod_df.groupby('subject')['duration'].sum().to_dict() if not prod_df.empty else {}
        
        # Chapter-wise data
        chapter_study_data = prod_df.groupby(['subject', 'chapter'])['duration'].sum().to_dict() if not prod_df.empty and 'chapter' in prod_df.columns else {}
        
        # Chapter completion data
        if not chapter_data.empty:
            chapter_completion = chapter_data.groupby('subject').agg({
                'completed': 'sum',
                'chapter': 'count'
            }).to_dict()
            chapter_completion_summary = {subject: f"{chapter_completion['completed'].get(subject, 0)}/{chapter_completion['chapter'].get(subject, 0)} chapters" 
                                         for subject in subj_data.keys()}
        else:
            chapter_completion_summary = {}
        
        # ── SMART WORK TIPS (Ask Esu Page) ──
        _sw_streak_esu = streak(df_all) if not df_all.empty else 0
        _sw_focus_esu = focus_score(df_all) if not df_all.empty else 0
        _sw_tips_esu = generate_smart_work_tips(
            prod_hours=prod_total_esu,
            waste_hours=waste_total_esu,
            essential_hours=essential_total_esu,
            study_streak=_sw_streak_esu,
            focus_pct=_sw_focus_esu,
            subject_count=len(subj_data),
            productivity_pct=0,
            context="ask_esu"
        )
        with st.expander("⚡ Smart Work Tips & Strategies", expanded=False):
            st.markdown(render_smart_work_section(_sw_tips_esu, max_tips=15), unsafe_allow_html=True)
        
        # ── Question Input & Type ──
        type_col, subj_col = st.columns([1, 2])
        with type_col:
            esu_query_type = st.selectbox(
                "🎯 Query Type",
                ["General Query", "Subject Wise Strategy"],
                help="General Query uses smart detection. Subject Wise allows you to pick specific subjects for detailed analysis.",
                key="esu_query_type"
            )
        
        selected_subj_keys = []
        if esu_query_type == "Subject Wise Strategy":
            with subj_col:
                # Get subject display names for the pills
                subj_options = {k: v['name'] for k, v in _ai_esu.ALL_SUBJECTS.items()}
                selected_subj_names = st.pills(
                    "📚 Select Subjects for Detailed Strategy",
                    options=list(subj_options.values()),
                    selection_mode="multi",
                    help="Pick 1-5 subjects. Esu will provide full detailed strategy tables for these.",
                    key="esu_selected_subjects"
                )
                # Map back to keys
                selected_subj_keys = [k for k, v in subj_options.items() if v in selected_subj_names]
        else:
            with subj_col:
                st.info("💡 Esu will automatically detect relevant subjects from your question.")

        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_prompt = st.text_area(
                "💬 What would you like to ask Esu?",
                placeholder="Examples:\n• Create a 30-day timetable for UPSC Prelims\n• My weak subjects are Polity and Economy — what should I focus on?\n• Which topics have highest PYQ frequency in Geography?\n• How to reduce my waste time and study 10 hours daily?",
                height=130,
                key="esu_prompt"
            )
        
        with col2:
            exam_date = st.date_input(
                "📅 Exam Date (optional)",
                value=None,
                key="esu_exam_date"
            )
            if exam_date:
                from database import get_ist_now
                days_left = (exam_date - get_ist_now().date()).days
                st.markdown(f"""
                <div style="background: #1e293b; padding: 10px; border-radius: 10px; border: 1px solid #334155; text-align: center;">
                    <div style="font-size: 24px; font-weight: 800; color: {'#f87171' if days_left < 30 else '#38bdf8'};">{days_left}</div>
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Days Left</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Generate Esu Response
        if st.button("💬 Ask Esu", type="primary", width='stretch'):
            if not user_prompt.strip():
                st.warning("Please enter a question or request for Esu!")
            else:
                with st.spinner("🤔 Esu is thinking..."):
                    # Context: only exam date (all tokens prioritized for UPSC strategy)
                    context = ""
                    if exam_date:
                        context = f"Exam: {exam_date.strftime('%b %d, %Y')} ({days_left} days left)"
                    
                    # Build COMPREHENSIVE PYQ context — ALL subjects with full details
                    # Sorted by importance (highest priority first)
                    pyq_context = ""
                    if pyq_data_prelims:
                        sorted_pyq = sorted(pyq_data_prelims, key=lambda x: x.get('importance_score', 0), reverse=True)
                        pyq_lines = []
                        for i, s in enumerate(sorted_pyq):
                            name = s.get('subject', '')
                            score = s.get('importance_score', 0)
                            topics = s.get('important_topics', '')[:120]
                            chapters = s.get('important_chapters', '')[:100]
                            strategy = s.get('revision_strategy', '')[:80]
                            pyq_lines.append(
                                f"{i+1}. {name}({score}/100) | Topics: {topics} | Ch: {chapters} | Rev: {strategy}"
                            )
                        pyq_context = "\n".join(pyq_lines)
                    
                    # Call AI with smart context injection
                    try:
                        esu_response = _ai_esu.ask_esu(user_prompt, context, pyq_context, selected_subjects=selected_subj_keys)
                        st.session_state["esu_response"] = esu_response
                        st.session_state["esu_last_question"] = user_prompt
                    except Exception as e:
                        st.error(f"Error getting response from Esu: {str(e)}")
        
        # Display Esu Response
        if st.session_state.get("esu_response"):
            st.divider()
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
                border: 2px solid #6366f1;
                border-radius: 15px;
                padding: 20px 25px 10px 25px;
                margin-bottom: 5px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            ">
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 24px; margin-right: 15px;">🤖</span>
                    <h3 style="margin: 0; color: #e0e7ff; font-weight: 700;">Esu's Guidance</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # Render response as proper markdown so tables, headers, bullets render correctly
            st.markdown(st.session_state["esu_response"])
            
            col_resp1, col_resp2, col_resp3 = st.columns(3)
            with col_resp1:
                if st.button("💾 Save to History", key="esu_save", type="primary"):
                    # Save to database
                    save_esu_response(USER, st.session_state.get("esu_last_question", ""), st.session_state["esu_response"])
                    # Refresh saved list
                    st.session_state["saved_esu_responses_db"] = get_esu_responses(USER)
                    st.toast("✅ Response saved to history!", icon="✅")
                    # Clear current response to show it moved to history
                    st.session_state["esu_response"] = None
                    st.rerun()
            with col_resp2:
                if st.button("❌ Cancel / Clear", key="esu_cancel_clear"):
                    st.session_state["esu_response"] = None
                    st.session_state["esu_prompt"] = "" # Also clear the prompt
                    st.toast("🗑️ Response cleared.")
                    st.rerun()
            with col_resp3:
                if st.button("🔄 New Question", key="esu_new"):
                    st.session_state["esu_response"] = None
                    st.rerun()
            
        
        # Display saved responses from database
        saved_db = st.session_state.get("saved_esu_responses_db", [])
        if saved_db:
            st.divider()
            sh_col1, sh_col2 = st.columns([3, 1])
            with sh_col1:
                st.subheader("📜 Esu History")
            with sh_col2:
                if st.button("🗑️ Clear All", key="clear_all_esu", help="This will delete all saved responses"):
                    st.session_state["confirm_clear_all_esu"] = True
            
            if st.session_state.get("confirm_clear_all_esu", False):
                st.warning("⚠️ Are you sure you want to delete ALL saved responses?")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("🔥 Yes, Clear All", key="clear_all_esu_confirm"):
                        for s in saved_db:
                            delete_esu_response(s['id'], USER)
                        st.session_state["saved_esu_responses_db"] = []
                        st.session_state["confirm_clear_all_esu"] = False
                        st.success("History cleared!")
                        st.rerun()
                with cc2:
                    if st.button("❌ Cancel", key="clear_all_esu_cancel"):
                        st.session_state["confirm_clear_all_esu"] = False
                        st.rerun()

            for saved in saved_db:
                resp_id = saved['id']
                with st.expander(f"📌 {saved['question'][:60]}... | {saved['timestamp'].strftime('%b %d, %H:%M')}"):
                    st.markdown(f"**🗣️ Question:** {saved['question']}")
                    st.divider()
                    st.markdown(saved['response'])
                    if st.button("🗑️ Delete", key=f"del_saved_db_{resp_id}"):
                        delete_esu_response(resp_id, USER)
                        st.session_state["saved_esu_responses_db"] = get_esu_responses(USER)
                        st.toast("🗑️ Response deleted.")
                        st.rerun()

    else:
        st.warning("No data found. Please log some activities first in Daily Entry.")

# ---------------- EXPENSE ----------------
elif menu == "Expenses":
    st.title("💰 Expenses")
    import ai as _ai_exp

    df_full = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    df_full = df_full[df_full['amount'] > 0]

    # Keep only last 60 days for delete management view to prevent page lag
    if not df_full.empty:
        cutoff_date = (get_ist_now().date() - timedelta(days=60)).strftime('%Y-%m-%d')
        df = df_full[df_full['date'] >= cutoff_date].copy()
    else:
        df = df_full.copy()

    if not df_full.empty:
        df_full['year_str'] = pd.to_datetime(df_full['date']).dt.strftime('%Y')
        df_full['month_str'] = pd.to_datetime(df_full['date']).dt.strftime('%Y-%m')
        
        current_year_str = get_ist_now().date().strftime('%Y')
        current_month_str = get_ist_now().date().strftime('%Y-%m')
        current_month_exp = df_full[df_full['month_str'] == current_month_str]['amount'].sum()
        current_month_cats = df_full[df_full['month_str'] == current_month_str]['type'].nunique()

        e1, e2 = st.columns(2)
        e1.metric(f"Current Month Expenses ({current_month_str})", f"₹{round(current_month_exp, 2)}")
        e2.metric("Categories (Current Month)", f"{current_month_cats}")

        # Month-wise Expenses
        st.markdown("### 📅 Month-wise Expenses")
        month_wise_exp = df_full.groupby('month_str')['amount'].sum().reset_index().sort_values('month_str', ascending=False)
        st.dataframe(month_wise_exp.rename(columns={'month_str': 'Month', 'amount': 'Total Expense (₹)'}), width='stretch', hide_index=True)

        # Year-wise Expenses
        st.markdown("### 📅 Year-wise Expenses")
        year_wise_exp = df_full.groupby('year_str')['amount'].sum().reset_index().sort_values('year_str', ascending=False)
        st.dataframe(year_wise_exp.rename(columns={'year_str': 'Year', 'amount': 'Total Expense (₹)'}), width='stretch', hide_index=True)

        # Date-wise Breakdown
        st.markdown("### 📅 Date-wise Expense Breakdown")
        date_breakdown_df = df_full[['date', 'type', 'subject', 'chapter', 'amount']].copy()
        date_breakdown_df = date_breakdown_df.rename(columns={
            'date': 'Date',
            'type': 'Category',
            'subject': 'Subject',
            'chapter': 'Description/Details',
            'amount': 'Amount (₹)'
        }).sort_values('Date', ascending=False)
        st.dataframe(date_breakdown_df, width='stretch', hide_index=True)

        # Category breakdown by Year & Month
        st.markdown("### 🔍 Category Breakdown")
        
        col_yr, col_mn = st.columns(2)
        with col_yr:
            selected_year = st.selectbox("Select Year", year_wise_exp['year_str'].tolist(), key="cat_breakdown_year")
            
        if selected_year:
            year_df = df_full[df_full['year_str'] == selected_year].copy()
            year_df['month_num'] = pd.to_datetime(year_df['date']).dt.month
            
            import calendar as _cal
            available_months = sorted(year_df['month_num'].unique())
            month_options = ["All Months"] + [_cal.month_name[m] for m in available_months]
            
            with col_mn:
                selected_month_name = st.selectbox("Select Month", month_options, key="cat_breakdown_month")
            
            if selected_month_name != "All Months":
                month_idx = list(_cal.month_name).index(selected_month_name)
                filtered_df = year_df[year_df['month_num'] == month_idx]
                title_suffix = f"{selected_month_name} {selected_year}"
            else:
                filtered_df = year_df
                title_suffix = f"{selected_year}"
                
            exp_grp = filtered_df.groupby('type')['amount'].sum().sort_values(ascending=False).reset_index()
            
            col_eb, col_ep = st.columns(2)
            with col_eb:
                st.dataframe(exp_grp.rename(columns={'type':'Category', 'amount':'Amount (₹)'}), width='stretch', hide_index=True)
            with col_ep:
                fig_ep = px.pie(exp_grp, names='type', values='amount',
                                title=f"Expense Distribution ({title_suffix})",
                                color_discrete_sequence=px.colors.qualitative.Set3)
                fig_ep.update_traces(
                    textinfo='percent+value',
                    texttemplate='₹%{value:,.2f}<br>%{percent:.1%}',
                    hovertemplate="%{label}<br>Amount: ₹%{value:,.2f}<br>Percentage: %{percent:.1%}<extra></extra>"
                )
                st.plotly_chart(fig_ep, width='stretch', key=f"expenses_pie_{selected_year}_{selected_month_name}")



        # Variables needed for 60-day summary below
        if not df.empty:
            total_exp = df['amount'].sum()
            exp_grp = df.groupby('type')['amount'].sum().sort_values(ascending=False)
        else:
            total_exp = 0
            exp_grp = pd.Series(dtype=float)

        # ── NEW: EXPENSE TREND GRAPHS (RESTRUCTURED) ─────────────────────────
        st.divider()
        st.markdown("### 📈 Expense Trend Analysis")
        
        # Prepare date-time features
        df_exp = df_full.copy()
        df_exp['date_dt'] = pd.to_datetime(df_exp['date'])
        df_exp['hour'] = df_exp.apply(extract_hour_from_row, axis=1)
        df_exp['day_name'] = df_exp['date_dt'].dt.day_name()
        df_exp['month_str'] = df_exp['date_dt'].dt.strftime('%Y-%m')
        df_exp['year'] = df_exp['date_dt'].dt.year
        
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # 1. Hourly Distribution
        st.markdown("#### ⏰ Hourly Distribution")
        h_exp = df_exp.dropna(subset=['hour']).groupby('hour')['amount'].sum().reset_index()
        if not h_exp.empty:
            h_all = pd.DataFrame({'hour': range(24)})
            h_full = h_all.merge(h_exp, on='hour', how='left').fillna(0)
            h_full['hour_label'] = h_full['hour'].apply(lambda h: f"{h:02d}:00")
            fig_h = px.line(h_full, x='hour_label', y='amount', markers=True,
                           title="Expenses by Hour of Day",
                           labels={'hour_label': 'Hour', 'amount': 'Amount (₹)'},
                           color_discrete_sequence=['#f59e0b'])
            st.plotly_chart(fig_h, width='stretch', key="exp_hourly_line")
            
            if st.checkbox("Show trend for all activities (Category-wise)", key="exp_hour_all_activities"):
                h_cat_exp = df_exp.dropna(subset=['hour']).groupby(['hour', 'type'])['amount'].sum().reset_index()
                h_cat_exp['hour_label'] = h_cat_exp['hour'].apply(lambda h: f"{h:02d}:00")
                fig_h_cat = px.line(h_cat_exp, x='hour_label', y='amount', color='type', markers=True,
                               title="Hourly Expense Trend by Category",
                               labels={'hour_label': 'Hour', 'amount': 'Amount (₹)', 'type': 'Category'})
                st.plotly_chart(fig_h_cat, width='stretch', key="exp_hourly_trend_cat")
        else:
            st.caption("No hourly data available.")

        # 2. Weekday Distribution
        st.markdown("#### 📅 Weekday Distribution")
        d_exp = df_exp.groupby('day_name')['amount'].sum().reindex(days_order).reset_index().fillna(0)
        fig_d = px.line(d_exp, x='day_name', y='amount', markers=True,
                       title="Expenses by Day of Week",
                       labels={'day_name': 'Day', 'amount': 'Amount (₹)'},
                       color_discrete_sequence=['#3b82f6'])
        st.plotly_chart(fig_d, width='stretch', key="exp_daywise_line")
        
        if st.checkbox("Show trend for all activities (Category-wise)", key="exp_daywise_all_activities"):
            d_cat_exp = df_exp.groupby(['day_name', 'type'])['amount'].sum().reset_index()
            # To ensure the order is correct, we can convert day_name to categorical
            d_cat_exp['day_name'] = pd.Categorical(d_cat_exp['day_name'], categories=days_order, ordered=True)
            d_cat_exp = d_cat_exp.sort_values('day_name')
            fig_d_cat = px.line(d_cat_exp, x='day_name', y='amount', color='type', markers=True,
                           title="Expenses by Day of Week by Category",
                           labels={'day_name': 'Day', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_d_cat, width='stretch', key="exp_daywise_trend_cat")

        # 3. Daily Trend
        st.markdown("#### 📆 Daily Trend")
        daily_exp = df.groupby('date')['amount'].sum().reset_index().sort_values('date')
        fig_daily = px.line(daily_exp, x='date', y='amount', markers=True,
                           title="Daily Expense Trend",
                           labels={'date': 'Date', 'amount': 'Amount (₹)'},
                           color_discrete_sequence=['#10b981'])
        st.plotly_chart(fig_daily, width='stretch', key="exp_daily_trend")
        
        if st.checkbox("Show trend for all activities (Category-wise)", key="exp_daily_all_activities"):
            daily_cat_exp = df_exp.groupby(['date', 'type'])['amount'].sum().reset_index().sort_values('date')
            fig_daily_cat = px.line(daily_cat_exp, x='date', y='amount', color='type', markers=True,
                               title="Daily Expense Trend by Category",
                               labels={'date': 'Date', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_daily_cat, width='stretch', key="exp_daily_trend_cat")

        # 3.5 Monthly Trend
        st.markdown("#### 📅 Monthly Trend")
        monthly_exp = df_exp.groupby('month_str')['amount'].sum().reset_index().sort_values('month_str')
        fig_monthly = px.line(monthly_exp, x='month_str', y='amount', markers=True,
                             title="Monthly Expense Trend (Overall)",
                             labels={'month_str': 'Month', 'amount': 'Amount (₹)'},
                             color_discrete_sequence=['#f59e0b'])
        st.plotly_chart(fig_monthly, width='stretch', key="exp_monthly_trend_overall")

        show_all_activities = st.checkbox("Show trend for all activities (Category-wise)", key="exp_month_all_activities")
        if show_all_activities:
            month_cat_trend = df_exp.groupby(['month_str', 'type'])['amount'].sum().reset_index().sort_values('month_str')
            fig_monthly_cat = px.line(month_cat_trend, x='month_str', y='amount', color='type', markers=True,
                                     title="Monthly Expense Trend by Category",
                                     labels={'month_str': 'Month', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_monthly_cat, width='stretch', key="exp_monthly_trend_cat")

        # 4. Yearly Trend
        st.markdown("#### 📊 Yearly Trend")
        y_trend = df_exp.groupby('year')['amount'].sum().reset_index().sort_values('year')
        fig_y = px.line(y_trend, x='year', y='amount', markers=True,
                       title="Yearly Expense Trend",
                       labels={'year': 'Year', 'amount': 'Amount (₹)'},
                       color_discrete_sequence=['#8b5cf6'])
        st.plotly_chart(fig_y, width='stretch', key="exp_yearly_trend")
        
        if st.checkbox("Show trend for all activities (Category-wise)", key="exp_year_all_activities"):
            y_cat_trend = df_exp.groupby(['year', 'type'])['amount'].sum().reset_index().sort_values('year')
            fig_y_cat = px.line(y_cat_trend, x='year', y='amount', color='type', markers=True,
                           title="Yearly Expense Trend by Category",
                           labels={'year': 'Year', 'amount': 'Amount (₹)', 'type': 'Category'})
            st.plotly_chart(fig_y_cat, width='stretch', key="exp_yearly_trend_cat")

        # Expense Summary Analysis
        st.divider()
        st.markdown(f"### 📊 Expense Analysis Summary ({current_year_str})")
        
        df_yearly = df_full[df_full['year_str'] == current_year_str]
        
        exp_stats_col1, exp_stats_col2, exp_stats_col3, exp_stats_col4 = st.columns(4)
        
        total_exp_yearly = df_yearly['amount'].sum()
        
        with exp_stats_col1:
            st.metric("Total Expenses", f"₹{total_exp_yearly:.0f}")
        with exp_stats_col2:
            avg_exp = df_yearly['amount'].mean()
            st.metric("Average Expense", f"₹{avg_exp:.0f}" if pd.notna(avg_exp) else "₹0")
        with exp_stats_col3:
            yearly_exp_grp = df_yearly.groupby('type')['amount'].sum().sort_values(ascending=False)
            max_category = yearly_exp_grp.idxmax() if not yearly_exp_grp.empty else "N/A"
            max_amount = yearly_exp_grp.max() if not yearly_exp_grp.empty else 0
            st.metric("Highest Category", max_category, f"₹{max_amount:.0f}")
        with exp_stats_col4:
            day_grp = df_yearly.groupby('date')['amount'].sum()
            highest_day = day_grp.idxmax() if not day_grp.empty else "N/A"
            highest_day_amount = day_grp.max() if not day_grp.empty else 0
            st.metric("Highest Spending Day", str(highest_day), f"₹{highest_day_amount:.0f}")
        
        # Daily average
        daily_avg = df_yearly.groupby('date')['amount'].sum().mean()
        st.info(f"📆 **Daily Average**: ₹{daily_avg:.0f}/day" if pd.notna(daily_avg) else "📆 **Daily Average**: ₹0/day")
        
        st.info("💡 Use the **Ask Esu** page to get personalized expense optimization and budgeting strategies.")


    else:
        st.info("No expenses recorded yet.")

# ---------------- MANAGE USERS ----------------
elif menu == "Manage Users":
    st.title("👥 User Management Portal")
    st.write("Manage access and update security settings.")
    
    # ── Change Password Section ──
    st.subheader("🔐 Change User Password")
    with st.expander("Update credentials for an existing user"):
        with st.form("change_password_form"):
            target_usr_list = [""] + read_sql("SELECT username FROM users")['username'].tolist()
            target_usr = st.selectbox("Select User", target_usr_list)
            new_pass = st.text_input("New Password", type="password")
            if st.form_submit_button("Update Password"):
                if not target_usr or not new_pass:
                    st.error("Please select a user and provide a new password.")
                else:
                    try:
                        c.execute("UPDATE users SET password=%s WHERE username=%s", (new_pass, target_usr))
                        conn.commit()
                        st.success(f"Password for '{target_usr}' updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update password: {e}")

    # ── Add New User Section ──
    st.subheader("➕ Register New User")
    with st.form("add_user_form"):
        new_usr = st.text_input("New Username")
        new_pwd = st.text_input("New Password", type="password")
        if st.form_submit_button("Add User"):
            try:
                c.execute("SELECT id FROM users WHERE username=%s", (new_usr,))
                if c.fetchone():
                    st.error(f"Username '{new_usr}' already exists!")
                elif not new_usr.strip() or not new_pwd:
                    st.error("Username and Password cannot be empty.")
                else:
                    c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (new_usr, new_pwd))
                    conn.commit()
                    st.success(f"User '{new_usr}' added successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to add user: {e}")
            
    # ── Existing Users List ──
    st.subheader("📋 Current System Access")
    try:
        df_users = read_sql("SELECT id, username, password, last_login FROM users ORDER BY id")
        for _, row in df_users.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([5, 1, 1])
                
                # Format last login
                l_log = row['last_login']
                if pd.notnull(l_log):
                    # Convert to string and handle potential timezone aware objects
                    if hasattr(l_log, 'strftime'):
                        l_log_str = l_log.strftime('%d %b, %H:%M')
                    else:
                        l_log_str = str(l_log)
                else:
                    l_log_str = "Never"
                    
                c1.write(f"👤 **{row['username']}** (ID: {row['id']}) — 🔑 Password: `{row['password']}`  \n🕒 Last Login: `{l_log_str}`")
                if row['username'] != 'admin':
                    if c2.button("Delete", key=f"del_{row['id']}", help="Remove user access"):
                        st.session_state[f"conf_del_{row['id']}"] = True
                    
                    if st.session_state.get(f"conf_del_{row['id']}"):
                        st.warning(f"Delete '{row['username']}'?")
                        y, n = st.columns(2)
                        if y.button("Yes", key=f"y_{row['id']}"):
                            c.execute("DELETE FROM users WHERE id=%s", (row['id'],))
                            conn.commit()
                            st.session_state[f"conf_del_{row['id']}"] = False
                            st.rerun()
                        if n.button("No", key=f"n_{row['id']}"):
                            st.session_state[f"conf_del_{row['id']}"] = False
                            st.rerun()
                st.divider()
    except Exception as e:
        st.error(f"Error loading users: {e}")

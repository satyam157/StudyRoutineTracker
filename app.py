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

import database
get_fresh_cursor = database.get_fresh_cursor
reconnect = database.reconnect
save_esu_response = database.save_esu_response
get_esu_responses = database.get_esu_responses
delete_esu_response = database.delete_esu_response
ensure_connection = database.ensure_connection
get_ist_now = database.get_ist_now



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
import logic
from logic import *

# Initialize or ensure connection at startup
database.ensure_connection()
conn = database.conn
c = database.c
from streamlit_calendar import calendar


from utils import read_sql, get_user_subjects, get_user_defaults, get_all_songs, get_song_url, clean_song_name, get_song_lists

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
get_user_config = database.get_user_config
update_user_config = database.update_user_config
get_allowed_recipients = database.get_allowed_recipients
set_allowed_recipients = database.set_allowed_recipients
USER_CONFIG = get_user_config(USER)

# --- GLOBAL SIDEBAR MUSIC PLAYER ---

# We need to defer the actual rendering until after the menu is selected,
# but we initialise music state now so it persists across pages.
import os
import re
import random as _rand
supabase_client = database.supabase_client
STORAGE_BUCKET = database.STORAGE_BUCKET



# Initial load
all_mp3s, song_options_dict, song_names_list = get_song_lists()

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

# --- AUTO-NEXT DETECTION: Check if JS triggered a song advance via query param ---
_qp = st.query_params
if _qp.get("_auto_next"):
    # Clear the query param immediately
    del _qp["_auto_next"]
    # Advance to next song
    if song_names_list:
        if st.session_state.music_autoswitch:
            st.session_state.music_playing = True
            if st.session_state.music_shuffle:
                _new_idx = _rand.randint(0, len(song_names_list) - 1)
                if len(song_names_list) > 1 and _new_idx == st.session_state.music_idx:
                    _new_idx = (_new_idx + 1) % len(song_names_list)
                st.session_state.music_idx = _new_idx
            else:
                st.session_state.music_idx = (st.session_state.music_idx + 1) % len(song_names_list)
            st.rerun()

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
            let targetWin = window;
            try { if (window.parent && window.parent.document) targetWin = window.parent; } catch(e) {}
            if (targetWin._musicAutoSwitchInterval) {
                clearInterval(targetWin._musicAutoSwitchInterval);
            }
            targetWin._musicAutoSwitchInterval = setInterval(() => {
                try {
                    let audios = [];
                    try { audios = Array.from(targetWin.document.querySelectorAll('audio')); } catch(e) {}
                    try {
                        let frames = targetWin.document.querySelectorAll('iframe');
                        for (let i = 0; i < frames.length; i++) {
                            try { audios = audios.concat(Array.from(frames[i].contentWindow.document.querySelectorAll('audio'))); } catch(e) {}
                        }
                    } catch(e) {}
                    
                    for (let a of audios) {
                        const isDone = a.ended || (a.duration > 0 && a.currentTime >= a.duration - 0.3);
                        if (isDone && a.dataset.autoSwitchTriggered !== "1") {
                            a.dataset.autoSwitchTriggered = "1";
                            
                            // Try clicking the Next button (cleanest approach)
                            let b = Array.from(targetWin.document.querySelectorAll('button')).find(btn => 
                                btn.title === 'Next Song' || btn.title === 'Next' || 
                                (btn.getAttribute('aria-label') && (btn.getAttribute('aria-label') === 'Next Song' || btn.getAttribute('aria-label') === 'Next'))
                            );
                            if (b) {
                                b.click();
                            } else {
                                // Fallback: Navigate with query param to trigger Streamlit rerun
                                const url = new URL(targetWin.location.href);
                                url.searchParams.set('_auto_next', '1');
                                targetWin.location.href = url.toString();
                            }
                            return; // Stop processing
                        }
                        // Reset trigger when not near end
                        if (a.duration > 0 && a.currentTime < a.duration - 2) {
                            a.dataset.autoSwitchTriggered = "";
                        }
                    }
                } catch(e) {}
            }, 800);
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


# =============== DYNAMIC ROUTING ===============
if menu == "Daily Entry":
    from views.daily_entry import render
    render(USER, USER_CONFIG)
elif menu == "Calendar":
    from views.calendar_main import render
    render(USER, USER_CONFIG)
elif menu == "Social Life":
    from views.social_life import render
    render(USER, USER_CONFIG)
elif menu == "Study Calendar":
    from views.study_calendar import render
    render(USER, USER_CONFIG)
elif menu == "Set Target":
    from views.set_target import render
    render(USER, USER_CONFIG)
elif menu == "Study Target Manager":
    from views.target_manager import render
    render(USER, USER_CONFIG)
elif menu == "Productivity Analysis":
    from views.analysis import render
    render(USER, USER_CONFIG)
elif menu == "Ask Esu":
    from views.ask_esu import render
    render(USER, USER_CONFIG)
elif menu == "Expenses":
    from views.expenses import render
    render(USER, USER_CONFIG)
elif menu == "Manage Users":
    from views.manage_users import render
    render(USER, USER_CONFIG)
elif menu == "MyLove Special":
    from views.mylove_special import render
    render(USER, USER_CONFIG)
elif menu == "Notifications":
    from views.notifications import render
    render(USER, USER_CONFIG)
elif menu == "Media Player":
    from views.media_player import render
    render(USER, USER_CONFIG)
elif menu == "Love Management":
    from views.love_management import render
    render(USER, USER_CONFIG)
elif menu == "Chat":
    from views.chat import render
    render(USER, USER_CONFIG)

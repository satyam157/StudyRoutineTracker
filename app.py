import mimetypes
mimetypes.init()
mimetypes.types_map['.js'] = 'application/javascript'
mimetypes.types_map['.css'] = 'text/css'

import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
import plotly.express as px
import datetime
from datetime import timedelta, date


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

    /* --- Media Player main page card (class-scoped, safe) --- */
    .media-player-card {
        background: linear-gradient(160deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)


# Sidebar Header: User Emoji, Username and Logout button below
import database
from database import get_fresh_cursor, reconnect, save_esu_response, get_esu_responses, delete_esu_response, ensure_connection
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
    "Daily Entry","Calendar","Set Target","Study Target Manager","Productivity Analysis","Ask Esu","Expenses"
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

all_mp3s = [f for f in os.listdir(".") if f.lower().endswith(".mp3")]

def clean_song_name(filename):
    name = filename.replace(".mp3", "")
    name = re.sub(r' \d+ [Kk]bps| Youngistaan', '', name)
    name = name.replace("_", " ").replace("-", " ")
    name = " ".join(name.split()).title()
    icons = {"Perfect": "💍", "Tum Se Hi": "✨", "Phir Bhi": "💖", "Suno Na": "🎵", "Ishq": "🔥", "Rang": "🎨", "Waalian": "🎧"}
    for key, icon in icons.items():
        if key.lower() in name.lower():
            return f"{name} {icon}"
    return f"{name} 🎵"

if "Perfect.mp3" in all_mp3s:
    all_mp3s.remove("Perfect.mp3")
    all_mp3s.sort()
    all_mp3s.insert(0, "Perfect.mp3")
else:
    all_mp3s.sort()

song_options_dict = {clean_song_name(f): f for f in all_mp3s} if all_mp3s else {}
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
        st.sidebar.info("No .mp3 files found in root directory.")
        st.sidebar.divider()
        return

    st.sidebar.markdown('<div id="sidebar-music-marker"></div>', unsafe_allow_html=True)

    st.sidebar.markdown("""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                    padding: 12px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 15px;">
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

    # The detailed song list and selector have been removed from the sidebar.
    # Users will select songs from the Media Player page instead.
    
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
    st.sidebar.audio(current_song_path, format="audio/mp3", autoplay=should_autoplay)

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
        setInterval(() => {
            try {
                const audioTags = window.parent.document.querySelectorAll('audio');
                if (audioTags.length > 0) {
                    const sidebarAudio = window.parent.document.querySelector('[data-testid="stSidebar"] audio');
                    let audio = sidebarAudio || audioTags[audioTags.length - 1];
                    if (audio && !audio.dataset.autoswitchAttached) {
                        audio.dataset.autoswitchAttached = "true";
                        audio.addEventListener('ended', function() {
                            const buttons = window.parent.document.querySelectorAll('button');
                            for (let btn of buttons) {
                                if (btn.innerText.includes('⏭️')) {
                                    btn.click();
                                    break;
                                }
                            }
                        });
                    }
                }
            } catch(e) {}
        }, 1000);
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
        for n_id, msg, ts, sender in notifs:
            if f"toasted_{n_id}" not in st.session_state:
                st.toast(f"New Message: {msg}", icon="💖")
                st.session_state[f"toasted_{n_id}"] = True
            st.sidebar.markdown(f"""
                <div style="background-color: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; padding: 10px; border-radius: 12px; margin-bottom: 5px;">
                    <p style="font-size: 0.85rem; margin: 0;"><b>{sender}:</b> {msg[:30]}...</p>
                </div>
            """, unsafe_allow_html=True)

if USER == "admin":
    menu_options.append("Manage Users")
    menu_options.append("Love Management")

if USER_CONFIG.get("can_access_music") or USER == "admin":
    menu_options.append("Media Player")

menu_options.append("Chat")

if USER_CONFIG.get("can_view_mylove_special"):
    menu_options.append("MyLove Special")

menu = st.sidebar.radio("Menu", menu_options)

# Handle "Media Player" jump from sidebar music player button
if st.session_state.get("_jump_to_media_player"):
    st.session_state["_jump_to_media_player"] = False
    menu = "Media Player"

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
    tab_notes, tab_send, tab_alerts = st.tabs(["📥 Personal Notes", "🚀 Send a Note", "🔔 System Alerts"])
    
    import proposal
    with tab_notes:
        proposal.show_admin_notifications(USER, mode='personal')
        
    with tab_alerts:
        proposal.show_admin_notifications(USER, mode='system')
        
    with tab_send:
        if USER_CONFIG.get("can_send_love_messages") or USER == 'admin':
            st.markdown("### 💝 Love Express")
            st.write("Send a romantic note or a quick surprise!")
            
            if USER == 'admin':
                if st.button("❤️ Quick 'I Love You' to Her"):
                    proposal.send_love_notification("admin", "I love you too, my princess! 💖🌹", "foryou")
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
        users_df = read_sql("SELECT u.username, c.can_view_mylove_special, c.can_send_love_messages, c.can_receive_love_messages, c.can_receive_love_notifications, c.can_delete_messages, c.can_delete_system_alerts, c.can_access_music, c.music_pages, c.mylove_default_song FROM users u LEFT JOIN user_config c ON u.username = c.username WHERE u.username != 'admin'")
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
                    _mp3_files = [f for f in os.listdir(".") if f.lower().endswith(".mp3")]
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
                    success = update_user_config(row['username'], v1, v2, v3, v4, v5, v6, v7, v8, v9)
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
            st.audio(_current_mp_path, format="audio/mp3", autoplay=st.session_state.music_playing)

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
                            background: #111827; padding: 8px; border-radius: 8px; border: 1px solid #374151;">
                    <span style="color: #9ca3af; font-size: 0.8rem;">Playback:</span>
                    <span style="color: #38bdf8; font-size: 0.9rem; font-weight: 600;">{_mode_txt}</span>
                </div>
            """, unsafe_allow_html=True)

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

        # Autoswitch JS for the Media Player page
        if st.session_state.music_autoswitch:
            st.html("""
            <script>
            setInterval(() => {
                try {
                    const audioTags = window.parent.document.querySelectorAll('audio');
                    if (audioTags.length > 0) {
                        let audio = audioTags[0];
                        if (audio && !audio.dataset.autoswitchAttached) {
                            audio.dataset.autoswitchAttached = "true";
                            audio.addEventListener('ended', function() {
                                const buttons = window.parent.document.querySelectorAll('button');
                                for (let btn of buttons) {
                                    if (btn.innerText.includes('⏭️')) {
                                        btn.click();
                                        break;
                                    }
                                }
                            });
                        }
                    }
                } catch(e) {}
            }, 1000);
            </script>
            """, unsafe_allow_javascript=True)
    else:
        st.info("No .mp3 files found in the project directory.")

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
        
        if st.button("⬇️ Download as MP3", type="primary", width='stretch'):
            if yt_url.strip():
                import subprocess
                import shutil
                
                # Check if yt-dlp is available
                if not shutil.which("yt-dlp"):
                    st.warning("⏳ Installing yt-dlp... this may take a moment.")
                    try:
                        subprocess.run(["pip", "install", "yt-dlp"], check=True, capture_output=True)
                        st.success("✅ yt-dlp installed!")
                    except Exception as e:
                        st.error(f"Failed to install yt-dlp: {e}")
                        st.stop()
                
                with st.spinner("🎵 Downloading and converting to MP3..."):
                    try:
                        output_template = f"{custom_name.strip()}.%(ext)s" if custom_name.strip() else "%(title)s.%(ext)s"
                        
                        cmd = [
                            "yt-dlp",
                            "-x",
                            "--audio-format", "mp3",
                            "--audio-quality", "192K",
                            "-o", output_template,
                            "--no-playlist",
                            "--restrict-filenames" if not custom_name.strip() else "--no-restrict-filenames",
                            yt_url.strip()
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        if result.returncode == 0:
                            # Find the newly downloaded file
                            import glob
                            new_mp3s = set(glob.glob("*.mp3")) - set(all_mp3s)
                            if new_mp3s:
                                new_file = list(new_mp3s)[0]
                                st.success(f"✅ Downloaded: **{new_file}**")
                                st.balloons()
                                st.info("🔄 Refresh the page to see it in the music player.")
                            else:
                                st.success("✅ Download complete! Refresh to see the new song.")
                        else:
                            st.error(f"Download failed:\n```\n{result.stderr[-500:]}\n```")
                    except subprocess.TimeoutExpired:
                        st.error("⏱️ Download timed out (5 min limit). Try a shorter video.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter a YouTube URL.")
    
    with tab_upload:
        st.markdown("### 📤 Upload an MP3 file directly")
        uploaded_file = st.file_uploader("Choose an MP3 file", type=["mp3"])
        if uploaded_file is not None:
            save_name = st.text_input("Save as (filename)", value=uploaded_file.name, key="upload_save_name")
            if not save_name.endswith(".mp3"):
                save_name += ".mp3"
            if st.button("💾 Save Song", key="save_upload_btn"):
                with open(save_name, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"✅ Saved as **{save_name}**")
                st.balloons()
                import time; time.sleep(1)
                st.rerun()
    
    with tab_manage:
        st.markdown("### 📋 Current Song Library")
        current_mp3s = [f for f in os.listdir(".") if f.lower().endswith(".mp3")]
        if not current_mp3s:
            st.info("No songs found.")
        else:
            st.caption(f"**{len(current_mp3s)}** songs in library")
            for mp3 in sorted(current_mp3s):
                file_size_mb = os.path.getsize(mp3) / (1024 * 1024)
                mc1, mc2, mc3 = st.columns([3, 1, 1])
                mc1.markdown(f"🎵 **{clean_song_name(mp3)}**")
                mc2.caption(f"{file_size_mb:.1f} MB")
                if mc3.button("🗑️", key=f"del_song_{mp3}", help=f"Delete {mp3}"):
                    st.session_state[f"confirm_del_song_{mp3}"] = True
                
                if st.session_state.get(f"confirm_del_song_{mp3}", False):
                    st.warning(f"⚠️ Delete **{mp3}**? This cannot be undone.")
                    yc, nc = st.columns(2)
                    if yc.button("✅ Yes, Delete", key=f"yes_del_song_{mp3}"):
                        try:
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

    base_activities = [
        "Study", "Revision", "Book Reading", "Answer Writing", "Practice", "Test",
        "Entertainment", "Social Media", "Food", "Transport",
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

    # Activity selection with inline delete for custom activities and base activities
    _act_col, _del_col = st.columns([3, 1])
    with _act_col:
        activity = st.selectbox("Activity", base_activities + custom + ["+ Add New"])
    
    # Show delete button for custom and base activities (lets user delete instance from dropdown)
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
            # Show info that this is a base activity that cannot be deleted
            st.caption("Base activity", help="Base activities cannot be deleted")

    if activity == "+ Add New":
        new_act_col1, new_act_col2, new_act_col3 = st.columns([2, 1, 1])
        with new_act_col1:
            new = st.text_input("New Activity Name")
        with new_act_col2:
            new_act_type = st.selectbox("Activity Type", ["Productive", "Essential", "Waste"], index=2,
                                        help="Productive = Study/Work | Essential = Must-do | Waste = Time sink")
        with new_act_col3:
            new_track_type = st.selectbox("Track by", ["Hours", "Expense (₹)"])
        if st.button("Save Activity"):
            if new.strip():
                c.execute("INSERT INTO custom_boxes(name, username, activity_type, tracking_type) VALUES(%s, %s, %s, %s)", (new.strip(), USER, new_act_type, new_track_type))
                conn.commit()
                st.toast(f"✅ Activity '{new.strip()}' added as **{new_act_type}** tracked in **{new_track_type}**!", icon="✅")
                import time; time.sleep(1)
                st.rerun()
            else:
                st.warning("Please enter an activity name.")

    sub1 = sub2 = ""
    _study_track = "Hours"  # Initialize default for Study activity

    # ── Subject-managed activities (Study, Revision, Answer Writing, Practice) ──
    if activity in _SUBJ_ACTS:
        _user_subjs = get_user_subjects(USER)
        
        # Subject selection with inline add/delete in same row (compact layout)
        _subj_col, _subj_del_col = st.columns([3, 1])
        with _subj_col:
            sub1 = st.selectbox("Subject", _user_subjs + ["+ Add New"], key="de_subject_sel")
        
        # Handle subject delete action (keep in same row with bin emoji)
        with _subj_del_col:
            if sub1 in _user_subjs:
                if st.button("🗑️", key=f"del_subj_{sub1}", help="Delete Subject"):
                    st.session_state[f"confirm_del_subj_{sub1}"] = True
            
            if sub1 in _user_subjs and st.session_state.get(f"confirm_del_subj_{sub1}", False):
                st.markdown(f"⚠️ Delete **{sub1}**?", unsafe_allow_html=True)
                _yc, _nc = st.columns([1, 1])
                with _yc:
                    if st.button("✅ Yes", key=f"yes_del_subj_{sub1}", width='stretch'):
                        c.execute(
                            "DELETE FROM user_subjects WHERE username=%s AND subject=%s",
                            (USER, sub1)
                        )
                        conn.commit()
                        st.session_state[f"confirm_del_subj_{sub1}"] = False
                        st.toast(f"🗑️ Subject '{sub1}' deleted.", icon="🗑️")
                        st.rerun()
                with _nc:
                    if st.button("❌ No", key=f"no_del_subj_{sub1}", width='stretch'):
                        st.session_state[f"confirm_del_subj_{sub1}"] = False
                        st.rerun()
        
        # Handle adding new subject
        if sub1 == "+ Add New":
            _new_subj_col, _ = st.columns([3, 1])
            with _new_subj_col:
                _new_subj = st.text_input("Subject Name", key="de_new_subj", placeholder="e.g. Science & Tech")
                if st.button("➕ Add Subject", key="de_add_subj_btn"):
                    _ns = _new_subj.strip()
                    if _ns:
                        try:
                            c.execute(
                                "INSERT INTO user_subjects (username, subject) VALUES (%s, %s) "
                                "ON CONFLICT (username, subject) DO NOTHING",
                                (USER, _ns)
                            )
                            conn.commit()
                            st.toast(f"✅ Subject '{_ns}' added to your list!", icon="✅")
                            import time; time.sleep(1)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error: {_e}")
                    else:
                        st.warning("Enter a subject name.")

    # ── Activity-specific sub-fields ──
    if activity == "Study":
        sub2 = st.text_input("Chapter / Topic", max_chars=50, placeholder="Enter chapter/topic...")

    elif activity == "Revision":
        sub2 = st.text_input("Chapter/Pages Revised", key="de_rev_ch", placeholder="e.g., Chapter 5 or Pages 23-45")

    elif activity == "Book Reading":
        sub1 = st.text_input("Book Title / Name", key="de_book_title")
        sub2 = st.text_input("Chapters/Pages Read", key="de_book_detail", placeholder="e.g., 3 chapters or pages 50-80")

    elif activity in ["Answer Writing", "Practice"]:
        _q_solved = st.number_input("No. of Questions Solved", min_value=0, step=1, key=f"de_q_{activity}")
        sub2 = f"Q:{int(_q_solved)}" if _q_solved > 0 else ""

    elif activity == "Test":
        sub1 = st.selectbox("Test Type", test_types)
        sub2 = st.text_input("#Questions")

    elif activity == "Entertainment":
        sub1 = st.selectbox("Type", ent_types)
        if sub1 == "Movie":
            sub2 = st.selectbox("Mode", movie_modes)

    elif activity == "Social Media":
        sub1 = st.selectbox("Platform", social_platform)
        sub2 = st.selectbox("Content", content_type)

    elif activity == "Food":
        sub1 = st.selectbox("Source", food_sources)

    elif activity == "Transport":
        sub1 = st.selectbox("Service", transport_services)

    elif activity == "WentOutside":
        sub1 = st.text_input("Location / Place", key="de_went_outside", placeholder="e.g., Park, Mall, Beach")

    elif activity == "Turf":
        sub1 = st.text_input("Sport / Activity", key="de_turf_sport", placeholder="e.g., Cricket, Football, Badminton")
        sub2 = st.text_input("Details", key="de_turf_detail", placeholder="e.g., Indoor/Outdoor, with friends")

    elif activity == "Travelling":
        sub1 = st.selectbox("Mode", ["✈️ Flight", "🚂 Railway", "🚗 Other"], key="de_travel_mode")
        sub2 = st.text_input("Destination / Details", key="de_travel_dest", placeholder="e.g., Delhi to Mumbai")

    # Auto-determine tracking type based on activity type
    # Activities that track both hours and expense
    _track_both = activity in ["Food", "Transport", "WentOutside", "Turf", "Travelling"]
    _track_by_expense = activity in ["Food", "Transport"]
    
    if activity in custom:
        _track_by_expense = custom_track_map.get(activity, "Hours") == "Expense (₹)"
        _track_both = False
    
    # Duration input mode selection (Hours vs Time Range)
    _duration_mode = st.radio("⏱️ Duration Input", ["Hours", "Time Range (From-To)"], index=1, horizontal=True, key=f"de_dur_mode_{activity}")
    
    duration = 0.0
    amount = 0.0
    start_time = ""  # Capture start time for time-of-day analysis
    is_midnight_crossing = False  # Track if activity spans midnight
    duration_today = 0.0
    duration_tomorrow = 0.0
    from_h = from_m = to_h = to_m = 0  # Track parsed times for midnight crossing
    
    def parse_time_value(raw):
        """Parse time input (e.g., '2:30 PM' or '14') into hours value"""
        raw = str(raw).strip()
        if not raw:
            return None
        try:
            if ":" in raw:
                h, m = raw.split(":", 1)
                h, m = int(h), int(m)
            else:
                h, m = int(raw), 0
            return h, m
        except:
            return None
    
    # Calculate duration based on selected mode
    if _duration_mode == "Hours":
        if _track_both:
            # For activities that track both hours and expense
            _trade_col1, _trade_col2 = st.columns(2)
            with _trade_col1:
                _dur_input = st.number_input("⏱️ Hours", min_value=0.0, step=0.5, value=None, key=f"de_hours_{activity}")
                duration = _dur_input if _dur_input is not None else 0.0
            with _trade_col2:
                _amt_input = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=None, key=f"de_amount_{activity}")
                amount = _amt_input if _amt_input is not None else 0.0
        elif _track_by_expense:
            _amt_input = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=None)
            amount   = _amt_input if _amt_input is not None else 0.0
            duration = 0.0
        else:
            _dur_input = st.number_input("⏱️ Hours", min_value=0.0, step=0.5, value=None)
            duration = _dur_input if _dur_input is not None else 0.0
            amount   = 0.0
    else:
        # Time Range Mode
        _time_col1, _time_col2 = st.columns(2)
        
        with _time_col1:
            from_time_raw = st.text_input("From Time (e.g., 2:30 or 14)", key=f"de_from_time_{activity}", placeholder="2:30 PM")
        with _time_col2:
            to_time_raw = st.text_input("To Time (e.g., 4:45 or 16)", key=f"de_to_time_{activity}", placeholder="4:45 PM")
        
        # Parse and calculate duration
        if from_time_raw and to_time_raw:
            from_parsed = parse_time_value(from_time_raw)
            to_parsed = parse_time_value(to_time_raw)
            
            if from_parsed and to_parsed:
                from_h, from_m = from_parsed
                to_h, to_m = to_parsed
                
                # Store start time for analysis
                start_time = f"{from_h}:{from_m:02d}"
                
                # Convert to minutes for calculation
                from_mins = from_h * 60 + from_m
                to_mins = to_h * 60 + to_m
                
                # Check if activity crosses midnight
                if to_mins < from_mins:
                    is_midnight_crossing = True
                    # Duration today: from from_time to 23:59:59 (1440 minutes = midnight)
                    duration_today = (24 * 60 - from_mins) / 60
                    # Duration tomorrow: from 00:00 to to_time
                    duration_tomorrow = to_mins / 60
                    duration = duration_today + duration_tomorrow
                else:
                    # Normal case: same day
                    duration = (to_mins - from_mins) / 60
                
                st.caption(f"Duration: **{duration:.1f} hours**" + (" (spans midnight ⏰)" if is_midnight_crossing else ""))
            else:
                st.error("Invalid time format. Use format like '2:30' or '14'")
                duration = 0.0
        
        if _track_both:
            _amt_tr = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=None, key=f"de_amount_tr_{activity}")
            amount = _amt_tr if _amt_tr is not None else 0.0

    if st.button("💾 Save Activity", key="save_main_activity"):
        if duration > 0 or amount > 0 or _track_by_expense is False:
            time_note = f" [{start_time}]" if start_time else ""
            
            if is_midnight_crossing:
                # Split activity across midnight
                # Save today's portion (from from_time to 23:59:59)
                st_today = f"{from_h}:{from_m:02d}"
                c.execute("""
                INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (str(date), activity, sub1, sub2, duration_today, amount, USER, st_today))
                
                # Save tomorrow's portion (from 00:00 to to_time)
                tomorrow_date = date + timedelta(days=1)
                st_tomorrow = f"{to_h}:{to_m:02d}"
                c.execute("""
                INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (str(tomorrow_date), activity, sub1, sub2, duration_tomorrow, 0, USER, st_tomorrow))
                
                conn.commit()
                st.toast(f"✅ Activity split across midnight!\n📅 {date.strftime('%b %d')}: {duration_today:.1f}h\n📅 {tomorrow_date.strftime('%b %d')}: {duration_tomorrow:.1f}h", icon="✅")
            else:
                # Normal case: save as single record
                c.execute("""
                INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (str(date), activity, sub1, sub2, duration, amount, USER, start_time))
                conn.commit()
                st.toast(f"✅ Activity '{activity}' saved successfully!", icon="✅")
            
            # Synchronize Powernap with health_logs for reporting
            if activity.strip().lower() == "powernap":
                try:
                    if is_midnight_crossing:
                        # Update today's portion
                        c.execute("""
                            INSERT INTO health_logs (username, date, powernap) VALUES (%s, %s, %s)
                            ON CONFLICT (username, date) DO UPDATE SET powernap = COALESCE(health_logs.powernap, 0) + EXCLUDED.powernap
                        """, (USER, str(date), duration_today))
                        # Update tomorrow's portion
                        c.execute("""
                            INSERT INTO health_logs (username, date, powernap) VALUES (%s, %s, %s)
                            ON CONFLICT (username, date) DO UPDATE SET powernap = COALESCE(health_logs.powernap, 0) + EXCLUDED.powernap
                        """, (USER, str(tomorrow_date), duration_tomorrow))
                    else:
                        c.execute("""
                            INSERT INTO health_logs (username, date, powernap) VALUES (%s, %s, %s)
                            ON CONFLICT (username, date) DO UPDATE SET powernap = COALESCE(health_logs.powernap, 0) + EXCLUDED.powernap
                        """, (USER, str(date), duration))
                    conn.commit()
                except Exception as e:
                    st.error(f"Error syncing powernap to health logs: {e}")
            
            import time; time.sleep(1)
            st.rerun()
        else:
            st.warning("Please enter duration or amount.")

    st.divider()

    # ═══════════════════════════════════════════════════════════
    # SECTION: Today's Activity Log (with delete)
    # ═══════════════════════════════════════════════════════════
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1.5px solid #4f46e5;
        border-radius: 14px;
        padding: 18px 20px 10px 20px;
        margin-bottom: 18px;
    ">
    <div style="font-size:17px; font-weight:700; color:#a78bfa; margin-bottom:10px;">
        📋 Activities Logged on Selected Date
    </div>
    </div>
    """, unsafe_allow_html=True)

    _today_df = read_sql(
        "SELECT id, type, subject, chapter, duration, amount, start_time FROM activities WHERE date=%s AND username=%s ORDER BY id",
        (str(date), USER)
    )

    if _today_df.empty:
        st.caption("No activities logged for this date yet.")
    else:
        for _, _row in _today_df.iterrows():
            _rid = int(_row['id'])
            _parts = [_row['type']]
            if _row['subject']: _parts.append(str(_row['subject']))
            
            # Clean display
            ch_clean = get_clean_chapter(_row['chapter'])
            st_val = _row.get('start_time')
            if not st_val: # Fallback for old entries
                hr = extract_time_of_day(_row['chapter'])
                if hr is not None: st_val = f"{hr}:00"
            
            if ch_clean: _parts.append(ch_clean)
            if st_val: _parts.append(f"[{st_val}]")
            
            _val = f"{_row['duration']}h" if _row['duration'] > 0 else (f"₹{_row['amount']}" if _row['amount'] > 0 else "")
            if _val: _parts.append(_val)
            _lc, _rc = st.columns([5, 1])
            with _lc:
                st.markdown(f"&nbsp;&nbsp;• **{'  |  '.join(_parts)}**", unsafe_allow_html=True)
            with _rc:
                if st.button("🗑️", key=f"del_daily_{_rid}", help="Delete this entry"):
                    st.session_state[f"confirm_daily_{_rid}"] = True
            if st.session_state.get(f"confirm_daily_{_rid}", False):
                st.warning(f"Delete **{_row['type']}** entry? This cannot be undone.")
                _yc, _nc = st.columns(2)
                with _yc:
                    if st.button("✅ Yes, Delete", key=f"yes_daily_{_rid}"):
                        # Synchronize Powernap deletion with health_logs
                        if _row['type'].strip().lower() == "powernap":
                            c.execute("UPDATE health_logs SET powernap = GREATEST(0, powernap - %s) WHERE username=%s AND date=%s", (_row['duration'], USER, str(date)))
                        
                        c.execute("DELETE FROM activities WHERE id=%s AND username=%s", (_rid, USER))
                        conn.commit()
                        st.session_state[f"confirm_daily_{_rid}"] = False
                        st.toast("🗑️ Entry deleted.", icon="🗑️")
                        st.rerun()
                with _nc:
                    if st.button("❌ No, Keep", key=f"no_daily_{_rid}"):
                        st.session_state[f"confirm_daily_{_rid}"] = False
                        st.rerun()

    st.divider()

    # ═══════════════════════════════════════════════════════════
    # SECTION: Sleep & Wake Log
    # ═══════════════════════════════════════════════════════════
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%);
        border: 1.5px solid #2563eb;
        border-radius: 14px;
        padding: 18px 20px 10px 20px;
        margin-bottom: 18px;
    ">
    <div style="font-size:17px; font-weight:700; color:#60a5fa; margin-bottom:10px;">
        🌙 Sleep &amp; Wake Log
    </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        sw_col1, sw_col2 = st.columns([1, 1])

        def parse_time(raw, always_am=False):
            """Parse '6', '6:30', '11' etc. into 'HH:MM AM/PM'."""
            raw = str(raw).strip()
            if not raw:
                return None, None
            try:
                if ":" in raw:
                    h, m = raw.split(":", 1)
                    h, m = int(h), int(m)
                else:
                    h, m = int(raw), 0
                period = "AM" if always_am else ("PM" if 7 <= h <= 11 else "AM")
                return f"{h}:{m:02d} {period}", None
            except Exception:
                return None, "Invalid format — use a number like 6 or 6:30"

        with sw_col1:
            wu_raw = st.text_input("⏰ Wakeup", key="wu_raw", placeholder="6:00")
            wu_fmt, wu_err = parse_time(wu_raw, always_am=True)
            if wu_raw:
                if wu_err: st.error(wu_err)
                else:       st.caption(f"→ **{wu_fmt}** AM")

        with sw_col2:
            sl_raw = st.text_input("😴 Sleep", key="sl_raw", placeholder="11:00")
            sl_fmt, sl_err = parse_time(sl_raw, always_am=False)
            if sl_raw:
                if sl_err: st.error(sl_err)
                else:       st.caption(f"→ **{sl_fmt}**")
        


        if st.button("💾 Save Sleep & Wake Log", key="save_health"):
            if wu_fmt or sl_fmt:
                c.execute("""
                    INSERT INTO health_logs (username, date, wakeup_time, sleep_time)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username, date) DO UPDATE SET 
                        wakeup_time=EXCLUDED.wakeup_time, 
                        sleep_time=EXCLUDED.sleep_time
                """, (USER, str(date), wu_fmt or "", sl_fmt or ""))
                conn.commit()
                st.toast(f"✅ Log saved for {date}!", icon="✅")
                st.rerun()
            else:
                st.warning("Enter at least one value.")

# ---------------- CALENDAR ----------------
elif menu == "Calendar":
    st.title("📆 Calendars")
    
    cal_tab_month, cal_tab_year = st.tabs(["📅 Month Calendar", "📊 Year Calendar"])
    
    with cal_tab_month:
        import calendar as calmod
        import datetime
        
        today = datetime.date.today()
        
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

# ---------------- SET TARGET ----------------
elif menu == "Set Target":
    st.title("📚 Set Target")

    import datetime as _sm_dt
    GOAL_TYPES = ["Chapters", "Pages", "Questions Solved", "Topics / Units", "Problems", "Pomodoros", "Hours", "Custom"]

    st.markdown("### ➕ Set a New Target")
    with st.form("new_target_form"):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            subj_choice = st.selectbox("Subject / Topic", study_subjects + ["➕ Custom Subject"])
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
            today = pd.Timestamp.today().date()
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
                    .sort_values(['Chapter / Topic', 'Date'])
                )
                return summary, detail
            elif goal_unit == _HOURS_TYPE:
                daily = (
                    sub_acts.groupby('_date')['duration'].sum().reset_index()
                    .rename(columns={'_date': 'Date', 'duration': 'Hours'})
                    .sort_values('Date')
                )
                daily['Cumulative Hours'] = daily['Hours'].cumsum().round(2)
                return daily, None
            elif goal_unit in _CUMUL_TYPES:
                col = 'Pages' if goal_unit == 'Pages' else 'Questions'
                rows = [{'Date': r['_date'], col: parse_numeric(r['chapter']), 'Activity': r['type']}
                        for _, r in sub_acts.iterrows() if parse_numeric(r['chapter']) is not None]
                if not rows:
                    return None, None
                daily = pd.DataFrame(rows).groupby('Date')[col].sum().reset_index().sort_values('Date')
                daily[f'Cumulative {col}'] = daily[col].cumsum()
                return daily, None
            else:
                tbl = (
                    sub_acts.groupby(['chapter', '_date'], as_index=False)['duration'].sum()
                    .rename(columns={'chapter': 'Chapter / Item', '_date': 'Date', 'duration': 'Hours'})
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
                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                mc1.metric("Goal",     f"{total} {goal_unit}")
                mc2.metric("Done",     f"{label} {goal_unit}")
                mc3.metric("Progress", f"{percent}%")
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
        st.subheader("📉 Weak Subjects (Least Studied)")
        study_acts = act_df[act_df['type'] == 'Study']
        if study_acts.empty:
            st.info("No study entries yet.")
        else:
            subj_hours = study_acts.groupby('subject')['duration'].sum().sort_values()
            
            # Summary Metrics
            st.markdown("### 📊 Study Hours by Subject")
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
                st.metric("⏱️ Total Study Hours", f"{total_study_hours:.1f}h")
            with analysis_cols[2]:
                avg_hours = total_study_hours / num_subjects if num_subjects > 0 else 0
                st.metric("📊 Average per Subject", f"{avg_hours:.1f}h")
            
            # Weak vs Strong comparison
            st.markdown("### 🔍 Subject Performance Breakdown")
            
            # Initialize variables
            weakest_subject = subj_hours.index[0] if num_subjects >= 1 else None
            weakest_hours = subj_hours.iloc[0] if num_subjects >= 1 else 0
            strongest_subject = subj_hours.index[-1] if num_subjects >= 1 else None
            strongest_hours = subj_hours.iloc[-1] if num_subjects >= 1 else 0
            
            if num_subjects >= 2:
                comp_col1, comp_col2 = st.columns(2)
                
                with comp_col1:
                    st.error(f"""
                    ⚠️ **Weakest Subject**: {weakest_subject}
                    
                    Hours Logged: {weakest_hours:.1f}h
                    
                    This subject needs more attention and focused study sessions.
                    """)
                
                with comp_col2:
                    st.success(f"""
                    ✅ **Strongest Subject**: {strongest_subject}
                    
                    Hours Logged: {strongest_hours:.1f}h
                    
                    Maintain or increase effort to consolidate your knowledge.
                    """)
            
            # Subject Distribution Analysis
            st.markdown("### 📈 Study Distribution Analysis")
            
            weak_subjects = subj_hours[subj_hours < subj_hours.mean()].index.tolist()
            strong_subjects = subj_hours[subj_hours >= subj_hours.mean()].index.tolist()
            
            dist_col1, dist_col2 = st.columns(2)
            
            with dist_col1:
                st.info(f"""
                📍 **Below Average Subjects** ({len(weak_subjects)})
                
                {', '.join(weak_subjects[:3]) if weak_subjects else 'None'}
                {f'and {len(weak_subjects)-3} more...' if len(weak_subjects) > 3 else ''}
                """)
            
            with dist_col2:
                st.info(f"""
                ✨ **Above Average Subjects** ({len(strong_subjects)})
                
                {', '.join(strong_subjects[:3]) if strong_subjects else 'None'}
                {f'and {len(strong_subjects)-3} more...' if len(strong_subjects) > 3 else ''}
                """)


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

        if df.empty:
            st.info("No activity data found.")
        else:
            # Load sleep data for daily report
            try:
                hl_df = read_sql(
                    "SELECT date, sleep_time, wakeup_time, powernap FROM health_logs WHERE username=%s ORDER BY date ASC",
                    (USER,)
                )
                sleep_hours_dict = {}
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
            except:
                sleep_hours_dict = {}
                powernap_dict = {}
            
            prod_df     = df[df['type'].isin(ALL_PRODUCTIVE)]
            essential_df= df[df['type'].isin(ALL_ESSENTIAL)]
            waste_df    = df[~df['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL)]

            # Metrics row
            m1, m2, m3 = st.columns(3)
            m1.metric("Productivity %", f"{productivity_score(df, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict)}%")
            m2.metric("Study Streak",   f"{streak(df)} days")
            m3.metric("Focus Score",    f"{focus_score(df)}%")

            st.divider()

            # ── PRODUCTIVITY ANALYSIS ────────────────────────────────────
            st.markdown("### 📈 Productivity Analysis")

            # TABLE FIRST
            report_df = daily_report(df, sleep_data=sleep_hours_dict, powernap_data=powernap_dict)
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

            bar_df = pd.DataFrame({
                'Type': ['Productive', 'Essential', 'Waste'],
                'Hours': [prod_total, essential_total, waste_total]
            })
            col_bar, col_pie = st.columns(2)
            with col_bar:
                fig_bar = px.bar(bar_df, x='Type', y='Hours', color='Type',
                                 color_discrete_map={'Productive':'#22c55e','Essential':'#3b82f6','Waste':'#ef4444'},
                                 title="Overall Time Distribution")
                st.plotly_chart(fig_bar, width='stretch', key="daily_bar")
            with col_pie:
                fig_pie = px.pie(bar_df, names='Type', values='Hours', color='Type',
                                 color_discrete_map={'Productive':'#22c55e','Essential':'#3b82f6','Waste':'#ef4444'},
                                 title="Time Share")
                st.plotly_chart(fig_pie, width='stretch', key="daily_pie")

            # Line: Productive & Waste ONLY — Essential removed
            if not report_df.empty:
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=report_df['date'], y=report_df['productive_hours'],
                    mode='lines+markers', name='Productive', line=dict(color='#22c55e', width=3)))
                fig_trend.add_trace(go.Scatter(x=report_df['date'], y=report_df['waste_hours'],
                    mode='lines+markers', name='Waste', line=dict(color='#ef4444', width=3)))
                fig_trend.update_layout(title="Productive vs Waste Daily Trend",
                                        xaxis_title="Date", yaxis_title="Hours")
                st.plotly_chart(fig_trend, width='stretch', key="daily_trend_line")

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
                st.metric("🎯 Overall Score", f"{productivity_score(df, sleep_hours=sleep_hours_dict):.0f}%",
                         delta=f"Streak: {streak(df)}d")
            
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
                        st.markdown(f"You're maintaining a high study ratio! Your top subjects are: **{', '.join(df[df['type'].isin(ALL_PRODUCTIVE)].groupby('subject')['duration'].sum().nlargest(2).index.tolist())}**.")
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
                    f_score = focus_score(df)
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
                        streak(df)
                    )
                    st.markdown("#### 🤖 Esu's Recommendation")
                    st.info(insight)
                    st.success("✅ Analysis complete. Use these tips to optimize your study routine!")
            else:
                st.markdown(f"""
                **📊 Quick Stats:**
                - **Productive**: {prod_total:.1f}h | **Essential**: {essential_total:.1f}h | **Waste**: {waste_total:.1f}h
                - **Study Streak**: {streak(df)} days
                
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
                waste_tbl = _filtered_waste_df.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date')
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

                st.info("💡 Use the **Ask Esu** page to get personalized waste reduction strategies.")

                # ── WASTE ACTIVITY TREND ─────────────────────────────────────
                st.markdown("---")
                st.markdown("### 📉 Waste Activity Trend")
                st.markdown("*Select a specific waste activity to see its detailed trend across hours, days, and months.*")

                # Use filtered types for the trend selector
                _daily_waste_types = sorted(_filtered_waste_df['type'].unique().tolist())
                if _daily_waste_types:
                    _sel_waste_act_d = st.selectbox(
                        "🔍 Select Activity for Detailed Trend",
                        _daily_waste_types,
                        index=0,
                        key="daily_waste_act_sel"
                    )
                    _act_df_d = _filtered_waste_df[_filtered_waste_df['type'] == _sel_waste_act_d].copy()

                    # --- Hourly Distribution ---
                    st.markdown(f"#### ⏰ Hourly Distribution — *{_sel_waste_act_d}*")
                    _act_df_d['_hour'] = _act_df_d.apply(extract_hour_from_row, axis=1)
                    _hourly_d = _act_df_d.dropna(subset=['_hour'])
                    if not _hourly_d.empty:
                        _hourly_grp_d = _hourly_d.groupby('_hour')['duration'].sum().reset_index()
                        _hourly_grp_d['_hour_label'] = _hourly_grp_d['_hour'].apply(lambda h: f"{int(h):02d}:00")
                        _hourly_grp_d = _hourly_grp_d.sort_values('_hour')

                        # Build a full 24-hour series (fill missing hours with 0)
                        _all_hours_d = pd.DataFrame({'_hour': range(24)})
                        _all_hours_d['_hour_label'] = _all_hours_d['_hour'].apply(lambda h: f"{h:02d}:00")
                        _full_24_d = _all_hours_d.merge(
                            _hourly_grp_d[['_hour', 'duration']], on='_hour', how='left'
                        ).fillna(0)

                        _hcol1_d, _hcol2_d = st.columns(2)
                        with _hcol1_d:
                            _fig_h_d = px.bar(_hourly_grp_d, x='_hour_label', y='duration',
                                              labels={'_hour_label': 'Hour of Day', 'duration': 'Hours'},
                                              color_discrete_sequence=['#f97316'],
                                              title=f"{_sel_waste_act_d} — Bar (logged hours only)")
                            _fig_h_d.update_layout(template='plotly_dark', xaxis_tickangle=-45, height=380)
                            st.plotly_chart(_fig_h_d, width='stretch', key=f"daily_wat_hourly_bar_{_sel_waste_act_d}")
                        with _hcol2_d:
                            _fig_h_line_d = go.Figure()
                            _fig_h_line_d.add_trace(go.Scatter(
                                x=_full_24_d['_hour_label'], y=_full_24_d['duration'],
                                mode='lines+markers', name=_sel_waste_act_d,
                                line=dict(color='#f97316', width=3),
                                fill='tozeroy', fillcolor='rgba(249,115,22,0.15)',
                                marker=dict(size=6, color='#fb923c')
                            ))
                            _fig_h_line_d.update_layout(
                                title=f"{_sel_waste_act_d} — Line (all 24 hours)",
                                xaxis_title="Hour of Day", yaxis_title="Hours",
                                template='plotly_dark', hovermode='x unified',
                                height=380, xaxis_tickangle=-45
                            )
                            st.plotly_chart(_fig_h_line_d, width='stretch', key=f"daily_wat_hourly_line_{_sel_waste_act_d}")
                    else:
                        st.caption("No time-stamped entries for this activity (log activities with 'Time Range (From-To)' to see hourly data).")

                    # --- Day-wise Trend ---
                    st.markdown(f"#### 📅 Day-wise Trend — *{_sel_waste_act_d}*")
                    _daywise_d = _act_df_d.groupby('date')['duration'].sum().reset_index().sort_values('date')
                    if not _daywise_d.empty:
                        _fig_day_d = go.Figure()
                        _fig_day_d.add_trace(go.Scatter(
                            x=_daywise_d['date'], y=_daywise_d['duration'],
                            mode='lines+markers', name=_sel_waste_act_d,
                            line=dict(color='#f97316', width=3),
                            fill='tozeroy', fillcolor='rgba(249,115,22,0.12)',
                            marker=dict(size=7)
                        ))
                        _fig_day_d.update_layout(
                            title=f"{_sel_waste_act_d} — Day-wise Trend",
                            xaxis_title="Date", yaxis_title="Hours",
                            template='plotly_dark', hovermode='x unified'
                        )
                        st.plotly_chart(_fig_day_d, width='stretch', key=f"daily_wat_daywise_{_sel_waste_act_d}")
                    else:
                        st.caption("No day-wise data available.")


                else:
                    st.caption("No waste activities found to analyze.")

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
                selected_date_td = st.date_input("📅 Select Date", value=pd.to_datetime(list(df['date'])[-1] if not df.empty else date.today()).date() if not df.empty else date.today(), key="24h_date_picker")
            
            # Filter data for selected date
            df_selected = df[pd.to_datetime(df['date']).dt.date == selected_date_td]
            
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

            # --- NEW: TOP 5 HOURLY SLOTS (OVERALL) ---
            st.markdown("### 🔝 Top 5 Productive & Waste Hours (Historical)")
            st.markdown("*Most productive and most wasted hours of the day based on your entire history*")
            
            t5_col1, t5_col2 = st.columns(2)
            with t5_col1:
                st.markdown("🎯 **Top 5 Productive Hours**")
                t5_prod = get_top_hours_all_time(df, type='productive')
                if t5_prod:
                    t5_prod_df = pd.DataFrame(t5_prod)
                    st.dataframe(t5_prod_df[['time', 'duration']], 
                                 column_config={"time": "Hour Slot", "duration": "Total Hours Logged"},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No data yet.")
            
            with t5_col2:
                st.markdown("⚠️ **Top 5 Waste Hours**")
                t5_waste = get_top_hours_all_time(df, type='waste')
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
                except:
                    sleep_hours_dict = {}
                    powernap_dict = {}
                
                prod_m      = month_df[month_df['type'].isin(ALL_PRODUCTIVE)]
                essential_m = month_df[month_df['type'].isin(ALL_ESSENTIAL)]
                waste_m     = month_df[~month_df['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL)]

                pm1, pm2, pm3, pm4 = st.columns(4)
                pm1.metric("Productive Hrs", f"{round(prod_m['duration'].sum(),1)}h")
                pm2.metric("Essential Hrs",  f"{round(essential_m['duration'].sum(),1)}h")
                pm3.metric("Waste Hrs",      f"{round(waste_m['duration'].sum(),1)}h")
                pm4.metric("Productivity %", f"{productivity_score(month_df, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict)}%")

                st.divider()

                # ── PRODUCTIVITY ANALYSIS ────────────────────────────────────
                st.markdown("### 📈 Productivity Analysis")

                daily_m = daily_report(month_df, sleep_data=sleep_hours_dict, powernap_data=powernap_dict)
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

                study_m = prod_m[prod_m['type'] == 'Study']
                if not study_m.empty:
                    st.markdown("**📚 Subject-wise Productive Hours**")
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

                    waste_m_tbl = _filtered_waste_m.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date')
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

                    st.info("💡 Use the **Ask Esu** page to get personalized waste reduction strategies.")

                    # ── WASTE ACTIVITY TREND (Monthly) ──────────────────────────────
                    st.markdown("---")
                    st.markdown("### 📉 Waste Activity Trend")
                    st.markdown("*Select a specific waste activity to see its detailed trend for the selected month.*")

                    _monthly_waste_types = sorted(_filtered_waste_m['type'].unique().tolist())
                    if _monthly_waste_types:
                        _sel_waste_act_m = st.selectbox(
                            "🔍 Select Activity for Detailed Trend",
                            _monthly_waste_types,
                            key=f"monthly_waste_act_sel_{month_str}"
                        )
                        _act_df_m = _filtered_waste_m[_filtered_waste_m['type'] == _sel_waste_act_m].copy()

                        # --- Hourly Distribution ---
                        st.markdown(f"#### ⏰ Hourly Distribution — *{_sel_waste_act_m}*")
                        _act_df_m['_hour'] = _act_df_m.apply(extract_hour_from_row, axis=1)
                        _hourly_m = _act_df_m.dropna(subset=['_hour'])
                        if not _hourly_m.empty:
                            _hourly_grp_m = _hourly_m.groupby('_hour')['duration'].sum().reset_index()
                            _hourly_grp_m['_hour_label'] = _hourly_grp_m['_hour'].apply(lambda h: f"{int(h):02d}:00")
                            _hourly_grp_m = _hourly_grp_m.sort_values('_hour')

                            # Build a full 24-hour series (fill missing hours with 0)
                            _all_hours_m = pd.DataFrame({'_hour': range(24)})
                            _all_hours_m['_hour_label'] = _all_hours_m['_hour'].apply(lambda h: f"{h:02d}:00")
                            _full_24_m = _all_hours_m.merge(
                                _hourly_grp_m[['_hour', 'duration']], on='_hour', how='left'
                            ).fillna(0)

                            _hcol1_m, _hcol2_m = st.columns(2)
                            with _hcol1_m:
                                _fig_h_m = px.bar(_hourly_grp_m, x='_hour_label', y='duration',
                                                  labels={'_hour_label': 'Hour of Day', 'duration': 'Hours'},
                                                  color_discrete_sequence=['#f97316'],
                                                  title=f"{_sel_waste_act_m} — Bar (logged hours only)")
                                _fig_h_m.update_layout(template='plotly_dark', xaxis_tickangle=-45, height=380)
                                st.plotly_chart(_fig_h_m, width='stretch', key=f"monthly_wat_hourly_bar_{_sel_waste_act_m}_{month_str}")
                            with _hcol2_m:
                                _fig_h_line_m = go.Figure()
                                _fig_h_line_m.add_trace(go.Scatter(
                                    x=_full_24_m['_hour_label'], y=_full_24_m['duration'],
                                    mode='lines+markers', name=_sel_waste_act_m,
                                    line=dict(color='#f97316', width=3),
                                    fill='tozeroy', fillcolor='rgba(249,115,22,0.15)',
                                    marker=dict(size=6, color='#fb923c')
                                ))
                                _fig_h_line_m.update_layout(
                                    title=f"{_sel_waste_act_m} — Line (all 24 hours)",
                                    xaxis_title="Hour of Day", yaxis_title="Hours",
                                    template='plotly_dark', hovermode='x unified',
                                    height=380, xaxis_tickangle=-45
                                )
                                st.plotly_chart(_fig_h_line_m, width='stretch', key=f"monthly_wat_hourly_line_{_sel_waste_act_m}_{month_str}")
                        else:
                            st.caption("No time-stamped entries for this activity. Log with 'Time Range (From-To)' to see hourly data.")

                        # --- Day-wise Trend ---
                        st.markdown(f"#### 📅 Day-wise Trend — *{_sel_waste_act_m}*")
                        _daywise_m = _act_df_m.groupby('date')['duration'].sum().reset_index().sort_values('date')
                        if not _daywise_m.empty:
                            _fig_day_m = go.Figure()
                            _fig_day_m.add_trace(go.Scatter(
                                x=_daywise_m['date'], y=_daywise_m['duration'],
                                mode='lines+markers', name=_sel_waste_act_m,
                                line=dict(color='#f97316', width=3),
                                fill='tozeroy', fillcolor='rgba(249,115,22,0.12)',
                                marker=dict(size=7)
                            ))
                            _fig_day_m.update_layout(
                                title=f"{_sel_waste_act_m} — Day-wise Trend ({month_str})",
                                xaxis_title="Date", yaxis_title="Hours",
                                template='plotly_dark', hovermode='x unified'
                            )
                            st.plotly_chart(_fig_day_m, width='stretch', key=f"monthly_wat_daywise_{_sel_waste_act_m}_{month_str}")
                        else:
                            st.caption("No day-wise data available.")

                    else:
                        st.caption("No waste activities found for this month.")

                st.divider()
                st.markdown(f"### 📈 Advanced Monthly Insights — {month_str}")
                
                # Top 5 Study Streaks in Month
                st.markdown("#### 🔥 Top 5 Study Streaks")
                m_streaks = calculate_top_streaks(month_df) # No need to pass year/month since month_df is already filtered
                if m_streaks:
                    st.dataframe(pd.DataFrame(m_streaks), 
                                 column_config={"start_date": "Start", "end_date": "End", "length": st.column_config.NumberColumn("Length (Days)", format="%d 🔥")},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No streaks found for this month.")

                # Top 5 Study Days in Month (Weekday vs Weekend)
                st.markdown("#### 🏆 Top Study Days & Content")
                wd_col, we_col = st.columns(2)
                with wd_col:
                    st.markdown("📅 **Top 5 Weekdays**")
                    top_wd = get_top_study_days(month_df, is_weekend=False)
                    if not top_wd.empty:
                        st.dataframe(top_wd[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekday study data.")
                
                with we_col:
                    st.markdown("Weekend **Top 5 Weekends**")
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
                                        f"As 'Esu', analyze my study patterns for {month_str}:\n"
                                        f"MONTHLY DATA: {recent_json}\n\n"
                                        f"HOURLY AVG PATTERNS: {hourly_json}\n\n"
                                        f"PEAK HOUR: {peak_hour} ({peak_prod:.0f}%)\n"
                                        f"LOWEST HOUR: {low_hour} ({low_prod:.0f}%)\n\n"
                                        f"1. Summarize my performance for this month.\n"
                                        f"2. Identify my 'Prime Time' and 'Danger Zones'.\n"
                                        f"3. Provide 3 specific recommendations for next month.\n"
                                        f"Keep it professional and encouraging."
                                    )
                                    ai_response = _ai_m.get_ai_insight(prompt)
                                    st.markdown(f"""
                                    <div style="background-color: #1a1a2e; border-left: 5px solid #4f46e5; padding: 20px; border-radius: 10px; color: #d1d5db;">
                                        {ai_response}
                                    </div>
                                    """, unsafe_allow_html=True)
                            
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
                except:
                    sleep_hours_dict = {}
                    powernap_dict = {}
                
                prod_y      = year_df[year_df['type'].isin(ALL_PRODUCTIVE)]
                essential_y = year_df[year_df['type'].isin(ALL_ESSENTIAL)]
                waste_y     = year_df[~year_df['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL)]

                py1, py2, py3, py4 = st.columns(4)
                py1.metric("Productive Hrs", f"{round(prod_y['duration'].sum(),1)}h")
                py2.metric("Essential Hrs",  f"{round(essential_y['duration'].sum(),1)}h")
                py3.metric("Waste Hrs",      f"{round(waste_y['duration'].sum(),1)}h")
                py4.metric("Productivity %", f"{productivity_score(year_df, sleep_hours=sleep_hours_dict, powernap_hours=powernap_dict)}%")

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
                        mp = mdata[mdata['type'].isin(ALL_PRODUCTIVE)]['duration'].sum()
                        me = mdata[mdata['type'].isin(ALL_ESSENTIAL)]['duration'].sum()
                        mw = mdata[~mdata['type'].isin(ALL_PRODUCTIVE + ALL_ESSENTIAL)]['duration'].sum()
                        month_rows.append({'Month': mlabel, 'Productive': round(mp,1),
                                           'Essential': round(me,1), 'Waste': round(mw,1)})
                yr_monthly_df = pd.DataFrame(month_rows)

                # ── PRODUCTIVITY ANALYSIS ────────────────────────────────────
                st.markdown("### 📈 Productivity Analysis")

                st.markdown("**📋 Month-by-Month Summary Table**")
                st.dataframe(yr_monthly_df.set_index('Month'), width='stretch')

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

                study_y = prod_y[prod_y['type'] == 'Study']
                if not study_y.empty:
                    st.markdown("**📚 Yearly Subject-wise Study Hours**")
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

                    waste_y_tbl = _filtered_waste_y.groupby(['date','type'])['duration'].sum().reset_index().sort_values('date')
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

                    # ── WASTE ACTIVITY TREND (Yearly) ────────────────────────────────
                    st.markdown("---")
                    st.markdown("### 📉 Waste Activity Trend")
                    st.markdown("*Select a specific waste activity to see its detailed trend for the selected year.*")

                    _yearly_waste_types = sorted(_filtered_waste_y['type'].unique().tolist())
                    if _yearly_waste_types:
                        _sel_waste_act_y = st.selectbox(
                            "🔍 Select Activity for Detailed Trend",
                            _yearly_waste_types,
                            key=f"yearly_waste_act_sel_{int(sel_year_y)}"
                        )
                        _act_df_y = _filtered_waste_y[_filtered_waste_y['type'] == _sel_waste_act_y].copy()

                        # --- Hourly Distribution ---
                        st.markdown(f"#### ⏰ Hourly Distribution — *{_sel_waste_act_y}*")
                        _act_df_y['_hour'] = _act_df_y.apply(extract_hour_from_row, axis=1)
                        _hourly_y = _act_df_y.dropna(subset=['_hour'])
                        if not _hourly_y.empty:
                            _hourly_grp_y = _hourly_y.groupby('_hour')['duration'].sum().reset_index()
                            _hourly_grp_y['_hour_label'] = _hourly_grp_y['_hour'].apply(lambda h: f"{int(h):02d}:00")
                            _hourly_grp_y = _hourly_grp_y.sort_values('_hour')

                            # Build a full 24-hour series (fill missing hours with 0)
                            _all_hours_y = pd.DataFrame({'_hour': range(24)})
                            _all_hours_y['_hour_label'] = _all_hours_y['_hour'].apply(lambda h: f"{h:02d}:00")
                            _full_24_y = _all_hours_y.merge(
                                _hourly_grp_y[['_hour', 'duration']], on='_hour', how='left'
                            ).fillna(0)

                            _hcol1_y, _hcol2_y = st.columns(2)
                            with _hcol1_y:
                                _fig_h_y = px.bar(_hourly_grp_y, x='_hour_label', y='duration',
                                                  labels={'_hour_label': 'Hour of Day', 'duration': 'Hours'},
                                                  color_discrete_sequence=['#f97316'],
                                                  title=f"{_sel_waste_act_y} — Bar (logged hours only)")
                                _fig_h_y.update_layout(template='plotly_dark', xaxis_tickangle=-45, height=380)
                                st.plotly_chart(_fig_h_y, width='stretch', key=f"yearly_wat_hourly_bar_{_sel_waste_act_y}_{int(sel_year_y)}")
                            with _hcol2_y:
                                _fig_h_line_y = go.Figure()
                                _fig_h_line_y.add_trace(go.Scatter(
                                    x=_full_24_y['_hour_label'], y=_full_24_y['duration'],
                                    mode='lines+markers', name=_sel_waste_act_y,
                                    line=dict(color='#f97316', width=3),
                                    fill='tozeroy', fillcolor='rgba(249,115,22,0.15)',
                                    marker=dict(size=6, color='#fb923c')
                                ))
                                _fig_h_line_y.update_layout(
                                    title=f"{_sel_waste_act_y} — Line (all 24 hours)",
                                    xaxis_title="Hour of Day", yaxis_title="Hours",
                                    template='plotly_dark', hovermode='x unified',
                                    height=380, xaxis_tickangle=-45
                                )
                                st.plotly_chart(_fig_h_line_y, width='stretch', key=f"yearly_wat_hourly_line_{_sel_waste_act_y}_{int(sel_year_y)}")
                        else:
                            st.caption("No time-stamped entries for this activity. Log with 'Time Range (From-To)' to see hourly data.")

                        # --- Day-wise Trend ---
                        st.markdown(f"#### 📅 Day-wise Trend — *{_sel_waste_act_y}*")
                        _daywise_y = _act_df_y.groupby('date')['duration'].sum().reset_index().sort_values('date')
                        if not _daywise_y.empty:
                            _fig_day_y = go.Figure()
                            _fig_day_y.add_trace(go.Scatter(
                                x=_daywise_y['date'], y=_daywise_y['duration'],
                                mode='lines+markers', name=_sel_waste_act_y,
                                line=dict(color='#f97316', width=3),
                                fill='tozeroy', fillcolor='rgba(249,115,22,0.12)',
                                marker=dict(size=7)
                            ))
                            _fig_day_y.update_layout(
                                title=f"{_sel_waste_act_y} — Day-wise Trend ({int(sel_year_y)})",
                                xaxis_title="Date", yaxis_title="Hours",
                                template='plotly_dark', hovermode='x unified'
                            )
                            st.plotly_chart(_fig_day_y, width='stretch', key=f"yearly_wat_daywise_{_sel_waste_act_y}_{int(sel_year_y)}")
                        else:
                            st.caption("No day-wise data available.")

                    else:
                        st.caption("No waste activities found for this year.")

                st.divider()
                st.markdown(f"### 📈 Advanced Yearly Insights — {int(sel_year_y)}")
                
                # Top 5 Study Streaks in Year
                st.markdown("#### 🔥 Top 5 Study Streaks")
                y_streaks = calculate_top_streaks(year_df)
                if y_streaks:
                    st.dataframe(pd.DataFrame(y_streaks), 
                                 column_config={"start_date": "Start", "end_date": "End", "length": st.column_config.NumberColumn("Length (Days)", format="%d 🔥")},
                                 hide_index=True, width='stretch')
                else:
                    st.caption("No streaks found for this year.")

                # Top 5 Study Days in Year (Weekday vs Weekend)
                st.markdown("#### 🏆 Top Study Days & Content")
                ywd_col, ywe_col = st.columns(2)
                with ywd_col:
                    st.markdown("📅 **Top 5 Weekdays**")
                    top_ywd = get_top_study_days(year_df, is_weekend=False)
                    if not top_ywd.empty:
                        st.dataframe(top_ywd[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekday study data.")
                
                with ywe_col:
                    st.markdown("Weekend **Top 5 Weekends**")
                    top_ywe = get_top_study_days(year_df, is_weekend=True)
                    if not top_ywe.empty:
                        st.dataframe(top_ywe[['date', 'hours', 'readings']], 
                                     column_config={"date": "Date", "hours": "Hrs", "readings": "What I was reading"},
                                     hide_index=True, width='stretch')
                    else:
                        st.caption("No weekend study data.")

                    st.info("💡 Use the **Ask Esu** page to get personalized waste reduction strategies.")

elif menu == "Ask Esu":
    st.title("🤖 Ask Esu - Personalized Study Assistant")
    
    # Pre-load saved responses from database
    if "saved_esu_responses_db" not in st.session_state:
        st.session_state["saved_esu_responses_db"] = get_esu_responses(USER)
    
    st.markdown("""
    Esu is your personalized AI study assistant. Ask Esu any question about your study habits, productivity, 
    weak subjects, or get a custom study plan. Esu analyzes all your data along with UPSC PYQ trends to provide tailored recommendations.
    """)
    
    import ai as _ai_esu
    
    # Get all data for analysis
    df_all = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    if not df_all.empty:
        if 'start_time' not in df_all.columns: df_all['start_time'] = None
        df_all['start_time'] = df_all.apply(lambda r: r['start_time'] if (pd.notna(r['start_time']) and r['start_time']) else (f"{extract_time_of_day(r['chapter'])}:00" if extract_time_of_day(r['chapter']) is not None else None), axis=1)
        df_all['chapter'] = df_all['chapter'].apply(get_clean_chapter)
    chapter_data = read_sql("SELECT * FROM chapters WHERE username=%s", (USER,))
    
    # Load UPSC PYQ Analysis data from JSON file
    import json
    try:
        with open('pyq_data.json', 'r') as f:
            pyq_json_data = json.load(f)
            pyq_data_prelims = pyq_json_data.get('prelims', [])
            pyq_data_mains = pyq_json_data.get('mains', [])
    except Exception as e:
        st.warning(f"Could not load PYQ data: {e}")
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
        
        st.divider()
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📝 Your Question/Request")
            user_prompt = st.text_area(
                "Ask Esu anything about your study habit, productivity, or request a personalized plan:",
                placeholder="E.g., 'Help me improve my weak subjects', 'Create a 30-day study plan for UPSC', 'Focus on PYQ patterns'",
                height=120,
                key="esu_prompt"
            )
        
        with col2:
            st.subheader("📅 Exam Date (Optional)")
            exam_date = st.date_input(
                "If you have an exam coming up, select the date:",
                value=None,
                key="esu_exam_date"
            )
            if exam_date:
                days_left = (exam_date - pd.Timestamp.now().date()).days
                st.info(f"⏱️ **Days until exam:** {days_left} days")
        
        st.divider()
        
        # Data Summary before asking - Now as Dropdown
        with st.expander("📊 **Your Current Data Summary**", expanded=False):
            col_summ1, col_summ2, col_summ3, col_summ4 = st.columns(4)
            
            with col_summ1:
                st.metric("📚 Study Hours", f"{prod_total_esu:.1f}h")
            with col_summ2:
                st.metric("⚙️ Essential Hours", f"{essential_total_esu:.1f}h")
            with col_summ3:
                st.metric("⚠️ Waste Hours", f"{waste_total_esu:.1f}h")
            with col_summ4:
                st.metric("📖 Subjects", len(subj_data))
            
            # Subject breakdown
            if subj_data:
                st.markdown("**Subject-wise Study Hours:**")
                subj_df_display = pd.DataFrame(list(subj_data.items()), columns=['Subject', 'Hours']).sort_values('Hours', ascending=False)
                st.dataframe(subj_df_display, width='stretch', hide_index=True)
        
        st.divider()
        
        # Display UPSC PYQ Trends from JSON File - Now as Dropdowns
        st.subheader("📈 UPSC PYQ Trends (Latest Database)")
        
        # Prelims dropdown
        with st.expander("📋 **UPSC Prelims - Important Subjects**", expanded=False):
            if pyq_data_prelims:
                st.markdown("**Ranked by PYQ Frequency:**")
                for subject_data in pyq_data_prelims:
                    with st.expander(f"#{subject_data['frequency_rank']} {subject_data['subject']} (Importance: {subject_data['importance_score']}/100)", expanded=False):
                        st.markdown(f"**📚 Important Chapters:** {subject_data['important_chapters']}")
                        st.markdown(f"**🎯 Key Topics:** {subject_data['important_topics']}")
                        st.markdown(f"**📖 Revision Strategy:** {subject_data['revision_strategy']}")
            else:
                st.info("No Prelims data available")
        
        # Mains dropdown
        with st.expander("📘 **UPSC Mains - Important Subjects**", expanded=False):
            if pyq_data_mains:
                st.markdown("**Ranked by PYQ Frequency:**")
                for subject_data in pyq_data_mains:
                    with st.expander(f"#{subject_data['frequency_rank']} {subject_data['subject']} (Importance: {subject_data['importance_score']}/100)", expanded=False):
                        st.markdown(f"**📚 Important Chapters:** {subject_data['important_chapters']}")
                        st.markdown(f"**🎯 Key Topics:** {subject_data['important_topics']}")
                        st.markdown(f"**📖 Revision Strategy:** {subject_data['revision_strategy']}")
            else:
                st.info("No Mains data available")
        
        # Weak subjects based on study hours
        subj_series = pd.Series(subj_data)
        avg_subj_hours = subj_series.mean()
        weak_subjects_list = subj_series[subj_series < avg_subj_hours].index.tolist()
        strong_subjects_list = subj_series[subj_series >= avg_subj_hours].index.tolist()
        
        analysis_col1, analysis_col2 = st.columns(2)
        
        with analysis_col1:
            st.markdown("**⚠️ Weak Subjects (Below Average):**")
            if weak_subjects_list:
                for ws in weak_subjects_list:
                    st.write(f"• {ws}: {subj_data.get(ws, 0):.1f}h")
            else:
                st.write("All well balanced!")
        
        with analysis_col2:
            st.markdown("**✅ Strong Subjects (Above Average):**")
            if strong_subjects_list:
                for ss in strong_subjects_list:
                    st.write(f"• {ss}: {subj_data.get(ss, 0):.1f}h")
            else:
                st.write("More focus needed on all!")
        
        st.divider()
        
        # Generate Esu Response
        if st.button("💬 Ask Esu", type="primary", width='stretch'):
            if not user_prompt.strip():
                st.warning("Please enter a question or request for Esu!")
            else:
                with st.spinner("🤔 Esu is thinking..."):
                    # Prepare comprehensive context for Esu
                    context = f"""
                    User's Study Data Summary:
                    - Total Study Hours: {prod_total_esu:.1f}h
                    - Essential Hours (Work/Coaching): {essential_total_esu:.1f}h
                    - Waste Time: {waste_total_esu:.1f}h
                    - Number of Subjects: {len(subj_data)}
                    - Subject Breakdown: {subj_data}
                    - Total Tracked Hours: {prod_total_esu + essential_total_esu + waste_total_esu:.1f}h
                    """
                    
                    # Add subject analysis
                    if weak_subjects_list:
                        context += f"\n- Weak Subjects (Below Average Study): {', '.join(weak_subjects_list)}"
                    if strong_subjects_list:
                        context += f"\n- Strong Subjects (Above Average Study): {', '.join(strong_subjects_list)}"
                    
                    # Add chapter data
                    if chapter_completion_summary:
                        context += f"\n- Chapter Completion Status: {chapter_completion_summary}"
                    
                    # Add UPSC PYQ data from JSON
                    if pyq_data_prelims:
                        context += "\n\nUPSC PRELIMS - Important Subjects by PYQ Frequency:"
                        for subject_data in pyq_data_prelims:
                            context += f"\n  {subject_data['frequency_rank']}. {subject_data['subject']} (Importance: {subject_data['importance_score']}/100)"
                            context += f"\n     Important Chapters: {subject_data['important_chapters']}"
                            context += f"\n     Key Topics: {subject_data['important_topics']}"
                            context += f"\n     Revision Strategy: {subject_data['revision_strategy']}"
                    
                    if pyq_data_mains:
                        context += "\n\nUPSC MAINS - Important Subjects by PYQ Frequency:"
                        for subject_data in pyq_data_mains:
                            context += f"\n  {subject_data['frequency_rank']}. {subject_data['subject']} (Importance: {subject_data['importance_score']}/100)"
                            context += f"\n     Important Chapters: {subject_data['important_chapters']}"
                            context += f"\n     Key Topics: {subject_data['important_topics']}"
                            context += f"\n     Revision Strategy: {subject_data['revision_strategy']}"
                    
                    if exam_date:
                        context += f"\n\nExam Timeline:"
                        context += f"\n- Exam Date: {exam_date.strftime('%B %d, %Y')}"
                        context += f"\n- Days Remaining: {days_left} days"
                        context += f"\n- Available Study Hours: {prod_total_esu:.1f}h (current)"
                        context += f"\n- Required Daily Hours: ~{(prod_total_esu/(days_left+1)):.1f}h (if distributed evenly)"
                        context += "\n- Focus: Exam-focused study plan with PYQ patterns and time optimization"
                    
                    # Call AI for personalized response
                    try:
                        esu_response = _ai_esu.ask_esu(user_prompt, context)
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
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            ">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <span style="font-size: 24px; margin-right: 15px;">🤖</span>
                    <h3 style="margin: 0; color: #e0e7ff; font-weight: 700;">Esu's Guidance</h3>
                </div>
                <div style="color: #cbd5e1; line-height: 1.6; font-size: 16px;">
                    {st.session_state["esu_response"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
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
                if st.button("🗑️ Delete Response", key="esu_delete"):
                    st.session_state["confirm_esu_delete"] = True
            with col_resp3:
                if st.button("🔄 New Question", key="esu_new"):
                    st.session_state["esu_response"] = None
                    st.session_state["esu_prompt"] = ""
                    st.rerun()
            
            if st.session_state.get("confirm_esu_delete", False):
                st.warning("Delete this response?")
                del_col1, del_col2 = st.columns(2)
                with del_col1:
                    if st.button("✅ Yes, Delete", key="esu_confirm_delete"):
                        st.session_state["esu_response"] = None
                        st.session_state["confirm_esu_delete"] = False
                        st.success("Response deleted.")
                        st.rerun()
                with del_col2:
                    if st.button("❌ Cancel", key="esu_cancel_delete"):
                        st.session_state["confirm_esu_delete"] = False
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

    df = read_sql("SELECT * FROM activities WHERE username=%s", (USER,))
    df = df[df['amount'] > 0]

    if not df.empty:
        total_exp = df['amount'].sum()
        e1, e2 = st.columns(2)
        e1.metric("Total Expenses", f"₹{round(total_exp, 2)}")
        e2.metric("Categories", f"{df['type'].nunique()}")

        # TABLE FIRST
        st.markdown("**📋 All Expense Entries**")
        exp_tbl = df[['date','type','subject','amount']].sort_values('date', ascending=False)
        st.dataframe(exp_tbl.rename(columns={'date':'Date','type':'Category','subject':'Details','amount':'Amount (₹)'}),
                     width='stretch')

        # Charts side by side
        col_eb, col_ep = st.columns(2)
        with col_eb:
            exp_grp = df.groupby('type')['amount'].sum().sort_values(ascending=False)
            st.bar_chart(exp_grp)
        with col_ep:
            fig_ep = px.pie(exp_grp.reset_index(), names='type', values='amount',
                            title="Expense Distribution",
                            color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_ep, width='stretch', key="expenses_pie")

        # Expense Summary Analysis
        st.divider()
        st.markdown("### 📊 Expense Analysis Summary")
        
        exp_stats_col1, exp_stats_col2, exp_stats_col3, exp_stats_col4 = st.columns(4)
        
        with exp_stats_col1:
            st.metric("Total Expenses", f"₹{total_exp:.0f}")
        with exp_stats_col2:
            avg_exp = df['amount'].mean()
            st.metric("Average Expense", f"₹{avg_exp:.0f}")
        with exp_stats_col3:
            max_category = exp_grp.idxmax()
            max_amount = exp_grp.max()
            st.metric("Highest Category", max_category, f"₹{max_amount:.0f}")
        with exp_stats_col4:
            highest_day = df.groupby('date')['amount'].sum().idxmax()
            highest_day_amount = df.groupby('date')['amount'].sum().max()
            st.metric("Highest Spending Day", str(highest_day), f"₹{highest_day_amount:.0f}")
        
        # Category breakdown
        st.markdown("**Category Breakdown:**")
        exp_breakdown_col1, exp_breakdown_col2 = st.columns(2)
        with exp_breakdown_col1:
            for category, amount in exp_grp.items():
                pct = (amount / total_exp) * 100
                st.markdown(f"- **{category}**: ₹{amount:.0f} ({pct:.1f}%)")
        with exp_breakdown_col2:
            # Daily average
            daily_avg = df.groupby('date')['amount'].sum().mean()
            st.info(f"📆 **Daily Average**: ₹{daily_avg:.0f}/day")
        
        st.info("💡 Use the **Ask Esu** page to get personalized expense optimization and budgeting strategies.")

        st.divider()
        st.subheader("Manage Expenses")
        for _, row in df.iterrows():
            cols = st.columns([4, 1, 1, 1])
            with cols[0]:
                st.write(f"{row['date']} | {row['type']} | ₹{row['amount']}")
            with cols[1]:
                if st.button("Delete", key=f"del_exp_{row['id']}"):
                    st.session_state[f"confirm_exp_{row['id']}"] = True

            if st.session_state.get(f"confirm_exp_{row['id']}", False):
                with cols[2]:
                    if st.button("Yes", key=f"yes_exp_{row['id']}"):
                        c.execute("DELETE FROM activities WHERE id=%s AND username=%s", (row['id'], USER))
                        conn.commit()
                        st.session_state[f"confirm_exp_{row['id']}"] = False
                        st.rerun()
                with cols[3]:
                    if st.button("No", key=f"no_exp_{row['id']}"):
                        st.session_state[f"confirm_exp_{row['id']}"] = False
                        st.rerun()
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
        df_users = read_sql("SELECT id, username, last_login FROM users ORDER BY id")
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
                    
                c1.write(f"👤 **{row['username']}** (ID: {row['id']})  \n🕒 Last Login: `{l_log_str}`")
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

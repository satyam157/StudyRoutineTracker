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

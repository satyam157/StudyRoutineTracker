import streamlit as st
import base64
import random

# ------------------ DATABASE ------------------
def log_love_acceptance(username):
    from database import get_fresh_cursor
    try:
        tmp_conn, tmp_cur = get_fresh_cursor()
        msg = "💖 YES! I have officially accepted to be your Girlfriend! 💖"
        
        # Notify admin, users with specific notification permission, and assigned recipients
        # Start with admin
        recipients = ['admin']
        
        # Add users who opted in via config
        tmp_cur.execute("SELECT username FROM user_config WHERE can_receive_love_notifications = TRUE")
        recipients.extend([r[0] for r in tmp_cur.fetchall()])
        
        # Add specific assigned recipients for this sender
        tmp_cur.execute("SELECT recipient FROM user_recipients WHERE sender = %s", (username,))
        recipients.extend([r[0] for r in tmp_cur.fetchall()])
        
        for recipient in set(recipients):
            from database import get_ist_now
            tmp_cur.execute(
                "INSERT INTO system_notifications (username, message, recipient, timestamp) VALUES (%s, %s, %s, %s)",
                (username, msg, recipient, get_ist_now()),
            )
        tmp_conn.commit()
        tmp_cur.close()
        tmp_conn.close()
    except:
        pass


def send_love_notification(sender, message, recipient):
    from database import conn, c
    try:
        from database import get_ist_now
        c.execute(
            "INSERT INTO system_notifications (username, message, recipient, timestamp) VALUES (%s, %s, %s, %s)",
            (sender, message, recipient, get_ist_now()),
        )
        conn.commit()
    except:
        pass


def notify_page_open(username):
    from database import get_fresh_cursor
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        recipients = ['admin']
        tmp_c.execute("SELECT username FROM user_config WHERE can_receive_love_notifications = TRUE")
        recipients.extend([r[0] for r in tmp_c.fetchall()])
        tmp_c.execute("SELECT recipient FROM user_recipients WHERE sender = %s", (username,))
        recipients.extend([r[0] for r in tmp_c.fetchall()])
        msg = f"🔔 {username} has opened the MyLove Special page! 💌"
        for recipient in set(recipients):
            from database import get_ist_now
            tmp_c.execute(
                "INSERT INTO system_notifications (username, message, recipient, timestamp) VALUES (%s, %s, %s, %s)",
                (username, msg, recipient, get_ist_now()),
            )
        tmp_conn.commit()
        tmp_c.close()
        tmp_conn.close()
    except:
        pass


def log_no_rejection(username):
    from database import get_fresh_cursor
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        recipients = ['admin']
        tmp_c.execute("SELECT username FROM user_config WHERE can_receive_love_notifications = TRUE")
        recipients.extend([r[0] for r in tmp_c.fetchall()])
        tmp_c.execute("SELECT recipient FROM user_recipients WHERE sender = %s", (username,))
        recipients.extend([r[0] for r in tmp_c.fetchall()])
        msg = f"💔 Oh no! {username} just clicked 'NO' on the proposal! 😢"
        for recipient in set(recipients):
            from database import get_ist_now
            tmp_c.execute(
                "INSERT INTO system_notifications (username, message, recipient, timestamp) VALUES (%s, %s, %s, %s)",
                (username, msg, recipient, get_ist_now()),
            )
        tmp_conn.commit()
        tmp_c.close()
        tmp_conn.close()
    except:
        pass



# ------------------ NOTIFICATIONS ------------------

def get_latest_love_notifications(recipient):
    from database import conn, c
    try:
        c.execute("""
            SELECT id, message, timestamp, username 
            FROM system_notifications 
            WHERE is_read = FALSE AND (recipient = %s OR (recipient IS NULL AND %s = 'admin'))
            ORDER BY timestamp DESC
        """, (recipient, recipient))
        return c.fetchall()
    except:
        return []


def mark_notification_read(notif_id):
    from database import conn, c
    try:
        c.execute("UPDATE system_notifications SET is_read = TRUE WHERE id = %s", (notif_id,))
        conn.commit()
    except:
        pass


def delete_notification(notif_id):
    from database import get_fresh_cursor
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        tmp_c.execute("DELETE FROM system_notifications WHERE id = %s", (notif_id,))
        tmp_conn.commit()
        tmp_c.close()
        tmp_conn.close()
    except:
        pass



def get_all_love_notifications(recipient):
    from database import conn, c
    try:
        c.execute("""
            SELECT id, message, timestamp, username 
            FROM system_notifications 
            WHERE recipient = %s OR (recipient IS NULL AND %s = 'admin')
            ORDER BY timestamp DESC
        """, (recipient, recipient))
        return c.fetchall()
    except:
        return []


# ------------------ ADMIN NOTIFICATIONS UI ------------------

def show_admin_notifications(recipient='admin', mode='all'):

    # Fetch all notifications
    notifs = get_all_love_notifications(recipient)

    # Filter based on mode
    filtered_notifs = []
    for n in notifs:
        msg = n[1] # row is (id, message, timestamp, username)
        is_system = any(prefix in msg for prefix in ["🔔", "💔", "💖 YES!"])
        
        if mode == 'system' and is_system:
            filtered_notifs.append(n)
        elif mode == 'personal' and not is_system:
            filtered_notifs.append(n)
        elif mode == 'all':
            filtered_notifs.append(n)

    if not filtered_notifs:
        msg_map = {
            'system': "No system alerts yet. Everything is quiet! 🕊️",
            'personal': "No personal letters yet. Patience is a virtue of love! 💌",
            'all': "Your inbox is empty for now. But don't worry, love is always in the air! 💭"
        }
        st.info(msg_map.get(mode, "Your inbox is empty."))
        return

    # Fetch user config for permissions
    from database import get_user_config
    config = get_user_config(recipient)
    
    # Determine permission based on mode
    if mode == 'system':
        can_delete = config.get("can_delete_system_alerts", False) or recipient == 'admin'
    else: # mode == 'personal' or 'all'
        # Default to checking personal note permission for 'all' mode or specified 'personal' mode
        can_delete = config.get("can_delete_messages", False) or recipient == 'admin'

    for n_id, msg, ts, sender in filtered_notifs:
        # Determine if it's a love message, rejection, or system
        if "accepted" in msg.lower() or "Love" in msg:
            icon = "💖"
        elif "clicked 'NO'" in msg or "rejected" in msg.lower():
            icon = "💔"
        else:
            icon = "🔔"
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
            padding: 20px;
            border-radius: 20px;
            margin-bottom: 5px;
            border-left: 5px solid #ff4b4b;
            box-shadow: 0 10px 20px rgba(255, 75, 75, 0.05);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 14px; font-weight: 600; color: #ff4b4b;">{icon} From: {sender}</span>
                <span style="font-size: 12px; color: #999;">⏰ {ts}</span>
            </div>
            <div style="font-size: 18px; color: #333; line-height: 1.5; font-style: italic;">
                "{msg}"
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Conscious Delete implementation - only show if permitted
        if can_delete:
            if st.checkbox(f"🗑️ Delete Message #{n_id}?", key=f"chk_del_{n_id}"):
                st.warning("Are you sure? This cannot be undone.")
                c1, c2 = st.columns(2)
                if c1.button("✅ Yes, Delete", key=f"y_del_{n_id}", type="primary"):
                    delete_notification(n_id)
                    st.rerun()
                if c2.button("❌ No, Keep It", key=f"n_del_{n_id}"):
                    st.rerun()

        # Mark as read
        mark_notification_read(n_id)

    # Clear all button - only show if permitted
    if can_delete:
        st.divider()
        if st.button(f"🗑️ Clear {mode.capitalize()} History", width='stretch'):
            from database import get_fresh_cursor
            tmp_conn, tmp_c = get_fresh_cursor()
            if tmp_c:
                try:
                    # Use the same classification logic as the display to identify IDs
                    notifs = get_all_love_notifications(recipient)
                    ids_to_delete = []
                    
                    for n_id, msg, ts, sender in notifs:
                        is_system = any(prefix in msg for prefix in ["🔔", "💔", "💖 YES!"])
                        if (mode == 'system' and is_system):
                            ids_to_delete.append(n_id)
                        elif (mode == 'personal' and not is_system):
                            ids_to_delete.append(n_id)
                        elif mode == 'all':
                            ids_to_delete.append(n_id)
                    
                    if ids_to_delete:
                        # Use ANY for PostgreSQL to delete a list of IDs efficiently
                        tmp_c.execute("DELETE FROM system_notifications WHERE id = ANY(%s)", (ids_to_delete,))
                        tmp_conn.commit()
                    tmp_c.close()
                    tmp_conn.close()
                    st.success("History cleared! ✨")
                    import time; time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing notifications: {e}")
            else:
                st.error("Database connection failed")



# ------------------ MUSIC ------------------
def play_music(song_path="Perfect.mp3"):
    # MyLove Special page has its own music — the sidebar player is skipped on this page
    try:
        import os
        if os.path.exists(song_path):
            st.audio(song_path, format="audio/mp3", autoplay=True, loop=True)
        else:
            st.sidebar.warning(f"⚠️ {song_path} not found. Please add the file to the project folder.")
            if song_path != "Perfect.mp3" and os.path.exists("Perfect.mp3"):
                st.audio("Perfect.mp3", format="audio/mp3", autoplay=True, loop=True)
    except Exception as e:
        st.error(f"Error playing music: {e}")

# ------------------ CSS ------------------
def inject_css():
    st.markdown("""
    <style>

    .center-box {
        max-width: 720px;
        margin: auto;
        text-align: center;
    }

    .title {
        font-size: 36px;
        font-weight: bold;
        color: #ff2e63;
        margin-bottom: 20px;
    }

    .card {
        background: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }

    .typing {
        font-size: 18px;
        line-height: 1.7;
        color: #333;
        white-space: pre-line;
        overflow: hidden;
        border-right: 2px solid black;
        display: inline-block;
        animation: typing 4s steps(80, end) forwards, blink 0.7s infinite;
    }

    @keyframes typing {
        from {width: 0}
        to {width: 100%}
    }

    @keyframes blink {
        50% {border-color: transparent}
    }

    div.stButton > button {
        width: 240px;
        height: 50px;
        border-radius: 30px;
        font-size: 16px;
        font-weight: bold;
        margin: 10px auto;
        display: block;
    }

    </style>
    """, unsafe_allow_html=True)


# ------------------ HEART BURST ------------------
def heart_burst():
    hearts = ""
    for _ in range(25):
        left = random.randint(0, 100)
        delay = random.uniform(0, 2)
        hearts += f"""
        <div style="position:fixed; bottom:0; left:{left}%;
        font-size:20px; animation:floatUp 4s linear infinite;
        animation-delay:{delay}s;">💖</div>
        """

    st.markdown("""
    <style>
    @keyframes floatUp {
        0% {transform: translateY(0); opacity:1;}
        100% {transform: translateY(-100vh); opacity:0;}
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(hearts, unsafe_allow_html=True)


# ------------------ MAIN ------------------
def show_proposal(USER):

    if "phase" not in st.session_state:
        st.session_state.phase = "proposal"


    # Notify admin and assigned users that the page has been opened (only once per session)
    if not st.session_state.get("notified_open", False):
        notify_page_open(USER)
        st.session_state.notified_open = True

    inject_css()
    
    # Music playback is now handled by the sidebar music player
    # (auto-selects Perfect.mp3 when entering this page)

    # ------------------ SUCCESS ------------------
    if st.session_state.phase == "success":
        st.balloons()
        heart_burst()
        log_love_acceptance(USER)

        st.markdown('<div class="center-box">', unsafe_allow_html=True)

        st.markdown('<div class="title">🎊 Congratulations, my love! 💫</div>', unsafe_allow_html=True)

        st.success("""
Status update: You are now officially Satyam Sourav’s girlfriend 💍😉  
The universe just made it official… you are now Satyam Sourav’s girlfriend 💍❤️  

A love story has just begun 💖  
And guess what — your love letter is already on its way to steal his heart 💌💘
        """)

        if st.button("Restart 💫"):
            st.session_state.phase = "proposal"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ------------------ PROPOSAL ------------------
    elif st.session_state.phase == "proposal":

        st.markdown('<div class="center-box">', unsafe_allow_html=True)

        st.markdown('<div class="title">Will you be my Girlfriend? 💌</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <div class="typing">
Priye Likhkar Naam Tumhara,
Kuch Jagah Beech Me Chhod Likh Du Sada Tumhara,
Likha Beech Me Kya Yeh Tmko Padhna Hai,
Kagaz Par Mann Ki Bhasha Ka Arth Samjhna Hai,
Jo bhi Arth Nikalogi Tum Wo Mujhko Swikar Hai.
Jhuke Nayan, Maun Adhar, Ya Kora Kagaz,
Arth Sabhi Ka Pyar Hai ❤️
        </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("💖 YES"):
                st.session_state.phase = "success"
                st.rerun()

            if st.button("No 😢"):
                log_no_rejection(USER)
                st.session_state.phase = "rejected"
                st.rerun()


        st.markdown('</div>', unsafe_allow_html=True)

    # ------------------ REJECTED ------------------
    elif st.session_state.phase == "rejected":

        st.markdown('<div class="center-box">', unsafe_allow_html=True)

        st.markdown('<div class="title">💭 Think it twice, my love… for in every heartbeat of mine, I’m waiting for your “yes.” 💘🌹✨</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <div class="typing">
Bas Ab Ek Haan Ke Intezaar Me Raat Yunhi Guzar Jaayegi,
Ab Toh Bas Uljhan Hai Saath Mere Neend Kahan Aayegi,
Subah Ki Kiran Na Jaane Konsa Sandesh Laayegi,
Rimjhim Si Gungunayegi Ya Pyaas Adhuri Reh Jaayegi 💔
        </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("🥺 Please Say Yes 💖"):
                st.session_state.phase = "success"
                st.rerun()

        st.markdown("""
        <div style="text-align:center; margin-top:20px; font-size:18px; color:#555; line-height:1.6;">
        I may smile in front of you... but deep inside, my heart is softly whispering your name 💭<br>
        Every moment feels incomplete without your "yes"... 💘<br>
        Don’t let this love remain just a wish... make it our forever 🌹✨
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

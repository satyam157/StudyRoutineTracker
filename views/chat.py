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
                        import database
                        get_fresh_cursor = database.get_fresh_cursor
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
                    try:
                        _her_df = read_sql("SELECT username FROM user_config WHERE can_receive_love_messages = TRUE AND username != 'admin' LIMIT 1")
                        _her = _her_df.iloc[0]['username'] if not _her_df.empty else None
                    except:
                        _her = None
                    if _her:
                        proposal.send_love_notification("admin", "I love you too, my princess! 💖🌹", _her)
                        proposal.notify_admins_personal_note("admin", "I love you too, my princess! 💖🌹", _her)
                        st.toast("Love message sent! 💌", icon="❤️")
            
            with st.container():
                love_msg = st.text_area("Message", placeholder="Write your heart out...", height=150)
                
                # Determine allowed recipients
                if USER == "admin":
                    try:
                        allowed_users_df = read_sql("SELECT username FROM user_config WHERE can_receive_love_messages = TRUE AND username != 'admin'")
                        allowed_users = allowed_users_df['username'].tolist()
                    except:
                        allowed_users = get_allowed_recipients(USER)
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
    
    

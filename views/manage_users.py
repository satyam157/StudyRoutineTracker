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

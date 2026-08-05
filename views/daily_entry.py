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
    if st.session_state.get("_clear_de_form"):
        for k in list(st.session_state.keys()):
            if k.startswith("de_"):
                del st.session_state[k]
        st.session_state["_clear_de_form"] = False

    conn = database.conn
    c = database.c
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
    
    selected_tab = st.radio("Tab Selection", ["📝 Log Activities", "✈️ Log Trip", "🌙 Sleep & Wake Log", "⚙️ Manage Defaults"], 
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
    
        _editing_entry = st.session_state.get("editing_entry", None)
        _editing_entry_id = None
        _edit_type = ""
        _edit_sub = ""
        _edit_ch = ""
        _edit_desc = ""
        _edit_dur = 0.0
        _edit_amt = 0.0
        _edit_st = ""
        _editing_activity_type = None

        if _editing_entry:
            _editing_entry_id = _editing_entry.get("id")
            _edit_type = _editing_entry.get("type", "")
            _edit_sub = _editing_entry.get("subject", "")
            _edit_ch = _editing_entry.get("chapter", "")
            _edit_desc = _editing_entry.get("description", "")
            _edit_dur = _editing_entry.get("duration", 0.0)
            _edit_amt = _editing_entry.get("amount", 0.0)
            _edit_st = _editing_entry.get("start_time", "")
            if _edit_type:
                _editing_activity_type = _edit_type
                _user_defaults[_edit_type] = (_edit_sub or "", _edit_ch or "")

        # Seed de_* session state keys from edit values (once per edit session)
        if _editing_entry and not st.session_state.get("de_seeded"):
            # Study mode
            if "de_study_mode" not in st.session_state:
                st.session_state["de_study_mode"] = "Current Affairs" if _edit_sub == "Current Affairs" else "Static GS Syllabus"
            # Time range fields — seed from_time if start_time is known
            if _edit_st:
                _from_key = f"de_from_{_edit_type}"
                if _from_key not in st.session_state:
                    st.session_state[_from_key] = _edit_st
                # Compute to_time from start + duration
                if _edit_dur and float(_edit_dur) > 0:
                    try:
                        _fh, _fm = map(int, str(_edit_st).split(":"))
                        _total_mins = int(_fh * 60 + _fm + float(_edit_dur) * 60)
                        _to_key = f"de_to_{_edit_type}"
                        if _to_key not in st.session_state:
                            st.session_state[_to_key] = f"{(_total_mins // 60) % 24}:{_total_mins % 60:02d}"
                    except:
                        pass
            st.session_state["de_seeded"] = True

        # Show editing banner if editing
        if _editing_entry_id:
            st.markdown(f"""<div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1.5px solid #f59e0b; border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size:15px; font-weight:700; color:#fbbf24;">✏️ Editing Entry #{_editing_entry_id} — {_editing_entry.get('type', '')}</span>
                <span style="font-size:12px; color:#94a3b8;">Fill in the fields below and click Submit to save changes</span>
            </div>""", unsafe_allow_html=True)
            _cancel_col1, _cancel_col2 = st.columns([3, 1])
            with _cancel_col2:
                if st.button("❌ Cancel Edit", key="cancel_editing_entry", use_container_width=True):
                    del st.session_state["editing_entry"]
                    for k in list(st.session_state.keys()):
                        if k.startswith("de_"):
                            del st.session_state[k]
                    if "de_seeded" in st.session_state: del st.session_state["de_seeded"]
                    st.rerun()

        # Activity selection with inline delete
        _act_col, _del_col = st.columns([3, 1])
        with _act_col:
            _all_acts = base_activities + custom + ["+ Add New"]
            _def_act_idx = _all_acts.index(_editing_activity_type) if _editing_activity_type in _all_acts else 0
            activity = st.selectbox("Activity", _all_acts, index=_def_act_idx)
            
            if st.session_state.get("last_selected_activity") != activity:
                # Don't wipe edit state when editing mode just loaded with the correct activity
                _is_same_as_edit = bool(_editing_entry and activity == _edit_type)
                if not _is_same_as_edit:
                    for k in list(st.session_state.keys()):
                        if k.startswith("de_"):
                            del st.session_state[k]
                    if "de_seeded" in st.session_state:
                        del st.session_state["de_seeded"]
                    st.session_state["last_selected_activity"] = activity
                    st.rerun()
                st.session_state["last_selected_activity"] = activity
        
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
    
        # Helper for default placeholders
        _is_editing_act = bool(_editing_entry_id and _editing_entry.get('type') == activity)
        def _val_ph(def_val, base_ph=""): return (def_val, base_ph) if _is_editing_act else ("", def_val or base_ph)
        def _final_val(typed, default): return typed if (typed or _is_editing_act) else default
        
        # Activity specific fields
        if activity == "Study":
            if "de_study_mode" in st.session_state and st.session_state["de_study_mode"] == "Current Affairs":
                pass
            else:
                _def_sub1, _def_sub2 = _user_defaults.get("Study", ("", ""))
                _def_ch = _def_sub2 if _def_sub1 != "Current Affairs" else ""
                _v, _p = _val_ph(_def_ch, "Enter chapter/topic...")
                _t2 = st.text_input("Chapter / Topic", value=_v, max_chars=50, placeholder=_p, key="de_study_static_ch")
                sub2 = _final_val(_t2, _def_ch)
        elif activity == "Revision":
            _def_sub1, _def_sub2 = _user_defaults.get("Revision", ("", ""))
            _rev_idx = 1 if _def_sub1 == "Pages" else 0
            _rev_type = st.radio("Revision Type", ["Chapter", "Pages"], index=_rev_idx, horizontal=True, key="de_rev_type")
            if _rev_type == "Chapter":
                _v, _p = _val_ph(_def_sub2, "Chapter Name")
                _t2 = st.text_input("Chapter Revised", value=_v, placeholder=_p, key="de_rev_ch")
                sub2 = _final_val(_t2, _def_sub2)
            else:
                _def_pg = _def_sub2.replace(" pg", "") if _def_sub2 else ""
                _v, _p = _val_ph(_def_pg, "Pages")
                _pg_val = st.text_input("Pages Revised", value=_v, placeholder=_p, key="de_rev_pg")
                _final_pg = _final_val(_pg_val, _def_pg)
                sub2 = f"{_final_pg} pg" if str(_final_pg).strip() else ""
        elif activity == "Book Reading":
            _def_sub1, _def_sub2 = _user_defaults.get("Book Reading", ("", ""))
            _v1, _p1 = _val_ph(_def_sub1, "Book Title")
            _t1 = st.text_input("Book Title", value=_v1, placeholder=_p1, key="de_book_title")
            sub1 = _final_val(_t1, _def_sub1)
            _v2, _p2 = _val_ph(_def_sub2, "Chapters/Pages")
            _t2 = st.text_input("Chapters/Pages", value=_v2, placeholder=_p2, key="de_book_detail")
            sub2 = _final_val(_t2, _def_sub2)
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
                _v, _p = _val_ph(_def_sub2, "#Questions")
                _t2 = st.text_input("#Questions", value=_v, placeholder=_p)
                sub2 = _final_val(_t2, _def_sub2)
        elif activity == "Office":
            _def_sub1, _def_sub2 = _user_defaults.get("Office", ("", ""))
            _v1, _p1 = _val_ph(_def_sub1, "Work Notes")
            _t1 = st.text_input("Work Notes", value=_v1, placeholder=_p1, key="de_office_notes")
            sub1 = _final_val(_t1, _def_sub1)
        elif activity == "Coaching":
            _def_sub1, _def_sub2 = _user_defaults.get("Coaching", ("", ""))
            _v1, _p1 = _val_ph(_def_sub1, "Subject")
            _t1 = st.text_input("Subject", value=_v1, placeholder=_p1, key="de_coaching_topic")
            sub1 = _final_val(_t1, _def_sub1)
            _v2, _p2 = _val_ph(_def_sub2, "Notes")
            _t2 = st.text_input("Notes", value=_v2, placeholder=_p2, key="de_coaching_notes")
            sub2 = _final_val(_t2, _def_sub2)
        elif activity == "WFH":
            _def_sub1, _def_sub2 = _user_defaults.get("WFH", ("", ""))
            _v1, _p1 = _val_ph(_def_sub1, "Work Notes")
            _t1 = st.text_input("Work Notes", value=_v1, placeholder=_p1, key="de_wfh_notes")
            sub1 = _final_val(_t1, _def_sub1)
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
            _v2, _p2 = _val_ph(_def_sub2, "Topic / Notes")
            _t2 = st.text_input("Topic / Notes", value=_v2, placeholder=_p2, key="de_talk_notes")
            sub2 = _final_val(_t2, _def_sub2)
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
            _v1, _p1 = _val_ph(_def_sub1, "Location")
            _t1 = st.text_input("Location", value=_v1, placeholder=_p1, key="de_went_outside")
            sub1 = _final_val(_t1, _def_sub1)
        elif activity == "Turf":
            _def_sub1, _def_sub2 = _user_defaults.get("Turf", ("", ""))
            _v1, _p1 = _val_ph(_def_sub1, "Sport")
            _t1 = st.text_input("Sport", value=_v1, placeholder=_p1, key="de_turf_sport")
            sub1 = _final_val(_t1, _def_sub1)
            _v2, _p2 = _val_ph(_def_sub2, "Details")
            _t2 = st.text_input("Details", value=_v2, placeholder=_p2, key="de_turf_detail")
            sub2 = _final_val(_t2, _def_sub2)
        elif activity == "Travelling":
            _def_sub1, _def_sub2 = _user_defaults.get("Travelling", ("", ""))
            _travel_modes = ["✈️ Flight", "🚂 Railway", "🚗 Other"]
            _def_travel_idx = 2
            if _def_sub1 in _travel_modes:
                _def_travel_idx = _travel_modes.index(_def_sub1)
            sub1 = st.selectbox("Mode", _travel_modes, index=_def_travel_idx, key="de_travel_mode")
            
            _base_dest = _def_sub2
            if _is_editing_act and " | Studied: " in _def_sub2:
                _base_dest = _def_sub2.split(" | Studied: ")[0]
            _v2, _p2 = _val_ph(_base_dest, "Destination")
            _t2 = st.text_input("Destination", value=_v2, placeholder=_p2, key="de_travel_dest")
            sub2 = _final_val(_t2, _base_dest)
            st.caption("💡 For multi-day trips with study tracking, use the **✈️ Log Trip** tab.")
    
        _track_both = activity in ["Food", "Transport", "WentOutside", "Turf", "Travelling", "Office", "WFH", "Coaching", "Test"]
        _track_by_expense = activity in ["Food", "Transport"]
        if activity in custom:
            _track_both = (custom_track_map.get(activity) == "Expense (₹)")
            _track_by_expense = False
    
        _desc_default = ""
        if _editing_entry_id and _editing_entry.get('type') == activity and _edit_desc:
            _desc_default = _edit_desc
        description = st.text_input("📝 Description (Optional)", value=_desc_default, key=f"de_desc_{activity}")
        
        if not _editing_entry_id:
            pass
    
        # Pre-select mode based on edit entry: use "Hours" if no start_time, else "Time Range"
        if _editing_entry_id and _editing_entry.get('type') == activity:
            _def_dur_mode_idx = 1 if _edit_st else 0
        else:
            _def_dur_mode_idx = 1
                
        _duration_mode = st.radio("⏱️ Duration Input", ["Hours", "Time Range (From-To)"], index=_def_dur_mode_idx, horizontal=True, key=f"de_dur_mode_{activity}")
        
        duration = 0.0
        amount = 0.0
        start_time = ""
        is_midnight_crossing = False
        duration_today = duration_tomorrow = 0.0
        from_h = from_m = to_h = to_m = 0
    
        def parse_time_value(raw):
            try:
                if not raw: return None
                raw_str = str(raw).strip().lower()
                is_pm = 'pm' in raw_str or 'p.m.' in raw_str
                is_am = 'am' in raw_str or 'a.m.' in raw_str
                
                raw_str = raw_str.replace('.', ':')
                import re
                clean_raw = re.sub(r'[^\d:]', '', raw_str)
                if not clean_raw: return None
                
                if ":" in clean_raw:
                    parts = clean_raw.split(":", 1)
                    h = int(parts[0]) if parts[0] else 0
                    m = int(parts[1]) if parts[1] else 0
                else:
                    if len(clean_raw) == 3 or len(clean_raw) == 4:
                        h = int(clean_raw[:-2])
                        m = int(clean_raw[-2:])
                    else:
                        h, m = int(clean_raw), 0
                        
                if is_pm and h < 12: h += 12
                elif is_am and h == 12: h = 0
                h = h % 24
                return h, m
            except: return None
    
        if _duration_mode == "Hours":
            _def_dur = float(_edit_dur) if (_editing_entry_id and _editing_entry.get('type') == activity) else 0.0
            _def_amt = float(_edit_amt) if (_editing_entry_id and _editing_entry.get('type') == activity) else 0.0
            if _track_both:
                c1, c2 = st.columns(2)
                with c1: duration = st.number_input("⏱️ Hours", min_value=0.0, step=0.5, value=_def_dur, key=f"de_hours_{activity}")
                with c2: amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=_def_amt, key=f"de_amount_{activity}")
            elif _track_by_expense:
                amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=_def_amt)
            else:
                duration = st.number_input("⏱️ Hours", min_value=0.0, step=0.5, value=_def_dur)
        else:
            _def_st = _edit_st if (_editing_entry_id and _editing_entry.get('type') == activity) else ""
            _def_to = ""
            if _def_st:
                _dur_to_use = _edit_dur if (_editing_entry_id and _editing_entry.get('type') == activity) else 0.0
                if _dur_to_use > 0:
                    try:
                        f_h, f_m = map(int, _def_st.split(":"))
                        total_mins = int(f_h * 60 + f_m + float(_dur_to_use) * 60)
                        t_h = (total_mins // 60) % 24
                        t_m = total_mins % 60
                        _def_to = f"{t_h}:{t_m:02d}"
                    except:
                        pass
            _def_amt = float(_edit_amt) if (_editing_entry_id and _editing_entry.get('type') == activity) else 0.0
            
            from database import get_ist_now
            _ist_now = get_ist_now()
            _now_str = f"{_ist_now.hour}:{_ist_now.minute:02d}"
            
            # Explicitly seed session_state ONLY if key doesn't exist yet
            _from_key = f"de_from_{activity}"
            _to_key = f"de_to_{activity}"
            if _from_key not in st.session_state:
                st.session_state[_from_key] = _def_st
            if _to_key not in st.session_state:
                st.session_state[_to_key] = _def_to
            
            c1, c2 = st.columns([1, 1])
            with c1:
                from_time_raw = st.text_input("From Time", key=_from_key, placeholder="e.g. 10:30")
            with c2:
                to_time_raw = st.text_input("To Time", key=_to_key, placeholder="e.g. 12:00")
            
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
                    else:
                        duration = (t_mins - f_mins) / 60
                    st.caption(f"⏱️ Duration: **{format_duration(duration)}**" + (" (spans midnight ⏰)" if is_midnight_crossing else ""))
                elif from_time_raw and not parse_time_value(to_time_raw):
                    st.warning("⚠️ Invalid To Time format. Use HH:MM or H:MM AM/PM")
            elif from_time_raw and not to_time_raw:
                st.caption("ℹ️ Enter To Time")
            if _track_both: amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=1.0, value=_def_amt if _duration_mode != "Hours" else 0.0, key=f"de_amt_tr_{activity}")
        


        _submit_label = "💾 Update Activity" if _editing_entry_id else "💾 Submit Activity"
        save_clicked = st.button(_submit_label, key="submit_main_activity", use_container_width=True)



        if save_clicked:
            if duration <= 0.0 and amount <= 0.0:
                if _duration_mode == "Time Range (From-To)":
                    st.error("⚠️ Both 'From Time' and 'To Time' are required to calculate duration.")
                else:
                    st.error("⚠️ Please enter a valid duration or amount before submitting.")
                st.stop()
                
            entry_status = 'Completed'
            
            # Delete any active draft when submitting
            c.execute("DELETE FROM activities WHERE username=%s AND status='Draft'", (USER,))
            
            if _editing_entry_id:
                # UPDATE the existing entry instead of inserting a new one
                if is_midnight_crossing:
                    # For midnight crossing edits, update original and insert the next-day part
                    c.execute(
                        "UPDATE activities SET type=%s, subject=%s, chapter=%s, duration=%s, amount=%s, start_time=%s, description=%s, status=%s WHERE id=%s AND username=%s",
                        (activity, sub1, sub2, duration_today, amount, f"{from_h}:{from_m:02d}", description, entry_status, _editing_entry_id, USER)
                    )
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date + timedelta(days=1)), activity, sub1, sub2, duration_tomorrow, 0, USER, f"{to_h}:{to_m:02d}", description, entry_status))
                else:
                    c.execute(
                        "UPDATE activities SET type=%s, subject=%s, chapter=%s, duration=%s, amount=%s, start_time=%s, description=%s, status=%s WHERE id=%s AND username=%s",
                        (activity, sub1, sub2, duration, amount, start_time, description, entry_status, _editing_entry_id, USER)
                    )
                # Clear editing state
                if "editing_entry" in st.session_state:
                    del st.session_state["editing_entry"]
            else:
                # Normal insert
                if is_midnight_crossing:
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date), activity, sub1, sub2, duration_today, amount, USER, f"{from_h}:{from_m:02d}", description, entry_status))
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date + timedelta(days=1)), activity, sub1, sub2, duration_tomorrow, 0, USER, f"{to_h}:{to_m:02d}", description, entry_status))
                else:
                    c.execute("INSERT INTO activities (date,type,subject,chapter,duration,amount,username,start_time,description,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(date), activity, sub1, sub2, duration, amount, USER, start_time, description, entry_status))

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
            
            _msg = "✅ Activity updated!" if _editing_entry_id else "✅ Activity saved!"
            st.toast(_msg, icon="✅")
            invalidate_activities_cache(USER)
            # Request clearing of input fields safely to force frontend update
            st.session_state["_clear_de_form"] = True
                    
            import time; time.sleep(1); st.rerun()

    
        st.divider()
        st.markdown("### 📋 Activities Logged")
        _today_df = read_sql("SELECT id, type, subject, chapter, duration, amount, start_time, description, COALESCE(status, 'Completed') as status FROM activities WHERE date=%s AND username=%s AND COALESCE(status, 'Completed') != 'Draft' ORDER BY CASE WHEN start_time IS NULL OR start_time = '' THEN 1 ELSE 0 END, LPAD(start_time, 5, '0') ASC, id ASC", (str(date), USER))
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
                _has_time = (_row['duration'] and float(_row['duration']) > 0) or (_row['amount'] and float(_row['amount']) > 0)
                val = format_duration(_row['duration']) if _row['duration'] and float(_row['duration']) > 0 else (f"₹{_row['amount']}" if _row['amount'] and float(_row['amount']) > 0 else "")
                if val: parts.append(val)
                
                l, r_edit, r_del = st.columns([4, 0.5, 0.5])
                
                raw_desc = _row.get('description')
                desc_text = ""
                if raw_desc and str(raw_desc).strip() and str(raw_desc).strip().lower() not in ('none', 'nan', 'null'):
                    desc_text = f"<br><span style='font-size:12px; color:#94a3b8;'>{str(raw_desc).strip()}</span>"
                
                if _has_time:
                    l.markdown(f"• **{' | '.join(parts)}**{desc_text}", unsafe_allow_html=True)
                else:
                    _no_time_label = ' | '.join(parts)
                    l.markdown(f"""<div style="background: rgba(251, 191, 36, 0.1); border-left: 3px solid #f59e0b; padding: 6px 10px; border-radius: 6px; margin: 2px 0;">
                        <span style="color: #fbbf24; font-weight: 600;">⏳ {_no_time_label}</span>
                        <span style="font-size: 11px; color: #f59e0b; margin-left: 6px;">(no time logged)</span>{desc_text}
                    </div>""", unsafe_allow_html=True)
                
                # Edit button — redirect to main form pre-filled with this entry's values
                if r_edit.button("✏️", key=f"edit_daily_{rid}"):
                    _e_dur = float(_row['duration']) if _row['duration'] else 0.0
                    _e_amt = float(_row['amount']) if _row['amount'] else 0.0
                    _e_sub = str(_row['subject']) if _row['subject'] and str(_row['subject']).strip().lower() not in ('none', 'nan', 'null') else ""
                    _e_ch = str(_row['chapter']) if _row['chapter'] and str(_row['chapter']).strip().lower() not in ('none', 'nan', 'null') else ""
                    _e_st = str(_row['start_time']) if _row['start_time'] and str(_row['start_time']).strip().lower() not in ('none', 'nan', 'null') else ""
                    _e_desc = str(raw_desc).strip() if raw_desc and str(raw_desc).strip().lower() not in ('none', 'nan', 'null') else ""
                    st.session_state["editing_entry"] = {
                        "id": rid,
                        "type": _row['type'],
                        "subject": _e_sub,
                        "chapter": _e_ch,
                        "duration": _e_dur,
                        "amount": _e_amt,
                        "start_time": _e_st,
                        "description": _e_desc,
                    }
                    for k in list(st.session_state.keys()):
                        if k.startswith("de_"):
                            del st.session_state[k]
                    st.rerun()
                
                # Delete button
                if r_del.button("🗑️", key=f"del_daily_{rid}"):
                    st.session_state[f"confirm_daily_del_{rid}"] = True
                
                # --- Delete Confirmation ---
                if st.session_state.get(f"confirm_daily_del_{rid}", False):
                    st.warning("Delete this entry?", icon="⚠️")
                    yc, nc = st.columns([1, 1])
                    with yc:
                        if st.button("✅ Yes", key=f"yes_daily_del_{rid}", use_container_width=True):
                            database.c.execute("DELETE FROM activities WHERE id=%s AND username=%s", (rid, USER))
                            database.conn.commit()
                            invalidate_activities_cache(USER)
                            st.session_state[f"confirm_daily_del_{rid}"] = False
                            st.rerun()
                    with nc:
                        if st.button("❌ No", key=f"no_daily_del_{rid}", use_container_width=True):
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
                    if "wu_raw" in st.session_state:
                        del st.session_state["wu_raw"]
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
                    if "sl_raw" in st.session_state:
                        del st.session_state["sl_raw"]
                    import time; time.sleep(1); st.rerun()
                else: st.warning("Enter sleep time.")
    
    elif selected_tab == "✈️ Log Trip":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%); border: 1.5px solid #f59e0b; border-radius: 14px; padding: 18px 20px 10px 20px; margin-bottom: 18px;">
            <div style="font-size:17px; font-weight:700; color:#fbbf24; margin-bottom:4px;">✈️ Log Trip</div>
            <div style="font-size:13px; color:#94a3b8;">Log multi-day trips with date range, transport, cost, and study details. Each trip is saved as a single entry.</div>
        </div>
        """, unsafe_allow_html=True)

        # ── TRIP ENTRY FORM ──
        _trip_travel_modes = ["✈️ Flight", "🚂 Railway", "🚗 Other"]
        _trip_tab_entry, _trip_tab_study = st.tabs(["🚗 Trip Details", "📚 Study During Trip"])

        # Initialize destination count in session state
        if "lt_dest_count" not in st.session_state:
            st.session_state.lt_dest_count = 1

        with _trip_tab_entry:
            _tc1, _tc2 = st.columns(2)
            with _tc1:
                _trip_start = st.date_input("📅 Start Date", value=database.get_ist_now().date(), key="lt_start_date")
            with _tc2:
                _trip_end = st.date_input("📅 End Date", value=database.get_ist_now().date(), key="lt_end_date")

            _trip_source = st.text_input("🏠 Source (From)", placeholder="e.g. Delhi, Patna", key="lt_source")

            # Dynamic destinations
            st.markdown("**📍 Destinations**")
            _trip_dests = []
            for _di in range(st.session_state.lt_dest_count):
                _d_val = st.text_input(
                    f"Destination {_di + 1}" if st.session_state.lt_dest_count > 1 else "Destination",
                    placeholder="e.g. Katihar, Banaras",
                    key=f"lt_dest_{_di}",
                    label_visibility="collapsed" if _di > 0 else "visible"
                )
                if _d_val and _d_val.strip():
                    _trip_dests.append(_d_val.strip())

            _add_col, _rem_col = st.columns([1, 1])
            with _add_col:
                if st.button("➕ Add Destination", key="lt_add_dest", use_container_width=True):
                    st.session_state.lt_dest_count += 1
                    st.rerun()
            with _rem_col:
                if st.session_state.lt_dest_count > 1:
                    if st.button("➖ Remove", key="lt_rem_dest", use_container_width=True):
                        # Clear the last destination key
                        _last_key = f"lt_dest_{st.session_state.lt_dest_count - 1}"
                        if _last_key in st.session_state:
                            del st.session_state[_last_key]
                        st.session_state.lt_dest_count -= 1
                        st.rerun()

            _trip_mode = st.selectbox("🚗 Transport Mode", _trip_travel_modes, index=2, key="lt_mode")
            _trip_cost = st.number_input("💰 Total Cost (₹)", min_value=0.0, step=100.0, key="lt_cost")
            _trip_desc = st.text_input("📝 Description (Optional)", placeholder="e.g. Family trip, solo trip", key="lt_desc")

        with _trip_tab_study:
            st.caption("Track chapters completed during this trip:")
            _lt_all_subjs = get_user_subjects(USER)
            _lt_selected_subjs = st.multiselect("Subjects Studied", _lt_all_subjs, key="lt_study_subjs")
            _lt_study_entries = []
            for _lt_subj in _lt_selected_subjs:
                _lt_ch_input = st.text_input(f"Chapters for {_lt_subj}", placeholder="e.g. Chapter 1, 2", key=f"lt_study_ch_{_lt_subj}")
                if _lt_ch_input and _lt_ch_input.strip():
                    _lt_study_entries.append(f"{_lt_subj} ({_lt_ch_input.strip()})")

        # Submit button
        if st.button("💾 Save Trip", key="lt_save_trip", use_container_width=True, type="primary"):
            if not _trip_dests:
                st.warning("Please enter at least one destination.")
            elif _trip_end < _trip_start:
                st.warning("End date cannot be before start date.")
            else:
                _num_trip_days = (_trip_end - _trip_start).days + 1
                # Build chapter value: "Source → Dest1, Dest2" or just "Dest1, Dest2"
                _dest_str = " → ".join(_trip_dests) if len(_trip_dests) > 1 else _trip_dests[0]
                if _trip_source and _trip_source.strip():
                    _chapter_val = f"{_trip_source.strip()} → {_dest_str}"
                else:
                    _chapter_val = _dest_str
                if _lt_study_entries:
                    _chapter_val += " | Studied: " + ", ".join(_lt_study_entries)

                # Encode end_date in description as prefix: "END:YYYY-MM-DD" or "END:YYYY-MM-DD | user desc"
                _desc_val = f"END:{str(_trip_end)}"
                if _trip_desc and _trip_desc.strip():
                    _desc_val += f" | {_trip_desc.strip()}"

                # Store as a SINGLE entry: date=start_date, duration=num_days, amount=cost
                conn = database.conn
                c = database.c
                c.execute(
                    "INSERT INTO activities (date, type, subject, chapter, duration, amount, username, start_time, description, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(_trip_start), 'Travelling', _trip_mode, _chapter_val, float(_num_trip_days), float(_trip_cost), USER, '', _desc_val, 'Completed')
                )
                conn.commit()
                invalidate_activities_cache(USER)
                # Reset destination count
                st.session_state.lt_dest_count = 1
                st.toast(f"✅ Trip to {_dest_str} saved! ({_num_trip_days} days)", icon="✅")
                import time; time.sleep(1); st.rerun()

        st.divider()

        # ── PAST TRIPS DISPLAY ──
        st.markdown("""
        <div style="font-size:17px; font-weight:700; color:#fbbf24; margin-bottom:12px;">🗺️ Past Trips</div>
        """, unsafe_allow_html=True)

        _trip_df = read_sql(
            "SELECT id, date, subject, chapter, duration, amount, description FROM activities WHERE username=%s AND type='Travelling' ORDER BY date DESC",
            (USER,)
        )

        if _trip_df.empty:
            st.info("No trips logged yet. Fill in the form above and click Save Trip! 🗺️")
        else:
            import re as _re

            def _extract_dest(ch):
                if not ch or str(ch).strip().lower() in ('none', 'nan', 'null'): return ''
                s = str(ch)
                if ' | Studied: ' in s: return s.split(' | Studied: ')[0].strip()
                return s.strip()

            def _extract_study_info(ch):
                if not ch or ' | Studied: ' not in str(ch): return ''
                return str(ch).split(' | Studied: ')[1].strip()

            def _parse_end_date(desc):
                """Extract end date from description with format END:YYYY-MM-DD ..."""
                if not desc or not str(desc).startswith('END:'):
                    return None
                try:
                    end_part = str(desc).split('|')[0].replace('END:', '').strip()
                    return pd.to_datetime(end_part)
                except: return None

            def _parse_user_desc(desc):
                """Extract user description (after END:date | )"""
                if not desc: return ''
                s = str(desc)
                if s.startswith('END:') and '|' in s:
                    return s.split('|', 1)[1].strip()
                if not s.startswith('END:'):
                    return s.strip() if s.strip().lower() not in ('none', 'nan', 'null') else ''
                return ''

            # Build trip list — each row is already a single trip entry (new format)
            # or an old day-by-day entry (legacy). Group legacy entries by consecutive dest.
            _trip_df['dest'] = _trip_df['chapter'].apply(_extract_dest)
            _trip_df['study_info'] = _trip_df['chapter'].apply(_extract_study_info)
            _trip_df['end_date_parsed'] = _trip_df['description'].apply(_parse_end_date)
            _trip_df['user_desc'] = _trip_df['description'].apply(_parse_user_desc)
            _trip_df['date_parsed'] = pd.to_datetime(_trip_df['date'])

            # Separate new-format (has END: prefix) and legacy entries
            _new_fmt = _trip_df[_trip_df['description'].apply(lambda x: str(x).startswith('END:') if x else False)].copy()
            _legacy = _trip_df[~_trip_df['description'].apply(lambda x: str(x).startswith('END:') if x else False)].copy()

            trips = []

            # New format trips: each row is one trip
            for _, row in _new_fmt.iterrows():
                _end = row['end_date_parsed'] if row['end_date_parsed'] is not None else row['date_parsed']
                _num_days = int(float(row['duration'])) if row['duration'] and float(row['duration']) >= 1 else ((_end - row['date_parsed']).days + 1)
                trips.append({
                    'id': int(row['id']),
                    'dest': row['dest'] or 'Unknown',
                    'start_date': row['date_parsed'],
                    'end_date': _end,
                    'num_days': _num_days,
                    'total_cost': float(row['amount'] or 0),
                    'transports': [row['subject']] if row['subject'] else [],
                    'study_str': row['study_info'],
                    'desc_str': row['user_desc'],
                    'is_new_fmt': True,
                })

            # Legacy format: group consecutive days with same destination
            if not _legacy.empty:
                _legacy = _legacy.sort_values('date_parsed').reset_index(drop=True)
                _cur = None
                for _, row in _legacy.iterrows():
                    dest = row['dest']
                    d = row['date_parsed']
                    transport = row['subject'] or ''
                    amt = float(row['amount'] or 0)
                    study = row['study_info']
                    desc = row['user_desc']

                    if _cur and _cur['dest'] == dest and (d - _cur['end_date']).days <= 1:
                        _cur['end_date'] = d
                        _cur['total_cost'] += amt
                        _cur['num_days'] += 1
                        if transport and transport not in _cur['transports']: _cur['transports'].append(transport)
                        if study and study not in _cur['study_entries']: _cur['study_entries'].append(study)
                        if desc and desc not in _cur['desc_entries']: _cur['desc_entries'].append(desc)
                    else:
                        if _cur:
                            trips.append({
                                'id': None, 'dest': _cur['dest'], 'start_date': _cur['start_date'],
                                'end_date': _cur['end_date'], 'num_days': _cur['num_days'],
                                'total_cost': _cur['total_cost'], 'transports': _cur['transports'],
                                'study_str': '; '.join(_cur['study_entries']),
                                'desc_str': ' | '.join(_cur['desc_entries']),
                                'is_new_fmt': False,
                            })
                        _cur = {
                            'dest': dest, 'start_date': d, 'end_date': d, 'num_days': 1,
                            'total_cost': amt, 'transports': [transport] if transport else [],
                            'study_entries': [study] if study else [],
                            'desc_entries': [desc] if desc else [],
                        }
                if _cur:
                    trips.append({
                        'id': None, 'dest': _cur['dest'], 'start_date': _cur['start_date'],
                        'end_date': _cur['end_date'], 'num_days': _cur['num_days'],
                        'total_cost': _cur['total_cost'], 'transports': _cur['transports'],
                        'study_str': '; '.join(_cur['study_entries']),
                        'desc_str': ' | '.join(_cur['desc_entries']),
                        'is_new_fmt': False,
                    })

            # Sort by start date descending
            trips.sort(key=lambda t: t['start_date'], reverse=True)

            # Summary stats
            st.markdown(f"""<div style="display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
                <div style="background:#1e293b; padding:10px 18px; border-radius:10px; border:1px solid #334155;">
                    <span style="color:#94a3b8; font-size:12px;">Total Trips</span><br>
                    <span style="color:#fbbf24; font-size:22px; font-weight:700;">{len(trips)}</span>
                </div>
                <div style="background:#1e293b; padding:10px 18px; border-radius:10px; border:1px solid #334155;">
                    <span style="color:#94a3b8; font-size:12px;">Total Days Travelled</span><br>
                    <span style="color:#38bdf8; font-size:22px; font-weight:700;">{sum(t['num_days'] for t in trips)}</span>
                </div>
                <div style="background:#1e293b; padding:10px 18px; border-radius:10px; border:1px solid #334155;">
                    <span style="color:#94a3b8; font-size:12px;">Total Spent</span><br>
                    <span style="color:#22c55e; font-size:22px; font-weight:700;">₹{sum(t['total_cost'] for t in trips):,.0f}</span>
                </div>
            </div>""", unsafe_allow_html=True)

            # Render trip cards
            for idx, trip in enumerate(trips):
                _trip_num = len(trips) - idx
                _start = trip['start_date']
                _end = trip['end_date']
                _num_days = trip['num_days']
                _dest = trip['dest']

                _months = _num_days // 30
                _remaining_days = _num_days % 30
                if _months > 0 and _remaining_days > 0:
                    _dur_str = f"{_months} month{'s' if _months > 1 else ''} {_remaining_days} day{'s' if _remaining_days != 1 else ''}"
                elif _months > 0:
                    _dur_str = f"{_months} month{'s' if _months > 1 else ''}"
                else:
                    _dur_str = f"{_num_days} day{'s' if _num_days != 1 else ''}"

                _start_str = _start.strftime('%d %b %Y')
                _end_str = _end.strftime('%d %b %Y')
                _date_range = f"{_start_str} → {_end_str}" if _start_str != _end_str else _start_str

                _transport_str = ', '.join(trip['transports']) if trip['transports'] else '—'
                _cost_str = f"₹{trip['total_cost']:,.0f}" if trip['total_cost'] > 0 else '—'
                _study_str = trip.get('study_str', '')
                _desc_str = trip.get('desc_str', '')

                _study_html = ''
                if _study_str:
                    _study_html = f"""<div style="margin-top:8px; padding:8px 12px; background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3); border-radius:8px;">
<span style="color:#a78bfa; font-size:11px; font-weight:700;">📚 STUDY DURING TRIP</span><br>
<span style="color:#e2e8f0; font-size:13px;">{_study_str}</span>
</div>"""

                _desc_html = ''
                if _desc_str:
                    _desc_html = f"""
        <div style="background:rgba(255,255,255,0.05); padding:10px 14px; border-radius:10px;">
            <div style="color:#94a3b8; font-size:11px; font-weight:600;">👥 COMPANION</div>
            <div style="color:#e2e8f0; font-size:14px; font-weight:700; margin-top:2px;">{_desc_str}</div>
        </div>"""

                # Left-align to prevent Markdown from rendering it as an indented code block
                st.markdown(f"""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #334155; border-left: 4px solid #fbbf24; border-radius: 14px; padding: 18px 22px; margin-bottom: 14px;">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
        <div>
            <div style="font-size:20px; font-weight:800; color:#fbbf24; margin-bottom:4px;">
                <span style="color:#64748b; font-size:16px;">#{_trip_num}</span> 📍 {_dest}
            </div>
            <div style="font-size:13px; color:#94a3b8;">{_date_range}</div>
        </div>
        <div style="background:rgba(251,191,36,0.15); padding:6px 14px; border-radius:20px; border:1px solid rgba(251,191,36,0.3);">
            <span style="color:#fbbf24; font-size:14px; font-weight:700;">{_dur_str}</span>
        </div>
    </div>
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin-top:14px;">
        <div style="background:rgba(255,255,255,0.05); padding:10px 14px; border-radius:10px;">
            <div style="color:#94a3b8; font-size:11px; font-weight:600;">🚗 TRANSPORT</div>
            <div style="color:#e2e8f0; font-size:14px; font-weight:700; margin-top:2px;">{_transport_str}</div>
        </div>
        <div style="background:rgba(255,255,255,0.05); padding:10px 14px; border-radius:10px;">
            <div style="color:#94a3b8; font-size:11px; font-weight:600;">💰 COST</div>
            <div style="color:#22c55e; font-size:14px; font-weight:700; margin-top:2px;">{_cost_str}</div>
        </div>
        <div style="background:rgba(255,255,255,0.05); padding:10px 14px; border-radius:10px;">
            <div style="color:#94a3b8; font-size:11px; font-weight:600;">📅 DAYS</div>
            <div style="color:#fbbf24; font-size:14px; font-weight:700; margin-top:2px;">{_num_days}</div>
        </div>
        {_desc_html}
    </div>
    {_study_html}
</div>
""", unsafe_allow_html=True)

                # Delete button for new-format trips (single entry)
                if trip.get('is_new_fmt') and trip.get('id'):
                    _tid = trip['id']
                    if st.button(f"🗑️ Delete Trip", key=f"del_trip_{_tid}"):
                        st.session_state[f"confirm_trip_del_{_tid}"] = True
                    if st.session_state.get(f"confirm_trip_del_{_tid}", False):
                        st.warning("Delete this trip?", icon="⚠️")
                        _yc, _nc = st.columns([1, 1])
                        with _yc:
                            if st.button("✅ Yes", key=f"yes_trip_del_{_tid}", use_container_width=True):
                                database.c.execute("DELETE FROM activities WHERE id=%s AND username=%s", (_tid, USER))
                                database.conn.commit()
                                invalidate_activities_cache(USER)
                                st.session_state[f"confirm_trip_del_{_tid}"] = False
                                st.rerun()
                        with _nc:
                            if st.button("❌ No", key=f"no_trip_del_{_tid}", use_container_width=True):
                                st.session_state[f"confirm_trip_del_{_tid}"] = False
                                st.rerun()


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
    
    # ── SMART WORK TIPS (Daily Entry Page) ── Lazy-loaded only when expander is opened
    with st.expander("⚡ Smart Work Tips & UPSC Strategies", expanded=False):
        if st.button("🔄 Load Tips", key="de_load_tips") or st.session_state.get("de_tips_loaded"):
            st.session_state["de_tips_loaded"] = True
            _de_df_all = read_sql("SELECT type, subject, duration FROM activities WHERE username=%s", (USER,))
            if not _de_df_all.empty:
                _de_prod = _de_df_all[_de_df_all['type'].isin(PRODUCTIVE_TYPES)]['duration'].sum()
                _de_waste = _de_df_all[~_de_df_all['type'].isin(PRODUCTIVE_TYPES + ESSENTIAL_TYPES + NEUTRAL_TYPES)]['duration'].sum()
                _de_ess = _de_df_all[_de_df_all['type'].isin(ESSENTIAL_TYPES)]['duration'].sum()
                _de_tips = generate_smart_work_tips(
                    prod_hours=_de_prod, waste_hours=_de_waste, essential_hours=_de_ess,
                    study_streak=streak(_de_df_all), focus_pct=focus_score(_de_df_all),
                    subject_count=len(_de_df_all[_de_df_all['type'].isin(PRODUCTIVE_TYPES)]['subject'].unique()),
                    productivity_pct=0, context="general"
                )
                st.markdown(render_smart_work_section(_de_tips, max_tips=12), unsafe_allow_html=True)
            else:
                st.info("No activity data yet. Log some activities to get personalized tips!")
        else:
            st.caption("Click **Load Tips** above to generate personalized UPSC study tips based on your activity data.")

    # ---------------- CALENDAR ----------------

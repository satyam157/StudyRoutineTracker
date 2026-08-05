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
    import database
    get_esu_responses = database.get_esu_responses
    save_esu_response = database.save_esu_response
    delete_esu_response = database.delete_esu_response
    get_ist_now = database.get_ist_now
    
    conn = database.conn
    c = database.c
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
    df_all = get_activities_df(USER)
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
        prod_df = df_all[df_all['type'].isin(['Study', 'Study during trip', 'Revision', 'Book Reading', 'Answer Writing', 'Practice', 'Test'])]
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
                import database
                get_ist_now = database.get_ist_now
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

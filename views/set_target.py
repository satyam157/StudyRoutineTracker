import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
import plotly.graph_objects as go
import plotly.express as px
from utils import *
from logic import *
import database
from smart_tips import generate_smart_work_tips, render_smart_work_section
import proposal

def render(USER, USER_CONFIG):
    conn = database.conn
    c = database.c
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

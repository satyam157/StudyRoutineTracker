import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
from utils import *
from logic import *
import database
import plotly.graph_objects as go
from smart_tips import generate_smart_work_tips, render_smart_work_section
import proposal

def render(USER, USER_CONFIG):
    import plotly.graph_objects as go
    conn = database.conn
    c = database.c
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
            
            hours_taken = format_duration(sub_acts['duration'].sum())
            days_taken  = sub_acts['date'].nunique()
            _ch_active  = sub_acts[sub_acts['clean_ch'] != ""]
            max_item    = _ch_active.groupby('clean_ch')['duration'].sum().idxmax() if not _ch_active.empty else "N/A"
    
            label  = f"{format_duration(done)}" if goal_unit == _HOURS_TYPE else str(done)
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
                mc4.metric("Total Time", hours_taken)
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
                st.metric("⏱️ Total Productive Hours", format_duration(total_study_hours))
            with analysis_cols[2]:
                avg_hours = total_study_hours / num_subjects if num_subjects > 0 else 0
                st.metric("📊 Average per Subject", format_duration(avg_hours))
            
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
                    _t_html = (
                        f'<div style="background:rgba(30, 41, 59, 0.6);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);'
                        f'border:1px solid rgba(255, 255, 255, 0.08);border-radius:16px;padding:20px 24px;margin-bottom:16px;'
                        f'border-left:5px solid {tech["color"]};transition:all 0.3s ease;box-shadow:0 4px 15px rgba(0,0,0,0.1);"'
                        f' onmouseover="this.style.transform=\'translateY(-3px) scale(1.01)\';this.style.boxShadow=\'0 8px 25px rgba(0,0,0,0.25)\';this.style.background=\'rgba(30, 41, 59, 0.85)\'"'
                        f' onmouseout="this.style.transform=\'none\';this.style.boxShadow=\'0 4px 15px rgba(0,0,0,0.1)\';this.style.background=\'rgba(30, 41, 59, 0.6)\'">'
                        f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">'
                        f'<div style="font-size:24px;background:rgba(255,255,255,0.05);padding:10px;border-radius:12px;display:flex;align-items:center;justify-content:center;">{tech["icon"]}</div>'
                        f'<span style="font-size:18px;font-weight:800;color:#f8fafc;letter-spacing:0.5px;">{tech["name"]}</span></div>'
                        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:13.5px;color:#cbd5e1;line-height:1.6;">'
                        f'<div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.03);"><div style="color:{tech["color"]};font-weight:800;font-size:11px;text-transform:uppercase;margin-bottom:6px;letter-spacing:1px;">\U0001f4cc What It Is</div>{_md(tech["what"])}</div>'
                        f'<div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.03);"><div style="color:{tech["color"]};font-weight:800;font-size:11px;text-transform:uppercase;margin-bottom:6px;letter-spacing:1px;">\U0001f527 How to Apply</div>{_md(tech["how"])}</div>'
                        f'<div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.03);"><div style="color:{tech["color"]};font-weight:800;font-size:11px;text-transform:uppercase;margin-bottom:6px;letter-spacing:1px;">\u23f0 When to Use</div>{_md(tech["when"])}</div>'
                        f'<div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.03);"><div style="color:{tech["color"]};font-weight:800;font-size:11px;text-transform:uppercase;margin-bottom:6px;letter-spacing:1px;">\U0001f4da Best For Subjects</div>{_md(tech["subjects"])}</div>'
                        f'</div><div style="margin-top:16px;padding:12px 16px;background:rgba(139,92,246,0.1);border-radius:10px;border:1px solid rgba(139,92,246,0.2);font-size:13px;color:#c4b5fd;">\U0001f4a1 <strong>Impact:</strong> {_md(tech["impact"])}</div></div>'
                    )
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
                    _m_html = (
                        f'<div style="background:rgba(30, 41, 59, 0.6);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);'
                        f'border:1px solid rgba(255, 255, 255, 0.08);border-radius:16px;padding:20px 24px;margin-bottom:16px;'
                        f'border-left:5px solid {method["color"]};transition:all 0.3s ease;box-shadow:0 4px 15px rgba(0,0,0,0.1);"'
                        f' onmouseover="this.style.transform=\'translateY(-3px) scale(1.01)\';this.style.boxShadow=\'0 8px 25px rgba(0,0,0,0.25)\';this.style.background=\'rgba(30, 41, 59, 0.85)\'"'
                        f' onmouseout="this.style.transform=\'none\';this.style.boxShadow=\'0 4px 15px rgba(0,0,0,0.1)\';this.style.background=\'rgba(30, 41, 59, 0.6)\'">'
                        f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">'
                        f'<div style="font-size:24px;background:rgba(255,255,255,0.05);padding:10px;border-radius:12px;display:flex;align-items:center;justify-content:center;">{method["icon"]}</div>'
                        f'<span style="font-size:18px;font-weight:800;color:#f8fafc;letter-spacing:0.5px;">{method["name"]}</span></div>'
                        f'<div style="display:grid;grid-template-columns:1fr;gap:12px;font-size:14px;color:#cbd5e1;line-height:1.7;">'
                        f'<div><span style="color:{method["color"]};font-weight:800;text-transform:uppercase;font-size:11px;letter-spacing:1px;margin-right:8px;background:rgba(255,255,255,0.05);padding:4px 8px;border-radius:6px;">\U0001f4cc What It Is</span> {_md(method["what"])}</div>'
                        f'<div><span style="color:{method["color"]};font-weight:800;text-transform:uppercase;font-size:11px;letter-spacing:1px;margin-right:8px;background:rgba(255,255,255,0.05);padding:4px 8px;border-radius:6px;">\U0001f4c5 Routine</span> {_md(method["routine"])}</div>'
                        f'<div><span style="color:{method["color"]};font-weight:800;text-transform:uppercase;font-size:11px;letter-spacing:1px;margin-right:8px;background:rgba(255,255,255,0.05);padding:4px 8px;border-radius:6px;">\U0001f527 How to Apply</span> {_md(method["apply"])}</div>'
                        f'</div></div>'
                    )
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

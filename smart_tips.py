"""
Smart Work Tips Engine — Expanded with UPSC subject-wise tips,
exam paper-attempting strategies, pagination & scroll support.
"""
import re as _re_sw
import random

# ══════════════════════════════════════════════════════════════════
#  TIP CATEGORIES
# ══════════════════════════════════════════════════════════════════

CORE_TECHNIQUES = [
    {"icon": "🍅", "category": "Pomodoro Technique",
     "tip": "**25 min focus → 5 min break → repeat 4x → 30 min long break.** Best for subjects you find boring. Use a physical timer to avoid phone distraction."},
    {"icon": "🧠", "category": "Active Recall",
     "tip": "**Close the book and write everything you remember.** Then check what you missed. This builds 3x stronger memory than passive reading."},
    {"icon": "📆", "category": "Spaced Repetition",
     "tip": "**Revise on Day 1 → Day 3 → Day 7 → Day 21 → Day 45.** Mark revision dates in your calendar. Without this, you'll forget 80% within a week."},
    {"icon": "🎯", "category": "Eat The Frog",
     "tip": "**Do your hardest/most boring subject FIRST in the morning** when willpower is highest. Save easier subjects for evening when energy dips."},
    {"icon": "📝", "category": "Feynman Technique",
     "tip": "**Explain the topic as if teaching a 10-year-old.** Where you struggle to simplify = where you don't truly understand. Go back and study those gaps."},
    {"icon": "🔄", "category": "Interleaving Practice",
     "tip": "**Mix different subjects/topics in one session** instead of blocking a single subject. This forces your brain to discriminate between concepts, boosting long-term retention by 25%."},
    {"icon": "🗺️", "category": "Mind Mapping",
     "tip": "**Create visual mind maps for complex topics.** Central idea → branches → sub-branches. Especially powerful for History timelines, Polity article connections, and Geography interlinking."},
    {"icon": "📖", "category": "SQ3R Method",
     "tip": "**Survey → Question → Read → Recite → Review.** Before reading a chapter, skim headings first, form questions, then read to answer them. Doubles comprehension vs passive reading."},
]

SUBJECT_TIPS = {
    "polity": [
        {"icon": "⚖️", "category": "Polity — Articles & Amendments",
         "tip": "**Group Articles by theme, don't memorize sequentially.** FR (12-35), DPSP (36-51), FD (51A). Make comparison tables: Lok Sabha vs Rajya Sabha, President vs Governor. Focus on Amendments: 1st, 42nd, 44th, 73rd, 74th, 86th, 91st, 101st."},
        {"icon": "🏛️", "category": "Polity — Landmark Judgments",
         "tip": "**Master 15 landmark cases for 80% of judiciary questions.** Kesavananda Bharati (basic structure), Minerva Mills (FR vs DPSP), Maneka Gandhi (Art 21), S.R. Bommai (Art 356), Vishaka (sexual harassment). Link each case to the Article it interprets."},
        {"icon": "📊", "category": "Polity — Comparison Tables",
         "tip": "**Make one-page comparison sheets:** Money Bill vs Finance Bill, Ordinary Bill vs Constitutional Amendment, National vs State Emergency. These tables alone can solve 3-4 Prelims questions."},
    ],
    "economy": [
        {"icon": "💰", "category": "Economy — RBI & Monetary Policy",
         "tip": "**Master RBI tools as a flowchart:** Repo↔Reverse Repo, CRR↔SLR, OMO, LAF, MSF. Know the CURRENT rates. Understand transmission mechanism: RBI changes rate → banks adjust → credit flow → inflation/GDP impact."},
        {"icon": "📉", "category": "Economy — Budget & Fiscal",
         "tip": "**Learn Budget terminology cold:** Revenue vs Capital (receipts & expenditure), Fiscal/Revenue/Primary deficit formulas, FRBM targets. Read the latest Budget highlights — 2-3 questions guaranteed from recent Budget."},
        {"icon": "🏦", "category": "Economy — Banking System",
         "tip": "**Differentiate clearly:** Commercial vs Cooperative, Payment Banks vs SFBs vs Universal Banks, NBFC regulation. Know IBC process for NPAs. Digital banking: UPI, CBDC, Account Aggregator framework."},
    ],
    "geography": [
        {"icon": "🌍", "category": "Geography — Map Work Daily",
         "tip": "**Spend 15 min daily on map marking.** Rivers with tributaries, mountain passes, national parks, mineral belts. Use blank India/World maps. 4-5 Prelims questions are directly map-based every year."},
        {"icon": "🌧️", "category": "Geography — Climatology",
         "tip": "**Indian Monsoon is the highest-frequency topic.** Master: SW & NE monsoon mechanism, jet streams, ENSO/IOD, western disturbances, rainfall distribution. Draw diagrams — they cement understanding better than text."},
        {"icon": "🏔️", "category": "Geography — Physical Features",
         "tip": "**Learn Himalayas as 3 parallel ranges** with passes. Know all major rivers (origin, tributaries, dams, disputes). Peninsular plateau divisions. Coastal plains East vs West differences. Use NCERT maps as base."},
    ],
    "history": [
        {"icon": "📜", "category": "History — Freedom Struggle Priority",
         "tip": "**Modern History = 60% of all history questions.** Focus: 1857 Revolt causes/impact, Congress phases (Moderate→Extremist→Gandhian), all Gandhian movements (NCM/CDM/QIM) with dates, Subhas Bose & INA, Partition."},
        {"icon": "🏛️", "category": "History — Ancient & Medieval",
         "tip": "**Be selective:** Buddhism & Jainism (comparison table), Maurya & Gupta empires, Bhakti & Sufi movements are repeatedly asked. Skip deep dynastic details. For Medieval: focus on administration systems, not battles."},
        {"icon": "📅", "category": "History — Timeline Charts",
         "tip": "**Create a master timeline wall chart:** 1757 → 1857 → 1885 → 1905 → 1919 → 1920 → 1930 → 1942 → 1947. Pin key events, acts, and movements to each year. Visual timelines prevent date confusion in MCQs."},
    ],
    "environment": [
        {"icon": "🌿", "category": "Environment — Running Lists",
         "tip": "**Maintain 4 running lists (update monthly):** 1) All Ramsar sites India 2) Tiger Reserves 3) Biosphere Reserves 4) Recent species in news. These lists alone can crack 3-4 Prelims questions."},
        {"icon": "🌡️", "category": "Environment — Climate Agreements",
         "tip": "**Master the climate architecture:** UNFCCC → Kyoto → Paris Agreement (NDCs, 1.5°C vs 2°C). Know India's targets: Net Zero 2070, 500 GW non-fossil by 2030, 50% energy from renewables. IPCC AR6 key findings."},
        {"icon": "🦁", "category": "Environment — Biodiversity",
         "tip": "**India's 4 biodiversity hotspots** (Himalaya, Western Ghats, Indo-Burma, Sundaland). IUCN categories (CR, EN, VU). Key acts: Wildlife Protection 1972, Forest Conservation, Biodiversity Act 2002. CBD vs CITES vs CMS differences."},
    ],
    "art_culture": [
        {"icon": "🎨", "category": "Art & Culture — Visual Learning",
         "tip": "**Use images, not just text.** Watch 2-min videos of each classical dance form. See actual paintings (Ajanta, Miniature schools). Temple architecture: draw Nagara vs Dravida vs Vesara yourself. Visual memory is 6x stronger for Art & Culture."},
        {"icon": "🗿", "category": "Art & Culture — State-wise Mapping",
         "tip": "**Create a state-wise matrix:** Each state → its classical dance, folk dance, painting style, handicraft, festival, GI tag. This single sheet covers 60% of Art & Culture Prelims questions."},
    ],
    "science_tech": [
        {"icon": "🚀", "category": "S&T — ISRO Mission Tracker",
         "tip": "**Know ALL recent ISRO missions:** Chandrayaan-3, Gaganyaan, Aditya-L1, NISAR. For each: objective, orbit type, key instruments. Compare PSLV vs GSLV vs SSLV. Space Policy 2023 provisions."},
        {"icon": "🧬", "category": "S&T — Emerging Tech Basics",
         "tip": "**Understand applications, not deep theory:** AI/ML (what it does, not algorithms), CRISPR (gene editing applications), Quantum Computing (why it matters), Blockchain (beyond crypto). Link each to a government initiative."},
        {"icon": "🛡️", "category": "S&T — Defence Technology",
         "tip": "**Master India's indigenous defence:** Missile families (Agni 1-5, BrahMos, Akash), LCA Tejas, INS Vikrant, Arjun MBT. Know DRDO vs HAL vs BEL roles. Defence corridors (UP & TN)."},
    ],
    "ethics": [
        {"icon": "🧭", "category": "Ethics — Case Study Framework",
         "tip": "**Use DECIDE framework for every case study:** Define problem → Examine values → Consider stakeholders → Identify options → Decide with justification → Evaluate outcome. Practice 2 cases/week. Case studies = 120/250 marks in GS4."},
        {"icon": "💭", "category": "Ethics — Thinkers Quick Reference",
         "tip": "**Master 8 thinkers with one-line theories:** Gandhi (trusteeship), Ambedkar (social justice), Kautilya (statecraft), Aristotle (virtue), Kant (duty/categorical imperative), Bentham (greatest good), Rawls (veil of ignorance), Confucius (ren/li)."},
    ],
    "international_relations": [
        {"icon": "🌐", "category": "IR — Bilateral Matrix",
         "tip": "**Make a 1-page summary per major relationship:** India-China (LAC, trade, Tibet), India-US (QUAD, defence), India-Russia (S-400, energy), India-Japan. For each: key agreements, irritants, recent developments. IR = 70% current affairs."},
        {"icon": "🏢", "category": "IR — International Organizations",
         "tip": "**Know structure & India's role in:** UN (UNSC reform demand), WTO (disputes), IMF/WB (voting share), G20 (India presidency outcomes), QUAD, BRICS+, SCO, ASEAN, BIMSTEC. Compare: SAARC vs BIMSTEC, QUAD vs AUKUS."},
    ],
    "internal_security": [
        {"icon": "🔒", "category": "Internal Security — Laws & Bodies",
         "tip": "**Know key security laws:** UAPA, NIA Act, AFSPA (where applied), PMLA, IT Act. Security bodies: NIA vs NSG vs MARCOS vs COBRA roles. Border forces: BSF, ITBP, SSB, Assam Rifles — which border, which force."},
    ],
    "current_affairs": [
        {"icon": "🗞️", "category": "Current Affairs — Daily Routine",
         "tip": "**30 min daily: The Hindu editorial → national → international.** Don't just read — link every news item to a GS paper. Make 1-line notes. Monthly compilation > daily note-making. Topic-wise notes, NOT date-wise."},
        {"icon": "📋", "category": "Current Affairs — Scheme Tracker",
         "tip": "**Maintain a running scheme tracker:** For each major scheme: launch year, ministry, budget, target, latest data. Government schemes = 4-5 guaranteed Prelims questions. Update monthly from PIB."},
    ],
    "sociology": [
        {"icon": "📚", "category": "Sociology Optional — Thinker Mastery",
         "tip": "**Master 6 core thinkers deeply:** Marx (class/alienation), Durkheim (social facts/suicide), Weber (social action/bureaucracy), Mead (self/identity), Parsons (AGIL), Merton (manifest/latent). They cover 30% of Paper I."},
    ],
}

EXAM_STRATEGY_TIPS = [
    {"icon": "📋", "category": "Prelims — Paper Attempting",
     "tip": "**First pass (60 min): Attempt all questions you're 90%+ sure of.** Mark answers, don't waste time on doubtful ones. Second pass (40 min): Attempt 60-70% confidence questions using elimination. Third pass (20 min): Educated guesses only if you can eliminate 2 options. Never guess blindly — negative marking kills."},
    {"icon": "⏱️", "category": "Prelims — Time Management",
     "tip": "**100 questions in 120 minutes = 72 seconds per question.** But don't time each question equally. Easy ones: 30-40 sec. Medium: 60-90 sec. Hard: skip initially, return if time permits. Keep a watch on the desk, check every 25 questions."},
    {"icon": "❌", "category": "Prelims — Elimination Technique",
     "tip": "**For every MCQ, eliminate before selecting.** Read all 4 options first. Cross out obviously wrong ones. Between remaining options, look for absolute words ('always', 'never', 'only') — these are usually wrong. UPSC loves 'partially correct' traps."},
    {"icon": "🎯", "category": "Prelims — CSAT Strategy",
     "tip": "**CSAT is qualifying (33%).** Don't over-prepare. Focus: Reading Comprehension (easiest marks), Basic Math (percentages, ratios), Logical Reasoning. Practice 1 CSAT mock/week. RC alone can get you past cutoff if you're good at it."},
    {"icon": "✍️", "category": "Mains — Answer Structure",
     "tip": "**Every Mains answer must follow:** Introduction (2-3 lines, define/contextualize) → Body (points with examples/data, use subheadings) → Conclusion (way forward, balanced view). Use diagrams/flowcharts where possible — they fetch extra marks."},
    {"icon": "📏", "category": "Mains — Word Limit Discipline",
     "tip": "**150-word answers: 8-10 minutes max. 250-word answers: 15 minutes max.** Practice writing within limits. Count words in your handwriting per line (typically 8-10). So 150 words ≈ 15-18 lines. Don't exceed — examiners penalize lengthy, unfocused answers."},
    {"icon": "🔗", "category": "Mains — Interlinking Subjects",
     "tip": "**Cross-reference subjects in answers for higher marks.** Polity question? Add economic impact. Geography question? Link to environment/climate. This shows 'holistic understanding' that UPSC rewards. Example: Article 21 → Environmental protection → NGT → Sustainable Development."},
    {"icon": "📊", "category": "Mains — Data & Examples",
     "tip": "**Every answer needs 2-3 data points or examples.** Census data, NFHS-5, Economic Survey figures, Supreme Court cases, committee recommendations. Generic answers without data score 4-5/12.5. Data-rich answers score 8-10/12.5."},
    {"icon": "🗓️", "category": "Mains — Paper-wise Time Allocation",
     "tip": "**GS paper (250 marks, 3 hours): 20 questions.** Allocate: 10 min per 150-word answer, 15 min per 250-word answer. Keep 10 min buffer for review. Start with your strongest section to build confidence. Don't leave any question unattempted."},
    {"icon": "📝", "category": "Essay — Structure Blueprint",
     "tip": "**Essay (1000-1200 words, 125 marks each):** Intro (hook + thesis) → Dimension 1 (social) → Dimension 2 (economic) → Dimension 3 (political) → Dimension 4 (philosophical/ethical) → Conclusion (vision). Use quotes, data, examples in every dimension. Multi-dimensional essays score 100+."},
]

PRODUCTIVITY_TIPS = [
    {"icon": "📈", "category": "Energy Management",
     "tip": "**Track energy, not just time.** Your brain has 2-3 peak hours/day (usually 9-11 AM). Use these for hardest subjects. Reserve low-energy slots for revision, notes, or current affairs."},
    {"icon": "😴", "category": "Sleep = Memory",
     "tip": "**7-8 hours sleep is non-negotiable.** During deep sleep, your brain consolidates everything studied that day. Cutting sleep to study more actually REDUCES what you retain. Sleep before midnight for best quality."},
    {"icon": "🏃", "category": "Exercise for Focus",
     "tip": "**30 min daily exercise boosts focus by 30%.** Walk, jog, yoga — anything that raises heart rate. Exercise releases BDNF which directly improves learning capacity. Schedule it as non-negotiable."},
    {"icon": "📵", "category": "Digital Detox Blocks",
     "tip": "**Keep phone in another room during study.** Even a visible phone reduces cognitive capacity by 10%. Use app blockers (Forest, Freedom) during study hours. Check phone only during scheduled breaks."},
    {"icon": "🥗", "category": "Brain Fuel",
     "tip": "**Eat for cognition:** Nuts, dark chocolate, berries, eggs for brain function. Avoid heavy carbs before study (causes drowsiness). Stay hydrated — even 2% dehydration impairs concentration by 25%."},
]

TARGET_TIPS = [
    {"icon": "🎯", "category": "Target Acceleration",
     "tip": "**Falling behind? Use 'Sprint Weeks.'** Pick the target closest to deadline, block 4-5h/day for just that subject for 5 days. Intense focused bursts are more effective than slow, scattered effort."},
    {"icon": "✅", "category": "Micro-Goals",
     "tip": "**Break each target into daily micro-goals.** Instead of 'Complete 10 chapters in 30 days,' set 'Finish Chapter 5, pages 45-80 today.' Specific = actionable = achievable."},
    {"icon": "📐", "category": "80/20 Rule for Targets",
     "tip": "**20% of chapters contain 80% of exam questions.** Identify high-PYQ-frequency chapters and complete them FIRST. Use the priority markings in your strategy data to decide what to study and what to skim."},
]


def generate_smart_work_tips(prod_hours=0, waste_hours=0, essential_hours=0,
                              study_streak=0, focus_pct=0, subject_count=0,
                              productivity_pct=0, context="general"):
    """
    Generate contextual smart work tips based on user's actual data.
    Now includes subject-wise UPSC tips, exam strategy, and more categories.
    """
    tips = []

    # ── DATA-DRIVEN TIPS ──
    if waste_hours > 0:
        if waste_hours >= 2:
            tips.append({
                "category": "Rule of Distraction",
                "tip": f"**You have {format_duration(waste_hours)} of waste time.** Use the '2-Minute Rule': if tempted by distraction, tell yourself 'just 2 more minutes of study.' Install app blockers during study hours.",
                "icon": "⏳", "priority": 1})
        elif waste_hours > 1:
            tips.append({
                "category": "Controlled Leisure",
                "tip": f"**{format_duration(waste_hours)} waste is recoverable.** Schedule specific 'guilt-free' leisure slots (e.g., 7-8 PM). Outside those slots, phone stays in another room.",
                "icon": "📱", "priority": 2})

    if focus_pct < 30:
        tips.append({"icon": "🔬", "category": "Deep Work",
            "tip": "**Your deep work sessions (≥2h unbroken) are low.** Try 'Cave Mode': pick one subject, set a 2-hour timer, put phone in airplane mode, and work in complete silence.",
            "priority": 1})
    elif focus_pct > 60:
        tips.append({"icon": "💪", "category": "Deep Work Master",
            "tip": f"**Your focus score is {focus_pct:.0f}% — excellent.** Consider adding interleaving: switch between 2 related subjects within a deep session to strengthen cross-connections.",
            "priority": 3})

    if study_streak == 0:
        tips.append({"icon": "🔥", "category": "Start a Streak",
            "tip": "**Study even 30 minutes today to start a streak.** Consistency > intensity. A 30-day streak of 3h/day beats sporadic 10h marathon sessions.",
            "priority": 1})
    elif study_streak >= 7:
        tips.append({"icon": "🔥", "category": "Streak Power",
            "tip": f"**{study_streak}-day streak! 🔥** Add 'Progressive Overload': increase daily hours by 15 minutes every week. Small increments compound into massive results.",
            "priority": 3})

    if productivity_pct > 0:
        if productivity_pct < 30:
            tips.append({"icon": "📊", "category": "Productivity Boost",
                "tip": f"**{productivity_pct:.0f}% productivity — room for growth.** Use the 'MIT Method': identify 3 Most Important Tasks each morning. Complete those BEFORE anything else.",
                "priority": 1})
        elif productivity_pct > 60:
            tips.append({"icon": "🏆", "category": "High Performer",
                "tip": f"**{productivity_pct:.0f}% productivity — strong!** Optimize quality: for every 2 hours of new learning, spend 30 min on revision. 20% of topics = 80% of exam marks.",
                "priority": 3})

    if essential_hours > 0:
        tips.append({
            "category": "Work + Study Balance",
            "tip": f"**You have {format_duration(essential_hours)} of work/coaching.** Use 'Sandwich Technique': study 1h BEFORE work, 2-3h AFTER. Lunch break = flashcard revision. Commute = podcasts.",
            "icon": "⚖️", "priority": 2})

    if subject_count > 5:
        tips.append({"icon": "🔄", "category": "Subject Rotation",
            "tip": f"**{subject_count} subjects — use a 3-day rotation.** Day 1: 3 subjects (2 hard + 1 easy). Day 2: next 3. Day 3: remaining + revision of Day 1.",
            "priority": 2})

    # ── CONTEXT-SPECIFIC TIPS ──
    if context == "productivity":
        for t in PRODUCTIVITY_TIPS:
            tips.append({**t, "priority": 2})
    elif context == "target":
        for t in TARGET_TIPS:
            tips.append({**t, "priority": 2})
    elif context == "ask_esu":
        tips.append({"icon": "🗞️", "category": "Current Affairs Strategy", "priority": 2,
            "tip": "**30 min daily: The Hindu/Indian Express.** Link every news to a GS paper. Environment → GS3, Policy → GS2. Monthly compilation = revision-ready."})
        tips.append({"icon": "✍️", "category": "Answer Writing", "priority": 2,
            "tip": "**Write 2 answers daily from Day 1.** Structure: Intro (2 lines) → Body (points + examples) → Conclusion (way forward). Get them evaluated weekly."})

    # ── EXAM STRATEGY TIPS (always include a rotating selection) ──
    random.seed(hash(str(prod_hours) + str(waste_hours) + context))
    exam_sample = random.sample(EXAM_STRATEGY_TIPS, min(3, len(EXAM_STRATEGY_TIPS)))
    for t in exam_sample:
        tips.append({**t, "priority": 5})

    # ── SUBJECT-WISE TIPS (rotating selection from all subjects) ──
    all_subj_tips = []
    for subj_key, subj_tips in SUBJECT_TIPS.items():
        all_subj_tips.extend(subj_tips)
    random.shuffle(all_subj_tips)
    for t in all_subj_tips[:4]:
        tips.append({**t, "priority": 6})

    # ── CORE TECHNIQUES ──
    for i, t in enumerate(CORE_TECHNIQUES):
        tips.append({**t, "priority": 7 + i})

    tips.sort(key=lambda x: x.get("priority", 99))
    return tips


def render_smart_work_section(tips, max_tips=6, page_key="sw_page"):
    """
    Returns HTML for rendering smart work tips with scrollable container
    and pagination support. Shows max_tips per page with scroll.
    """
    if not tips:
        return ""

    display_tips = tips[:max(max_tips, len(tips))]

    def _md_to_html(text):
        return _re_sw.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', str(text))

    # Category color mapping
    cat_colors = {
        "Polity": "#f59e0b", "Economy": "#10b981", "Geography": "#3b82f6",
        "History": "#ef4444", "Environment": "#22c55e", "Art": "#a78bfa",
        "Ethics": "#f472b6", "S&T": "#06b6d4", "IR": "#8b5cf6",
        "Security": "#f87171", "Current": "#fbbf24", "Sociology": "#c084fc",
        "Prelims": "#38bdf8", "Mains": "#34d399", "Essay": "#fb923c",
        "CSAT": "#a3e635",
    }

    def _get_border_color(category):
        for key, color in cat_colors.items():
            if key.lower() in category.lower():
                return color
        return "#8b5cf6"

    cards_html = ""
    for t in display_tips:
        tip_html = _md_to_html(t['tip'])
        border = _get_border_color(t['category'])
        cards_html += (
            f'<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);'
            f'border:1px solid #334155;border-radius:14px;padding:16px 20px;margin-bottom:10px;'
            f'border-left:4px solid {border};transition:transform 0.2s,box-shadow 0.2s;"'
            f' onmouseover="this.style.transform=\'translateX(4px)\';this.style.boxShadow=\'0 4px 20px rgba(0,0,0,0.3)\'"'
            f' onmouseout="this.style.transform=\'none\';this.style.boxShadow=\'none\'">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
            f'<span style="font-size:20px;">{t["icon"]}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{border};text-transform:uppercase;'
            f'letter-spacing:0.5px;">{t["category"]}</span></div>'
            f'<div style="font-size:14px;color:#e2e8f0;line-height:1.6;">{tip_html}</div></div>'
        )

    total = len(display_tips)
    counter_html = (
        f'<div style="text-align:center;margin-top:8px;font-size:12px;color:#64748b;">'
        f'Showing {total} tips • Scroll for more</div>'
    )

    html = (
        f'<div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#1e3a5f 100%);'
        f'padding:20px 22px 10px 22px;border-radius:16px;border:1px solid #4f46e5;margin:20px 0;'
        f'box-shadow:0 8px 32px rgba(79,70,229,0.15);">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">'
        f'<span style="font-size:26px;">⚡</span>'
        f'<h3 style="margin:0;color:#e0e7ff;font-weight:800;letter-spacing:-0.3px;">Smart Work Tips</h3>'
        f'<span style="font-size:12px;color:#818cf8;background:rgba(129,140,248,0.15);'
        f'padding:3px 10px;border-radius:20px;font-weight:600;">UPSC Strategy Engine</span></div>'
        f'<div style="max-height:500px;overflow-y:auto;padding-right:6px;'
        f'scrollbar-width:thin;scrollbar-color:#4f46e5 transparent;">'
        f'{cards_html}</div>{counter_html}</div>'
    )
    return html

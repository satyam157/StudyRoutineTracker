import os
import json
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Import strategy data
try:
    from upsc_strategy_data import (
        ALL_SUBJECTS, detect_subjects, get_subject_strategy_text,
        get_subject_summary_text, get_routine_text, DAILY_ROUTINE, 
        WEEKLY_PLAN, MONTHLY_PLAN
    )
except ImportError:
    # Fallback if file doesn't exist yet
    ALL_SUBJECTS = {}
    def detect_subjects(q): return []
    def get_subject_strategy_text(s): return ""
    def get_routine_text(): return ""

# Load from explicit path so it works regardless of working directory
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

# Models for fallback chain
MODELS = [
    ("llama-3.3-70b-versatile", 6000, 0.3),
    ("llama-3.1-70b-versatile", 6000, 0.4),
    ("llama-3.1-8b-instant", 4000, 0.5),
]
ACTIVE_MODEL = MODELS[0][0]

def _get_api_key() -> str:
    """Try os.environ first, then Streamlit secrets as fallback."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    return api_key


def _compress_prompt(prompt: str) -> str:
    """Aggressively compress prompt to save tokens."""
    import re
    # Remove multiple newlines
    prompt = re.sub(r'\n{3,}', '\n\n', prompt)
    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in prompt.split('\n')]
    # Remove decorative separators
    lines = [l for l in lines if not re.match(r'^[─═━\-=*#]{5,}$', l)]
    # Remove empty lines
    lines = [l for l in lines if l]
    return '\n'.join(lines)


def get_ai_insight(prompt: str, model_type: str = "heavy", max_tokens: int = 4000) -> str:
    """Enhanced Groq call with fallback model chain."""
    try:
        from groq import Groq
        
        api_key = _get_api_key()
        if not api_key:
            return "⚠️ AI unavailable: GROQ_API_KEY not found."
        
        client = Groq(api_key=api_key)
        compressed = _compress_prompt(prompt)
        
        last_error = None
        for model_name, model_tokens, temp in MODELS:
            try:
                # Use the requested max_tokens if provided, else use model default
                tokens = max_tokens if max_tokens else model_tokens
                
                res = client.chat.completions.create(
                    messages=[{"role": "user", "content": compressed}],
                    model=model_name,
                    max_tokens=tokens,
                    temperature=temp,
                    timeout=90
                )
                
                if res and res.choices:
                    return res.choices[0].message.content
            except Exception as e:
                last_error = str(e)
                continue
                
        return f"⚠️ AI error: {last_error if last_error else 'All models failed'}"
    
    except ImportError:
        return "⚠️ Groq library not installed."
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"



# ── Target analysis ────────────────────────────────────────────────────────
def analyze_target(target_subject, target_chapters, deadline,
                   days_taken, hours_taken, max_chapter) -> str:
    total_h = float(hours_taken) if hours_taken else 0
    total_ch = int(target_chapters) if target_chapters else 1
    avg_h_per_ch = total_h / max(days_taken, 1)
    prompt = (
        f"You are an elite study strategist. Analyze this target and give ACTIONABLE advice.\n\n"
        f"TARGET DATA:\n"
        f"- Subject: {target_subject}\n"
        f"- Total chapters/units: {target_chapters}\n"
        f"- Deadline: {deadline}\n"
        f"- Days studied so far: {days_taken}\n"
        f"- Total hours invested: {hours_taken}h\n"
        f"- Avg hours/day: {avg_h_per_ch:.1f}h\n"
        f"- Slowest chapter: '{max_chapter}'\n\n"
        f"RESPOND WITH THIS EXACT STRUCTURE (use markdown):\n\n"
        f"## 📊 Progress Verdict\n"
        f"One bold sentence — on track or behind? By how much?\n\n"
        f"## ⚡ Smart Adjustments\n"
        f"| Area | Current | Recommended | Why |\n"
        f"|------|---------|-------------|-----|\n"
        f"(fill 3-4 rows: pace, hours/day, chapter strategy, revision)\n\n"
        f"## 🧠 Smart Work Tips\n"
        f"- 3 specific techniques (Pomodoro timing, active recall, interleaving, etc.)\n"
        f"- Each with HOW to apply it to {target_subject}\n\n"
        f"## 🎯 Action Plan\n"
        f"Numbered list: exactly what to do this week to get back/stay on track.\n"
        f"Be specific — chapter names, hours, methods.\n"
    )
    return get_ai_insight(prompt)


# ── Weak subjects ──────────────────────────────────────────────────────────
def analyze_weak_subjects(subject_hours: dict) -> str:
    subjects_str = ", ".join(
        f"{s}: {h:.1f}h" for s, h in sorted(subject_hours.items(), key=lambda x: x[1])
    )
    total = sum(subject_hours.values())
    prompt = (
        f"You are a smart study strategist. Analyze subject time distribution.\n\n"
        f"SUBJECT HOURS: {subjects_str}\n"
        f"TOTAL: {total:.1f}h\n\n"
        f"RESPOND WITH:\n\n"
        f"## 📊 Time Distribution Analysis\n"
        f"| Subject | Hours | % of Total | Verdict | Action |\n"
        f"|---------|-------|------------|---------|--------|\n"
        f"(fill for each subject — verdict: ✅ Good / ⚠️ Low / 🔴 Critical)\n\n"
        f"## 🔄 Rebalancing Strategy\n"
        f"- Which subjects to increase, by how many hours/week\n"
        f"- Which subjects to maintain or reduce\n\n"
        f"## 🧠 Smart Study Techniques\n"
        f"For the weakest 2-3 subjects, give ONE specific technique each:\n"
        f"- Active recall, spaced repetition, Feynman method, mind mapping, etc.\n"
        f"- HOW to apply it (not just the name)\n"
    )
    return get_ai_insight(prompt)


# ── Waste time ─────────────────────────────────────────────────────────────
def analyze_waste_time(waste_summary: dict, period: str) -> str:
    waste_str = ", ".join(
        f"{k}: {v:.1f}h" for k, v in sorted(waste_summary.items(), key=lambda x: -x[1])
    )
    total_waste = sum(waste_summary.values())
    prompt = (
        f"You are a productivity scientist. Analyze waste time data.\n\n"
        f"PERIOD: {period}\n"
        f"WASTE BREAKDOWN: {waste_str}\n"
        f"TOTAL WASTE: {total_waste:.1f}h\n\n"
        f"RESPOND WITH:\n\n"
        f"## 🚨 Waste Impact\n"
        f"| Activity | Hours | Recoverable | Replacement Activity |\n"
        f"|----------|-------|-------------|---------------------|\n"
        f"(fill for each waste activity)\n\n"
        f"## ⚡ Recovery Plan\n"
        f"| Technique | What To Do | Expected Time Saved | Difficulty |\n"
        f"|-----------|-----------|---------------------|------------|\n"
        f"(3-4 specific techniques like time-blocking, phone lock apps, environment design)\n\n"
        f"## 🧠 Behavioral Hacks\n"
        f"3 psychology-backed techniques to break waste habits:\n"
        f"- Implementation intentions, temptation bundling, 2-minute rule, etc.\n"
        f"- Each with a SPECIFIC example for their situation\n"
    )
    return get_ai_insight(prompt)


# ── Overall productivity ───────────────────────────────────────────────────
def analyze_productivity(prod_h: float, essential_h: float,
                         waste_h: float, period: str,
                         streak_days: int = 0) -> str:
    total = prod_h + essential_h + waste_h
    prod_pct = (prod_h / total * 100) if total > 0 else 0
    waste_pct = (waste_h / total * 100) if total > 0 else 0
    prompt = (
        f"You are an elite productivity coach. Analyze and provide a transformation plan.\n\n"
        f"DATA ({period}):\n"
        f"- Productive: {prod_h:.1f}h ({prod_pct:.0f}%)\n"
        f"- Essential: {essential_h:.1f}h\n"
        f"- Waste: {waste_h:.1f}h ({waste_pct:.0f}%)\n"
        f"- Study streak: {streak_days} days\n"
        f"- Total tracked: {total:.1f}h\n\n"
        f"RESPOND WITH:\n\n"
        f"## 📊 Productivity Scorecard\n"
        f"| Metric | Value | Rating | Benchmark |\n"
        f"|--------|-------|--------|-----------|\n"
        f"(Productive %, Waste %, Streak, Efficiency — rate each 🟢🟡🔴)\n\n"
        f"## ⚡ Top 3 Productivity Multipliers\n"
        f"For each, give: technique name, how to implement, expected impact.\n"
        f"Use techniques like: deep work blocks, Pomodoro, time-boxing, "
        f"energy management, 90-min focus cycles, MIT method, Eisenhower matrix.\n\n"
        f"## 📈 Weekly Optimization Plan\n"
        f"| Day | Morning Block | Afternoon Block | Evening Block | Target Hours |\n"
        f"|-----|--------------|-----------------|---------------|-------------|\n"
        f"(suggest an ideal week structure)\n\n"
        f"## 🎯 30-Day Challenge\n"
        f"3 specific measurable goals to hit in the next 30 days.\n"
    )
    return get_ai_insight(prompt)


# ── Expenses ───────────────────────────────────────────────────────────────
def analyze_expenses(expense_summary: dict, total: float) -> str:
    exp_str = ", ".join(
        f"{k}: ₹{v:.0f}" for k, v in sorted(expense_summary.items(), key=lambda x: -x[1])
    )
    prompt = (
        f"Act as a financial advisor for a student. Total expenses: ₹{total:.0f}. "
        f"Breakdown by category: {exp_str}. "
        f"In 3-4 sentences, identify spending patterns, flag excessive categories, "
        f"and give practical advice to cut unnecessary expenses."
    )
    return get_ai_insight(prompt)


# ── SMART QUESTION CLASSIFIER ────────────────────────────────────────────
# Keywords that indicate the question is UPSC/study/timetable related
_STUDY_KEYWORDS = {
    # UPSC specific
    'upsc', 'ias', 'prelims', 'mains', 'gs1', 'gs2', 'gs3', 'gs4', 'csat',
    'pyq', 'previous year', 'civil services', 'optional', 'essay',
    # Subjects
    'polity', 'geography', 'history', 'economics', 'economy', 'environment',
    'ecology', 'science', 'current affairs', 'public administration',
    'indian constitution', 'fundamental rights', 'directive principles',
    # Study actions
    'study', 'revise', 'revision', 'timetable', 'time table', 'schedule',
    'plan', 'routine', 'strategy', 'prepare', 'preparation', 'syllabus',
    'chapter', 'topic', 'subject', 'ncert', 'mock test', 'test series',
    'answer writing', 'notes', 'booklist', 'book list', 'resources',
    # Productivity
    'productivity', 'waste', 'procrastination', 'focus', 'concentration',
    'distraction', 'weak subject', 'strong subject', 'improve',
    'backlog', 'behind', 'catch up', 'hours', 'daily routine',
    # Exam related
    'exam', 'cutoff', 'marks', 'score', 'rank', 'topper', 'coaching',
}

def _is_study_related(prompt: str) -> bool:
    """Detect if the user's question is about study/UPSC/timetable."""
    prompt_lower = prompt.lower()
    match_count = sum(1 for kw in _STUDY_KEYWORDS if kw in prompt_lower)
    # If 1+ study keywords found, it's study-related
    return match_count >= 1


# ── Ask Esu: Comprehensive UPSC Study Mentor ──────────────────────────
# ── SMART RESPONSE PROMPT — Strategy-First ───────────────────────────────
SMART_RESPONSE_PROMPT = """
You are **Esu** — an elite UPSC mentor with 15+ years of coaching experience. 
Give the **MOST COMPREHENSIVE, DETAILED, and ACTIONABLE answer possible**.

## YOUR PERSONALITY:
- BRUTALLY HONEST but supportive.
- DATA-DRIVEN — use the provided subject and strategy data for EVERY SUBJECT.
- EXHAUSTIVE — if the user asks for a general plan, you MUST cover all subjects (Polity, Economy, Geography, History, Art & Culture, Society, Environment, S&T, Ethics, IR, Security, etc.) using the provided data.
- ELABORATIVE — explain the WHY.
- MINIMUM RESPONSE LENGTH: 1200+ words for general strategy. Short answers are failures.

## RESPONSE STRUCTURE (ALL 7 SECTIONS MANDATORY):

### SECTION 1: Direct Answer (Detailed)
- Answer the user's exact question with FULL depth.
- Include specific book/chapter references.
- For subjects: give chapter-wise breakdown with priority and focus topics.

### SECTION 2: 📚 Revision & Short Notes Strategy
| Chapter/Topic | Revisions Needed | Make Short Notes? | Note-Making Method | When to Revise |
|---------------|-----------------|-------------------|-------------------|----------------|
- Explain HOW to make short notes (flowcharts, mind maps).
- Spaced repetition: Day 1, 3, 7, 21, 45.

### SECTION 3: 🎯 Chapter-wise Focus & Priority Ranking
| Priority Rank | Chapter | Focus Topics (Most Important) | PYQ Frequency | Time to Allocate |
|--------------|---------|-------------------------------|---------------|-----------------|
- List 3-5 topics to SKIP or DEPRIORITIZE.

### SECTION 4: 📅 Study Plan & Routine
**Daily Plan Table:** Slot-wise (6AM to 10PM).
**Weekly Plan Table:** Subject rotation across the week.
**Monthly Milestones Table:** Phase-wise planning.

### SECTION 5: 🏋 Practice Strategy
- MCQ count per day, Answer writing targets, Mock schedule.

### SECTION 6: ⚠ Danger Zones & Common Mistakes
- 3-5 specific traps and how to avoid them.

### SECTION 7: 💬 Esu's Honest Take
- 5-8 lines of personal, direct mentor advice.

## STRATEGY CONTEXT (Use this data):
{strategy_context}

{routine_context}

## STUDENT QUESTION:
{user_prompt}
"""

def _build_strategy_context(user_prompt, selected_subjects=None):
    """
    Build strategy context. 
    Smart Pruning: Full detail for manually selected subjects, detected subjects or Core ones.
    """
    detected = detect_subjects(user_prompt)
    context_parts = []
    
    # Priority subjects for UPSC
    core_subjects = ["polity", "economy", "history"]
    
    # If the user asks for "all" or a general plan
    is_general = any(kw in user_prompt.lower() for kw in ["all", "everything", "general", "complete", "strategy"])
    
    # Selection priority: Manual Selection > Query Detection > Core Subjects (if general)
    target_subjects = []
    if selected_subjects:
        target_subjects = selected_subjects
    
    for subj_key in list(ALL_SUBJECTS.keys()):
        # Determine if this subject needs full detail
        if subj_key in target_subjects:
            context_parts.append(get_subject_strategy_text(subj_key))
        elif not selected_subjects and subj_key in detected:
            # Only use auto-detection if no manual selection is made
            context_parts.append(get_subject_strategy_text(subj_key))
        elif not selected_subjects and is_general and subj_key in core_subjects:
            # Only use core fallback if no manual selection is made
            context_parts.append(get_subject_strategy_text(subj_key))
        else:
            # Very compact summary for everything else
            context_parts.append(get_subject_summary_text(subj_key))
            
    return "\n".join(context_parts)


def ask_esu(user_prompt: str, context: str, pyq_context: str = "", selected_subjects: list = None) -> str:
    """
    Esu: Elite UPSC mentor providing holistic strategy.
    Technique adapted from UPSC-AI project for maximum coverage.
    """
    is_study = _is_study_related(user_prompt)
    
    if not is_study:
        return get_ai_insight(f"Answer this question as Esu, a UPSC mentor: {user_prompt}\n\nContext: {context}")

    # Build holistic context - ALWAYS include ALL subjects, but prioritize selected ones
    strategy_context = _build_strategy_context(user_prompt, selected_subjects=selected_subjects)
    
    routine_keywords = ["routine", "timetable", "schedule", "daily", "weekly", "plan"]
    include_routine = any(kw in user_prompt.lower() for kw in routine_keywords) or "strategy" in user_prompt.lower()
    routine_context = get_routine_text() if include_routine else "(Routine details available on request)"

    full_prompt = SMART_RESPONSE_PROMPT.format(
        strategy_context=strategy_context,
        routine_context=routine_context,
        user_prompt=user_prompt
    )
    
    if context:
        full_prompt += f"\n\nUSER'S CURRENT PERFORMANCE DATA:\n{context}"
    if pyq_context:
        full_prompt += f"\n\nADDITIONAL PYQ DATA:\n{pyq_context}"

    return get_ai_insight(full_prompt, max_tokens=3000)

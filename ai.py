import os
from dotenv import load_dotenv, find_dotenv

# Load from explicit path so it works regardless of working directory
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

# Current working model on Groq API (verified April 2026)
# llama-3.1-8b-instant is the only stable model available
ACTIVE_MODEL = "llama-3.1-8b-instant"

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


def get_ai_insight(prompt: str, model_type: str = "heavy", max_tokens: int = 4000) -> str:
    """Generic Groq call — non-blocking, no retries to avoid websocket timeouts."""
    try:
        from groq import Groq
        
        api_key = _get_api_key()
        if not api_key:
            return "⚠️ AI unavailable: GROQ_API_KEY not found in .env or Streamlit secrets."
        
        client = Groq(api_key=api_key)
        
        try:
            res = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=ACTIVE_MODEL,
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            if res and res.choices and len(res.choices) > 0:
                message = res.choices[0].message
                if message and message.content:
                    return message.content
            
            return "⚠️ Empty response from AI. Please try again."
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate" in error_str or "429" in error_str or "too many" in error_str:
                # Extract wait time from error if available
                import re
                wait_match = re.search(r'try again in (\d+\.?\d*)', error_str)
                wait_hint = f" (wait ~{wait_match.group(1)}s)" if wait_match else ""
                return f"⚠️ Rate limit reached{wait_hint}. Please wait 1-2 minutes and try again."
            elif "decommissioned" in error_str:
                return "⚠️ AI model temporarily unavailable. Please try again."
            elif "authentication" in error_str or "unauthorized" in error_str:
                return "⚠️ API authentication failed. Please verify your Groq API key in .env file."
            elif "connection" in error_str or "timeout" in error_str:
                return "⚠️ Connection error. Please check your internet connection."
            else:
                return f"⚠️ AI error: {str(e)[:150]}"
    
    except ImportError:
        return "⚠️ Groq library not installed. Install with: pip install groq"
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


# ── Ask Esu: Smart Personalized Study Assistant ──────────────────────────
def ask_esu(user_prompt: str, context: str, pyq_context: str = "") -> str:
    """
    Esu: A smart study assistant that detects what the user is asking and
    responds with the best possible answer — rich tables, actionable advice,
    and UPSC PYQ data when the question is study-related.
    
    Args:
        user_prompt: User's question or request
        context: User's study data summary
        pyq_context: UPSC PYQ trend data (only injected when study-related)
    
    Returns:
        Personalized response from Esu
    """
    is_study = _is_study_related(user_prompt)
    
    # ── COMPACT SYSTEM PROMPT (token-efficient to avoid rate limits) ──
    base_prompt = (
        "You are Esu — a sharp, warm AI study mentor.\n\n"
        "RULES:\n"
        "1. Answer EXACTLY what the user asks. No deviation.\n"
        "2. Use ## Headers, **bold**, bullet points, numbered lists.\n"
        "3. Include at least 1 markdown table in every response.\n"
        "4. Keep paragraphs to 2-3 lines MAX.\n"
        "5. End with 🎯 Key Takeaway (2-3 actionable lines).\n\n"
    )
    
    # ── STUDY-SPECIFIC ENHANCEMENT ──
    if is_study:
        base_prompt += (
            "STUDY MODE ACTIVE:\n"
            "- For TIMETABLE: Use | Time Slot | Activity | Duration | Notes | format with exact times. Include meals, breaks, walk.\n"
            "- For SUBJECTS: Create priority table with PYQ frequency.\n"
            "- For REVISION: Phase-wise plan with daily targets.\n"
            "- For PRODUCTIVITY: Before/after table with recoverable time.\n"
            "- UPSC refs: Laxmikanth, Spectrum, Shankar IAS, Ramesh Singh, NCERT 6-12.\n\n"
        )
    else:
        base_prompt += "Answer directly with best knowledge. Use tables where applicable.\n\n"
    
    # ── BUILD FINAL PROMPT (keep it lean) ──
    full_prompt = base_prompt
    
    # Add study data context (compact)
    full_prompt += f"USER DATA:\n{context}\n\n"
    
    # Add PYQ data ONLY for study-related questions — truncate to top subjects
    if is_study and pyq_context:
        # Limit PYQ context to ~500 chars to save tokens
        truncated_pyq = pyq_context[:500]
        if len(pyq_context) > 500:
            truncated_pyq += "\n...(more subjects available)"
        full_prompt += f"PYQ TRENDS:\n{truncated_pyq}\n\n"
    
    full_prompt += f"QUESTION: {user_prompt}\n\nAnswer the EXACT question. Use tables. Be specific."
    
    return get_ai_insight(full_prompt, model_type="light", max_tokens=3000)

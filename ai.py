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


def get_ai_insight(prompt: str, model_type: str = "heavy") -> str:
    """Generic Groq call using the only currently available working model."""
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
                max_tokens=2000,
                temperature=0.7
            )
            
            if res and res.choices and len(res.choices) > 0:
                message = res.choices[0].message
                if message and message.content:
                    return message.content
            
            return "⚠️ Empty response from AI. Please try again."
            
        except Exception as e:
            error_str = str(e)
            
            # Specific error messages
            if "decommissioned" in error_str.lower():
                return "⚠️ AI model temporarily unavailable. Please try again."
            elif "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
                return "⚠️ API authentication failed. Please verify your Groq API key in .env file."
            elif "rate" in error_str.lower():
                return "⚠️ Rate limit reached. Please wait a moment and try again."
            elif "connection" in error_str.lower() or "timeout" in error_str.lower():
                return "⚠️ Connection error. Please check your internet connection."
            else:
                return f"⚠️ AI error: {error_str[:100]}"
    
    except ImportError:
        return "⚠️ Groq library not installed. Install with: pip install groq"
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"




# ── Target analysis (original) ─────────────────────────────────────────────
def analyze_target(target_subject, target_chapters, deadline,
                   days_taken, hours_taken, max_chapter) -> str:
    prompt = (
        f"Act as a strict but encouraging study mentor. "
        f"I have a target to complete '{target_subject}' ({target_chapters} chapters) by {deadline}. "
        f"So far I have spent {days_taken} separate study days, accumulating {hours_taken} total hours. "
        f"The chapter that took the most time is '{max_chapter}'. "
        f"Provide a concise (max 3 sentences) analysis of my progress. "
        f"Advise if I am spending too much time on a single chapter, or if my pace is good to hit the deadline."
    )
    return get_ai_insight(prompt)


# ── Weak subjects ──────────────────────────────────────────────────────────
def analyze_weak_subjects(subject_hours: dict) -> str:
    subjects_str = ", ".join(
        f"{s}: {h:.1f}h" for s, h in sorted(subject_hours.items(), key=lambda x: x[1])
    )
    prompt = (
        f"Act as a study coach. Here are the hours I have spent on each subject: {subjects_str}. "
        f"In 3-4 sentences, identify which subjects are being neglected, and give specific actionable "
        f"advice to reallocate study time and cover weak areas before exams."
    )
    return get_ai_insight(prompt)


# ── Waste time ─────────────────────────────────────────────────────────────
def analyze_waste_time(waste_summary: dict, period: str) -> str:
    waste_str = ", ".join(
        f"{k}: {v:.1f}h" for k, v in sorted(waste_summary.items(), key=lambda x: -x[1])
    )
    prompt = (
        f"Act as a productivity coach. During {period} I spent time on these activities: {waste_str}. "
        f"In 3-4 sentences, identify the biggest time wasters and provide specific, "
        f"actionable steps to reduce them and redirect that time toward productive study."
    )
    return get_ai_insight(prompt)


# ── Overall productivity ───────────────────────────────────────────────────
def analyze_productivity(prod_h: float, essential_h: float,
                         waste_h: float, period: str,
                         streak_days: int = 0) -> str:
    prompt = (
        f"Act as a productivity analyst. For {period}:\n"
        f"- Productive hours: {prod_h:.1f}h\n"
        f"- Essential hours: {essential_h:.1f}h\n"
        f"- Waste hours: {waste_h:.1f}h\n"
        f"- Study streak: {streak_days} days\n"
        f"In 3-4 sentences, evaluate the overall productivity balance and give concrete tips "
        f"to increase productive hours while reducing waste."
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


# ── Ask Esu: Comprehensive Personalized Study Assistant ──────────────────
def ask_esu(user_prompt: str, context: str) -> str:
    """
    Esu: A personalized study assistant with expertise in UPSC/competitive exam preparation.
    Considers PYQ patterns, important subjects, chapters, and personalized study data.
    
    Args:
        user_prompt: User's question or request
        context: User's study data summary, UPSC insights, and exam information
    
    Returns:
        Personalized response from Esu
    """
    system_prompt = (
        "You are Esu, an elite AI study consultant specialized in UPSC exam preparation (Prelims & Mains). "
        "You combine PYQ analysis with individual study patterns to create highly personalized strategies.\n\n"
        
        "YOUR EXPERTISE:\n"
        "✓ UPSC PYQ trend analysis (subjects, chapters, topics by frequency)\n"
        "✓ Prelims vs Mains specific strategies and time allocation\n"
        "✓ Weak subject remediation based on current study hours\n"
        "✓ High-frequency PYQ topic prioritization\n"
        "✓ Chapter revision sequencing (important → less frequent → rest)\n"
        "✓ Time management and daily/weekly study routines\n"
        "✓ Mock test strategy and practice methodology\n"
        "✓ Productivity optimization and eliminating time waste\n"
        "✓ Smart note-making and retention techniques\n"
        "✓ Exam-day preparation and stress management\n\n"
        
        "ANALYSIS APPROACH:\n"
        "1. PYQ FREQUENCY: Use the provided importance scores (1-99) to prioritize subjects\n"
        "2. CURRENT EFFORT: Compare user's current study hours vs PYQ importance\n"
        "3. WEAK AREAS: Identify where user is under-studying high-importance topics\n"
        "4. TIMELINE: Calculate daily targets based on days remaining\n"
        "5. EFFICIENCY: Suggest subject combinations and time blocks\n"
        "6. STRATEGY: Tailor approach based on Prelims/Mains focus\n\n"
        
        "PRELIMS SPECIFIC (GS):\n"
        "- Focus on breadth over depth initially\n"
        "- Quick facts and dates requirement\n"
        "- Current affairs integration crucial\n"
        "- Quick revision possible (factual recall)\n\n"
        
        "MAINS SPECIFIC:\n"
        "- Depth and holistic understanding required\n"
        "- Essay/answer writing practice essential\n"
        "- Case studies and examples integration\n"
        "- Longer revision cycles needed\n\n"
        
        "RESPONSE FORMAT:\n"
        "- Lead with the most important action\n"
        "- Provide specific daily/weekly routine when requesting study plan\n"
        "- Quantify recommendations (hours, chapters, topics)\n"
        "- Highlight high-frequency PYQ topics to focus on\n"
        "- Suggest mock test strategy\n"
        "- Include revision timeline\n"
        "- Be realistic about timelines\n\n"
        
        "KEY INSTRUCTION:\n"
        "Use the UPSC PYQ data provided (importance scores, frequency ranks, important chapters/topics) "
        "to justify your recommendations. If user's weak subjects have high importance scores, "
        "emphasize urgent action needed. Always reference specific PYQ patterns.routine when requesting study plan\n"
        "- Quantify recommendations (hours, chapters, topics)\n"
        "- Highlight high-frequency PYQ topics to focus on\n"
        "- Suggest mock test strategy\n"
        "- Include revision timeline\n"
        "- Be realistic about timelines\n\n"
        
        "KEY INSTRUCTION:\n"
        "Use the UPSC PYQ data provided (importance scores, frequency ranks, important chapters/topics) "
        "to justify your recommendations. If user's weak subjects have high importance scores, "
        "emphasize urgent action needed. Always reference specific PYQ patterns."
    )
    
    full_prompt = f"{system_prompt}\n\n{context}\n\nUser's Request: {user_prompt}"
    
    # Use lightweight model for Ask Esu (less frequent usage)
    return get_ai_insight(full_prompt, model_type="light")

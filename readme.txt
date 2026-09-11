# Study Routine Tracker


pip install -r requirements.txt
streamlit run app.py

net start postgresql-x64-18

python -m streamlit run app.py
python -m py_compile app.py

python -m streamlit run app.py --server.headless true


Codeforces Performance Graph, Contribution Heatmaps, and Test Hours Exclusion
We have implemented:

Inverted Red Brightness Logic for Heatmap:
Implemented your specified brightness direction in 

cf_visuals.py
:
0 hrs (Inactive / Empty): Subtle dark slate (#1e293b)
Level 1 (Less Activity / Lower Hours): Dark deep wine red (#6b1414)
Level 2 (Moderate Activity): Medium crimson red (#b91c1c)
Level 3 (High Activity): Vibrant bright scarlet red (#ef4444)
Level 4 (Peak Activity / More Hours): Ultra-bright glowing neon red (#ff0033)
Legend Updated: Less [#1e293b] [#6b1414] [#b91c1c] [#ef4444] [#ff0033] More. Higher hours now appear progressively brighter and more radiant.
Codeforces Performance Graph & Heatmap Kept to Hours & Routine Metrics:
Performance Graph: Plotted strictly against time in hours and routine scores:
⏱️ Productive Hours (Excl. Test)
⏱️ Total Productive Hours
📚 Study Hours
🔄 Revision Hours
📝 Test Hours
🎯 Productivity Score (%)
🧠 Focus Score (%)
😴 Sleep Hours
Activity Filter: All 3 Combined, Study, Revision, Test, or 📑 Stacked View (All 3).
Year Filter: Last 365 Days, 2026, 2025, 2024, etc.
Graph Metric Selector: Switch between Productive Hours (Excl. Test), Total Productive Hours, Study Hours, Revision Hours, Test Hours, Productivity Score (%), and Focus Score (%).
Verification & Results
Top 10 Productive Days (Excl. Test)
Before the change, 24 May 2026 was ranked #1 due to a 17.0h D-Day Exam (Test). With the new logic:


Top 5 Productive Days (Excl. Test):
                Period  productive_hours
2        03 April 2026             14.50
1        02 April 2026             14.50
162  14 September 2026             13.00
25       26 April 2026             10.15
133     16 August 2026             10.00
May 24 row:
          date  productive_hours  productive_no_test_hours  test_hours
52  2026-05-24              17.0                       0.0        17.0
May 24 is now correctly excluded from the Productive Days ranking.

Activity Statistics Verified
Study: 478.9h all-time | 167.0h last 30 days | 25-day max streak
Revision: 78.8h all-time | 7.0h last 30 days | 10-day max streak
Test: 18.8h all-time | 1-day max streak
All 3 Combined: 576.4h all-time | 174.0h last 30 days | 39-day max streak

CF Ratings: Automatically assigned based on the productivity score:
0% - 40%: Developing
40% - 60%: Consistent
60% - 75%: Specialist
75% - 85%: Expert
85% - 95%: Master
95% - 100%: Grandmaster
Good Days (Last 30d) Card: Highlights total good days, percentage, and criteria badge.
Daily Performance Report Table: Displays Productivity (%) and Waste (%) as progress columns, accompanied by CF Rating and Good Day? (✅ / ❌)
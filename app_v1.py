import streamlit as st
import pandas as pd
from database import conn, c
from logic import *
import plotly.express as px
from streamlit_calendar import calendar

st.set_page_config(layout="wide")

menu = st.sidebar.radio("Menu",[
    "Daily Entry","Calendar","Year View","Targets","Analytics","Expenses"
])

# ---------------- DAILY ENTRY ----------------
if menu == "Daily Entry":
    st.title("📅 Smart Entry")

    date = st.date_input("Date")

    base_activities = [
        "Study","Entertainment","Social Media","Food","Transport",
        "Office","WFH","Test","Coaching"
    ]

    custom = pd.read_sql("SELECT * FROM custom_boxes", conn)['name'].tolist()

    activity = st.selectbox("Activity", base_activities + custom + ["+ Add New"])

    if activity == "+ Add New":
        new = st.text_input("New Activity")
        if st.button("Save Activity"):
            c.execute("INSERT INTO custom_boxes VALUES (NULL,?)",(new,))
            conn.commit()
            st.success("Added")

    sub1=sub2=sub3=""

    if activity == "Study":
        sub1 = st.selectbox("Subject", study_subjects)
        sub2 = st.text_input("Chapter")

    elif activity == "Entertainment":
        sub1 = st.selectbox("Type", ent_types)
        if sub1 == "Movie":
            sub2 = st.selectbox("Mode", movie_modes)

    elif activity == "Social Media":
        sub1 = st.selectbox("Platform", social_platform)
        sub2 = st.selectbox("Content", content_type)

    elif activity == "Food":
        sub1 = st.selectbox("Source", food_sources)

    elif activity == "Transport":
        sub1 = st.selectbox("Service", transport_services)

    # duration system
    if activity in ["Food","Transport"]:
        amount = st.number_input("Amount")
        duration = 0
    else:
        mode = st.radio("Time Mode",["Duration","Time Range"])

        if mode == "Duration":
            duration = st.number_input("Hours")
        amount = 0

    if st.button("Save"):
        c.execute("INSERT INTO activities VALUES(NULL,?,?,?,?,?,?,?)",
                  (str(date),activity,sub1,sub2,sub3,duration,amount))
        conn.commit()
        st.success("Saved")

# ---------------- CALENDAR ----------------
elif menu == "Calendar":
    st.title("📆 Calendar View")

    df = pd.read_sql("SELECT * FROM activities", conn)

    events=[]

    if not df.empty:
        grouped = df.groupby("date")

        for d, group in grouped:
            study = group[group['activity']=="Study"]['duration'].sum()
            is_test = any(group['activity']=="Test")
            weekend = not any(group['activity'].isin(["Office","WFH","Test","Coaching"]))

            color = get_color(study, weekend, is_test)

            events.append({
                "title": f"{round(study,1)} hr",
                "start": d,
                "color": color
            })

    calendar(events=events)

# ---------------- YEAR VIEW ----------------
elif menu == "Year View":
    st.title("📊 Yearly")
    df = pd.read_sql("SELECT * FROM activities", conn)

    if not df.empty:
        df['month']=pd.to_datetime(df['date']).dt.month
        st.bar_chart(df.groupby('month')['duration'].sum())

# ---------------- TARGETS ----------------
elif menu == "Targets":
    st.title("🎯 Advanced Targets")

    activity = st.selectbox("Activity", ["Study","Revision","Test"])
    hrs = st.number_input("Target Hours")
    duration_type = st.selectbox("Duration Type",["Daily","Weekly","Monthly"])
    chapters = st.number_input("Chapters Target")

    if st.button("Save Target"):
        c.execute("INSERT INTO targets VALUES(NULL,?,?,?,?)",
                  (activity,hrs,duration_type,chapters))
        conn.commit()

    df = pd.read_sql("SELECT * FROM activities", conn)

    if not df.empty:
        study = df[df['activity']=="Study"]['duration'].sum()
        st.metric("Total Study", study)

# elif menu == "Targets":
#     st.title("🎯 Targets")
#
#     subject = st.selectbox("Subject",study_subjects)
#     hrs = st.number_input("Target Hours")
#     chapters = st.number_input("Chapters")
#     deadline = st.date_input("Deadline")
#
#     if st.button("Save Target"):
#         c.execute("INSERT INTO targets VALUES(NULL,?,?,?,?)",
#                   ("Study",subject,hrs,str(deadline),chapters))
#         conn.commit()
#
#     df = pd.read_sql("SELECT * FROM activities", conn)
#     tgt = pd.read_sql("SELECT * FROM targets", conn)
#
#     if not tgt.empty:
#         for _,t in tgt.iterrows():
#             sub = t['subject']
#             target_hours = t['target_hours']
#
#             actual = df[df['subject']==sub]['duration'].sum()
#             percent = (actual/target_hours)*100 if target_hours>0 else 0
#
#             st.write(f"{sub}: {round(percent,1)}% complete")

# ---------------- ANALYTICS ----------------
elif menu == "Analytics":
    st.title("📈 Analytics")

    df = pd.read_sql("SELECT * FROM activities", conn)

    if not df.empty:
        fig = px.pie(df, names='activity', values='duration')
        st.plotly_chart(fig)
        st.metric("Productivity %", productivity_score(df))
        st.metric("Study Streak", streak(df))

        sub_df = df[df['activity'] == "Study"].groupby('subject')['duration'].sum()
        st.bar_chart(sub_df)

        st.subheader("Weak Subjects")
        st.write(sub_df.sort_values().head())

# ---------------- EXPENSE ----------------
elif menu == "Expenses":
    st.title("💰 Expense Tracker")

    df = pd.read_sql("SELECT * FROM activities", conn)
    df = df[df['amount']>0]

    if not df.empty:
        st.bar_chart(df.groupby('activity')['amount'].sum())

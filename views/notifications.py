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
    conn = database.conn
    c = database.c
    import proposal
    proposal.show_admin_notifications(USER)
    st.stop()
    
    # ---------------- DAILY ENTRY ----------------

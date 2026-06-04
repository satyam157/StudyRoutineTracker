import pandas as pd
import psycopg2
import os
import datetime
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
df = pd.read_sql("SELECT id, date, type, subject, chapter, start_time, duration, status FROM activities ORDER BY id DESC LIMIT 10", conn)
print(df.to_string())

import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
df = pd.read_sql("SELECT id, type, subject, chapter, start_time, duration, status FROM activities WHERE duration=0 OR status='Pending' ORDER BY id DESC LIMIT 20", conn)
print(df.to_string())

from datetime import timedelta, date, timezone
import datetime
import psycopg2
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
        DATABASE_URL = st.secrets["DATABASE_URL"]
    else:
        DATABASE_URL = os.environ.get("DATABASE_URL")
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "study_tracker")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")

import time

conn = None
c = None

def get_ist_now():
    """Get current time in Indian Standard Time (UTC+5:30)."""
    return datetime.datetime.now(timezone(timedelta(hours=5, minutes=30)))


def _make_connection():
    """Create a fresh psycopg2 connection using env config."""
    if DATABASE_URL:
        new_conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    else:
        new_conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=10
        )
    new_conn.autocommit = True
    return new_conn


def reconnect():
    """Re-establish the global conn/c if the connection has dropped."""
    global conn, c
    try:
        if conn is not None:
            try:
                conn.close()
            except:
                pass
        conn = _make_connection()
        c = conn.cursor()
        return conn, c
    except Exception as e:
        print(f"reconnect() failed: {e}")
        return None, None


def ensure_connection():
    """Check if connection is alive, reconnect if not."""
    global conn, c
    if conn is None or conn.closed != 0:
        return reconnect()
    try:
        # Ping the database
        tmp_cur = conn.cursor()
        tmp_cur.execute("SELECT 1")
        tmp_cur.close()
    except Exception:
        return reconnect()
    return conn, c


def get_fresh_cursor():
    """Return a cursor from a brand-new, throw-away connection."""
    try:
        tmp = _make_connection()
        return tmp, tmp.cursor()
    except Exception as e:
        print(f"get_fresh_cursor() failed: {e}")
        return None, None

try_count = 5
delay = 3

for attempt in range(try_count):
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        else:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
                connect_timeout=5
            )
        conn.autocommit = True
        c = conn.cursor()
        break
    except psycopg2.OperationalError as e:
        if f'database "{DB_NAME}" does not exist' in str(e):
            print(f"Database {DB_NAME} does not exist. Attempting to create it...")
            try:
                temp_conn = psycopg2.connect(
                    host=DB_HOST, database="postgres", user=DB_USER, password=DB_PASS, port=DB_PORT, connect_timeout=5
                )
                temp_conn.autocommit = True
                temp_c = temp_conn.cursor()
                # Use psycopg2.sql to safely quote the db name if needed, but for simplicity:
                temp_c.execute(f"CREATE DATABASE {DB_NAME}")
                temp_c.close()
                temp_conn.close()
                print(f"Successfully created database {DB_NAME}! Retrying connection...")
            except Exception as create_e:
                print(f"Failed to auto-create database {DB_NAME}: {create_e}")
                
        if attempt < try_count - 1:
            print(f"Database connection failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
        else:
            print(f"Database connection failed after {try_count} attempts: {e}")
    except Exception as e:
        if attempt < try_count - 1:
            print(f"Database connection failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
        else:
            print(f"Database connection failed after {try_count} attempts: {e}")

if c is not None:
    try:
        c.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id SERIAL PRIMARY KEY,
            username TEXT,
            date TEXT,
            type TEXT,
            subject TEXT,
            chapter TEXT,
            duration REAL,
            amount REAL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id SERIAL PRIMARY KEY,
            username TEXT,
            subject TEXT,
            chapter TEXT,
            completed INTEGER
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id SERIAL PRIMARY KEY,
            username TEXT,
            subject TEXT,
            total_chapters INTEGER,
            deadline TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS custom_boxes (
            id SERIAL PRIMARY KEY,
            username TEXT,
            name TEXT,
            activity_type TEXT DEFAULT 'Waste'
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
        """)
        try:
            c.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
        except:
            pass

        c.execute("""
        CREATE TABLE IF NOT EXISTS health_logs (
            id SERIAL PRIMARY KEY,
            username TEXT,
            date TEXT,
            wakeup_time TEXT,
            sleep_time TEXT,
            UNIQUE(username, date)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS social_logs (
            id SERIAL PRIMARY KEY,
            username TEXT,
            date TEXT,
            entertainment_hours REAL DEFAULT 0,
            went_outside_hours REAL DEFAULT 0,
            UNIQUE(username, date)
        )
        """)

        try:
            c.execute("SELECT COUNT(*) FROM users")
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO users (username, password) VALUES ('admin', 'rishav')")
                c.execute("INSERT INTO users (username, password) VALUES ('harsh', 'bro')")
                c.execute("INSERT INTO users (username, password) VALUES ('esu', 'satyam')")
                c.execute("INSERT INTO users (username, password) VALUES ('rishika', 'love')")
                c.execute("INSERT INTO users (username, password) VALUES ('love', 'esu')")
                c.execute("INSERT INTO users (username, password) VALUES ('foryou', 'mylove')")
        except Exception as e:
            print(f"Error seeding users: {e}")

        try:
            c.execute("ALTER TABLE activities ADD COLUMN amount REAL")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE activities ADD COLUMN username TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE chapters ADD COLUMN username TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE targets ADD COLUMN username TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE targets ADD COLUMN date_created TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE targets ADD COLUMN ai_feedback TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE custom_boxes ADD COLUMN username TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE custom_boxes ADD COLUMN activity_type TEXT DEFAULT 'Waste'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE health_logs ADD COLUMN wakeup_time TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE health_logs ADD COLUMN sleep_time TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE health_logs ADD COLUMN powernap REAL DEFAULT 0")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE social_logs ADD COLUMN entertainment_hours REAL DEFAULT 0")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE social_logs ADD COLUMN went_outside_hours REAL DEFAULT 0")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE targets ADD COLUMN goal_type TEXT DEFAULT 'Chapters'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE targets ADD COLUMN goal_unit TEXT DEFAULT 'Chapters'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE targets ADD COLUMN custom_subject TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE custom_boxes ADD COLUMN tracking_type TEXT DEFAULT 'Hours'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE activities ADD COLUMN start_time TEXT")
        except Exception:
            pass

        c.execute("""
        CREATE TABLE IF NOT EXISTS system_notifications (
            id SERIAL PRIMARY KEY,
            username TEXT,
            recipient TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT FALSE
        )
        """)
        try:
            c.execute("ALTER TABLE system_notifications ADD COLUMN recipient TEXT")
        except Exception:
            pass

        c.execute("""
        CREATE TABLE IF NOT EXISTS user_recipients (
            sender TEXT,
            recipient TEXT,
            PRIMARY KEY (sender, recipient)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS user_config (
            username TEXT PRIMARY KEY,
            can_view_mylove_special BOOLEAN DEFAULT FALSE,
            can_send_love_messages BOOLEAN DEFAULT FALSE,
            can_receive_love_messages BOOLEAN DEFAULT FALSE,
            can_receive_love_notifications BOOLEAN DEFAULT FALSE,
            can_delete_messages BOOLEAN DEFAULT FALSE,
            can_delete_system_alerts BOOLEAN DEFAULT FALSE,
            can_access_music BOOLEAN DEFAULT FALSE,
            music_pages TEXT DEFAULT 'all'
        )
        """)

        # Sync user_config with existing users
        try:
            c.execute("INSERT INTO user_config (username) SELECT username FROM users ON CONFLICT DO NOTHING")
            # Default for 'foryou'
            c.execute("UPDATE user_config SET can_view_mylove_special = TRUE, can_receive_love_messages = TRUE WHERE username = 'foryou'")
            conn.commit()
        except:
            pass

        
        try:
            c.execute("ALTER TABLE user_config ADD COLUMN can_send_love_messages BOOLEAN DEFAULT FALSE")
        except:
            pass
        
        try:
            c.execute("ALTER TABLE user_config ADD COLUMN can_delete_messages BOOLEAN DEFAULT FALSE")
        except:
            pass
            
        try:
            c.execute("ALTER TABLE user_config ADD COLUMN can_delete_system_alerts BOOLEAN DEFAULT FALSE")
        except:
            pass
            
        try:
            c.execute("ALTER TABLE user_config ADD COLUMN can_access_music BOOLEAN DEFAULT FALSE")
        except:
            pass

        try:
            c.execute("ALTER TABLE user_config ADD COLUMN music_pages TEXT DEFAULT 'all'")
        except:
            pass

        try:
            c.execute("ALTER TABLE user_config ADD COLUMN mylove_default_song TEXT DEFAULT 'Perfect.mp3'")
        except:
            pass

        c.execute("""
        CREATE TABLE IF NOT EXISTS user_subjects (
            id SERIAL PRIMARY KEY,
            username TEXT,
            subject TEXT,
            UNIQUE(username, subject)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS esu_responses (
            id SERIAL PRIMARY KEY,
            username TEXT,
            question TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS upsc_pyq_analysis (
            id SERIAL PRIMARY KEY,
            subject TEXT UNIQUE,
            exam_type TEXT,
            importance_score INTEGER,
            frequency_rank INTEGER,
            important_chapters TEXT,
            important_topics TEXT,
            revision_strategy TEXT
        )
        """)

        # Insert UPSC PYQ data if not exists
        c.execute("SELECT COUNT(*) FROM upsc_pyq_analysis")
        if c.fetchone()[0] == 0:
            upsc_data = [
                # PRELIMS - Top GS subjects
                ('History', 'Prelims', 95, 1, 'Ancient India, Medieval India, Modern India, World History', 'Mauryan Empire, Mughal Period, British Rule, Independence Movement, World Wars, Cold War', 'Date-wise chronological revision, Important events flashcards'),
                ('Geography', 'Prelims', 92, 2, 'Physical Geography, Human Geography, India Geography, World Geography', 'Monsoon, Plate Tectonics, Climate Zones, Population Distribution, Resources, Disasters', 'Map-based learning, Latitude-longitude references, Physical features mapping'),
                ('Polity', 'Prelims', 96, 3, 'Indian Constitution, Government Structure, Elections, Judiciary, Federalism', 'Articles 1-51, Fundamental Rights, Directive Principles, Parliament, Executive, Supreme Court', 'Constitution study with important judgments, Article-by-article revision'),
                ('Economics', 'Prelims', 88, 4, 'Microeconomics, Macroeconomics, Indian Economy, Banking, Inflation', 'GDP, Inflation, Monetary Policy, Fiscal Policy, Stock Market, Development Indicators', 'Current economic trends, Policy analysis, Statistics memorization'),
                ('Environment & Ecology', 'Prelims', 87, 5, 'Biodiversity, Climate Change, Conservation, Pollution, Renewable Energy', 'Wildlife Protection Act, Forest Conservation, Climate Agreements, Renewable Sources', 'Current environmental news, Conservation strategies, Biodiversity hotspots'),
                ('Current Affairs', 'Prelims', 99, 6, 'National Events, International Relations, Science News, Sports', 'Government policies, International relations, Technological advancements, Sports achievements', 'Daily news reading, Monthly compilation, Thematic organization'),
                
                # MAINS - Same subjects but deeper
                ('History', 'Mains', 97, 1, 'Ancient Civilizations, Medieval Transitions, Colonial Period, Post-Independence, World Context', 'Harappan Civilization, Vedic Period, Mughal Administration, British Economic Impact, Partition, Nation Building, Cold War Dynamics', 'Thematic essay writing, Comparative historical analysis, Primary source study'),
                ('Geography', 'Mains', 94, 2, 'Geomorphology, Climate Systems, Resource Management, Regional Geography, Geopolitics', 'Plate Boundaries, Ocean Currents, Soil Formation, Agriculture Systems, Urbanization, Water Resources', 'Integrated regional studies, Human-environment interaction, Development geography'),
                ('Polity', 'Mains', 98, 3, 'Constitutional Framework, Democratic Processes, Governance, Rights & Duties, Federalism, Local Administration', 'Constitutional Evolution, Legislative Process, Judicial Activism, Administrative Law, Centre-State Relations, Panchayati Raj', 'Case law analysis, Constitutional amendments study, Governance nuances'),
                ('Economics', 'Mains', 91, 4, 'Development Economics, Sectoral Analysis, Fiscal-Monetary Policy, International Trade, Sustainable Development', 'Rural Development, Agricultural Economics, Industry Policy, Trade Agreements, Sustainable Development Goals', 'Policy critique, Economic data analysis, Development model comparison'),
                ('Environment & Ecology', 'Mains', 90, 5, 'Ecosystem Services, Conservation Biology, Climate Mitigation, Environmental Law, Sustainable Development', 'Biodiversity Conservation, Climate Action, Renewable Energy Systems, Environmental Impact Assessment, International Agreements', 'Conservation case studies, Climate scenario planning, Environmental ethics'),
                ('Public Administration', 'Mains', 85, 6, 'Administrative Structures, Human Resource Management, Budget & Finance, E-governance, Ethics', 'Bureaucracy, Civil Service, Administrative Reforms, Good Governance, Accountability', 'Administrative reforms analysis, Case studies in governance'),
            ]
            
            for subject, exam_type, score, rank, chapters, topics, strategy in upsc_data:
                c.execute("""
                    INSERT INTO upsc_pyq_analysis 
                    (subject, exam_type, importance_score, frequency_rank, important_chapters, important_topics, revision_strategy)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (subject, exam_type, score, rank, chapters, topics, strategy))

    except Exception as e:
        print(f"Database schema setup failed: {e}")


def save_esu_response(username, question, response):
    """Save an AI response from Esu to the database."""
    try:
        c.execute(
            "INSERT INTO esu_responses (username, question, response, timestamp) VALUES (%s, %s, %s, %s)",
            (username, question, response, get_ist_now())
        )
        conn.commit()
    except Exception as e:
        print(f"Error saving Esu response: {e}")


def get_esu_responses(username):
    """Retrieve all saved Esu responses for a user."""
    try:
        c.execute(
            "SELECT id, question, response, timestamp FROM esu_responses WHERE username=%s ORDER BY timestamp DESC",
            (username,)
        )
        rows = c.fetchall()
        return [{"id": r[0], "question": r[1], "response": r[2], "timestamp": r[3]} for r in rows]
    except Exception as e:
        print(f"Error getting Esu responses: {e}")
        return []


def delete_esu_response(response_id, username):
    """Delete a specific Esu response."""
    try:
        reconnect()  # Ensure connection is fresh
        c.execute("DELETE FROM esu_responses WHERE id=%s AND username=%s", (response_id, username))
        conn.commit()
    except Exception as e:
        print(f"Error deleting Esu response: {e}")


def get_user_config(username):
    """Retrieve love-related permissions for a user."""
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        tmp_c.execute("SELECT can_view_mylove_special, can_send_love_messages, can_receive_love_messages, can_receive_love_notifications, can_delete_messages, can_delete_system_alerts, can_access_music, music_pages, mylove_default_song FROM user_config WHERE username=%s", (username,))
        row = tmp_c.fetchone()
        tmp_c.close()
        tmp_conn.close()
        if row:
            return {
                "can_view_mylove_special": row[0],
                "can_send_love_messages": row[1],
                "can_receive_love_messages": row[2],
                "can_receive_love_notifications": row[3],
                "can_delete_messages": row[4] if len(row) > 4 else False,
                "can_delete_system_alerts": row[5] if len(row) > 5 else False,
                "can_access_music": row[6] if len(row) > 6 else False,
                "music_pages": row[7] if len(row) > 7 else "all",
                "mylove_default_song": row[8] if len(row) > 8 else "Perfect.mp3"
            }
        return {"can_view_mylove_special": False, "can_send_love_messages": False, "can_receive_love_messages": False, "can_receive_love_notifications": False, "can_delete_messages": False, "can_delete_system_alerts": False, "can_access_music": False, "music_pages": "all", "mylove_default_song": "Perfect.mp3"}
    except:
        return {"can_view_mylove_special": False, "can_send_love_messages": False, "can_receive_love_messages": False, "can_receive_love_notifications": False, "can_delete_messages": False, "can_delete_system_alerts": False, "can_access_music": False, "music_pages": "all", "mylove_default_song": "Perfect.mp3"}


def update_user_config(username, can_view, can_send_msg, can_receive_msg, can_receive_notif, delete_msgs, delete_alerts, can_access_music=False, music_pages="all", mylove_default_song="Perfect.mp3"):
    """Update love-related permissions for a user."""
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        tmp_c.execute("""
            UPDATE user_config 
            SET can_view_mylove_special=%s, can_send_love_messages=%s, can_receive_love_messages=%s, can_receive_love_notifications=%s, can_delete_messages=%s, can_delete_system_alerts=%s, can_access_music=%s, music_pages=%s, mylove_default_song=%s
            WHERE username=%s
        """, (can_view, can_send_msg, can_receive_msg, can_receive_notif, delete_msgs, delete_alerts, can_access_music, music_pages, mylove_default_song, username))
        tmp_conn.commit()
        tmp_c.close()
        tmp_conn.close()
        return True
    except:
        return False


def get_allowed_recipients(sender):
    """Retrieve list of users a sender is allowed to send love messages to."""
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        tmp_c.execute("SELECT recipient FROM user_recipients WHERE sender=%s", (sender,))
        rows = tmp_c.fetchall()
        tmp_c.close()
        tmp_conn.close()
        return [r[0] for r in rows]
    except:
        return []


def set_allowed_recipients(sender, recipients):
    """Define the list of people a user can send love messages to."""
    try:
        tmp_conn, tmp_c = get_fresh_cursor()
        tmp_c.execute("DELETE FROM user_recipients WHERE sender=%s", (sender,))
        for r in recipients:
            tmp_c.execute("INSERT INTO user_recipients (sender, recipient) VALUES (%s, %s)", (sender, r))
        tmp_conn.commit()
        tmp_c.close()
        tmp_conn.close()
        return True
    except:
        return False

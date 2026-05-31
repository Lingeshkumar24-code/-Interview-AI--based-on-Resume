"""
database.py - SQLite database operations for InterviewAI
Handles all CRUD operations for interview sessions, questions, answers, and reports.
"""

import sqlite3
import json
import os
import tempfile
from datetime import datetime

# Database file path
DB_PATH = os.getenv('DATABASE_PATH')
if not DB_PATH:
    if os.getenv('VERCEL'):
        DB_PATH = os.path.join(tempfile.gettempdir(), 'interview-ai', 'database.db')
    else:
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db_connection():
    """Create and return a database connection with row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize the SQLite database and create all tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Interview Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_filename TEXT NOT NULL,
            resume_text TEXT,
            resume_data TEXT,
            difficulty TEXT DEFAULT 'fresher',
            total_questions INTEGER DEFAULT 0,
            completed_questions INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    ''')

    # Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT DEFAULT 'technical',
            order_num INTEGER DEFAULT 0,
            is_followup INTEGER DEFAULT 0,
            parent_question_id INTEGER,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
        )
    ''')

    # Answers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            strengths TEXT DEFAULT '[]',
            missing TEXT DEFAULT '[]',
            improved_answer TEXT DEFAULT '',
            evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
        )
    ''')

    # Reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER UNIQUE NOT NULL,
            overall_score REAL DEFAULT 0,
            technical_score REAL DEFAULT 0,
            communication_score REAL DEFAULT 0,
            project_score REAL DEFAULT 0,
            confidence_score REAL DEFAULT 0,
            hr_score REAL DEFAULT 0,
            strengths TEXT DEFAULT '[]',
            weaknesses TEXT DEFAULT '[]',
            recommendations TEXT DEFAULT '[]',
            overall_assessment TEXT DEFAULT '',
            hiring_recommendation TEXT DEFAULT 'Maybe',
            interview_summary TEXT DEFAULT '',
            interview_improvement_tips TEXT DEFAULT '[]',
            per_question_improvements TEXT DEFAULT '[]',
            gd_round TEXT DEFAULT '{}',
            rounds_guide TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
        )
    ''')

    # ─── Migrate existing reports table (add new columns if they don't exist) ───
    new_columns = [
        ('overall_assessment', 'TEXT DEFAULT ""'),
        ('hiring_recommendation', 'TEXT DEFAULT "Maybe"'),
        ('interview_summary', 'TEXT DEFAULT ""'),
        ('interview_improvement_tips', 'TEXT DEFAULT "[]"'),
        ('per_question_improvements', 'TEXT DEFAULT "[]"'),
        ('gd_round', 'TEXT DEFAULT "{}"'),
        ('rounds_guide', 'TEXT DEFAULT "[]"'),
    ]
    for col_name, col_def in new_columns:
        try:
            cursor.execute(f'ALTER TABLE reports ADD COLUMN {col_name} {col_def}')
        except Exception:
            pass  # Column already exists

    # ─── Migrate answers table (add key_concepts_to_know if needed) ───
    try:
        cursor.execute('ALTER TABLE answers ADD COLUMN key_concepts_to_know TEXT DEFAULT "[]"')
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully.")


# ─────────────────────────────────────────────
# Interview Session Operations
# ─────────────────────────────────────────────

def create_session(resume_filename, resume_text, resume_data, difficulty, total_questions):
    """Create a new interview session and return the session ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interview_sessions 
        (resume_filename, resume_text, resume_data, difficulty, total_questions, status)
        VALUES (?, ?, ?, ?, ?, 'active')
    ''', (resume_filename, resume_text, json.dumps(resume_data), difficulty, total_questions))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id):
    """Get a session by ID and return as a dict."""
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM interview_sessions WHERE id = ?', (session_id,)).fetchone()
    conn.close()
    if row:
        session = dict(row)
        session['resume_data'] = json.loads(session['resume_data'] or '{}')
        return session
    return None


def update_session_status(session_id, status):
    """Update session status (active/completed)."""
    conn = get_db_connection()
    completed_at = datetime.now().isoformat() if status == 'completed' else None
    conn.execute('''
        UPDATE interview_sessions SET status = ?, completed_at = ? WHERE id = ?
    ''', (status, completed_at, session_id))
    conn.commit()
    conn.close()


def update_session_completed_questions(session_id, count):
    """Update the count of completed questions in a session."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE interview_sessions SET completed_questions = ? WHERE id = ?
    ''', (count, session_id))
    conn.commit()
    conn.close()


def get_all_sessions():
    """Get all interview sessions ordered by newest first."""
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT s.*, r.overall_score 
        FROM interview_sessions s
        LEFT JOIN reports r ON s.id = r.session_id
        ORDER BY s.created_at DESC
    ''').fetchall()
    conn.close()
    sessions = []
    for row in rows:
        s = dict(row)
        s['resume_data'] = json.loads(s.get('resume_data') or '{}')
        sessions.append(s)
    return sessions


def get_dashboard_stats():
    """Return aggregated stats for the dashboard."""
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM interview_sessions WHERE status='completed'").fetchone()[0]
    avg_score = conn.execute("SELECT AVG(overall_score) FROM reports").fetchone()[0] or 0
    best_score = conn.execute("SELECT MAX(overall_score) FROM reports").fetchone()[0] or 0
    active = conn.execute("SELECT COUNT(*) FROM interview_sessions WHERE status='active'").fetchone()[0]
    conn.close()
    return {
        'total_completed': total,
        'avg_score': round(avg_score, 1),
        'best_score': round(best_score, 1),
        'active_sessions': active
    }


# ─────────────────────────────────────────────
# Question Operations
# ─────────────────────────────────────────────

def save_questions(session_id, questions_list):
    """
    Save a list of question dicts to the database.
    Each dict: { 'text': str, 'type': str, 'order': int }
    Returns list of inserted question IDs.
    """
    conn = get_db_connection()
    ids = []
    for q in questions_list:
        cursor = conn.execute('''
            INSERT INTO questions (session_id, question_text, question_type, order_num)
            VALUES (?, ?, ?, ?)
        ''', (session_id, q['text'], q['type'], q['order']))
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids


def get_question(question_id):
    """Get a single question by ID."""
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_session_questions(session_id):
    """Get all questions for a session ordered by order_num."""
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT * FROM questions WHERE session_id = ? ORDER BY order_num ASC
    ''', (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_followup_question(session_id, question_text, parent_id, order_num):
    """Save a dynamically generated follow-up question."""
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO questions (session_id, question_text, question_type, order_num, is_followup, parent_question_id)
        VALUES (?, ?, 'followup', ?, 1, ?)
    ''', (session_id, question_text, order_num, parent_id))
    qid = cursor.lastrowid
    conn.commit()
    conn.close()
    return qid


# ─────────────────────────────────────────────
# Answer Operations
# ─────────────────────────────────────────────

def save_answer(question_id, session_id, answer_text, evaluation):
    """Save an answer along with its AI evaluation (includes key concepts)."""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO answers
        (question_id, session_id, answer_text, score, strengths, missing, improved_answer, key_concepts_to_know)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        question_id,
        session_id,
        answer_text,
        evaluation.get('score', 0),
        json.dumps(evaluation.get('strengths', [])),
        json.dumps(evaluation.get('missing', [])),
        evaluation.get('improved_answer', ''),
        json.dumps(evaluation.get('key_concepts_to_know', []))
    ))
    conn.commit()
    conn.close()


def get_session_answers(session_id):
    """Get all answers with question text for a session."""
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT a.*, q.question_text, q.question_type
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.session_id = ?
        ORDER BY q.order_num ASC
    ''', (session_id,)).fetchall()
    conn.close()
    results = []
    for row in rows:
        r = dict(row)
        r['strengths']            = json.loads(r.get('strengths') or '[]')
        r['missing']              = json.loads(r.get('missing') or '[]')
        r['key_concepts_to_know'] = json.loads(r.get('key_concepts_to_know') or '[]')
        results.append(r)
    return results


# ─────────────────────────────────────────────
# Report Operations
# ─────────────────────────────────────────────

def save_report(session_id, report_data):
    """Save the final comprehensive report for a session (upsert)."""
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO reports
        (session_id, overall_score, technical_score, communication_score,
         project_score, confidence_score, hr_score,
         strengths, weaknesses, recommendations,
         overall_assessment, hiring_recommendation,
         interview_summary, interview_improvement_tips,
         per_question_improvements, gd_round, rounds_guide)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        report_data.get('overall_score', 0),
        report_data.get('technical_score', 0),
        report_data.get('communication_score', 0),
        report_data.get('project_score', 0),
        report_data.get('confidence_score', 0),
        report_data.get('hr_score', 0),
        json.dumps(report_data.get('strengths', [])),
        json.dumps(report_data.get('weaknesses', [])),
        json.dumps(report_data.get('recommendations', [])),
        report_data.get('overall_assessment', ''),
        report_data.get('hiring_recommendation', 'Maybe'),
        report_data.get('interview_summary', ''),
        json.dumps(report_data.get('interview_improvement_tips', [])),
        json.dumps(report_data.get('per_question_improvements', [])),
        json.dumps(report_data.get('gd_round', {})),
        json.dumps(report_data.get('rounds_guide', []))
    ))
    conn.commit()
    conn.close()


def get_report(session_id):
    """Get a full report by session ID, deserializing all JSON fields."""
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM reports WHERE session_id = ?', (session_id,)).fetchone()
    conn.close()
    if row:
        r = dict(row)
        r['strengths']                 = json.loads(r.get('strengths') or '[]')
        r['weaknesses']                = json.loads(r.get('weaknesses') or '[]')
        r['recommendations']           = json.loads(r.get('recommendations') or '[]')
        r['interview_improvement_tips']= json.loads(r.get('interview_improvement_tips') or '[]')
        r['per_question_improvements'] = json.loads(r.get('per_question_improvements') or '[]')
        r['gd_round']                  = json.loads(r.get('gd_round') or '{}')
        r['rounds_guide']              = json.loads(r.get('rounds_guide') or '[]')
        return r
    return None

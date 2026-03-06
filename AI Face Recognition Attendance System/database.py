import sqlite3
import os
from datetime import datetime

DB_PATH = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            registered_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            UNIQUE(student_id, date) -- Prevent duplicate attendance per day
        )
    ''')
    conn.commit()
    conn.close()

def add_student(student_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO students (student_id, name) VALUES (?, ?)", (student_id, name))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False # Student ID already exists
    conn.close()
    return success

def get_all_students():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY registered_on DESC")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return students

def mark_attendance(student_id):
    if not student_id:
        return False, "Invalid student ID."
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    try:
        cursor.execute("INSERT INTO attendance (student_id, date, time) VALUES (?, ?, ?)", (student_id, date_str, time_str))
        conn.commit()
        success = True
        msg = f"Attendance marked for {student_id}"
    except sqlite3.IntegrityError:
        # Duplicate attendance for today
        success = False
        msg = f"Attendance already marked for {student_id} today."
        
    conn.close()
    return success, msg

def get_attendance_report(date=None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, s.student_id, s.name, a.date, a.time 
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.date = ?
        ORDER BY a.time DESC
    ''', (date,))
    report = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return report

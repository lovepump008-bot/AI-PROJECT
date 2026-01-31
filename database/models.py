"""
models.py - Database Models สำหรับระบบ Smart Scan Face
ใช้ SQLite เก็บข้อมูลนักศึกษาและ log การเข้าเรียน
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta

# Thailand Timezone (UTC+7)
THAILAND_TZ = timezone(timedelta(hours=7))

def get_thai_time():
    """ดึงเวลาปัจจุบันของประเทศไทย (UTC+7)"""
    return datetime.now(THAILAND_TZ).strftime("%Y-%m-%d %H:%M:%S")

def get_thai_date():
    """ดึงวันที่ปัจจุบันของประเทศไทย"""
    return datetime.now(THAILAND_TZ).strftime("%Y-%m-%d")

# กำหนด path ของ database
DB_PATH = os.path.join(os.path.dirname(__file__), "smartscan.db")


def get_connection():
    """
    สร้าง connection ไปยัง SQLite database
    row_factory = sqlite3.Row ทำให้สามารถเข้าถึงข้อมูลแบบ dict ได้
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    สร้างตารางในฐานข้อมูลถ้ายังไม่มี
    - students: เก็บข้อมูลนักศึกษา
    - attendance_logs: เก็บ log การเข้าเรียน
    """
    conn = get_connection()
    cursor = conn.cursor()

    # === ตาราง students ===
    # เก็บข้อมูลนักศึกษาและ path ไปยังไฟล์ face encoding
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            first_name TEXT,
            last_name TEXT,
            face_encoding_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === ตาราง attendance_logs ===
    # เก็บ log การเช็คชื่อเข้าเรียน (รองรับเข้า-ออก)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            class_name TEXT,
            check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            check_out_time TIMESTAMP,
            face_image_path TEXT,
            status TEXT DEFAULT 'checked_in',
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)

    # เพิ่ม columns ถ้ายังไม่มี (สำหรับ database เก่า)
    try:
        cursor.execute("ALTER TABLE attendance_logs ADD COLUMN check_out_time TIMESTAMP")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE attendance_logs ADD COLUMN face_image_path TEXT")
    except:
        pass

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


# === STUDENT CRUD OPERATIONS ===

def add_student(face_encoding_path: str, student_id: str = None,
                first_name: str = None, last_name: str = None):
    """
    เพิ่มนักศึกษาใหม่เข้าฐานข้อมูล
    ขั้นตอนแรกจะมีแค่ face_encoding_path
    ชื่อและรหัสนักศึกษาจะถูกเพิ่มภายหลังโดย Admin
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students (student_id, first_name, last_name, face_encoding_path)
        VALUES (?, ?, ?, ?)
    """, (student_id, first_name, last_name, face_encoding_path))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_student(id: int, student_id: str, first_name: str, last_name: str):
    """
    อัพเดทข้อมูลนักศึกษา (ใช้ตอน Admin กรอกข้อมูล)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students
        SET student_id = ?, first_name = ?, last_name = ?, updated_at = ?
        WHERE id = ?
    """, (student_id, first_name, last_name, datetime.now(), id))

    conn.commit()
    conn.close()


def get_all_students():
    """ดึงข้อมูลนักศึกษาทั้งหมด"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY created_at DESC")
    students = cursor.fetchall()
    conn.close()
    return [dict(s) for s in students]


def get_student_by_id(id: int):
    """ดึงข้อมูลนักศึกษาจาก ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
    student = cursor.fetchone()
    conn.close()
    return dict(student) if student else None


def delete_student(id: int):
    """ลบนักศึกษาจากฐานข้อมูล"""
    conn = get_connection()
    cursor = conn.cursor()

    # ดึง path ของ face encoding ก่อนลบ
    cursor.execute("SELECT face_encoding_path FROM students WHERE id = ?", (id,))
    result = cursor.fetchone()

    if result:
        # ลบไฟล์ face encoding
        face_path = result['face_encoding_path']
        if os.path.exists(face_path):
            os.remove(face_path)

    # ลบ log ที่เกี่ยวข้อง
    cursor.execute("DELETE FROM attendance_logs WHERE student_id = ?", (id,))
    # ลบนักศึกษา
    cursor.execute("DELETE FROM students WHERE id = ?", (id,))

    conn.commit()
    conn.close()


# === ATTENDANCE LOG OPERATIONS ===

def add_attendance_log(student_id: int, class_name: str, face_image_path: str = None):
    """
    บันทึก log การเข้าเรียน (เช็คเข้า) - ใช้เวลาไทย
    """
    conn = get_connection()
    cursor = conn.cursor()
    thai_time = get_thai_time()

    cursor.execute("""
        INSERT INTO attendance_logs (student_id, class_name, face_image_path, status, check_in_time)
        VALUES (?, ?, ?, 'checked_in', ?)
    """, (student_id, class_name, face_image_path, thai_time))

    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def update_checkout_time(log_id: int, face_image_path: str = None):
    """
    อัพเดทเวลาเช็คออก - ใช้เวลาไทย
    """
    conn = get_connection()
    cursor = conn.cursor()
    thai_time = get_thai_time()

    if face_image_path:
        cursor.execute("""
            UPDATE attendance_logs 
            SET check_out_time = ?, status = 'checked_out', face_image_path = ?
            WHERE id = ?
        """, (thai_time, face_image_path, log_id))
    else:
        cursor.execute("""
            UPDATE attendance_logs 
            SET check_out_time = ?, status = 'checked_out'
            WHERE id = ?
        """, (thai_time, log_id))

    conn.commit()
    conn.close()


def get_active_checkin(student_id: int, class_name: str):
    """
    หา log ที่เช็คเข้าแล้วแต่ยังไม่เช็คออก (ของวันนี้) - ใช้เวลาไทย
    """
    conn = get_connection()
    cursor = conn.cursor()
    today = get_thai_date()

    cursor.execute("""
        SELECT * FROM attendance_logs 
        WHERE student_id = ? AND class_name = ? 
        AND DATE(check_in_time) = ? AND check_out_time IS NULL
        ORDER BY check_in_time DESC LIMIT 1
    """, (student_id, class_name, today))

    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def get_attendance_logs(limit: int = 100, date_filter: str = None):
    """
    ดึง log การเข้าเรียนล่าสุด พร้อมข้อมูลนักศึกษา
    """
    conn = get_connection()
    cursor = conn.cursor()

    if date_filter:
        cursor.execute("""
            SELECT
                al.id,
                al.class_name,
                al.check_in_time,
                al.check_out_time,
                al.face_image_path,
                al.status,
                s.student_id,
                s.first_name,
                s.last_name
            FROM attendance_logs al
            LEFT JOIN students s ON al.student_id = s.id
            WHERE DATE(al.check_in_time) = ?
            ORDER BY al.check_in_time DESC
            LIMIT ?
        """, (date_filter, limit))
    else:
        cursor.execute("""
            SELECT
                al.id,
                al.class_name,
                al.check_in_time,
                al.check_out_time,
                al.face_image_path,
                al.status,
                s.student_id,
                s.first_name,
                s.last_name
            FROM attendance_logs al
            LEFT JOIN students s ON al.student_id = s.id
            ORDER BY al.check_in_time DESC
            LIMIT ?
        """, (limit,))

    logs = cursor.fetchall()
    conn.close()
    return [dict(log) for log in logs]


def get_today_attendance(class_name: str = None):
    """
    ดึง log การเข้าเรียนของวันนี้ - ใช้เวลาไทย
    """
    conn = get_connection()
    cursor = conn.cursor()

    today = get_thai_date()

    if class_name:
        cursor.execute("""
            SELECT
                al.id,
                al.class_name,
                al.check_in_time,
                al.check_out_time,
                al.face_image_path,
                al.status,
                s.student_id,
                s.first_name,
                s.last_name
            FROM attendance_logs al
            LEFT JOIN students s ON al.student_id = s.id
            WHERE DATE(al.check_in_time) = ? AND al.class_name = ?
            ORDER BY al.check_in_time DESC
        """, (today, class_name))
    else:
        cursor.execute("""
            SELECT
                al.id,
                al.class_name,
                al.check_in_time,
                al.check_out_time,
                al.face_image_path,
                al.status,
                s.student_id,
                s.first_name,
                s.last_name
            FROM attendance_logs al
            LEFT JOIN students s ON al.student_id = s.id
            WHERE DATE(al.check_in_time) = ?
            ORDER BY al.check_in_time DESC
        """, (today,))

    logs = cursor.fetchall()
    conn.close()
    return [dict(log) for log in logs]


# เริ่มต้นสร้าง database เมื่อ import module
init_database()

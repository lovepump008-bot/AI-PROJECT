"""
main.py - FastAPI Application หลักของระบบ Smart Scan Face
ระบบเช็คชื่อเข้าห้องเรียนด้วยการสแกนใบหน้า
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import base64
import os
from datetime import datetime

# Import services
from face_recognition_service import face_service
from discord_service import discord_service
from database.models import (
    add_student, update_student, get_all_students,
    get_student_by_id, delete_student, add_attendance_log,
    get_attendance_logs, get_today_attendance, update_checkout_time,
    get_active_checkin
)
from config import DEFAULT_CLASS_NAME, HOST, PORT

# === สร้าง FastAPI Application ===
app = FastAPI(
    title="Smart Scan Face",
    description="ระบบเช็คชื่อเข้าห้องเรียนด้วยการสแกนใบหน้า",
    version="1.0.0"
)

# === Mount Static Files และ Templates ===
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# === Pydantic Models สำหรับ Request/Response ===

class StudentUpdate(BaseModel):
    """Model สำหรับอัพเดทข้อมูลนักศึกษา"""
    student_id: str
    first_name: str
    last_name: str


class FaceScanRequest(BaseModel):
    """Model สำหรับรับภาพจากการสแกนใบหน้า"""
    image_base64: str  # ภาพในรูปแบบ base64


class AttendanceRequest(BaseModel):
    """Model สำหรับเช็คชื่อเข้าเรียน"""
    image_base64: str
    class_name: Optional[str] = DEFAULT_CLASS_NAME
    scan_type: Optional[str] = "check_in"  # check_in or check_out


# === Page Routes (HTML Pages) ===

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """หน้าแรก - หน้าสแกนเช็คชื่อ"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """หน้าลงทะเบียนใบหน้านักศึกษาใหม่"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """หน้า Admin - จัดการข้อมูลนักศึกษา"""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """หน้าดู Log การเข้าเรียน"""
    return templates.TemplateResponse("logs.html", {"request": request})


# === API Routes ===

# --- Student Management APIs ---

@app.get("/api/students")
async def api_get_students():
    """
    ดึงข้อมูลนักศึกษาทั้งหมด
    ใช้แสดงในหน้า Admin
    """
    students = get_all_students()
    return {"success": True, "data": students}


@app.get("/api/students/{student_id}")
async def api_get_student(student_id: int):
    """ดึงข้อมูลนักศึกษาตาม ID"""
    student = get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"success": True, "data": student}


@app.put("/api/students/{id}")
async def api_update_student(id: int, data: StudentUpdate):
    """
    อัพเดทข้อมูลนักศึกษา (ชื่อ, รหัสนักศึกษา)
    ใช้ตอน Admin กรอกข้อมูลหลังจากลงทะเบียนใบหน้าแล้ว
    """
    student = get_student_by_id(id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_student(id, data.student_id, data.first_name, data.last_name)
    return {"success": True, "message": "Student updated successfully"}


@app.delete("/api/students/{id}")
async def api_delete_student(id: int):
    """ลบนักศึกษาออกจากระบบ"""
    student = get_student_by_id(id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    delete_student(id)
    return {"success": True, "message": "Student deleted successfully"}


# --- Face Registration APIs ---

@app.post("/api/register-face")
async def api_register_face(data: FaceScanRequest):
    """
    ลงทะเบียนใบหน้านักศึกษาใหม่

    ขั้นตอนการทำงาน:
    1. รับภาพ base64 จาก webcam
    2. ตรวจจับใบหน้าในภาพ
    3. สร้าง face encoding
    4. บันทึกลงฐานข้อมูล (ยังไม่มีชื่อ - รอ Admin กรอก)
    """
    # แปลง base64 เป็น image array
    image = face_service.process_image_from_base64(data.image_base64)

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image data")

    # ตรวจจับใบหน้า
    face_locations = face_service.detect_face(image)

    if len(face_locations) == 0:
        raise HTTPException(status_code=400, detail="ไม่พบใบหน้าในภาพ กรุณาลองใหม่")

    if len(face_locations) > 1:
        raise HTTPException(status_code=400, detail="พบใบหน้ามากกว่า 1 คน กรุณาให้มีแค่คนเดียวในภาพ")

    # สร้าง face encoding
    encoding = face_service.get_face_encoding(image)

    if encoding is None:
        raise HTTPException(status_code=400, detail="ไม่สามารถสร้างข้อมูลใบหน้าได้")

    # ตรวจสอบว่าใบหน้านี้มีในระบบแล้วหรือไม่
    students = get_all_students()
    existing = face_service.find_matching_student(encoding, students)

    if existing:
        name = f"{existing.get('first_name', '')} {existing.get('last_name', '')}".strip()
        if not name:
            name = f"ID: {existing['id']}"
        raise HTTPException(
            status_code=400,
            detail=f"ใบหน้านี้ลงทะเบียนแล้ว ({name})"
        )

    # บันทึกนักศึกษาใหม่ (ยังไม่มีข้อมูล รอ Admin กรอก)
    # ใช้ ID ชั่วคราวก่อน แล้วค่อยอัพเดท path
    temp_id = add_student(face_encoding_path="temp")

    # บันทึก face encoding
    encoding_path = face_service.save_face_encoding(encoding, temp_id)

    # อัพเดท path ในฐานข้อมูล
    from database.models import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE students SET face_encoding_path = ? WHERE id = ?",
        (encoding_path, temp_id)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "ลงทะเบียนใบหน้าสำเร็จ! กรุณาแจ้ง Admin เพื่อกรอกข้อมูล",
        "student_db_id": temp_id
    }


@app.post("/api/register-face-upload")
async def api_register_face_upload(file: UploadFile = File(...)):
    """
    ลงทะเบียนใบหน้าจากการอัพโหลดรูปภาพ
    (ทางเลือกแทนการใช้ webcam)
    """
    import cv2
    import numpy as np

    # อ่านไฟล์ภาพ
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # ตรวจจับใบหน้า
    face_locations = face_service.detect_face(image)

    if len(face_locations) == 0:
        raise HTTPException(status_code=400, detail="ไม่พบใบหน้าในภาพ")

    if len(face_locations) > 1:
        raise HTTPException(status_code=400, detail="พบใบหน้ามากกว่า 1 คน")

    # สร้าง face encoding
    encoding = face_service.get_face_encoding(image)

    if encoding is None:
        raise HTTPException(status_code=400, detail="ไม่สามารถสร้างข้อมูลใบหน้าได้")

    # ตรวจสอบว่าใบหน้านี้มีในระบบแล้วหรือไม่
    students = get_all_students()
    existing = face_service.find_matching_student(encoding, students)

    if existing:
        name = f"{existing.get('first_name', '')} {existing.get('last_name', '')}".strip()
        if not name:
            name = f"ID: {existing['id']}"
        raise HTTPException(
            status_code=400,
            detail=f"ใบหน้านี้ลงทะเบียนแล้ว ({name})"
        )

    # บันทึกนักศึกษาใหม่
    temp_id = add_student(face_encoding_path="temp")
    encoding_path = face_service.save_face_encoding(encoding, temp_id)

    from database.models import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE students SET face_encoding_path = ? WHERE id = ?",
        (encoding_path, temp_id)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "ลงทะเบียนใบหน้าสำเร็จ!",
        "student_db_id": temp_id
    }


# --- Attendance APIs ---

def save_face_capture(image_base64: str, student_id: int, scan_type: str) -> str:
    """
    บันทึกรูปใบหน้าที่สแกน
    """
    import cv2
    import numpy as np
    
    # ตัด header ออก
    if ',' in image_base64:
        image_base64 = image_base64.split(',')[1]
    
    # decode base64
    image_bytes = base64.b64decode(image_base64)
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # สร้างชื่อไฟล์
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{student_id}_{scan_type}_{timestamp}.jpg"
    filepath = f"static/captures/{filename}"
    
    # บันทึกไฟล์
    cv2.imwrite(filepath, image)
    
    return f"/static/captures/{filename}"


@app.post("/api/check-attendance")
async def api_check_attendance(data: AttendanceRequest):
    """
    เช็คชื่อเข้า/ออกด้วยการสแกนใบหน้า

    ขั้นตอนการทำงาน:
    1. รับภาพจาก webcam
    2. ตรวจจับและสร้าง encoding
    3. ค้นหานักศึกษาที่ match ในฐานข้อมูล
    4. บันทึก log และส่งแจ้งเตือน Discord
    """
    # แปลง base64 เป็น image
    image = face_service.process_image_from_base64(data.image_base64)

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image data")

    # ตรวจจับใบหน้า
    face_locations = face_service.detect_face(image)

    if len(face_locations) == 0:
        raise HTTPException(status_code=400, detail="ไม่พบใบหน้าในภาพ")

    # สร้าง face encoding
    encoding = face_service.get_face_encoding(image)

    if encoding is None:
        raise HTTPException(status_code=400, detail="ไม่สามารถประมวลผลใบหน้าได้")

    # ค้นหานักศึกษาที่ match
    students = get_all_students()
    matched_student = face_service.find_matching_student(encoding, students)

    if not matched_student:
        raise HTTPException(
            status_code=404,
            detail="ไม่พบข้อมูลในระบบ กรุณาลงทะเบียนก่อน"
        )

    # บันทึกรูปใบหน้า
    face_image_path = save_face_capture(data.image_base64, matched_student['id'], data.scan_type)

    # สร้างชื่อสำหรับแสดงผล
    display_name = f"{matched_student.get('first_name', 'ไม่ระบุ')} {matched_student.get('last_name', '')}".strip()
    student_id_display = matched_student.get('student_id') or 'ไม่ระบุรหัส'

    # ตรวจสอบประเภทการสแกน (check_in / check_out)
    if data.scan_type == "check_out":
        # หา log ที่เช็คเข้าแล้วแต่ยังไม่เช็คออก
        active_checkin = get_active_checkin(matched_student['id'], data.class_name)
        
        if not active_checkin:
            raise HTTPException(
                status_code=400,
                detail="ไม่พบการเช็คเข้าของวันนี้ กรุณาเช็คเข้าก่อน"
            )
        
        # อัพเดทเวลาเช็คออก
        update_checkout_time(active_checkin['id'], face_image_path)
        
        # ส่งแจ้งเตือนไป Discord
        await discord_service.send_attendance_log(
            student_id=matched_student.get('student_id'),
            first_name=matched_student.get('first_name'),
            last_name=matched_student.get('last_name'),
            class_name=data.class_name,
            scan_type="check_out",
            face_image_url=face_image_path
        )
        
        return {
            "success": True,
            "message": "เช็คออกสำเร็จ!",
            "scan_type": "check_out",
            "data": {
                "student_name": display_name,
                "student_id": student_id_display,
                "class_name": data.class_name,
                "check_out_time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "face_image": face_image_path
            }
        }
    else:
        # เช็คเข้า
        # ตรวจสอบว่าเช็คเข้าแล้วหรือยัง
        active_checkin = get_active_checkin(matched_student['id'], data.class_name)
        if active_checkin:
            raise HTTPException(
                status_code=400,
                detail="คุณเช็คเข้าแล้ววันนี้ กรุณาเช็คออกก่อน"
            )
        
        # บันทึก log การเข้าเรียน
        log_id = add_attendance_log(matched_student['id'], data.class_name, face_image_path)

        # ส่งแจ้งเตือนไป Discord
        await discord_service.send_attendance_log(
            student_id=matched_student.get('student_id'),
            first_name=matched_student.get('first_name'),
            last_name=matched_student.get('last_name'),
            class_name=data.class_name,
            scan_type="check_in",
            face_image_url=face_image_path
        )

        return {
            "success": True,
            "message": "เช็คเข้าสำเร็จ!",
            "scan_type": "check_in",
            "data": {
                "student_name": display_name,
                "student_id": student_id_display,
                "class_name": data.class_name,
                "check_in_time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "face_image": face_image_path
            }
        }


# --- Log APIs ---

@app.get("/api/logs")
async def api_get_logs(limit: int = 100, date: str = None):
    """ดึง log การเข้าเรียนทั้งหมด (สามารถกรองตามวันที่ได้)"""
    logs = get_attendance_logs(limit, date)
    return {"success": True, "data": logs}


@app.get("/api/logs/today")
async def api_get_today_logs(class_name: Optional[str] = None):
    """ดึง log การเข้าเรียนของวันนี้"""
    logs = get_today_attendance(class_name)
    return {"success": True, "data": logs}


# === Run Application ===
if __name__ == "__main__":
    print("=" * 50)
    print("🎯 Smart Scan Face - ระบบเช็คชื่อด้วยใบหน้า")
    print("=" * 50)
    print(f"🌐 Server: http://localhost:{PORT}")
    print(f"📋 Admin Panel: http://localhost:{PORT}/admin")
    print(f"📝 Register: http://localhost:{PORT}/register")
    print(f"📊 Logs: http://localhost:{PORT}/logs")
    print("=" * 50)

    uvicorn.run(app, host=HOST, port=PORT)

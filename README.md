# Smart Scan Face - ระบบเช็คชื่อเข้าห้องเรียนด้วยใบหน้า

ระบบเช็คชื่อเข้าเรียนอัตโนมัติโดยใช้เทคโนโลยี Face Recognition พัฒนาด้วย Python, FastAPI และ OpenCV

## คุณสมบัติ

- สแกนใบหน้าเพื่อเช็คชื่อเข้าเรียน
- ลงทะเบียนใบหน้านักศึกษาใหม่ (สแกนจากกล้องหรืออัพโหลดรูป)
- จัดการข้อมูลนักศึกษา (Admin Panel)
- บันทึก Log การเข้าเรียน
- ส่งแจ้งเตือนไป Discord เมื่อนักศึกษาเช็คชื่อ

## โครงสร้างโปรเจค

```
SmartScanFace/
├── main.py                     # FastAPI Application หลัก
├── config.py                   # ไฟล์ตั้งค่า
├── face_recognition_service.py # Service จดจำใบหน้า
├── discord_service.py          # Service ส่ง Discord
├── requirements.txt            # Dependencies
├── database/
│   ├── __init__.py
│   ├── models.py              # Database Models
│   └── smartscan.db           # SQLite Database (สร้างอัตโนมัติ)
├── face_data/                  # โฟลเดอร์เก็บ face encodings
├── static/
│   ├── css/
│   │   └── style.css          # Stylesheet
│   └── js/
│       └── camera.js          # JavaScript สำหรับกล้อง
└── templates/
    ├── base.html              # Template หลัก
    ├── index.html             # หน้าเช็คชื่อ
    ├── register.html          # หน้าลงทะเบียน
    ├── admin.html             # หน้า Admin
    └── logs.html              # หน้าดู Log
```

## การติดตั้ง

### 1. ติดตั้ง Dependencies

**สำหรับ Windows:**
```bash
# ติดตั้ง dlib ก่อน (แนะนำใช้ conda)
conda install -c conda-forge dlib

# หรือติดตั้งจาก wheel
pip install dlib

# ติดตั้ง requirements
pip install -r requirements.txt
```

**สำหรับ Linux/Mac:**
```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า Discord Webhook (ถ้าต้องการ)

1. สร้าง Webhook ใน Discord Server
   - ไปที่ Server Settings > Integrations > Webhooks
   - คลิก "New Webhook" และ copy URL

2. แก้ไขไฟล์ `config.py`:
```python
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/xxx/xxx"
```

### 3. รันระบบ

```bash
python main.py
```

เปิดเบราว์เซอร์ไปที่: http://localhost:8000

## วิธีใช้งาน

### ขั้นตอนที่ 1: ลงทะเบียนใบหน้านักศึกษา

1. ไปที่หน้า "ลงทะเบียน" (`/register`)
2. สแกนใบหน้าจากกล้อง หรืออัพโหลดรูปภาพ
3. ระบบจะบันทึกใบหน้าและสร้าง ID ในฐานข้อมูล

### ขั้นตอนที่ 2: Admin กรอกข้อมูลนักศึกษา

1. ไปที่หน้า "จัดการข้อมูล" (`/admin`)
2. คลิก "แก้ไข" ที่นักศึกษาที่ต้องการ
3. กรอกรหัสนักศึกษา, ชื่อ, นามสกุล
4. คลิก "บันทึก"

### ขั้นตอนที่ 3: เช็คชื่อเข้าเรียน

1. ไปที่หน้าหลัก (`/`)
2. เลือกวิชาที่ต้องการเช็คชื่อ
3. คลิก "สแกนเช็คชื่อ"
4. ระบบจะแสดงผลและส่ง Log ไป Discord

### ดู Log การเข้าเรียน

- ไปที่หน้า "ประวัติ" (`/logs`)
- สามารถกรองตามวิชาและช่วงเวลาได้

## API Endpoints

| Method | Endpoint | รายละเอียด |
|--------|----------|------------|
| GET | `/` | หน้าเช็คชื่อ |
| GET | `/register` | หน้าลงทะเบียน |
| GET | `/admin` | หน้า Admin |
| GET | `/logs` | หน้าดู Log |
| GET | `/api/students` | ดึงข้อมูลนักศึกษาทั้งหมด |
| GET | `/api/students/{id}` | ดึงข้อมูลนักศึกษาตาม ID |
| PUT | `/api/students/{id}` | อัพเดทข้อมูลนักศึกษา |
| DELETE | `/api/students/{id}` | ลบนักศึกษา |
| POST | `/api/register-face` | ลงทะเบียนใบหน้า (webcam) |
| POST | `/api/register-face-upload` | ลงทะเบียนใบหน้า (upload) |
| POST | `/api/check-attendance` | เช็คชื่อเข้าเรียน |
| GET | `/api/logs` | ดึง Log ทั้งหมด |
| GET | `/api/logs/today` | ดึง Log วันนี้ |

## เทคโนโลยีที่ใช้

- **Backend:** Python, FastAPI
- **Face Recognition:** face_recognition library, OpenCV, dlib
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Notification:** Discord Webhook

## หมายเหตุสำหรับอาจารย์

### โค้ดสำคัญและการทำงาน

1. **face_recognition_service.py** - หัวใจของระบบ
   - `get_face_encoding()`: สร้าง vector 128 มิติจากใบหน้า
   - `compare_faces()`: เปรียบเทียบใบหน้าด้วย Euclidean distance
   - `find_matching_student()`: ค้นหานักศึกษาที่ match

2. **main.py** - API endpoints
   - `api_register_face()`: รับภาพ → ตรวจจับใบหน้า → สร้าง encoding → บันทึก
   - `api_check_attendance()`: รับภาพ → สร้าง encoding → ค้นหา match → บันทึก log

3. **database/models.py** - จัดการฐานข้อมูล
   - ใช้ SQLite เก็บข้อมูลนักศึกษาและ log
   - face encoding เก็บเป็นไฟล์ .pkl แยก

### การปรับแต่ง

- **ความเข้มงวดในการจดจำ:** แก้ `FACE_RECOGNITION_TOLERANCE` ใน config.py
  - ค่าต่ำ (0.4) = เข้มงวด
  - ค่าสูง (0.8) = ผ่อนปรน

- **เพิ่มวิชา:** แก้ใน `templates/index.html` และ `templates/logs.html`

## ผู้พัฒนา

พัฒนาโดยนักศึกษาสำหรับวิชา AI ปัญญาประดิษฐ์

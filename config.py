"""
config.py - ไฟล์ตั้งค่าระบบ Smart Scan Face
ใช้เก็บค่า configuration ต่างๆ เช่น Discord Webhook, Database path
"""

import os
from datetime import timezone, timedelta

# === TIMEZONE CONFIGURATION ===
# Thailand timezone (UTC+7)
THAILAND_TZ = timezone(timedelta(hours=7))

# === DATABASE CONFIGURATION ===
# กำหนด path ของไฟล์ฐานข้อมูล SQLite
DATABASE_PATH = "database/smartscan.db"

# === DISCORD WEBHOOK CONFIGURATION ===
# URL สำหรับส่ง log ไปยัง Discord (ให้เปลี่ยนเป็น webhook URL ของคุณ)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1467135664943267933/N7GrzIb1S9aMiFIyciojzG1XciY_OeX2ncxoCZYu-sSNRUM75yfiQC4BwJkjvuk9ren8")

# === FACE RECOGNITION CONFIGURATION ===
# โฟลเดอร์เก็บข้อมูลใบหน้า (face encodings)
FACE_DATA_PATH = "face_data"

# ค่า tolerance สำหรับการเปรียบเทียบใบหน้า (ยิ่งต่ำยิ่งเข้มงวด)
# 0.6 = ค่าเริ่มต้น, 0.4 = เข้มงวดมาก, 0.8 = ผ่อนปรน
FACE_RECOGNITION_TOLERANCE = 0.6

# === CLASS CONFIGURATION ===
# ชื่อวิชาเริ่มต้น
DEFAULT_CLASS_NAME = "AI ปัญญาประดิษฐ์"

# === SERVER CONFIGURATION ===
HOST = "0.0.0.0"
PORT = 8000

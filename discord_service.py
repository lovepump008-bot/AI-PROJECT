"""
discord_service.py - บริการส่ง Log ไปยัง Discord
ใช้ Discord Webhook สำหรับส่งการแจ้งเตือนเมื่อนักศึกษาเช็คชื่อ
"""

import aiohttp
import asyncio
from datetime import datetime
from config import DISCORD_WEBHOOK_URL


class DiscordService:
    """
    Service class สำหรับส่งข้อความไปยัง Discord
    ใช้ Webhook URL ในการส่ง (ไม่ต้องใช้ bot token)
    """

    def __init__(self, webhook_url: str = DISCORD_WEBHOOK_URL):
        self.webhook_url = webhook_url

    async def send_attendance_log(self, student_id: str, first_name: str,
                                   last_name: str, class_name: str,
                                   scan_type: str = "check_in",
                                   face_image_url: str = None) -> bool:
        """
        ส่ง log การเข้า/ออกเรียนไปยัง Discord

        Args:
            student_id: รหัสนักศึกษา
            first_name: ชื่อ
            last_name: นามสกุล
            class_name: ชื่อวิชา
            scan_type: ประเภทการสแกน (check_in / check_out)
            face_image_url: URL รูปใบหน้าที่สแกน

        Returns:
            True ถ้าส่งสำเร็จ, False ถ้าล้มเหลว
        """
        # ตรวจสอบว่ามี webhook URL หรือไม่
        if not self.webhook_url or self.webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
            print("Warning: Discord Webhook URL not configured")
            return False

        # จัดรูปแบบเวลา
        current_time = datetime.now()
        time_str = current_time.strftime("%H:%M:%S")
        date_str = current_time.strftime("%d/%m/%Y")

        # สร้างชื่อเต็ม
        full_name = f"{first_name or 'ไม่ระบุชื่อ'} {last_name or ''}"
        student_id_display = student_id or "ไม่ระบุรหัส"

        # === กำหนดสีและข้อความตามประเภทการสแกน ===
        if scan_type == "check_out":
            title = "🚪 แจ้งเตือนการออก"
            color = 16753920  # สีส้ม
            time_label = "เวลาออก"
        else:
            title = "✅ แจ้งเตือนการเข้าเรียน"
            color = 5763719  # สีเขียว
            time_label = "เวลาเข้า"

        # === สร้าง Embed สำหรับ Discord ===
        embed = {
            "title": title,
            "color": color,
            "fields": [
                {
                    "name": "ชื่อนักศึกษา",
                    "value": full_name,
                    "inline": True
                },
                {
                    "name": "รหัสนักศึกษา",
                    "value": student_id_display,
                    "inline": True
                },
                {
                    "name": "วิชา",
                    "value": class_name,
                    "inline": False
                },
                {
                    "name": time_label,
                    "value": f"{time_str} น.",
                    "inline": True
                },
                {
                    "name": "วันที่",
                    "value": date_str,
                    "inline": True
                }
            ],
            "footer": {
                "text": "Smart Scan Face - ระบบเช็คชื่อด้วยใบหน้า"
            },
            "timestamp": current_time.isoformat()
        }

        # payload สำหรับส่งไป Discord
        payload = {
            "embeds": [embed]
        }

        try:
            # ใช้ aiohttp สำหรับ async HTTP request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        print(f"Discord log sent: {full_name} เข้าเรียน {class_name}")
                        return True
                    else:
                        print(f"Discord error: {response.status}")
                        return False

        except Exception as e:
            print(f"Discord send failed: {e}")
            return False

    def send_attendance_log_sync(self, student_id: str, first_name: str,
                                  last_name: str, class_name: str,
                                  scan_type: str = "check_in",
                                  face_image_url: str = None) -> bool:
        """
        Version synchronous สำหรับเรียกใช้จาก non-async code
        """
        return asyncio.run(
            self.send_attendance_log(student_id, first_name, last_name, class_name, scan_type, face_image_url)
        )


# สร้าง instance สำหรับใช้งาน
discord_service = DiscordService()

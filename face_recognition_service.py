"""
face_recognition_service.py - บริการจดจำใบหน้า
ใช้ face_recognition library (ที่ใช้ dlib) และ OpenCV สำหรับตรวจจับและจดจำใบหน้า
"""

import face_recognition
import cv2
import numpy as np
import os
import pickle
from datetime import datetime
from typing import Optional, Tuple, List
from config import FACE_DATA_PATH, FACE_RECOGNITION_TOLERANCE


class FaceRecognitionService:
    """
    Service class สำหรับจัดการการจดจำใบหน้า
    - ตรวจจับใบหน้าจากภาพ
    - สร้าง face encoding (ข้อมูลเฉพาะของใบหน้า)
    - เปรียบเทียบใบหน้ากับฐานข้อมูล
    """

    def __init__(self):
        # สร้างโฟลเดอร์เก็บ face data ถ้ายังไม่มี
        if not os.path.exists(FACE_DATA_PATH):
            os.makedirs(FACE_DATA_PATH)

    def detect_face(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        ตรวจจับตำแหน่งใบหน้าในภาพ

        Args:
            image: ภาพในรูปแบบ numpy array (BGR จาก OpenCV)

        Returns:
            List ของตำแหน่งใบหน้า [(top, right, bottom, left), ...]
        """
        # แปลงจาก BGR (OpenCV) เป็น RGB (face_recognition)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # ค้นหาตำแหน่งใบหน้าในภาพ
        # model="hog" เร็วกว่า, model="cnn" แม่นยำกว่า (ต้องใช้ GPU)
        face_locations = face_recognition.face_locations(rgb_image, model="hog")

        return face_locations

    def get_face_encoding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        สร้าง face encoding จากภาพ
        Face encoding คือ vector 128 มิติที่ represent ใบหน้าแต่ละคน

        Args:
            image: ภาพในรูปแบบ numpy array

        Returns:
            numpy array ขนาด 128 มิติ หรือ None ถ้าไม่พบใบหน้า
        """
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # ค้นหาใบหน้า
        face_locations = face_recognition.face_locations(rgb_image, model="hog")

        if len(face_locations) == 0:
            return None

        # สร้าง encoding จากใบหน้าแรกที่พบ
        # face_encodings() return list ของ encodings สำหรับทุกใบหน้าที่พบ
        encodings = face_recognition.face_encodings(rgb_image, face_locations)

        if len(encodings) > 0:
            return encodings[0]
        return None

    def save_face_encoding(self, encoding: np.ndarray, student_db_id: int) -> str:
        """
        บันทึก face encoding ลงไฟล์
        ใช้ pickle สำหรับ serialize numpy array

        Args:
            encoding: face encoding array
            student_db_id: ID ของนักศึกษาในฐานข้อมูล

        Returns:
            path ของไฟล์ที่บันทึก
        """
        filename = f"face_{student_db_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        filepath = os.path.join(FACE_DATA_PATH, filename)

        with open(filepath, 'wb') as f:
            pickle.dump(encoding, f)

        return filepath

    def load_face_encoding(self, filepath: str) -> Optional[np.ndarray]:
        """
        โหลด face encoding จากไฟล์
        """
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'rb') as f:
            return pickle.load(f)

    def compare_faces(self, known_encoding: np.ndarray,
                      unknown_encoding: np.ndarray) -> Tuple[bool, float]:
        """
        เปรียบเทียบใบหน้า 2 ใบหน้า

        Args:
            known_encoding: encoding ของใบหน้าที่รู้จัก (จากฐานข้อมูล)
            unknown_encoding: encoding ของใบหน้าที่ต้องการตรวจสอบ

        Returns:
            (is_match, distance)
            - is_match: True ถ้าเป็นคนเดียวกัน
            - distance: ค่าความแตกต่าง (ยิ่งน้อยยิ่งเหมือน)
        """
        # face_distance คำนวณ Euclidean distance ระหว่าง encodings
        # ค่ายิ่งน้อย = ยิ่งเหมือนกัน
        distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]

        # compare_faces ใช้ tolerance เป็นเกณฑ์ตัดสิน
        is_match = face_recognition.compare_faces(
            [known_encoding],
            unknown_encoding,
            tolerance=FACE_RECOGNITION_TOLERANCE
        )[0]

        return is_match, distance

    def find_matching_student(self, unknown_encoding: np.ndarray,
                              students: list) -> Optional[dict]:
        """
        ค้นหานักศึกษาที่ match กับใบหน้าที่สแกน

        Args:
            unknown_encoding: encoding ของใบหน้าที่สแกน
            students: list ของข้อมูลนักศึกษาจากฐานข้อมูล

        Returns:
            dict ของนักศึกษาที่ match หรือ None ถ้าไม่พบ
        """
        best_match = None
        best_distance = float('inf')

        for student in students:
            # โหลด encoding ของนักศึกษา
            known_encoding = self.load_face_encoding(student['face_encoding_path'])

            if known_encoding is None:
                continue

            # เปรียบเทียบใบหน้า
            is_match, distance = self.compare_faces(known_encoding, unknown_encoding)

            # เก็บ match ที่ดีที่สุด (distance น้อยที่สุด)
            if is_match and distance < best_distance:
                best_match = student
                best_distance = distance

        return best_match

    def process_image_from_base64(self, base64_string: str) -> Optional[np.ndarray]:
        """
        แปลงภาพจาก base64 string เป็น numpy array
        ใช้สำหรับรับภาพจาก frontend (webcam capture)

        Args:
            base64_string: ภาพในรูปแบบ base64

        Returns:
            numpy array ของภาพ
        """
        import base64

        # ตัด header ออก (data:image/jpeg;base64,)
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]

        # decode base64 เป็น bytes
        image_bytes = base64.b64decode(base64_string)

        # แปลง bytes เป็น numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)

        # decode เป็นภาพ
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        return image

    def draw_face_rectangle(self, image: np.ndarray,
                           face_locations: list) -> np.ndarray:
        """
        วาดกรอบสี่เหลี่ยมรอบใบหน้าที่ตรวจพบ
        ใช้สำหรับ debug หรือแสดงผลบน UI
        """
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)

        return image


# สร้าง instance สำหรับใช้งาน
face_service = FaceRecognitionService()

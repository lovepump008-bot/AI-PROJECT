/**
 * camera.js - JavaScript สำหรับจัดการกล้อง Webcam
 * ใช้ MediaDevices API ในการเข้าถึงกล้อง
 */

// เก็บ stream ของกล้องเพื่อใช้ปิดภายหลัง
let cameraStream = null;

/**
 * เริ่มต้นกล้อง Webcam
 * ขอสิทธิ์ใช้งานกล้องจาก browser และแสดงภาพบน video element
 *
 * @param {string} videoElementId - ID ของ <video> element
 */
async function initCamera(videoElementId) {
    const video = document.getElementById(videoElementId);

    if (!video) {
        console.error('Video element not found:', videoElementId);
        return;
    }

    try {
        // ขอสิทธิ์ใช้งานกล้อง
        // constraints กำหนดว่าต้องการ video (ไม่ต้องการ audio)
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },      // ความกว้างที่ต้องการ
                height: { ideal: 480 },     // ความสูงที่ต้องการ
                facingMode: 'user'          // ใช้กล้องหน้า (front camera)
            },
            audio: false
        });

        // เก็บ stream ไว้
        cameraStream = stream;

        // แสดงภาพจากกล้องบน video element
        video.srcObject = stream;

        console.log('Camera initialized successfully');

    } catch (error) {
        // จัดการ error กรณีไม่ได้รับอนุญาตหรือไม่มีกล้อง
        console.error('Camera error:', error);

        if (error.name === 'NotAllowedError') {
            alert('กรุณาอนุญาตการใช้งานกล้องในเบราว์เซอร์');
        } else if (error.name === 'NotFoundError') {
            alert('ไม่พบกล้องในอุปกรณ์นี้');
        } else {
            alert('ไม่สามารถเข้าถึงกล้องได้: ' + error.message);
        }
    }
}

/**
 * จับภาพจาก video และแปลงเป็น base64
 * ใช้ canvas เป็นตัวกลางในการจับภาพ
 *
 * @param {string} videoElementId - ID ของ <video> element
 * @param {string} canvasElementId - ID ของ <canvas> element
 * @returns {string} - ภาพในรูปแบบ base64 (data URL)
 */
function captureImage(videoElementId, canvasElementId) {
    const video = document.getElementById(videoElementId);
    const canvas = document.getElementById(canvasElementId);

    if (!video || !canvas) {
        console.error('Video or canvas element not found');
        return null;
    }

    // ตั้งขนาด canvas ให้เท่ากับ video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // วาดภาพจาก video ลงบน canvas
    // ต้อง flip ภาพเพราะ video ถูก mirror ด้วย CSS
    const ctx = canvas.getContext('2d');

    // Flip horizontal เพื่อให้ภาพไม่กลับซ้าย-ขวา
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);

    // วาดภาพ
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Reset transformation
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    // แปลง canvas เป็น base64 (JPEG format, quality 90%)
    const imageData = canvas.toDataURL('image/jpeg', 0.9);

    return imageData;
}

/**
 * ปิดกล้อง (หยุด stream)
 * ควรเรียกเมื่อไม่ใช้งานกล้องแล้ว
 */
function stopCamera() {
    if (cameraStream) {
        // หยุดทุก track ใน stream
        cameraStream.getTracks().forEach(track => {
            track.stop();
        });
        cameraStream = null;
        console.log('Camera stopped');
    }
}

/**
 * สลับกล้อง (หน้า/หลัง) - สำหรับมือถือ
 */
async function switchCamera() {
    // หยุดกล้องปัจจุบัน
    stopCamera();

    // ตรวจสอบว่าใช้กล้องหน้าหรือหลังอยู่
    const currentFacing = cameraStream?.getVideoTracks()[0]?.getSettings()?.facingMode;
    const newFacing = currentFacing === 'user' ? 'environment' : 'user';

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: newFacing
            },
            audio: false
        });

        cameraStream = stream;

        const video = document.querySelector('video');
        if (video) {
            video.srcObject = stream;
        }

    } catch (error) {
        console.error('Switch camera error:', error);
    }
}

/**
 * ตรวจสอบว่า browser รองรับการใช้งานกล้องหรือไม่
 * @returns {boolean}
 */
function isCameraSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

// ตรวจสอบ support เมื่อโหลดหน้า
if (!isCameraSupported()) {
    console.warn('Camera not supported in this browser');
}

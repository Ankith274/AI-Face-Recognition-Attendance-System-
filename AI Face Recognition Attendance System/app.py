import os
import base64
import numpy as np
import cv2
from flask import Flask, render_template, request, jsonify

from database import init_db, add_student, get_all_students, mark_attendance, get_attendance_report
from face_logic import extract_faces, train_model, predict_face, FACES_DIR

app = Flask(__name__)
app.secret_key = "secret_attendance_key"

# Ensure directories exist
os.makedirs(FACES_DIR, exist_ok=True)
init_db()

def decode_image(b64_string):
    header, encoded = b64_string.split(",", 1)
    data = base64.b64decode(encoded)
    np_arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/api/students', methods=['GET'])
def api_students():
    students = get_all_students()
    return jsonify(students)

@app.route('/api/attendance', methods=['GET'])
def api_attendance():
    date = request.args.get('date')
    report = get_attendance_report(date)
    return jsonify(report)

@app.route('/api/register_student', methods=['POST'])
def api_register_student():
    data = request.json
    student_id = data.get('student_id')
    name = data.get('name')
    if not student_id or not name:
        return jsonify({"success": False, "message": "Student ID and Name required."})
    
    if add_student(student_id, name):
        # Create a directory for their faces
        os.makedirs(os.path.join(FACES_DIR, student_id), exist_ok=True)
        return jsonify({"success": True, "message": "Student registered successfully. Proceed to capture faces."})
    else:
        return jsonify({"success": False, "message": "Student ID already exists."})

@app.route('/api/upload_training_frame', methods=['POST'])
def api_upload_training_frame():
    data = request.json
    student_id = data.get('student_id')
    image_b64 = data.get('image')
    
    if not student_id or not image_b64:
        return jsonify({"success": False, "message": "Missing parameters."})
        
    img = decode_image(image_b64)
    faces = extract_faces(img)
    
    if not faces:
        return jsonify({"success": False, "message": "No face detected in frame."})
    
    # Take the largest face if multiple
    faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
    x, y, w, h, face_roi = faces[0]
    
    # Save the face
    student_dir = os.path.join(FACES_DIR, student_id)
    count = len(os.listdir(student_dir))
    if count >= 30: # Max 30 frames per student to prevent over-capturing
        return jsonify({"success": False, "message": "Maximum frames (30) collected. Please train the model."})
        
    cv2.imwrite(os.path.join(student_dir, f"{count}.jpg"), face_roi)
    return jsonify({"success": True, "message": "Face captured.", "count": count + 1})


@app.route('/api/train', methods=['POST'])
def api_train():
    success, msg = train_model()
    return jsonify({"success": success, "message": msg})


@app.route('/api/recognize_frame', methods=['POST'])
def api_recognize():
    data = request.json
    image_b64 = data.get('image')
    
    if not image_b64:
        return jsonify({"success": False, "message": "No image provided."})
        
    img = decode_image(image_b64)
    faces = extract_faces(img)
    
    if not faces:
        return jsonify({"success": False, "message": "No face detected.", "recognized": False})
        
    # Take the largest face
    faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
    x, y, w, h, face_roi = faces[0]
    
    student_id, confidence = predict_face(face_roi)
    
    if student_id:
        # We got a match, try marking attendance
        success, msg = mark_attendance(student_id)
        return jsonify({
            "success": True, 
            "recognized": True, 
            "student_id": student_id,
            "confidence": confidence,
            "message": msg,
            "attendance_marked": success
        })
    else:
        return jsonify({
            "success": True, 
            "recognized": False, 
            "message": "Face not recognized."
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

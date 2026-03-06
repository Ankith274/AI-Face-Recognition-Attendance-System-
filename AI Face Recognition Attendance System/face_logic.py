import cv2
import numpy as np
import os
import json

FACES_DIR = "static/faces"
MODEL_PATH = "face_model.yml"
LABEL_MAP_PATH = "label_map.json"

# Load Haar cascade for face detection
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def ensure_dir_exists():
    if not os.path.exists(FACES_DIR):
        os.makedirs(FACES_DIR)

def extract_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_classifier.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(50, 50))
    if len(faces) == 0:
        return []
    
    extracted = []
    for (x, y, w, h) in faces:
        extracted.append((x, y, w, h, gray[y:y+h, x:x+w]))
    return extracted

def train_model():
    ensure_dir_exists()
    faces = []
    labels = []
    
    student_dirs = [d for d in os.listdir(FACES_DIR) if os.path.isdir(os.path.join(FACES_DIR, d))]
    
    label_map = {}
    current_label = 0
    
    for student_id in student_dirs:
        student_path = os.path.join(FACES_DIR, student_id)
        if not os.listdir(student_path):
            continue
            
        label_map[current_label] = student_id
        
        for img_name in os.listdir(student_path):
            img_path = os.path.join(student_path, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                labels.append(current_label)
                
        current_label += 1
        
    if len(faces) == 0:
        return False, "No training data found."
        
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.write(MODEL_PATH)
    
    with open(LABEL_MAP_PATH, "w") as f:
        json.dump(label_map, f)
        
    return True, f"Model trained with {len(student_dirs)} students."

def predict_face(face_roi):
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABEL_MAP_PATH):
        return None, 0
        
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    
    with open(LABEL_MAP_PATH, "r") as f:
        label_map = json.load(f)
        
    label, confidence = recognizer.predict(face_roi)
    
    # In LBPH, lower confidence is better (distance metric). 
    # Usually < 60-70 is a good match.
    if confidence < 75:
        student_id = label_map.get(str(label))
        return student_id, confidence
    return None, confidence

// Helper function to extract frame from video
function captureFrame(video) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    // Mirror the capture since video is mirrored
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.8);
}

// Global Camera Initialization
async function setupCamera() {
    const video = document.getElementById('webcam');
    if (!video) return null;
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: "user" }, 
            audio: false 
        });
        video.srcObject = stream;
        
        return new Promise((resolve) => {
            video.onloadedmetadata = () => {
                resolve(video);
            };
        });
    } catch (err) {
        console.error("Camera error:", err);
        alert("Could not access the camera. Please allow camera permissions.");
        return null;
    }
}

// -----------------------------------------
// Scanner Logic (index.html)
// -----------------------------------------
let scanInterval = null;

async function initScanner() {
    const video = await setupCamera();
    if (!video) return;

    const overlay = document.querySelector('.scan-overlay');
    const statusTitle = document.getElementById('status-title');
    const statusText = document.getElementById('status-text');
    const statusCard = document.querySelector('.status-card');
    const scanList = document.getElementById('scan-list');

    let isProcessing = false;

    // Scan heavily (every 1 second)
    scanInterval = setInterval(async () => {
        if (isProcessing) return;
        isProcessing = true;

        const frame = captureFrame(video);
        
        try {
            const res = await fetch('/api/recognize_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: frame })
            });

            const data = await res.json();
            
            if (data.recognized) {
                // We found a face
                statusTitle.innerText = `Matched: ${data.student_id}`;
                statusText.innerText = data.message;
                
                if (data.attendance_marked) {
                    statusCard.className = 'status-card success';
                    
                    // Add to list
                    const li = document.createElement('li');
                    li.innerHTML = `✅ <strong>${data.student_id}</strong> - ${new Date().toLocaleTimeString()} <br><small>Confidence: ${data.confidence.toFixed(2)}</small>`;
                    scanList.prepend(li); // add to top
                    
                    // Pause briefly to let user see success
                    overlay.style.animation = 'none';
                    overlay.style.top = '100%';
                    await new Promise(r => setTimeout(r, 2000));
                    overlay.style.animation = 'scanLine 3s infinite linear';
                } else {
                    // Already marked
                    statusCard.className = 'status-card error';
                    await new Promise(r => setTimeout(r, 1500));
                }
            } else {
                // Reset to default
                statusTitle.innerText = "System Ready";
                statusText.innerText = "Position your face inside the frame.";
                statusCard.className = 'status-card';
            }
        } catch (err) {
            console.error(err);
        }

        isProcessing = false;
    }, 1500);
}

// -----------------------------------------
// Registration Logic (register.html)
// -----------------------------------------
let capInterval = null;

async function initRegister() {
    const form = document.getElementById('register-form');
    if (!form) return;

    // Only start camera when needed, or start it right away.
    // Let's start right away so user sees themselves.
    const video = await setupCamera();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const studentId = document.getElementById('student_id').value;
        const name = document.getElementById('name').value;

        try {
            const res = await fetch('/api/register_student', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: studentId, name: name })
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message);
                document.getElementById('capture-section').classList.remove('hidden');
                document.getElementById('start-btn').disabled = true;
                
                // Set up capture btn
                const capBtn = document.getElementById('capture-btn');
                capBtn.onclick = () => startFaceCapture(video, studentId);
            } else {
                alert(data.message);
            }
        } catch (err) {
            console.error(err);
        }
    });

    document.getElementById('train-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('train-btn');
        btn.innerText = "Training...";
        btn.disabled = true;

        try {
            const res = await fetch('/api/train', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            if (data.success) {
                window.location.href = '/admin';
            }
        } catch (err) {
            console.error(err);
        }
        
        btn.innerText = "3. Train AI Model";
        btn.disabled = false;
    });
}

async function startFaceCapture(video, studentId) {
    if (!video) return;
    
    document.getElementById('capture-btn').disabled = true;
    document.getElementById('capture-btn').innerText = "Scanning...";
    document.getElementById('register-overlay').classList.remove('hidden');

    let isProcessing = false;
    
    // Capture every 200ms
    capInterval = setInterval(async () => {
        if (isProcessing) return;
        isProcessing = true;
        
        const frame = captureFrame(video);
        
        try {
            const res = await fetch('/api/upload_training_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: studentId, image: frame })
            });

            const data = await res.json();
            
            if (data.success) {
                const count = data.count;
                document.getElementById('capture-status').innerText = `${count} / 30 frames captured`;
                const pct = (count / 30) * 100;
                document.getElementById('progress-fill').style.width = pct + '%';

                if (count >= 30) {
                    clearInterval(capInterval);
                    document.getElementById('register-overlay').classList.add('hidden');
                    document.getElementById('capture-btn').innerText = "Capture Complete";
                    document.getElementById('train-btn').classList.remove('hidden');
                }
            } else if (data.message.includes("Maximum frames")) {
                clearInterval(capInterval);
                document.getElementById('register-overlay').classList.add('hidden');
                document.getElementById('capture-btn').innerText = "Capture Complete";
                document.getElementById('train-btn').classList.remove('hidden');
            }
        } catch (err) {
            console.error(err);
        }

        isProcessing = false;
    }, 200);
}

// -----------------------------------------
// Admin Dashboard (admin.html)
// -----------------------------------------

async function loadAttendance() {
    const tbody = document.getElementById('attendance-tbody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/attendance');
        const data = await res.json();
        
        tbody.innerHTML = '';
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${row.student_id}</strong></td>
                <td>${row.name}</td>
                <td>${row.time}</td>
                <td>${row.date}</td>
            `;
            tbody.appendChild(tr);
        });

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No attendance recorded today.</td></tr>';
        }
    } catch (err) {
        console.error(err);
    }
}

async function loadStudents() {
    const tbody = document.getElementById('students-tbody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/students');
        const data = await res.json();
        
        tbody.innerHTML = '';
        data.forEach(row => {
            const tr = document.createElement('tr');
            // convert timestamp
            let date = new Date(row.registered_on).toLocaleString();
            tr.innerHTML = `
                <td><strong>${row.student_id}</strong></td>
                <td>${row.name}</td>
                <td>${date}</td>
            `;
            tbody.appendChild(tr);
        });

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No students registered yet.</td></tr>';
        }
    } catch (err) {
        console.error(err);
    }
}

async function trainModel() {
    if(!confirm("Retrain the Face Recognition model? This may take a few moments.")) return;
    
    try {
        const res = await fetch('/api/train', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        console.error(err);
        alert("An error occurred while training model.");
    }
}

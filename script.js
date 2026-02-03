// ... (existing code)

// Enrollment demo
const enrollForm = document.getElementById('enroll-form');  // Assume you add this form
enrollForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData();
  formData.append('name', 'User Name');
  formData.append('email', 'user@email.com');
  // Capture multiple frames and append as 'image1', 'image2', etc.
  // Use canvas to capture 10 frames over time
  for (let i = 1; i <= 10; i++) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    canvas.toBlob(blob => formData.append(`image${i}`, blob, `image${i}.jpg`));
    await new Promise(r => setTimeout(r, 200));  // Delay for angles
  }
  
  const response = await fetch('/api/enroll', { method: 'POST', body: formData });
  const data = await response.json();
  alert(data.message);
});

// Recognition for attendance
async function recordAttendance() {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const formData = new FormData();
  canvas.toBlob(blob => formData.append('image', blob, 'capture.jpg'));
  
  const response = await fetch('/api/recognize', { method: 'POST', body: formData });
  const data = await response.json();
  alert(data.message);  // "Attendance recorded with your face"
}

// Call recordAttendance() on button click

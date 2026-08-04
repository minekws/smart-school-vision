document.addEventListener('DOMContentLoaded', function() {
    const name = document.getElementById('user-name');

    const role = document.getElementById('user-role');
    const cameraid = localStorage.getItem('cameraId');

    name.innerHTML = localStorage.getItem('username');
    role.innerHTML = localStorage.getItem('userRole');

    const cameraImg = document.getElementById('camer');

    const cameraId = localStorage.getItem('cameraId');

    if (cameraId) {
        cameraImg.src = `http://127.0.0.1:5000/${cameraId}/video_feed`;
    } else {
        console.error('camera_id не найден в localStorage!');
    }
});
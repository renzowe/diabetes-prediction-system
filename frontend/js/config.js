// En desarrollo local, usar el backend publicado por Docker.
// Conservar Render para el frontend desplegado.
const IS_LOCAL = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
const API_BASE = IS_LOCAL
    ? `http://${window.location.hostname}:8000`
    : 'https://diabetes-prediction-system-vs7y.onrender.com';

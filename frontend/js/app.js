// La URL del backend viene de config.js (cargado antes de este archivo)
const CIRCUMFERENCE = 339.3; // 2 * PI * r(54), debe coincidir con style.css

const screens = {
    start: document.getElementById('screen-start'),
    form: document.getElementById('screen-form'),
    result: document.getElementById('screen-result'),
};

let startTime = null;
let participantCode = '';

function showScreen(name) {
    Object.values(screens).forEach((el) => el.setAttribute('hidden', ''));
    screens[name].removeAttribute('hidden');
}

function nivelRiesgo(pct) {
    if (pct < 30) return 'bajo';
    if (pct < 60) return 'moderado';
    return 'alto';
}

const EXPLICACIONES = {
    bajo: 'Tus datos actuales no muestran señales fuertes de riesgo. Mantener hábitos saludables ayuda a que se mantenga así.',
    moderado: 'Se observan algunos factores que conviene vigilar. Considera conversarlo con un profesional de salud en tu próximo control.',
    alto: 'Varios factores sugieren un riesgo elevado. Te recomendamos acudir a un profesional de salud para una evaluación completa.',
};

// --- Pantalla 1: inicio ---
document.getElementById('btn-start').addEventListener('click', () => {
    const codigoInput = document.getElementById('codigo-participante');
    participantCode = codigoInput.value.trim() || 'anonimo';
    startTime = performance.now();
    showScreen('form');
});

// Evita que el navegador recargue la pagina si el participante presiona
// Enter dentro del formulario (comportamiento nativo de <form>).
document.getElementById('screen-form').addEventListener('submit', (e) => {
    e.preventDefault();
    document.getElementById('btn-submit').click();
});

// --- Pantalla 2: formulario ---
document.getElementById('btn-submit').addEventListener('click', async () => {
    const errorEl = document.getElementById('form-error');
    errorEl.hidden = true;

    const form = document.getElementById('screen-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const payload = {
        edad: Number(document.getElementById('edad').value),
        genero: document.getElementById('genero').value,
        hipertension: Number(document.querySelector('input[name="hipertension"]:checked').value),
        enfermedad_cardiaca: Number(document.querySelector('input[name="cardiaca"]:checked').value),
        historial_tabaquismo: document.getElementById('tabaquismo').value,
        imc: Number(document.getElementById('imc').value),
        hba1c: Number(document.getElementById('hba1c').value),
        glucosa: Number(document.getElementById('glucosa').value),
        momento: 'sistema',
        tiempo_segundos: Number(((performance.now() - startTime) / 1000).toFixed(1)),
        participante_codigo: participantCode,
    };

    const btn = document.getElementById('btn-submit');
    btn.disabled = true;
    btn.textContent = 'Evaluando…';

    try {
        const res = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const detail = await res.json().catch(() => null);
            throw new Error(detail?.detail ? JSON.stringify(detail.detail) : `Error del servidor (${res.status})`);
        }

        const data = await res.json();
        mostrarResultado(data, payload.tiempo_segundos);
    } catch (err) {
        errorEl.textContent = `No se pudo obtener el resultado: ${err.message}. Verifica que el servidor esté activo e inténtalo de nuevo.`;
        errorEl.hidden = false;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Evaluar mi riesgo';
    }
});

// --- Pantalla 3: resultado ---
function mostrarResultado(data, tiempoSegundos) {
    const pct = Math.round(data.probabilidad * 100);
    const nivel = data.nivel_riesgo || nivelRiesgo(pct);

    document.getElementById('result-pct').textContent = `${pct}%`;

    const labelEl = document.getElementById('result-label');
    labelEl.textContent = { bajo: 'Riesgo bajo', moderado: 'Riesgo moderado', alto: 'Riesgo alto' }[nivel];
    labelEl.className = `result__label result__label--${nivel}`;

    document.getElementById('result-explain').textContent = EXPLICACIONES[nivel];
    document.getElementById('result-meta').textContent =
        `Participante ${participantCode} · evaluado en ${tiempoSegundos}s · registro #${data.id}`;
    document.getElementById('link-sus').href = `sus.html?codigo=${encodeURIComponent(participantCode)}`;

    const gaugeColor = { bajo: 'var(--risk-low)', moderado: 'var(--risk-mid)', alto: 'var(--risk-high)' }[nivel];
    const gaugeEl = document.getElementById('gauge-value');
    gaugeEl.style.stroke = gaugeColor;
    gaugeEl.style.strokeDashoffset = CIRCUMFERENCE; // reinicia antes de animar

    showScreen('result');

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            gaugeEl.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - pct / 100));
        });
    });
}

// --- Reiniciar para el siguiente participante ---
document.getElementById('btn-reset').addEventListener('click', () => {
    document.getElementById('screen-form').reset();
    document.getElementById('codigo-participante').value = '';
    document.getElementById('form-error').hidden = true;
    startTime = null;
    participantCode = '';
    showScreen('start');
});
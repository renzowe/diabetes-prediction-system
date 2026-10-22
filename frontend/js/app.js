// La URL del backend viene de config.js (cargado antes de este archivo)
const CIRCUMFERENCE = 339.3; // 2 * PI * r(54), debe coincidir con style.css

const screens = {
    start: document.getElementById('screen-start'),
    form: document.getElementById('screen-form'),
    result: document.getElementById('screen-result'),
};

let participantCode = '';
let imcCalculado = null;

// Opciones de 0 a 7 dias para las preguntas de frutas y verduras
document.querySelectorAll('.select-dias').forEach((select) => {
    select.innerHTML = '<option value="" selected disabled>Selecciona</option>'
        + Array.from({ length: 8 }, (_, i) => `<option value="${i}">${i === 1 ? '1 día' : `${i} días`}</option>`).join('');
});

function actualizarIMC() {
    const peso = parseFloat(document.getElementById('peso').value);
    const talla = parseFloat(document.getElementById('talla').value);
    const display = document.getElementById('imc-display');

    if (!peso || !talla) {
        imcCalculado = null;
        display.textContent = '—';
        return;
    }

    const tallaMetros = talla / 100;
    imcCalculado = Math.round((peso / (tallaMetros * tallaMetros)) * 10) / 10; // 1 decimal
    display.textContent = imcCalculado.toFixed(1);
}

document.getElementById('peso').addEventListener('input', actualizarIMC);
document.getElementById('talla').addEventListener('input', actualizarIMC);

function showScreen(name) {
    Object.values(screens).forEach((el) => el.setAttribute('hidden', ''));
    screens[name].removeAttribute('hidden');
    window.scrollTo(0, 0);
}

function formatoPorcentaje(proporcion) {
    const pct = proporcion * 100;
    return `${pct < 10 ? pct.toFixed(1) : Math.round(pct)}%`;
}

function respuestaSiNo(nombre) {
    return document.querySelector(`input[name="${nombre}"]:checked`).value === '1';
}

// --- Pantalla 1: inicio ---
document.getElementById('btn-start').addEventListener('click', () => {
    participantCode = document.getElementById('codigo-participante').value.trim();
    showScreen('form');
});

// Evita que el navegador recargue la pagina si se presiona Enter dentro del formulario
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

    if (imcCalculado === null || imcCalculado < 12 || imcCalculado > 70) {
        errorEl.textContent = `El IMC calculado (${imcCalculado ?? '—'}) está fuera de un rango plausible. Revisa el peso y la talla ingresados.`;
        errorEl.hidden = false;
        return;
    }

    const payload = {
        edad: Number(document.getElementById('edad').value),
        sexo: document.getElementById('sexo').value,
        peso_kg: Number(document.getElementById('peso').value),
        talla_cm: Number(document.getElementById('talla').value),
        cintura_cm: Number(document.getElementById('cintura').value),
        hipertension: respuestaSiNo('hipertension'),
        fuma: respuestaSiNo('fuma'),
        alcohol: respuestaSiNo('alcohol'),
        dias_frutas: Number(document.getElementById('dias-frutas').value),
        dias_verduras: Number(document.getElementById('dias-verduras').value),
        participante_codigo: participantCode || null,
    };

    const btn = document.getElementById('btn-submit');
    btn.disabled = true;
    btn.textContent = 'Calculando…';

    try {
        const res = await fetch(`${API_BASE}/predict`, {
            signal: AbortSignal.timeout(30000),
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const detail = await res.json().catch(() => null);
            const mensajes = Array.isArray(detail?.detail) ? detail.detail.map((d) => d.msg).join('; ') : null;
            throw new Error(mensajes || `Error del servidor (${res.status})`);
        }

        mostrarResultado(await res.json());
    } catch (err) {
        errorEl.textContent = `No se pudo obtener el resultado: ${err.message}.`;
        errorEl.hidden = false;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Obtener estimación';
    }
});

// --- Pantalla 3: resultado ---
function crearFactor(factor) {
    // Se construye con textContent para no interpretar como HTML los textos que llegan de la API
    const item = document.createElement('li');
    item.className = 'factor';

    const nombre = document.createElement('span');
    nombre.className = 'factor__nombre';
    nombre.textContent = factor.factor;

    const valor = document.createElement('span');
    valor.className = 'factor__valor';
    valor.textContent = factor.valor;

    const efecto = document.createElement('span');
    efecto.className = `factor__efecto factor__efecto--${factor.efecto}`;
    efecto.textContent = factor.efecto === 'aumenta' ? 'eleva la estimación' : 'reduce la estimación';

    item.append(nombre, valor, efecto);
    return item;
}

function mostrarResultado(data) {
    document.getElementById('result-pct').textContent = formatoPorcentaje(data.probabilidad);
    document.getElementById('result-reference').textContent =
        `Como referencia, en la población con la que se desarrolló el modelo (adultos de 30 a 69 años de Lima `
        + `Metropolitana, ENDES 2021-2024), el ${formatoPorcentaje(data.prevalencia_referencia)} reportó un `
        + `diagnóstico de diabetes.`;
    document.getElementById('result-message').textContent = data.mensaje;

    const lista = document.getElementById('result-factores');
    lista.replaceChildren(...data.factores.map(crearFactor));
    document.getElementById('result-nota').textContent = data.nota_factores;

    document.getElementById('result-meta').textContent =
        `Registro #${data.id}${participantCode ? ` · participante ${participantCode}` : ''} · `
        + `modelo: ${data.modelo.algoritmo} (${data.modelo.datos_entrenamiento})`;

    const linkSus = document.getElementById('link-sus');
    linkSus.hidden = !participantCode;
    linkSus.href = `sus.html?codigo=${encodeURIComponent(participantCode)}`;

    const gaugeEl = document.getElementById('gauge-value');
    gaugeEl.style.strokeDashoffset = CIRCUMFERENCE; // reinicia antes de animar

    showScreen('result');

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            gaugeEl.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - data.probabilidad));
        });
    });
}

// --- Nueva evaluacion ---
document.getElementById('btn-reset').addEventListener('click', () => {
    document.getElementById('screen-form').reset();
    document.getElementById('codigo-participante').value = '';
    document.getElementById('form-error').hidden = true;
    document.getElementById('imc-display').textContent = '—';
    imcCalculado = null;
    participantCode = '';
    showScreen('start');
});

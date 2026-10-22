// La URL del backend viene de config.js (cargado antes de este archivo)
const CIRCUMFERENCE = 339.3; // 2 * PI * r(54), debe coincidir con style.css

const screens = {
    start: document.getElementById('screen-start'),
    filter: document.getElementById('screen-filter'),
    out: document.getElementById('screen-out'),
    form: document.getElementById('screen-form'),
    result: document.getElementById('screen-result'),
};

let participantCode = '';
let imcCalculado = null;

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

function respuesta(nombre) {
    return document.querySelector(`input[name="${nombre}"]:checked`)?.value ?? null;
}

function respuestaSiNo(nombre) {
    const valor = respuesta(nombre);
    return valor === 'ns' ? null : valor === '1'; // "No sé" se envía como null y el modelo lo imputa
}

// --- Pantalla 1: inicio ---
document.getElementById('btn-start').addEventListener('click', () => {
    participantCode = document.getElementById('codigo-participante').value.trim();
    showScreen('filter');
});

// --- Pantalla 2: pregunta de filtro ---
document.getElementById('btn-filter').addEventListener('click', () => {
    const valor = respuesta('diagnostico_previo');
    document.getElementById('filter-error').hidden = valor !== null;
    if (valor === null) return;
    showScreen(valor === '1' ? 'out' : 'form');
});

// La pregunta de embarazo solo se muestra (y se exige) a las mujeres
document.getElementById('sexo').addEventListener('change', (e) => {
    const esMujer = e.target.value === 'femenino';
    document.getElementById('grupo-embarazo').hidden = !esMujer;
    document.querySelectorAll('input[name="embarazo"]').forEach((input) => {
        input.required = esMujer;
        if (!esMujer) input.checked = false;
    });
});

// Evita que el navegador recargue la pagina si se presiona Enter dentro del formulario
document.getElementById('screen-form').addEventListener('submit', (e) => {
    e.preventDefault();
    document.getElementById('btn-submit').click();
});

// --- Pantalla 3: formulario ---
document.getElementById('btn-submit').addEventListener('click', async () => {
    const errorEl = document.getElementById('form-error');
    errorEl.hidden = true;

    const form = document.getElementById('screen-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    if (respuesta('embarazo') === '1') {
        showScreen('out');
        return;
    }

    if (imcCalculado === null || imcCalculado < 12 || imcCalculado > 70) {
        errorEl.textContent = `El IMC calculado (${imcCalculado ?? '—'}) está fuera de un rango plausible. Revisa el peso y la talla ingresados.`;
        errorEl.hidden = false;
        return;
    }

    const cintura = document.getElementById('cintura').value;
    const payload = {
        diagnostico_previo: false,
        embarazo: false,
        edad: Number(document.getElementById('edad').value),
        sexo: document.getElementById('sexo').value,
        peso_kg: Number(document.getElementById('peso').value),
        talla_cm: Number(document.getElementById('talla').value),
        cintura_cm: cintura === '' ? null : Number(cintura),
        hipertension: respuestaSiNo('hipertension'),
        familiar_diabetes: respuestaSiNo('familiar_diabetes'),
        actividad_fisica: respuestaSiNo('actividad_fisica'),
        fuma: respuestaSiNo('fuma'),
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
            const mensajes = Array.isArray(detail?.detail)
                ? detail.detail.map((d) => d.msg.replace(/^Value error, /, '')).join('; ')
                : null;
            throw new Error(mensajes || `Error del servidor (${res.status})`);
        }

        mostrarResultado(await res.json());
    } catch (err) {
        errorEl.textContent = `No se pudo obtener el resultado: ${err.message}`;
        errorEl.hidden = false;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Obtener estimación';
    }
});

// --- Pantalla 4: resultado ---
// Los elementos se construyen con textContent para no interpretar como HTML los textos de la API
function elemento(tag, clase, texto) {
    const el = document.createElement(tag);
    if (clase) el.className = clase;
    if (texto !== undefined) el.textContent = texto;
    return el;
}

function crearFactor(factor) {
    const item = elemento('li', 'factor');
    item.append(
        elemento('span', 'factor__nombre', factor.factor),
        elemento('span', 'factor__valor', factor.valor),
        elemento('span', `factor__efecto factor__efecto--${factor.efecto}`,
            factor.efecto === 'aumenta' ? 'eleva la estimación' : 'reduce la estimación'),
    );
    return item;
}

function crearRecomendacion(rec) {
    const item = elemento('li', 'recomendacion');
    const fuentes = elemento('details', 'recomendacion__fuentes');
    const lista = elemento('ul');
    lista.append(...rec.fuentes.map((f) => elemento('li', null, f)));
    fuentes.append(elemento('summary', null, rec.fuentes.length === 1 ? 'Fuente' : 'Fuentes'), lista);
    item.append(
        elemento('span', 'recomendacion__titulo', rec.titulo),
        elemento('p', 'recomendacion__texto', rec.texto),
        fuentes,
    );
    return item;
}

function mostrarResultado(data) {
    const [inferior, superior] = data.intervalo;
    document.getElementById('result-pct').textContent = formatoPorcentaje(data.probabilidad);
    document.getElementById('result-interval').textContent =
        `Intervalo del 95 %: ${formatoPorcentaje(inferior)} a ${formatoPorcentaje(superior)}`;
    document.getElementById('result-message').textContent = data.mensaje;
    document.getElementById('result-reference').textContent =
        `Como referencia, en la población con la que se desarrolló el modelo (adultos de 20 a 69 años de EE. UU. sin `
        + `diagnóstico previo), alrededor del ${formatoPorcentaje(data.prevalencia_referencia)} tenía HbA1c de 5.7 % o más.`;
    document.getElementById('result-nota-intervalo').textContent = data.nota_intervalo;

    document.getElementById('result-factores').replaceChildren(...data.factores.map(crearFactor));
    document.getElementById('result-nota').textContent = data.nota_factores;

    document.getElementById('result-recomendaciones').replaceChildren(...data.recomendaciones.map(crearRecomendacion));
    document.getElementById('result-nota-recomendaciones').textContent =
        `${data.nota_recomendaciones} Catálogo de mensajes, versión ${data.version_catalogo}.`;

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
document.querySelectorAll('.btn-reset').forEach((btn) => btn.addEventListener('click', () => {
    document.getElementById('screen-form').reset();
    document.querySelectorAll('input[name="diagnostico_previo"]').forEach((input) => { input.checked = false; });
    document.getElementById('grupo-embarazo').hidden = true;
    document.getElementById('codigo-participante').value = '';
    document.getElementById('form-error').hidden = true;
    document.getElementById('filter-error').hidden = true;
    document.getElementById('imc-display').textContent = '—';
    imcCalculado = null;
    participantCode = '';
    showScreen('start');
}));

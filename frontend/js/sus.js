// La URL del backend viene de config.js (cargado antes de este archivo)
const CIRCUMFERENCE = 339.3;

const PREGUNTAS_SUS = [
  'Creo que usaría este sistema frecuentemente.',
  'Encontré el sistema innecesariamente complejo.',
  'Pensé que el sistema era fácil de usar.',
  'Creo que necesitaría ayuda de alguien para poder usarlo.',
  'Las funciones del sistema están bien integradas.',
  'Encontré demasiada inconsistencia en el sistema.',
  'Imagino que la mayoría de las personas aprenderían a usarlo rápidamente.',
  'Encontré el sistema muy incómodo de usar.',
  'Me sentí muy seguro usando el sistema.',
  'Necesité aprender muchas cosas antes de poder manejarlo.',
];

const ESCALA = [
  { valor: 1, texto: 'Totalmente en desacuerdo' },
  { valor: 2, texto: 'En desacuerdo' },
  { valor: 3, texto: 'Neutral' },
  { valor: 4, texto: 'De acuerdo' },
  { valor: 5, texto: 'Totalmente de acuerdo' },
];

function construirFormulario() {
  const form = document.getElementById('sus-form');
  form.innerHTML = PREGUNTAS_SUS.map((texto, i) => `
    <fieldset class="likert" data-pregunta="${i + 1}">
      <legend>${i + 1}. ${texto}</legend>
      <div class="likert__scale">
        ${ESCALA.map(op => `
          <label class="likert__option">
            <input type="radio" name="q${i + 1}" value="${op.valor}" required>
            <span class="likert__dot"></span>
            <span class="likert__text">${op.texto}</span>
          </label>
        `).join('')}
      </div>
    </fieldset>
  `).join('<hr class="rule">');
}

construirFormulario();

// Pre-llenar el codigo de participante si viene en la URL (?codigo=P01)
const params = new URLSearchParams(window.location.search);
if (params.get('codigo')) {
  document.getElementById('codigo-participante').value = params.get('codigo');
}

document.getElementById('btn-submit-sus').addEventListener('click', async () => {
  const errorEl = document.getElementById('survey-error');
  errorEl.hidden = true;

  const form = document.getElementById('sus-form');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const codigo = document.getElementById('codigo-participante').value.trim();
  if (!codigo) {
    errorEl.textContent = 'Ingresa tu código de participante antes de enviar.';
    errorEl.hidden = false;
    return;
  }

  const respuestas = [];
  for (let i = 1; i <= 10; i++) {
    const seleccionado = document.querySelector(`input[name="q${i}"]:checked`);
    respuestas.push(Number(seleccionado.value));
  }

  const btn = document.getElementById('btn-submit-sus');
  btn.disabled = true;
  btn.textContent = 'Enviando…';

  try {
    const res = await fetch(`${API_BASE}/sus`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participante_codigo: codigo, respuestas }),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail ? JSON.stringify(detail.detail) : `Error del servidor (${res.status})`);
    }

    const data = await res.json();
    mostrarResultado(data);
  } catch (err) {
    errorEl.textContent = `No se pudo enviar la encuesta: ${err.message}. Verifica que el servidor esté activo e inténtalo de nuevo.`;
    errorEl.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Enviar evaluación';
  }
});

function mostrarResultado(data) {
  const pct = Math.round(data.puntaje_sus);
  const nivel = { Excelente: 'bajo', Buena: 'bajo', Aceptable: 'moderado', Deficiente: 'alto' }[data.interpretacion] || 'moderado';

  document.getElementById('sus-pct').textContent = pct;
  const labelEl = document.getElementById('sus-label');
  labelEl.textContent = data.interpretacion;
  labelEl.className = `result__label result__label--${nivel}`;

  const gaugeColor = { bajo: 'var(--risk-low)', moderado: 'var(--risk-mid)', alto: 'var(--risk-high)' }[nivel];
  const gaugeEl = document.getElementById('gauge-value');
  gaugeEl.style.stroke = gaugeColor;
  gaugeEl.style.strokeDashoffset = CIRCUMFERENCE;

  document.getElementById('screen-survey').setAttribute('hidden', '');
  document.getElementById('screen-thanks').removeAttribute('hidden');

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      gaugeEl.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - pct / 100));
    });
  });
}
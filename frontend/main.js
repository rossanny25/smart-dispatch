// URL base del servidor (servido en el mismo host)
const API_BASE = window.location.origin;

// Variables de estado
let technicians = [];
let orders = [];
let memoryLearnings = [];
let currentSimulationData = null;
let selectedOrder = null;

// Elementos del DOM
const orderForm = document.getElementById('order-form');
const rawText = document.getElementById('raw_text');
const address = document.getElementById('address');
const zoneSelect = document.getElementById('zone');
const weatherSelect = document.getElementById('weather-select');
const trafficSelect = document.getElementById('traffic-select');
const gpsSelect = document.getElementById('gps-select');
const btnReset = document.getElementById('btn-reset');
const btnGuidedDemo = document.getElementById('btn-guided-demo');
const btnLogout = document.getElementById('btn-logout');
const guidedDemoState = document.getElementById('guided-demo-state');
const guidedDemoMessage = document.getElementById('guided-demo-message');
const guidedDemoSteps = document.querySelectorAll('.guided-step');

const ordersList = document.getElementById('orders-list');
const techniciansGrid = document.getElementById('technicians-grid');
const memoryList = document.getElementById('memory-list');

const agentCycleCard = document.getElementById('agent-cycle-card');
const cycleStatusText = document.getElementById('cycle-status-text');
const timelineSteps = document.querySelectorAll('.timeline-step');
const detailsAgentTitle = document.getElementById('details-agent-title');
const detailsJsonOutput = document.getElementById('details-json-output');

const recommendationCard = document.getElementById('recommendation-card');
const recommendationBox = recommendationCard.querySelector('.recommendation-box');
const dispatcherActionsBox = recommendationCard.querySelector('.override-box');
const recTechName = document.getElementById('rec-tech-name');
const recTechReasoning = document.getElementById('rec-tech-reasoning');
const recScore = document.getElementById('rec-score');
const recConfidence = document.getElementById('rec-confidence');
const recTravelTime = document.getElementById('rec-travel-time');
const hardRulesPanel = document.getElementById('hard-rules-panel');
const hardRulesSummary = document.getElementById('hard-rules-summary');
const hardRulesList = document.getElementById('hard-rules-list');
const noFeasibleBox = document.getElementById('no-feasible-box');

const btnConfirmRecommended = document.getElementById('btn-confirm-recommended');
const btnOpenOverride = document.getElementById('btn-open-override');
const overrideFormContainer = document.getElementById('override-form-container');
const overrideTechSelect = document.getElementById('override-tech-select');
const overrideFeedback = document.getElementById('override-feedback');
const btnConfirmOverride = document.getElementById('btn-confirm-override');

// Modal
const completionModal = document.getElementById('completion-modal');
const modalClose = document.getElementById('modal-close');
const completionForm = document.getElementById('completion-form');
const modalOrderId = document.getElementById('modal-order-id');
const modalTechId = document.getElementById('modal-tech-id');
const modalFeedback = document.getElementById('modal-feedback');
const realDuration = document.getElementById('real-duration');

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function setGuidedDemoStatus(message, state = 'running', activeStep = null) {
  guidedDemoMessage.textContent = message;
  guidedDemoState.textContent = state === 'done' ? 'Listo' : state === 'error' ? 'Error' : 'Ejecutando';
  guidedDemoState.className = state === 'error'
    ? 'badge badge-status-error'
    : state === 'done'
      ? 'badge badge-status-completada'
      : 'badge badge-status-pendiente';
  guidedDemoSteps.forEach(step => {
    const key = step.getAttribute('data-guide-step');
    step.classList.toggle('active', key === activeStep);
    if (activeStep === null) {
      step.classList.remove('completed');
    } else if (key !== activeStep && !step.classList.contains('completed') && state !== 'error') {
      const order = ['reset', 'select', 'dispatch', 'review', 'approve'];
      if (order.indexOf(key) < order.indexOf(activeStep)) {
        step.classList.add('completed');
      }
    }
  });
}

// --- CARGA INICIAL DE DATOS ---

async function loadData() {
  try {
    const [techRes, ordersRes, memoryRes] = await Promise.all([
      fetch(`${API_BASE}/api/technicians`),
      fetch(`${API_BASE}/api/orders`),
      fetch(`${API_BASE}/api/memory/learning`)
    ]);

    technicians = await techRes.json();
    orders = await ordersRes.json();
    memoryLearnings = await memoryRes.json();

    renderTechnicians();
    renderOrders();
    renderMemory();
    populateOverrideSelect();
  } catch (error) {
    console.error('Error al cargar datos del backend:', error);
  }
}

// Renderizar técnicos
function renderTechnicians() {
  techniciansGrid.innerHTML = '';
  technicians.forEach(tech => {
    const card = document.createElement('div');
    card.className = 'tech-card';
    
    const certTags = tech.certifications
      .map(cert => `<span class="cert-tag">${cert}</span>`)
      .join('');

    card.innerHTML = `
      <div class="tech-header">
        <span class="tech-name">${tech.name}</span>
        <span class="tech-status-dot ${tech.status}" title="Estado: ${tech.status}"></span>
      </div>
      <div class="tech-body">
        <div><strong>Zona:</strong> ${tech.zone}</div>
        <div><strong>Carga Hoy:</strong> ${tech.active_workload_hours} hs</div>
        <div><strong>Calificación:</strong> <i class="fa-solid fa-star" style="color: gold;"></i> ${tech.rating}</div>
        <div class="tech-certs">${certTags}</div>
      </div>
    `;
    techniciansGrid.appendChild(card);
  });
}

// Renderizar órdenes
function renderOrders() {
  ordersList.innerHTML = '';
  if (orders.length === 0) {
    ordersList.innerHTML = '<div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 10px;">No hay órdenes de trabajo pendientes.</div>';
    return;
  }

  orders.forEach(order => {
    const item = document.createElement('div');
    item.className = 'order-item';
    
    const priority = order.structured_data?.priority || 2;
    const status = order.status || 'pendiente';

    item.innerHTML = `
      <div class="order-meta">
        <span class="order-title">${order.client} (${order.zone})</span>
        <span class="order-client">${order.raw_text.slice(0, 50)}${order.raw_text.length > 50 ? '...' : ''}</span>
      </div>
      <div class="order-actions">
        <span class="badge badge-priority-${priority}">Prioridad ${priority}</span>
        <span class="badge badge-status-${status}">${status}</span>
        ${status === 'pendiente' ? `<button class="btn btn-secondary btn-run" data-id="${order.id}" style="padding: 4px 8px; font-size: 11px;"><i class="fa-solid fa-play"></i> Despachar</button>` : ''}
      </div>
    `;
    ordersList.appendChild(item);
  });

  // Agregar eventos a botones de despacho
  document.querySelectorAll('.btn-run').forEach(button => {
    button.addEventListener('click', (e) => {
      const orderId = e.currentTarget.getAttribute('data-id');
      startAgentSimulation(orderId);
    });
  });
}

// Renderizar memoria semántica
function renderMemory() {
  memoryList.innerHTML = '';
  if (memoryLearnings.length === 0) {
    memoryList.innerHTML = '<div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 10px;">Aún no se registran conocimientos aprendidos en la base semántica.</div>';
    return;
  }

  memoryLearnings.forEach(item => {
    const card = document.createElement('div');
    card.className = 'memory-item';
    
    let iconClass = 'fa-lightbulb';
    if (item.type === 'calibracion_tiempo') iconClass = 'fa-clock';
    if (item.type === 'preferencia_usuario') iconClass = 'fa-user-tag';

    card.innerHTML = `
      <div class="memory-icon"><i class="fa-solid ${iconClass}"></i></div>
      <div class="memory-info" style="flex-grow: 1;">
        <span class="memory-text">${item.learning_content.description}</span>
        <div class="memory-meta">
          <span>Confianza: ${Math.round(item.confidence * 100)}%</span>
          <span>Actualizado: ${new Date(item.updated_at).toLocaleTimeString()}</span>
        </div>
      </div>
    `;
    memoryList.appendChild(card);
  });
}

// Popular select de anulación (override)
function populateOverrideSelect() {
  overrideTechSelect.innerHTML = '';
  technicians.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = `${t.name} (Habilidades: ${t.certifications.join(', ')})`;
    overrideTechSelect.appendChild(opt);
  });
}

function renderHardRuleEvidence(candidates = []) {
  const isApproved = (candidate) => candidate.validation_status
    ? candidate.validation_status === 'aprobado'
    : candidate.eligibility_status === 'eligible';
  const approved = candidates.filter(isApproved);
  const rejected = candidates.length - approved.length;
  hardRulesSummary.textContent = `${approved.length} aptos / ${rejected} descartados`;
  hardRulesList.innerHTML = '';

  if (candidates.length === 0) {
    hardRulesList.innerHTML = '<div class="empty-evidence">No hay evidencia de candidatos para esta orden.</div>';
    return;
  }

  candidates.forEach(candidate => {
    const approvedCandidate = isApproved(candidate);
    const row = document.createElement('div');
    row.className = `hard-rule-card ${approvedCandidate ? 'eligible' : 'rejected'}`;

    const checks = Array.isArray(candidate.hard_rule_checks)
      ? candidate.hard_rule_checks
      : [];
    const checksMarkup = checks.length > 0
      ? checks.map(check => `
          <span class="rule-chip ${check.status === 'pass' ? 'pass' : 'fail'}" title="${escapeHtml(check.detail || 'No informado')}">
            <i class="fa-solid ${check.status === 'pass' ? 'fa-check' : 'fa-xmark'}"></i>
            ${escapeHtml(check.label || check.key || 'Regla')}
          </span>
        `).join('')
      : '<span class="rule-chip unknown"><i class="fa-solid fa-circle-question"></i> No informado</span>';

    const alerts = Array.isArray(candidate.alerts) && candidate.alerts.length > 0
      ? `<div class="hard-rule-alerts">${candidate.alerts.map(alert => `<span>${escapeHtml(alert)}</span>`).join('')}</div>`
      : '';
    const scoreText = candidate.score === null || candidate.score === undefined ? 'Sin score' : `Score ${candidate.score}`;

    row.innerHTML = `
      <div class="hard-rule-topline">
        <strong>${escapeHtml(candidate.name)}</strong>
        <span class="eligibility-badge ${approvedCandidate ? 'eligible' : 'rejected'}">
          ${approvedCandidate ? 'Apto' : 'Descartado'}
        </span>
      </div>
      <div class="hard-rule-meta">
        <span>${escapeHtml(scoreText)}</span>
        <span>${escapeHtml(candidate.calculated_travel_time_minutes)} min viaje</span>
        <span>${escapeHtml(candidate.projected_workload_hours ?? 'N/D')} hs proyectadas</span>
      </div>
      <div class="rule-chip-grid">${checksMarkup}</div>
      ${alerts}
    `;
    hardRulesList.appendChild(row);
  });
}

function showNoFeasibleState(responseData) {
  recommendationBox.style.display = 'none';
  dispatcherActionsBox.style.display = 'none';
  noFeasibleBox.style.display = 'block';
  recommendationCard.style.display = 'block';
  renderHardRuleEvidence(responseData?.candidates || []);
  recommendationCard.scrollIntoView({ behavior: 'smooth' });
}

// --- CREAR ORDEN ---

orderForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const payload = {
    raw_text: rawText.value,
    address: address.value,
    zone: zoneSelect.value
  };

  try {
    const res = await fetch(`${API_BASE}/api/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const newOrder = await res.json();
      orderForm.reset();
      await loadData();
      // Comenzar automáticamente la simulación de agentes para la nueva orden
      startAgentSimulation(newOrder.id);
    }
  } catch (error) {
    console.error('Error al crear orden:', error);
  }
});

// --- SIMULADOR DEL CICLO DE AGENTES (OODA) ---

async function startAgentSimulation(orderId) {
  selectedOrder = orders.find(o => o.id === orderId);
  if (!selectedOrder) return;

  // Limpiar estados de UI
  recommendationCard.style.display = 'none';
  recommendationBox.style.display = 'flex';
  dispatcherActionsBox.style.display = 'block';
  noFeasibleBox.style.display = 'none';
  hardRulesSummary.textContent = 'Sin evaluación';
  hardRulesList.innerHTML = '';
  overrideFormContainer.style.display = 'none';
  agentCycleCard.style.display = 'block';
  cycleStatusText.textContent = 'Inicializando...';
  cycleStatusText.className = 'active-badge animate-pulse';
  
  detailsAgentTitle.textContent = "Selecciona un agente para ver sus trazas de pensamiento";
  detailsJsonOutput.textContent = "Haga clic en cualquiera de los agentes arriba para inspeccionar su salida JSON estructurada y traza cognitiva de ejecución.";

  // Resetear estados del timeline
  timelineSteps.forEach(step => {
    step.className = 'timeline-step';
    const statusDiv = step.querySelector('.step-status');
    statusDiv.innerHTML = '';
  });

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // 1. CAPTURE AGENT EXECUTION
  const stepCapture = document.getElementById('step-capture');
  stepCapture.classList.add('running');
  stepCapture.querySelector('.step-summary').textContent = 'Estructurando texto de entrada...';
  stepCapture.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
  await sleep(1000);
  
  stepCapture.classList.remove('running');
  stepCapture.classList.add('completed');
  stepCapture.querySelector('.step-summary').textContent = 'Datos estructurados con éxito';
  stepCapture.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-check"></i>';

  // 2. ANALYZE AGENT EXECUTION
  const stepAnalyze = document.getElementById('step-analyze');
  stepAnalyze.classList.add('running');
  stepAnalyze.querySelector('.step-summary').textContent = 'Asignando habilidades y prioridad...';
  stepAnalyze.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
  await sleep(1000);

  stepAnalyze.classList.remove('running');
  stepAnalyze.classList.add('completed');
  stepAnalyze.querySelector('.step-summary').textContent = `Urgencia y certificaciones identificadas`;
  stepAnalyze.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-check"></i>';

  // 3. PLANNING AGENT & BACKEND API CALL
  const stepPlan = document.getElementById('step-plan');
  stepPlan.classList.add('running');
  stepPlan.querySelector('.step-summary').textContent = 'Calculando asignaciones óptimas...';
  stepPlan.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

  // Realizar llamada al backend real para la simulación
  const simulatePayload = {
    order_id: orderId,
    environment: {
      weather: weatherSelect.value,
      traffic: trafficSelect.value,
      gps_signal: gpsSelect.value
    }
  };

  let responseData = null;
  try {
    const res = await fetch(`${API_BASE}/api/dispatch/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(simulatePayload)
    });
    if (res.ok) {
      responseData = await res.json();
      currentSimulationData = responseData;
    }
  } catch (error) {
    console.error('Error al simular agentes:', error);
  }

  await sleep(1000);
  stepPlan.classList.remove('running');
  stepPlan.classList.add('completed');
  stepPlan.querySelector('.step-summary').textContent = 'Candidatos ponderados';
  stepPlan.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-check"></i>';

  // 4. EVALUATION AGENT EXECUTION
  const stepEvaluate = document.getElementById('step-evaluate');
  stepEvaluate.classList.add('running');
  stepEvaluate.querySelector('.step-summary').textContent = 'Verificando reglas de negocio...';
  stepEvaluate.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
  await sleep(1000);

  stepEvaluate.classList.remove('running');
  stepEvaluate.classList.add('completed');
  stepEvaluate.querySelector('.step-summary').textContent = 'Reglas y SLAs validados';
  stepEvaluate.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-check"></i>';

  // 5. LEARNING AGENT (WAITING FOR USER ACTION)
  const stepLearning = document.getElementById('step-learning');
  if (responseData?.recommended_assignment) {
    stepLearning.classList.add('running');
    stepLearning.querySelector('.step-summary').textContent = 'A la espera de retroalimentación...';
    stepLearning.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-notch fa-spin" style="color: var(--accent-purple);"></i>';
  } else {
    stepLearning.classList.remove('running');
    stepLearning.classList.add('completed');
    stepLearning.querySelector('.step-summary').textContent = 'Sin asignación factible para aprender';
    stepLearning.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-info" style="color: var(--color-warning);"></i>';
  }

  // Finalizar carga del ciclo
  cycleStatusText.textContent = 'Ciclo Completado';
  cycleStatusText.className = 'badge badge-status-completada';

  // Cargar primera vista de traza de Capture Agent por defecto
  showAgentDetails('capture');

  // Renderizar Tarjeta de Recomendación de Asignación
  if (responseData && responseData.recommended_assignment) {
    const rec = responseData.recommended_assignment;
    recTechName.textContent = rec.name;
    recTechReasoning.textContent = rec.reasoning;
    recScore.textContent = rec.score;
    recConfidence.textContent = rec.confidence
      ? `${Math.round(rec.confidence.value * 100)}% (${rec.confidence.label})`
      : 'No calculada';
    recTravelTime.textContent = rec.travel_time;
    renderHardRuleEvidence(responseData.candidates || []);
    recommendationCard.style.display = 'block';
    
    // Auto-scroll a la recomendación
    recommendationCard.scrollIntoView({ behavior: 'smooth' });
  } else if (responseData) {
    showNoFeasibleState(responseData);
  } else {
    alert("No se pudo completar la simulación de despacho. Revisa el estado del servicio e intenta nuevamente.");
  }
  return responseData;
}

// Evento de clic en pasos de la línea de tiempo para ver trazas cognitivas
timelineSteps.forEach(step => {
  step.addEventListener('click', () => {
    if (!currentSimulationData) return;
    
    // Quitar activa de todos
    timelineSteps.forEach(s => s.classList.remove('active'));
    // Marcar esta como activa
    step.classList.add('active');
    
    const agentName = step.getAttribute('data-agent');
    showAgentDetails(agentName);
  });
});

function showAgentDetails(agentName) {
  if (!currentSimulationData) return;

  const log = currentSimulationData.agent_logs[agentName];
  if (!log) return;

  detailsAgentTitle.textContent = `${log.agent} - Traza de Pensamiento`;
  
  // Imprimir un formato bonito y legible
  const thoughtText = `Pensamiento:\n"${log.thought}"\n\nSalida Estructurada (JSON):\n${JSON.stringify(log.output, null, 2)}`;
  detailsJsonOutput.textContent = thoughtText;
}

// --- CONFIRMACIÓN Y ANULACIÓN (OVERRIDE) ---

// Confirmar recomendado
btnConfirmRecommended.addEventListener('click', () => {
  if (!currentSimulationData || !currentSimulationData.recommended_assignment) return;
  const rec = currentSimulationData.recommended_assignment;
  
  openCompletionModal(currentSimulationData.order_id, rec.technician_id, '');
});

// Abrir formulario de override
btnOpenOverride.addEventListener('click', () => {
  overrideFormContainer.style.display = 'block';
  overrideFormContainer.scrollIntoView({ behavior: 'smooth' });
});

// Confirmar con override
btnConfirmOverride.addEventListener('click', () => {
  const selectedTechId = overrideTechSelect.value;
  const comment = overrideFeedback.value;
  
  if (!comment.trim()) {
    alert("Por favor, ingresa el motivo por el cual decides cambiar al técnico recomendado por la IA.");
    return;
  }

  openCompletionModal(currentSimulationData.order_id, selectedTechId, comment);
});

// --- MODAL DE FINALIZACIÓN Y APRENDIZAJE ---

function openCompletionModal(orderId, techId, feedback) {
  modalOrderId.value = orderId;
  modalTechId.value = techId;
  modalFeedback.value = feedback;
  realDuration.value = 90; // Default

  completionModal.style.display = 'flex';
}

modalClose.addEventListener('click', () => {
  completionModal.style.display = 'none';
});

completionForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const payload = {
    order_id: modalOrderId.value,
    technician_id: modalTechId.value,
    duration_minutes: parseInt(realDuration.value),
    feedback_comment: modalFeedback.value
  };

  try {
    const res = await fetch(`${API_BASE}/api/dispatch/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const result = await res.json();
      
      // Mostrar al usuario qué aprendió el Learning Agent
      if (result.learnings_updated && result.learnings_updated.length > 0) {
        let updateMsg = "¡Asignación guardada con éxito!\n\nEl Agente de Aprendizaje procesó tu feedback y guardó en memoria:\n";
        result.learnings_updated.forEach(item => {
          updateMsg += `• [${item.type}] ${item.learning_content.description}\n`;
        });
        alert(updateMsg);
      } else {
        alert("Asignación confirmada y registrada en el historial.");
      }

      // Resetear UI
      completionModal.style.display = 'none';
      recommendationCard.style.display = 'none';
      agentCycleCard.style.display = 'none';
      currentSimulationData = null;
      selectedOrder = null;

      // Recargar datos
      await loadData();
    }
  } catch (error) {
    console.error('Error al confirmar despacho:', error);
  }
});

// --- RESETEAR SIMULACIÓN Y DEMO GUIADA ---

async function resetSimulation({ showConfirm = true, showAlert = true } = {}) {
  if (showConfirm && !confirm("¿Estás seguro de que deseas reiniciar el simulador y limpiar el historial de la memoria persistente?")) {
    return false;
  }

  try {
    const res = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
    if (!res.ok) {
      throw new Error(`Reset falló con estado ${res.status}`);
    }
    recommendationCard.style.display = 'none';
    agentCycleCard.style.display = 'none';
    currentSimulationData = null;
    selectedOrder = null;
    hardRulesSummary.textContent = 'Sin evaluación';
    hardRulesList.innerHTML = '';

    await loadData();
    if (showAlert) {
      alert("Simulación y memoria persistente reseteados a valores de fábrica.");
    }
    return true;
  } catch (error) {
    console.error('Error al resetear la simulación:', error);
    return false;
  }
}

btnReset.addEventListener('click', async () => {
  await resetSimulation();
});

btnGuidedDemo.addEventListener('click', async () => {
  btnGuidedDemo.disabled = true;
  setGuidedDemoStatus('Restaurando datos reproducibles...', 'running', 'reset');

  const resetOk = await resetSimulation({ showConfirm: false, showAlert: false });
  if (!resetOk) {
    setGuidedDemoStatus('No se pudo restaurar el escenario. Revisa la API e intenta nuevamente.', 'error', 'reset');
    btnGuidedDemo.disabled = false;
    return;
  }

  weatherSelect.value = 'soleado';
  trafficSelect.value = 'normal';
  gpsSelect.value = 'online';

  setGuidedDemoStatus('Seleccionando una orden pendiente...', 'running', 'select');
  const pendingOrder = orders.find(order => order.status === 'pendiente');
  if (!pendingOrder) {
    setGuidedDemoStatus('No hay órdenes pendientes para ejecutar la demo guiada.', 'error', 'select');
    btnGuidedDemo.disabled = false;
    return;
  }

  setGuidedDemoStatus(`Ejecutando despacho para ${pendingOrder.client}...`, 'running', 'dispatch');
  const responseData = await startAgentSimulation(pendingOrder.id);
  if (!responseData) {
    setGuidedDemoStatus('La simulación no devolvió resultado. Revisa el servicio e intenta nuevamente.', 'error', 'dispatch');
    btnGuidedDemo.disabled = false;
    return;
  }

  setGuidedDemoStatus(
    responseData.recommended_assignment
      ? 'Revisa reglas duras, score y confianza antes de aprobar o cambiar técnico.'
      : 'Revisa las razones de descarte. No se fuerza una recomendación.',
    'running',
    responseData.recommended_assignment ? 'approve' : 'review'
  );
  guidedDemoState.textContent = 'Revisión';
  btnGuidedDemo.disabled = false;
});

btnLogout.addEventListener('click', async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
  } finally {
    window.location.href = '/login';
  }
});

// Inicialización de la consola al cargar página
window.addEventListener('load', loadData);

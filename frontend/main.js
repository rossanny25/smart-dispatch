// URL base del servidor (servido en el mismo host)
const API_BASE = window.location.origin;

// Variables de estado
let technicians = [];
let orders = [];
let memoryLearnings = [];
let currentSimulationData = null;
let selectedOrder = null;
let currentSession = null;
let adminUsers = [];
let activeView = 'request';

// Elementos del DOM
const orderForm = document.getElementById('order-form');
const rawText = document.getElementById('raw_text');
const address = document.getElementById('address');
const zoneSelect = document.getElementById('zone');
const orderValidationMessage = document.getElementById('order-validation-message');
const weatherSelect = document.getElementById('weather-select');
const trafficSelect = document.getElementById('traffic-select');
const gpsSelect = document.getElementById('gps-select');
const btnReset = document.getElementById('btn-reset');
const btnGuidedDemo = document.getElementById('btn-guided-demo');
const btnLogout = document.getElementById('btn-logout');
const navButtons = document.querySelectorAll('.section-nav-btn[data-view-target]');
const appViews = document.querySelectorAll('.app-view[data-view]');
const btnAdminOpen = document.getElementById('btn-admin-open');
const adminWindow = document.getElementById('admin-window');
const adminWindowBody = document.getElementById('admin-window-body');
const adminWindowClose = document.getElementById('admin-window-close');
const adminTabButtons = document.querySelectorAll('.admin-tab-btn');
const adminUsersCard = document.getElementById('admin-users-card');
const adminUsersState = document.getElementById('admin-users-state');
const adminUserForm = document.getElementById('admin-user-form');
const adminUserId = document.getElementById('admin-user-id');
const adminUsername = document.getElementById('admin-username');
const adminDisplayName = document.getElementById('admin-display-name');
const adminRole = document.getElementById('admin-role');
const adminPassword = document.getElementById('admin-password');
const adminActive = document.getElementById('admin-active');
const adminClearUser = document.getElementById('admin-clear-user');
const adminUsersMessage = document.getElementById('admin-users-message');
const adminUsersList = document.getElementById('admin-users-list');
const adminTechCard = document.getElementById('admin-tech-card');
const adminTechState = document.getElementById('admin-tech-state');
const adminTechForm = document.getElementById('admin-tech-form');
const adminTechId = document.getElementById('admin-tech-id');
const adminTechName = document.getElementById('admin-tech-name');
const adminTechStatus = document.getElementById('admin-tech-status');
const adminTechZone = document.getElementById('admin-tech-zone');
const adminTechCertifications = document.getElementById('admin-tech-certifications');
const adminTechShiftStart = document.getElementById('admin-tech-shift-start');
const adminTechShiftEnd = document.getElementById('admin-tech-shift-end');
const adminTechWorkload = document.getElementById('admin-tech-workload');
const adminTechRating = document.getElementById('admin-tech-rating');
const adminTechPpe = document.getElementById('admin-tech-ppe');
const adminTechGpsLat = document.getElementById('admin-tech-gps-lat');
const adminTechGpsLng = document.getElementById('admin-tech-gps-lng');
const adminClearTech = document.getElementById('admin-clear-tech');
const adminTechMessage = document.getElementById('admin-tech-message');
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
const decisionBreakdown = document.getElementById('decision-breakdown');
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

function formatErrorMessage(value) {
  if (Array.isArray(value)) {
    return value
      .map(item => item?.msg || item?.message || JSON.stringify(item))
      .join(' ');
  }
  if (value && typeof value === 'object') {
    return value.error || value.message || JSON.stringify(value);
  }
  return String(value || 'Solicitud rechazada');
}

function parseList(value) {
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean);
  return String(value || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean);
}

function formatList(value) {
  return parseList(value).join(', ');
}

function getSessionRole() {
  return currentSession?.role || currentSession?.user?.role;
}

function isAdminSession() {
  return getSessionRole() === 'admin';
}

function getTechShift(tech) {
  const shift = tech.shift && typeof tech.shift === 'object' ? tech.shift : {};
  return {
    start: shift.start || tech.shift_start || '',
    end: shift.end || tech.shift_end || ''
  };
}

function getTechGps(tech) {
  const gps = tech.gps_coordinates || tech.gps || {};
  return {
    lat: gps.lat ?? gps.latitude ?? '',
    lng: gps.lng ?? gps.longitude ?? ''
  };
}

function statusLabel(status) {
  const labels = {
    disponible: 'Disponible',
    ocupado: 'Ocupado',
    fuera_servicio: 'Fuera de servicio'
  };
  return labels[status] || status || 'No informado';
}

function switchAppView(viewName) {
  const targetExists = Array.from(appViews).some(view => view.dataset.view === viewName);
  if (!targetExists) return;
  activeView = viewName;

  appViews.forEach(view => {
    view.classList.toggle('view-hidden', view.dataset.view !== viewName);
  });

  navButtons.forEach(button => {
    const active = button.dataset.viewTarget === viewName;
    button.classList.toggle('active', active);
    button.setAttribute('aria-current', active ? 'page' : 'false');
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function getActiveView() {
  return activeView;
}

function initializeAdminWindow() {
  if (!adminWindowBody) return;
  [adminUsersCard, adminTechCard].forEach(card => {
    if (card && card.parentElement !== adminWindowBody) {
      adminWindowBody.appendChild(card);
    }
  });
  switchAdminTab('users');
}

function switchAdminTab(tabName) {
  adminTabButtons.forEach(button => {
    const active = button.dataset.adminTab === tabName;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', active ? 'true' : 'false');
  });

  document.querySelectorAll('.admin-tab-panel').forEach(panel => {
    panel.hidden = panel.dataset.adminTabPanel !== tabName;
  });
}

function openAdminWindow(tabName = 'users') {
  if (!isAdminSession() || !adminWindow) return;
  switchAdminTab(tabName);
  adminWindow.hidden = false;
  document.body.classList.add('admin-window-open');
}

function closeAdminWindow() {
  if (!adminWindow) return;
  adminWindow.hidden = true;
  document.body.classList.remove('admin-window-open');
}

function showOrderValidation(message, type = 'error') {
  orderValidationMessage.hidden = false;
  orderValidationMessage.textContent = message;
  orderValidationMessage.className = `form-validation-message ${type}`;
}

function clearOrderValidation() {
  orderValidationMessage.hidden = true;
  orderValidationMessage.textContent = '';
  orderValidationMessage.className = 'form-validation-message';
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

function normalizeUsers(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.users)) return payload.users;
  if (Array.isArray(payload?.items)) return payload.items;
  return [];
}

function showAdminMessage(message, type = 'info') {
  adminUsersMessage.hidden = false;
  adminUsersMessage.textContent = message;
  adminUsersMessage.className = `admin-message ${type}`;
}

function clearAdminMessage() {
  adminUsersMessage.hidden = true;
  adminUsersMessage.textContent = '';
  adminUsersMessage.className = 'admin-message';
}

function resetAdminForm() {
  adminUserForm.reset();
  adminUserId.value = '';
  adminActive.checked = true;
  adminRole.value = 'tecnico';
  adminPassword.placeholder = 'Requerida al crear';
  adminUsername.disabled = false;
  clearAdminMessage();
}

function showAdminTechMessage(message, type = 'info') {
  adminTechMessage.hidden = false;
  adminTechMessage.textContent = message;
  adminTechMessage.className = `admin-message ${type}`;
}

function clearAdminTechMessage() {
  adminTechMessage.hidden = true;
  adminTechMessage.textContent = '';
  adminTechMessage.className = 'admin-message';
}

function resetAdminTechForm() {
  adminTechForm.reset();
  adminTechId.value = '';
  adminTechStatus.value = 'disponible';
  adminTechZone.value = 'Palermo';
  adminTechShiftStart.value = '08:00';
  adminTechShiftEnd.value = '17:00';
  adminTechWorkload.value = '0';
  adminTechRating.value = '4.5';
  adminTechGpsLat.value = '-34.6037';
  adminTechGpsLng.value = '-58.3816';
  adminTechState.textContent = 'Crear';
  adminTechState.className = 'badge badge-status-pendiente';
  clearAdminTechMessage();
}

function fillAdminTechForm(tech) {
  const shift = getTechShift(tech);
  const gps = getTechGps(tech);

  adminTechId.value = tech.id || '';
  adminTechName.value = tech.name || '';
  adminTechStatus.value = tech.status || 'disponible';
  adminTechZone.value = tech.zone || 'Palermo';
  adminTechCertifications.value = formatList(tech.certifications);
  adminTechShiftStart.value = shift.start || '08:00';
  adminTechShiftEnd.value = shift.end || '17:00';
  adminTechWorkload.value = tech.active_workload_hours ?? 0;
  adminTechRating.value = tech.rating ?? 4.5;
  adminTechPpe.value = formatList(tech.ppe);
  adminTechGpsLat.value = gps.lat || '';
  adminTechGpsLng.value = gps.lng || '';
  adminTechState.textContent = 'Editando';
  adminTechState.className = 'badge badge-status-completada';
  clearAdminTechMessage();
  adminTechForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

navButtons.forEach(button => {
  button.addEventListener('click', () => {
    switchAppView(button.dataset.viewTarget);
  });
});

btnAdminOpen.addEventListener('click', () => {
  openAdminWindow('users');
});

adminWindowClose.addEventListener('click', closeAdminWindow);

adminWindow.addEventListener('click', (event) => {
  if (event.target === adminWindow) {
    closeAdminWindow();
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !adminWindow.hidden) {
    closeAdminWindow();
  }
});

adminTabButtons.forEach(button => {
  button.addEventListener('click', () => {
    switchAdminTab(button.dataset.adminTab);
  });
});

function buildTechnicianPayload() {
  return {
    name: adminTechName.value.trim(),
    status: adminTechStatus.value,
    zone: adminTechZone.value,
    certifications: parseList(adminTechCertifications.value),
    shift: {
      start: adminTechShiftStart.value,
      end: adminTechShiftEnd.value
    },
    active_workload_hours: Number(adminTechWorkload.value),
    rating: Number(adminTechRating.value),
    ppe: parseList(adminTechPpe.value),
    gps_coordinates: {
      lat: Number(adminTechGpsLat.value),
      lng: Number(adminTechGpsLng.value)
    }
  };
}

async function fetchJson(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const isReplayableMutation = (
    url.includes('/api/v1/')
    || url.includes('/api/technicians')
  ) && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(isReplayableMutation ? { 'Idempotency-Key': crypto.randomUUID() } : {}),
      ...(options.headers || {})
    }
  });

  let payload = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    payload = await response.json();
  }

  if (!response.ok) {
    const message = formatErrorMessage(payload?.detail || payload?.message || payload?.error || `Solicitud rechazada (${response.status})`);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload;
}

async function loadSession() {
  try {
    currentSession = await fetchJson(`${API_BASE}/auth/session`);
  } catch (error) {
    currentSession = null;
    console.warn('No se pudo leer la sesión actual:', error);
  }

  if (isAdminSession()) {
    btnAdminOpen.hidden = false;
    await loadAdminUsers();
  } else {
    btnAdminOpen.hidden = true;
    adminUsersCard.hidden = true;
    adminTechCard.hidden = true;
    closeAdminWindow();
  }
}

async function loadAdminUsers() {
  if (!isAdminSession()) return;

  adminUsersState.textContent = 'Cargando';
  adminUsersState.className = 'badge badge-status-pendiente';
  try {
    const payload = await fetchJson(`${API_BASE}/api/v1/admin/users`);
    adminUsers = normalizeUsers(payload);
    renderAdminUsers();
    adminUsersState.textContent = `${adminUsers.length} usuarios`;
    adminUsersState.className = 'badge badge-status-completada';
  } catch (error) {
    adminUsers = [];
    renderAdminUsers();
    adminUsersState.textContent = 'No disponible';
    adminUsersState.className = 'badge badge-status-error';
    showAdminMessage(error.message, 'error');
  }
}

function renderAdminUsers() {
  adminUsersList.innerHTML = '';

  if (adminUsers.length === 0) {
    adminUsersList.innerHTML = '<div class="admin-empty">No hay usuarios para mostrar.</div>';
    return;
  }

  adminUsers.forEach(user => {
    const isActive = user.active ?? user.is_active ?? true;
    const displayName = user.display_name || user.name || user.username;
    const row = document.createElement('div');
    row.className = 'admin-user-row';
    row.innerHTML = `
      <div class="admin-user-main">
        <strong>${escapeHtml(displayName)}</strong>
        <span>${escapeHtml(user.username)}</span>
      </div>
      <div class="admin-user-meta">
        <span class="badge admin-role-badge">${escapeHtml(user.role)}</span>
        <span class="badge ${isActive ? 'badge-status-completada' : 'badge-status-error'}">${isActive ? 'Activo' : 'Inactivo'}</span>
        <button type="button" class="btn btn-secondary btn-admin-edit" data-user-id="${escapeHtml(user.id)}">
          <i class="fa-solid fa-pen-to-square"></i> Editar
        </button>
      </div>
    `;
    adminUsersList.appendChild(row);
  });

  document.querySelectorAll('.btn-admin-edit').forEach(button => {
    button.addEventListener('click', () => {
      const user = adminUsers.find(item => String(item.id) === button.dataset.userId);
      if (!user) return;
      adminUserId.value = user.id;
      adminUsername.value = user.username || '';
      adminUsername.disabled = true;
      adminDisplayName.value = user.display_name || user.name || user.username || '';
      adminRole.value = user.role || 'tecnico';
      adminActive.checked = user.active ?? user.is_active ?? true;
      adminPassword.value = '';
      adminPassword.placeholder = 'Dejar vacía para conservar';
      clearAdminMessage();
      adminUserForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });
}

adminUserForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const isEditing = Boolean(adminUserId.value);
  const payload = {
    display_name: adminDisplayName.value.trim(),
    role: adminRole.value,
    is_active: adminActive.checked
  };
  if (!isEditing) {
    payload.username = adminUsername.value.trim();
  }

  if (adminPassword.value.trim()) {
    payload.password = adminPassword.value;
  }

  if (!isEditing && !payload.password) {
    showAdminMessage('La clave es requerida al crear un usuario.', 'error');
    return;
  }

  try {
    await fetchJson(
      isEditing
        ? `${API_BASE}/api/v1/admin/users/${encodeURIComponent(adminUserId.value)}`
        : `${API_BASE}/api/v1/admin/users`,
      {
        method: isEditing ? 'PATCH' : 'POST',
        body: JSON.stringify(payload)
      }
    );
    resetAdminForm();
    await loadAdminUsers();
    showAdminMessage(isEditing ? 'Usuario actualizado.' : 'Usuario creado.', 'success');
  } catch (error) {
    showAdminMessage(error.message, 'error');
  }
});

adminClearUser.addEventListener('click', resetAdminForm);

async function saveTechnicianPayload(isEditing, payload, technicianId) {
  const primaryUrl = isEditing
    ? `${API_BASE}/api/technicians/${encodeURIComponent(technicianId)}`
    : `${API_BASE}/api/technicians`;
  const fallbackUrl = isEditing
    ? `${API_BASE}/api/v1/admin/technicians/${encodeURIComponent(technicianId)}`
    : `${API_BASE}/api/v1/admin/technicians`;
  const options = {
    method: isEditing ? 'PATCH' : 'POST',
    body: JSON.stringify(payload)
  };

  try {
    return await fetchJson(primaryUrl, options);
  } catch (error) {
    if (![404, 405].includes(error.status)) {
      throw error;
    }
    return fetchJson(fallbackUrl, options);
  }
}

adminTechForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const isEditing = Boolean(adminTechId.value);
  const payload = buildTechnicianPayload();

  if (!payload.certifications.length) {
    showAdminTechMessage('Agrega al menos una certificación separada por coma.', 'error');
    return;
  }

  try {
    await saveTechnicianPayload(isEditing, payload, adminTechId.value);
    resetAdminTechForm();
    await loadData();
    showAdminTechMessage(isEditing ? 'Técnico actualizado.' : 'Técnico creado.', 'success');
  } catch (error) {
    showAdminTechMessage(error.message, 'error');
  }
});

adminClearTech.addEventListener('click', resetAdminTechForm);

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

    const certifications = parseList(tech.certifications);
    const ppe = parseList(tech.ppe);
    const shift = getTechShift(tech);
    const gps = getTechGps(tech);
    const certTags = (certifications.length ? certifications : ['Sin certificaciones'])
      .map(cert => `<span class="cert-tag">${escapeHtml(cert)}</span>`)
      .join('');
    const ppeTags = (ppe.length ? ppe : ['EPP no informado'])
      .map(item => `<span class="cert-tag ppe-tag">${escapeHtml(item)}</span>`)
      .join('');
    const shiftText = shift.start && shift.end ? `${shift.start} - ${shift.end}` : 'Turno no informado';
    const gpsText = gps.lat !== '' && gps.lng !== '' ? `${Number(gps.lat).toFixed(4)}, ${Number(gps.lng).toFixed(4)}` : 'GPS no informado';
    const editButton = isAdminSession()
      ? `<button type="button" class="btn btn-secondary btn-tech-edit" data-tech-id="${escapeHtml(tech.id)}"><i class="fa-solid fa-pen-to-square"></i> Editar</button>`
      : '';

    card.innerHTML = `
      <div class="tech-header">
        <span class="tech-name">${escapeHtml(tech.name)}</span>
        <span class="tech-status">
          <span class="tech-status-dot ${escapeHtml(tech.status)}" title="Estado: ${escapeHtml(statusLabel(tech.status))}"></span>
          ${escapeHtml(statusLabel(tech.status))}
        </span>
      </div>
      <div class="tech-body">
        <div><strong>Zona base:</strong> ${escapeHtml(tech.zone || 'No informada')}</div>
        <div><strong>Turno:</strong> ${escapeHtml(shiftText)}</div>
        <div><strong>Carga hoy:</strong> ${escapeHtml(tech.active_workload_hours ?? 'N/D')} hs</div>
        <div><strong>Calificación:</strong> <i class="fa-solid fa-star" style="color: gold;"></i> ${escapeHtml(tech.rating ?? 'N/D')}</div>
        <div><strong>GPS:</strong> ${escapeHtml(gpsText)}</div>
        <div>
          <strong>Certificaciones:</strong>
          <div class="tech-certs">${certTags}</div>
        </div>
        <div>
          <strong>EPP:</strong>
          <div class="tech-certs">${ppeTags}</div>
        </div>
        ${editButton ? `<div class="tech-actions">${editButton}</div>` : ''}
      </div>
    `;
    techniciansGrid.appendChild(card);
  });

  document.querySelectorAll('.btn-tech-edit').forEach(button => {
    button.addEventListener('click', () => {
      const tech = technicians.find(item => String(item.id) === button.dataset.techId);
      if (tech) {
        openAdminWindow('technicians');
        fillAdminTechForm(tech);
      }
    });
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
    const rawPreview = String(order.raw_text || '');

    item.innerHTML = `
      <div class="order-meta">
        <span class="order-title">${escapeHtml(order.client || 'Cliente')} (${escapeHtml(order.zone || 'Zona N/D')})</span>
        <span class="order-client">${escapeHtml(rawPreview.slice(0, 50))}${rawPreview.length > 50 ? '...' : ''}</span>
      </div>
      <div class="order-actions">
        <span class="badge badge-priority-${escapeHtml(priority)}">Prioridad ${escapeHtml(priority)}</span>
        <span class="badge badge-status-${escapeHtml(status)}">${escapeHtml(status)}</span>
        ${status === 'pendiente' ? `<button class="btn btn-secondary btn-run" data-id="${escapeHtml(order.id)}" style="padding: 4px 8px; font-size: 11px;"><i class="fa-solid fa-play"></i> Despachar</button>` : ''}
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
    memoryList.innerHTML = '<div class="memory-empty">Sin cierres ni feedback suficientes todavía. La memoria no influye hasta que exista evidencia operativa registrada.</div>';
    return;
  }

  memoryLearnings.forEach(item => {
    const card = document.createElement('div');
    card.className = 'memory-item';
    
    let iconClass = 'fa-lightbulb';
    if (item.type === 'calibracion_tiempo') iconClass = 'fa-clock';
    if (item.type === 'preferencia_usuario') iconClass = 'fa-user-tag';
    const parameters = item.learning_content?.parameters || {};
    const sourceText = item.type === 'calibracion_tiempo'
      ? 'Fuente: duración real de cierres completados.'
      : item.type === 'preferencia_usuario'
        ? 'Fuente: override o feedback explícito del despachador.'
        : 'Fuente: registro operativo del simulador.';
    const effectText = parameters.technician_id
      ? `Impacto: puede sumar evidencia para ${parameters.technician_id}${parameters.zone ? ` en ${parameters.zone}` : ''}.`
      : 'Impacto: se muestra como contexto y no altera reglas duras.';

    card.innerHTML = `
      <div class="memory-icon"><i class="fa-solid ${iconClass}"></i></div>
      <div class="memory-info" style="flex-grow: 1;">
        <span class="memory-text">${escapeHtml(item.learning_content?.description || 'Aprendizaje sin descripción')}</span>
        <div class="memory-source">${escapeHtml(sourceText)} ${escapeHtml(effectText)}</div>
        <div class="memory-meta">
          <span>Confianza: ${Math.round((item.confidence || 0) * 100)}%</span>
          <span>Actualizado: ${item.updated_at ? new Date(item.updated_at).toLocaleTimeString() : 'N/D'}</span>
        </div>
      </div>
    `;
    memoryList.appendChild(card);
  });
}

function renderDecisionBreakdown(rec, responseData) {
  const candidates = responseData?.candidates || [];
  const selected = candidates.find(candidate => candidate.technician_id === rec.technician_id);
  const confidenceFactors = Array.isArray(rec.confidence?.factors)
    ? rec.confidence.factors
    : [];
  const memoryText = selected?.memory_bonus > 0
    ? `Memoria: +${selected.memory_bonus} por ${selected.memory_justification}`
    : 'Memoria: sin evidencia histórica aplicable a esta orden.';
  const factorMarkup = confidenceFactors.length
    ? confidenceFactors.map(factor => `<li>${escapeHtml(factor)}</li>`).join('')
    : '<li>La API no informó factores de confianza.</li>';

  decisionBreakdown.innerHTML = `
    <div><strong>Score:</strong> ordena candidatos aptos con cercanía, carga y evidencia histórica.</div>
    <div><strong>Confianza:</strong> mide calidad de evidencia y advertencias del contexto.</div>
    <div><strong>${escapeHtml(memoryText)}</strong></div>
    <ul>${factorMarkup}</ul>
  `;
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
  if (getActiveView() !== 'console') {
    switchAppView('console');
  }
  recommendationBox.style.display = 'none';
  dispatcherActionsBox.style.display = 'none';
  noFeasibleBox.style.display = 'block';
  decisionBreakdown.innerHTML = '';
  recommendationCard.style.display = 'block';
  renderHardRuleEvidence(responseData?.candidates || []);
  recommendationCard.scrollIntoView({ behavior: 'smooth' });
}

// --- CREAR ORDEN ---

orderForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearOrderValidation();
  
  const payload = {
    raw_text: rawText.value.trim(),
    address: address.value.trim(),
    zone: zoneSelect.value
  };

  try {
    const newOrder = await fetchJson(`${API_BASE}/api/orders`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    orderForm.reset();
    clearOrderValidation();
    await loadData();
    // Comenzar automáticamente la simulación de agentes para la nueva orden
    startAgentSimulation(newOrder.id);
  } catch (error) {
    console.error('Error al crear orden:', error);
    showOrderValidation(error.message || 'No se pudo validar la solicitud. Revisa la descripción, dirección y zona.');
  }
});

[rawText, address, zoneSelect].forEach(element => {
  element.addEventListener('input', clearOrderValidation);
  element.addEventListener('change', clearOrderValidation);
});

// --- SIMULADOR DEL CICLO DE AGENTES (OODA) ---

async function startAgentSimulation(orderId) {
  selectedOrder = orders.find(o => o.id === orderId);
  if (!selectedOrder) return;
  switchAppView('console');

  // Limpiar estados de UI
  recommendationCard.style.display = 'none';
  recommendationBox.style.display = 'flex';
  dispatcherActionsBox.style.display = 'block';
  noFeasibleBox.style.display = 'none';
  hardRulesSummary.textContent = 'Sin evaluación';
  hardRulesList.innerHTML = '';
  decisionBreakdown.innerHTML = '';
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
  let simulationError = null;
  try {
    const res = await fetch(`${API_BASE}/api/dispatch/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(simulatePayload)
    });
    if (!res.ok) {
      throw new Error(`Simulación rechazada (${res.status})`);
    }
    responseData = await res.json();
    currentSimulationData = responseData;
  } catch (error) {
    simulationError = error;
    console.error('Error al simular agentes:', error);
  }

  await sleep(1000);
  if (simulationError || !responseData) {
    stepPlan.classList.remove('running');
    stepPlan.classList.add('error');
    stepPlan.querySelector('.step-summary').textContent = 'No se pudo completar la simulación';
    stepPlan.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
    cycleStatusText.textContent = 'Error';
    cycleStatusText.className = 'badge badge-status-error';
    detailsAgentTitle.textContent = 'Simulación no completada';
    detailsJsonOutput.textContent = simulationError?.message || 'No se recibió respuesta del servicio de despacho.';
    alert("No se pudo completar la simulación de despacho. Revisa el estado del servicio e intenta nuevamente.");
    return null;
  }

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
    renderDecisionBreakdown(rec, responseData);
    renderHardRuleEvidence(responseData.candidates || []);
    recommendationCard.style.display = 'block';
    if (getActiveView() !== 'console') {
      switchAppView('console');
    }
    
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
      agentCycleCard.style.display = 'block';
      cycleStatusText.textContent = 'En espera';
      cycleStatusText.className = 'badge badge-status-pendiente';
      currentSimulationData = null;
      selectedOrder = null;

      // Recargar datos
      await loadData();
      switchAppView('orders');
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
    agentCycleCard.style.display = 'block';
    cycleStatusText.textContent = 'En espera';
    cycleStatusText.className = 'badge badge-status-pendiente';
    currentSimulationData = null;
    selectedOrder = null;
    hardRulesSummary.textContent = 'Sin evaluación';
    hardRulesList.innerHTML = '';

    await loadData();
    switchAppView('request');
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
  switchAppView('guided');
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
window.addEventListener('load', async () => {
  initializeAdminWindow();
  switchAppView('request');
  await loadSession();
  if (isAdminSession()) {
    resetAdminTechForm();
  }
  await loadData();
});

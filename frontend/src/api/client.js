const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function load(key) {
  const value = localStorage.getItem(key);
  return value ? JSON.parse(value) : null;
}

export function getToken() {
  return load('careerpilot_token');
}

export function setToken(token) {
  save('careerpilot_token', token);
}

export function getSession() {
  return load('careerpilot_session');
}

export function setSession(session) {
  save('careerpilot_session', session);
}

export function clearSession() {
  localStorage.removeItem('careerpilot_session');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error(`无法连接后端服务，请确认 ${API_BASE} 已启动`);
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(
      detail?.message ||
      detail?.code ||
      (typeof data === 'string' && data.trim()) ||
      `请求失败：${response.status}`
    );
  }

  return data;
}

export const api = {
  guest() {
    return request('/api/auth/guest', { method: 'POST' });
  },
  login(payload) {
    return request('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) });
  },
  register(payload) {
    return request('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) });
  },
  createSession(payload) {
    return request('/api/training-sessions', { method: 'POST', body: JSON.stringify(payload) });
  },
  updateSession(sessionId, payload) {
    return request(`/api/training-sessions/${sessionId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  },
  uploadMaterial({ sessionId, materialType, file }) {
    const form = new FormData();
    form.append('session_id', sessionId);
    form.append('material_type', materialType);
    form.append('file', file);
    return request('/api/materials/upload', { method: 'POST', body: form });
  },
  generateExam(payload) {
    return request('/api/exams/generate', { method: 'POST', body: JSON.stringify(payload) });
  },
  submitExam(payload) {
    return request('/api/exams/submit', { method: 'POST', body: JSON.stringify(payload) });
  },
  interviewMessage(payload) {
    return request('/api/interviews/message', { method: 'POST', body: JSON.stringify(payload) });
  },
  startSimulation(payload) {
    return request('/api/simulations/start-session', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  handleSimulationMessage(payload) {
    return request('/api/simulations/handle-user-message', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  finishSimulation(payload) {
    return request('/api/simulations/finish-session', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  generateSimulationReport(payload) {
    return request('/api/simulations/generate-report', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  generateReport(payload) {
    return request('/api/reports/generate', { method: 'POST', body: JSON.stringify(payload) });
  },
  listReports() {
    return request('/api/reports');
  },
  getReport(sessionId) {
    return request(`/api/reports/${sessionId}`);
  },
  listFavorites() {
    return request('/api/favorites');
  },
  addFavorite(question) {
    return request('/api/favorites', { method: 'POST', body: JSON.stringify({ question }) });
  },
  removeFavorite(questionId) {
    return request(`/api/favorites/${questionId}`, { method: 'DELETE' });
  }
};

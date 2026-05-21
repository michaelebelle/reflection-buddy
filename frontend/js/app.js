// ═══════════════════════════════════════════════════════════════════════════
// CONSTANTS & CONFIG
// ═══════════════════════════════════════════════════════════════════════════

// In local development the backend runs on a separate port (uvicorn :8000).
// In production (Vercel) both are on the same origin, so use a relative path.
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE = IS_LOCAL ? 'http://localhost:8000/api/v1' : '/api/v1';

// Default labels for the 4 reflection question fields.
// Matches the static HTML and is used to reset the form between sessions.
const DEFAULT_QUESTION_LABELS = [
  'What happened today?',
  'How did I feel?',
  'What did I learn about myself?',
  'What is one thing I want to improve tomorrow?',
];

// DOM IDs for the 4 reflection question <label> elements (in order).
const QUESTION_LABEL_IDS = ['label-q1', 'label-q2', 'label-q3', 'label-q4'];

// Centralized mood metadata — extend this list as moods are added.
// Colors use soft, pastel-leaning tones that sit comfortably on a stone palette.
const MOOD_META = {
  excited:    { emoji: '🤩', label: 'Excited',    bg: 'rgba(251,191,36,0.12)',  fg: '#92400E', border: 'rgba(251,191,36,0.28)'  },
  happy:      { emoji: '😊', label: 'Happy',      bg: 'rgba(52,211,153,0.12)',  fg: '#065F46', border: 'rgba(52,211,153,0.28)'  },
  calm:       { emoji: '😌', label: 'Calm',       bg: 'rgba(147,197,253,0.14)', fg: '#1E3A5F', border: 'rgba(147,197,253,0.28)' },
  neutral:    { emoji: '😐', label: 'Neutral',    bg: 'rgba(214,211,209,0.35)', fg: '#57534E', border: 'rgba(214,211,209,0.60)' },
  anxious:    { emoji: '😰', label: 'Anxious',    bg: 'rgba(253,186,116,0.14)', fg: '#9A3412', border: 'rgba(253,186,116,0.28)' },
  sad:        { emoji: '😢', label: 'Sad',        bg: 'rgba(165,180,252,0.14)', fg: '#3730A3', border: 'rgba(165,180,252,0.28)' },
  frustrated: { emoji: '😤', label: 'Frustrated', bg: 'rgba(252,165,165,0.14)', fg: '#991B1B', border: 'rgba(252,165,165,0.28)' },
};

// ═══════════════════════════════════════════════════════════════════════════
// AUTH STATE & TOKEN HELPERS
// ═══════════════════════════════════════════════════════════════════════════

const TOKEN_KEY = 'rb_token';

function getToken()          { return localStorage.getItem(TOKEN_KEY); }
function setToken(t)         { localStorage.setItem(TOKEN_KEY, t); }
function clearToken()        { localStorage.removeItem(TOKEN_KEY); }
function authHeaders() {
  const t = getToken();
  return t ? { 'Authorization': `Bearer ${t}` } : {};
}

// ═══════════════════════════════════════════════════════════════════════════
// APP STATE
// ═══════════════════════════════════════════════════════════════════════════

const state = {
  entries: [],
  total: 0,
  selectedEntry: null,
  selectedMood: null,    // currently selected mood button
  energyTouched: false,  // true only after user interacts with the slider
  authMode: 'login',     // 'login' | 'register'
};

// ═══════════════════════════════════════════════════════════════════════════
// API LAYER
// Future: swap these for an SDK or add auth headers here without touching UI code
// ═══════════════════════════════════════════════════════════════════════════

// Central 401 handler — clears token and sends the user back to the login screen.
// Called by every api method after it receives a response.
function handleUnauthorized() {
  clearToken();
  showAuthView();
}

const api = {
  async register(email, password) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Registration failed (${res.status})`);
    }
    return res.json();
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Login failed (${res.status})`);
    }
    return res.json(); // { access_token, token_type }
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
    if (res.status === 401) { handleUnauthorized(); return null; }
    if (!res.ok) throw new Error(`Could not verify session (${res.status})`);
    return res.json();
  },

  async getEntries(skip = 0, limit = 50) {
    const res = await fetch(`${API_BASE}/entries?skip=${skip}&limit=${limit}`, {
      headers: authHeaders(),
    });
    if (res.status === 401) { handleUnauthorized(); return null; }
    if (!res.ok) throw new Error(`Could not load entries (${res.status})`);
    return res.json();
  },

  async createEntry(data) {
    const res = await fetch(`${API_BASE}/entries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(data),
    });
    if (res.status === 401) { handleUnauthorized(); return null; }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Could not save entry (${res.status})`);
    }
    return res.json();
  },

  async deleteEntry(id) {
    const res = await fetch(`${API_BASE}/entries/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (res.status === 401) { handleUnauthorized(); return; }
    if (!res.ok) throw new Error(`Could not delete entry (${res.status})`);
  },

  async getPrompts() {
    const res = await fetch(`${API_BASE}/entries/prompts`, { headers: authHeaders() });
    if (res.status === 401) { handleUnauthorized(); return null; }
    if (!res.ok) throw new Error(`Could not load prompts (${res.status})`);
    return res.json();
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// DATE / TEXT UTILITIES
// ═══════════════════════════════════════════════════════════════════════════

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
}

function formatDateShort(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  });
}

// Unique key per calendar day — used to group entries in the list
function dayKey(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth()).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function excerpt(text, max = 180) {
  if (text.length <= max) return escapeHtml(text);
  return escapeHtml(text.slice(0, max).trimEnd()) + '…';
}

// Minimal HTML escaping — prevents XSS when rendering user-supplied text
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeHtmlAndBreaks(str) {
  return escapeHtml(str).replace(/\n/g, '<br>');
}

// Group a flat array of entries into [{ label, entries }] keyed by calendar day
function groupByDay(entries) {
  const map = new Map();
  for (const entry of entries) {
    const key = dayKey(entry.created_at);
    if (!map.has(key)) {
      map.set(key, { label: formatDate(entry.created_at), entries: [] });
    }
    map.get(key).entries.push(entry);
  }
  return Array.from(map.values());
}

// ═══════════════════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════════════════

let toastTimer = null;

function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast toast-${type} show`;
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ═══════════════════════════════════════════════════════════════════════════
// VIEW MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.getElementById(`view-${name}`).classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Auth view ──────────────────────────────────────────────────────────────

function showAuthView() {
  document.getElementById('app-header').classList.add('hidden');
  showView('auth');
  setTimeout(() => document.getElementById('auth-email').focus(), 50);
}

function showAppShell() {
  document.getElementById('app-header').classList.remove('hidden');
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isLogin = mode === 'login';

  const loginTab    = document.getElementById('auth-tab-login');
  const registerTab = document.getElementById('auth-tab-register');
  [loginTab, registerTab].forEach(t =>
    t.classList.remove('bg-white', 'text-stone-800', 'shadow-sm', 'text-stone-500')
  );
  (isLogin ? loginTab : registerTab).classList.add('bg-white', 'text-stone-800', 'shadow-sm');
  (isLogin ? registerTab : loginTab).classList.add('text-stone-500');

  document.getElementById('auth-submit-btn').textContent = isLogin ? 'Sign in' : 'Create account';
  document.getElementById('auth-password').autocomplete  = isLogin ? 'current-password' : 'new-password';
  document.getElementById('auth-error').classList.add('hidden');
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email    = document.getElementById('auth-email').value.trim();
  const password = document.getElementById('auth-password').value;
  const errEl    = document.getElementById('auth-error');
  const btn      = document.getElementById('auth-submit-btn');

  errEl.classList.add('hidden');
  btn.disabled    = true;
  btn.textContent = state.authMode === 'login' ? 'Signing in…' : 'Creating account…';

  try {
    if (state.authMode === 'register') {
      await api.register(email, password);
    }
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    showAppShell();
    showDashboard();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
    btn.disabled    = false;
    btn.textContent = state.authMode === 'login' ? 'Sign in' : 'Create account';
  }
}

function signOut() {
  clearToken();
  document.getElementById('auth-email').value    = '';
  document.getElementById('auth-password').value = '';
  showAuthView();
  setAuthMode('login');
}

// Called on every page load — verify the stored token is still valid.
async function bootstrapAuth() {
  if (!getToken()) { showAuthView(); setAuthMode('login'); return; }
  const user = await api.getMe();
  if (!user) return; // getMe() already redirects to auth on 401
  showAppShell();
  showDashboard();
}

// ─────────────────────────────────────────────────────────────────────────

function showDashboard() {
  showView('dashboard');
  loadEntries();
}

async function showNewEntry() {
  resetForm();
  showView('new-entry');
  document.getElementById('content').focus();

  // Fetch mood-tailored prompts in the background.
  // Silently falls back to the default labels already set by resetForm().
  try {
    const data = await api.getPrompts();
    applyPrompts(data);
  } catch {
    // No-op — default labels are already in place
  }
}

/**
 * Update the 4 reflection question labels with server-supplied prompts
 * and show/hide the context banner that explains why they changed.
 */
function applyPrompts(data) {
  data.prompts.forEach((question, i) => {
    const el = document.getElementById(QUESTION_LABEL_IDS[i]);
    if (el) el.textContent = question;
  });

  const banner  = document.getElementById('prompt-context-banner');
  const moodEl  = document.getElementById('prompt-context-mood');

  if (data.mood_context) {
    const meta = MOOD_META[data.mood_context];
    moodEl.textContent = meta ? `${meta.emoji} ${meta.label.toLowerCase()}` : data.mood_context;
    banner.classList.remove('hidden');
  } else {
    banner.classList.add('hidden');
  }
}

function showEntryDetail(entry) {
  state.selectedEntry = entry;
  renderEntryDetail(entry);
  showView('entry-detail');
}

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════

async function loadEntries() {
  const elList    = document.getElementById('entries-list');
  const elEmpty   = document.getElementById('entries-empty');
  const elLoading = document.getElementById('entries-loading');
  const elError   = document.getElementById('entries-error');
  const elBanner  = document.getElementById('entry-count-banner');

  elList.classList.add('hidden');
  elEmpty.classList.add('hidden');
  elError.classList.add('hidden');
  elBanner.classList.add('hidden');
  elLoading.classList.remove('hidden');

  try {
    const data = await api.getEntries();
    if (!data) return; // 401 — redirected to auth
    state.entries = data.entries;
    state.total   = data.total;

    elLoading.classList.add('hidden');

    if (state.entries.length === 0) {
      elEmpty.classList.remove('hidden');
      return;
    }

    elBanner.textContent = `${state.total} ${state.total === 1 ? 'entry' : 'entries'}`;
    elBanner.classList.remove('hidden');

    elList.innerHTML = renderEntriesList(state.entries);
    elList.classList.remove('hidden');

    // Attach click + keyboard handlers to entry cards
    elList.querySelectorAll('.entry-card').forEach(card => {
      card.addEventListener('click', () => {
        const entry = state.entries.find(e => e.id === card.dataset.id);
        if (entry) showEntryDetail(entry);
      });
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.click();
        }
      });
    });
  } catch (err) {
    elLoading.classList.add('hidden');
    elError.classList.remove('hidden');
    document.getElementById('entries-error-msg').textContent =
      `${err.message}. Is the backend running?`;
  }
}

// ── Rendering ──────────────────────────────────────────────────────────────

function renderEntriesList(entries) {
  return groupByDay(entries)
    .map(group => `
      <div class="mb-10">
        <div class="text-[11px] font-semibold text-stone-400 uppercase tracking-[0.08em] mb-3 pb-2.5 border-b border-stone-100">
          ${group.label}
        </div>
        ${group.entries.map(renderEntryCard).join('')}
      </div>
    `)
    .join('');
}

function renderEntryCard(entry) {
  const mood = entry.mood ? MOOD_META[entry.mood] : null;
  const hasReflection =
    entry.q_what_happened || entry.q_how_felt || entry.q_learned || entry.q_improve_tomorrow;

  const moodBadge = mood ? `
    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border"
      style="background:${mood.bg};color:${mood.fg};border-color:${mood.border}">
      ${mood.emoji} ${mood.label}
    </span>` : '';

  const energyBadge = entry.energy_level ? `
    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-stone-100 text-stone-500 border border-stone-200">
      ⚡ ${entry.energy_level}/10
    </span>` : '';

  const reflBadge = hasReflection ? `
    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-50 text-amber-600 border border-amber-100">
      ✦ Reflected
    </span>` : '';

  return `
    <div class="entry-card group bg-white rounded-2xl border border-stone-100 shadow-sm
                hover:shadow-md hover:-translate-y-0.5 transition-all duration-200
                cursor-pointer p-5 mb-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-300"
         data-id="${entry.id}" role="button" tabindex="0"
         aria-label="Journal entry from ${formatDateShort(entry.created_at)}">
      <div class="flex items-start justify-between gap-3 mb-3">
        <span class="text-[11px] text-stone-400 font-medium tabular-nums shrink-0 mt-0.5">
          ${formatTime(entry.created_at)}
        </span>
        <div class="flex flex-wrap gap-1.5 justify-end">
          ${moodBadge}${energyBadge}${reflBadge}
        </div>
      </div>
      <p class="text-[13px] text-stone-600 leading-relaxed line-clamp-3">
        ${excerpt(entry.content)}
      </p>
    </div>
  `;
}

// ═══════════════════════════════════════════════════════════════════════════
// ENTRY DETAIL
// ═══════════════════════════════════════════════════════════════════════════

function renderEntryDetail(entry) {
  const mood = entry.mood ? MOOD_META[entry.mood] : null;

  const moodBadge = mood ? `
    <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium border"
      style="background:${mood.bg};color:${mood.fg};border-color:${mood.border}">
      ${mood.emoji} ${mood.label}
    </span>` : '';

  const energyBadge = entry.energy_level ? `
    <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium bg-stone-100 text-stone-600 border border-stone-200">
      ⚡ Energy ${entry.energy_level}/10
    </span>` : '';

  const reflectionItems = [
    { q: 'What happened today?',                          a: entry.q_what_happened },
    { q: 'How did I feel?',                               a: entry.q_how_felt },
    { q: 'What did I learn about myself?',                a: entry.q_learned },
    { q: 'What is one thing I want to improve tomorrow?', a: entry.q_improve_tomorrow },
  ].filter(item => item.a);

  const reflectionSection = reflectionItems.length > 0 ? `
    <div class="border-t border-stone-100 mt-10 pt-8">
      <p class="text-[11px] font-semibold text-stone-400 uppercase tracking-[0.08em] mb-7">Reflection</p>
      ${reflectionItems.map(item => `
        <div class="mb-7">
          <p class="text-[11px] font-semibold text-stone-400 uppercase tracking-wider mb-2">${item.q}</p>
          <p class="text-[14px] text-stone-700 leading-relaxed">${escapeHtmlAndBreaks(item.a)}</p>
        </div>
      `).join('')}
    </div>
  ` : '';

  document.getElementById('entry-detail-content').innerHTML = `
    <div>
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-stone-900 tracking-tight leading-snug mb-1.5">
          ${formatDate(entry.created_at)}
        </h1>
        <p class="text-[13px] text-stone-400">${formatTime(entry.created_at)}</p>
      </div>

      ${(moodBadge || energyBadge) ? `
        <div class="flex flex-wrap gap-2 mb-8">${moodBadge}${energyBadge}</div>
      ` : ''}

      <div class="border-t border-stone-100 pt-8">
        <p class="text-[15px] text-stone-800 leading-[1.9] whitespace-pre-wrap">${escapeHtml(entry.content)}</p>
      </div>

      ${reflectionSection}
    </div>
  `;
}

// ═══════════════════════════════════════════════════════════════════════════
// NEW ENTRY FORM
// ═══════════════════════════════════════════════════════════════════════════

function resetForm() {
  document.getElementById('entry-form').reset();
  document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
  document.getElementById('energy-display').textContent = '—';
  updateSliderTrack(document.getElementById('energy-level'), false);
  document.getElementById('form-error').classList.add('hidden');
  document.getElementById('submit-btn').disabled = false;
  document.getElementById('submit-btn').textContent = 'Save Entry';
  state.selectedMood  = null;
  state.energyTouched = false;
  document.getElementById('reflection-details').removeAttribute('open');

  // Reset question labels to defaults so the user always sees something
  // sensible before the tailored prompts load from the server.
  DEFAULT_QUESTION_LABELS.forEach((label, i) => {
    const el = document.getElementById(QUESTION_LABEL_IDS[i]);
    if (el) el.textContent = label;
  });
  document.getElementById('prompt-context-banner').classList.add('hidden');
}

function initMoodSelector() {
  document.querySelectorAll('.mood-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const mood = btn.dataset.mood;
      if (state.selectedMood === mood) {
        btn.classList.remove('selected');
        state.selectedMood = null;
      } else {
        document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        state.selectedMood = mood;
      }
    });
  });
}

function updateSliderTrack(slider, active) {
  if (!active) {
    slider.style.background = '#E7E5E4'; // stone-200
    return;
  }
  const pct = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
  slider.style.background =
    `linear-gradient(to right, #1C1917 ${pct}%, #E7E5E4 ${pct}%)`; // stone-900 → stone-200
}

function initEnergySlider() {
  const slider  = document.getElementById('energy-level');
  const display = document.getElementById('energy-display');

  slider.addEventListener('input', () => {
    state.energyTouched = true;
    display.textContent = `${slider.value}/10`;
    updateSliderTrack(slider, true);
  });
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const content = document.getElementById('content').value.trim();
  if (!content) {
    showFormError('Please write something before saving.');
    document.getElementById('content').focus();
    return;
  }

  const submitBtn = document.getElementById('submit-btn');
  submitBtn.disabled    = true;
  submitBtn.textContent = 'Saving…';
  document.getElementById('form-error').classList.add('hidden');

  const payload = {
    content,
    mood:         state.selectedMood || null,
    energy_level: state.energyTouched
      ? parseInt(document.getElementById('energy-level').value, 10)
      : null,
    q_what_happened:    document.getElementById('q-what-happened').value.trim() || null,
    q_how_felt:         document.getElementById('q-how-felt').value.trim()      || null,
    q_learned:          document.getElementById('q-learned').value.trim()       || null,
    q_improve_tomorrow: document.getElementById('q-improve').value.trim()       || null,
  };

  try {
    const result = await api.createEntry(payload);
    if (!result) return; // 401 — redirected to auth
    showToast('Entry saved!');
    showDashboard();
  } catch (err) {
    showFormError(err.message);
    submitBtn.disabled    = false;
    submitBtn.textContent = 'Save Entry';
  }
}

function showFormError(msg) {
  const el = document.getElementById('form-error');
  el.textContent = msg;
  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ═══════════════════════════════════════════════════════════════════════════
// DELETE
// ═══════════════════════════════════════════════════════════════════════════

async function handleDelete() {
  if (!state.selectedEntry) return;
  if (!confirm('Delete this entry? This cannot be undone.')) return;

  try {
    await api.deleteEntry(state.selectedEntry.id);
    state.selectedEntry = null;
    showToast('Entry deleted.');
    showDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════════════════════════

function initKeyboard() {
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const active = document.querySelector('.view:not(.hidden)');
      if (active && active.id !== 'view-dashboard') showDashboard();
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════

function init() {
  // ── Auth ──
  document.getElementById('auth-form').addEventListener('submit', handleAuthSubmit);
  document.getElementById('auth-tab-login').addEventListener('click', () => setAuthMode('login'));
  document.getElementById('auth-tab-register').addEventListener('click', () => setAuthMode('register'));
  document.getElementById('btn-sign-out').addEventListener('click', signOut);

  // ── App ──
  document.getElementById('btn-new-entry').addEventListener('click', showNewEntry);
  document.getElementById('btn-back-from-form').addEventListener('click', showDashboard);
  document.getElementById('btn-back-from-detail').addEventListener('click', showDashboard);
  document.getElementById('btn-cancel-form').addEventListener('click', showDashboard);
  document.getElementById('btn-first-entry').addEventListener('click', showNewEntry);
  document.getElementById('btn-retry').addEventListener('click', loadEntries);
  document.getElementById('delete-entry-btn').addEventListener('click', handleDelete);
  document.getElementById('entry-form').addEventListener('submit', handleFormSubmit);

  initMoodSelector();
  initEnergySlider();
  initKeyboard();

  // Check for a stored token and validate it; show auth screen if none/expired.
  bootstrapAuth();
}

document.addEventListener('DOMContentLoaded', init);

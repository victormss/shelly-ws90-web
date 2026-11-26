/**
 * Weather Station — Historical Records Page Logic
 *
 * Fetches and renders daily, weekly, monthly, yearly, and all-time
 * weather records with exact registration date and time.
 */

const CONFIG = {
    API_BASE: window.location.origin,
    REFRESH_INTERVAL: 300_000, // 5 minutes
    PARTICLE_COUNT: 30,
};

const PERIOD_NAMES = {
    daily: 'Diario',
    weekly: 'Semanal',
    monthly: 'Mensual',
    yearly: 'Anual',
    all_time: 'Histórico Total',
};

const MONTH_NAMES_ES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

const state = {
    theme: localStorage.getItem('theme') || 'dark',
    selectedPeriod: 'daily',
    selectedKey: null,
    summary: null,
    cache: new Map(), // `${period}:${key}` -> WeatherPeriodRecordsResponse
    refreshTimer: null,
};

// ─── Initialization ───
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initParticles();
    initEventListeners();
    fetchSummary();
    startAutoRefresh();
});

// ─── Theme ───
function initTheme() {
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeIcon();
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('theme', state.theme);
    updateThemeIcon();
}

function updateThemeIcon() {
    const icon = document.querySelector('.theme-icon');
    if (icon) {
        icon.textContent = state.theme === 'dark' ? '🌙' : '☀️';
    }
}

// ─── Particles Background ───
function initParticles() {
    const container = document.getElementById('particles');
    if (!container) return;

    for (let i = 0; i < CONFIG.PARTICLE_COUNT; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.animationDuration = `${8 + Math.random() * 12}s`;
        particle.style.animationDelay = `${Math.random() * 10}s`;
        particle.style.width = `${1 + Math.random() * 2}px`;
        particle.style.height = particle.style.width;
        container.appendChild(particle);
    }
}

// ─── Event Listeners ───
function initEventListeners() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    const periodButtons = document.querySelectorAll('#periodSelector .range-btn');
    periodButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const period = btn.dataset.period;
            if (!period || period === state.selectedPeriod) return;

            periodButtons.forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');

            state.selectedPeriod = period;
            state.selectedKey = null;
            loadActivePeriod();
        });
    });

    const keySelect = document.getElementById('periodKeySelect');
    if (keySelect) {
        keySelect.addEventListener('change', () => {
            state.selectedKey = keySelect.value || null;
            loadPeriodKey(state.selectedPeriod, state.selectedKey);
        });
    }

    const prevBtn = document.getElementById('prevKeyBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', () => stepPeriodKey(1));
    }

    const nextBtn = document.getElementById('nextKeyBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', () => stepPeriodKey(-1));
    }
}

function stepPeriodKey(delta) {
    const select = document.getElementById('periodKeySelect');
    if (!select || select.options.length === 0) return;

    const nextIdx = select.selectedIndex + delta;
    if (nextIdx >= 0 && nextIdx < select.options.length) {
        select.selectedIndex = nextIdx;
        state.selectedKey = select.value;
        loadPeriodKey(state.selectedPeriod, state.selectedKey);
    }
}

// ─── Data Fetching ───
async function fetchSummary() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/weather/records/summary`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const summary = await response.json();
        state.summary = summary;

        // Populate cache with current periods
        for (const period of Object.keys(PERIOD_NAMES)) {
            if (summary[period]) {
                const pData = summary[period];
                state.cache.set(`${period}:${pData.period_key}`, pData);
            }
        }

        updateConnectionStatus(true);
        loadActivePeriod();
        renderComparisonTable(summary);
    } catch (error) {
        console.error('Error fetching records summary:', error);
        updateConnectionStatus(false);
        showStatusBanner('No se pudieron cargar los datos históricos. Reintentando automáticamente...', true);
    }
}

async function loadActivePeriod() {
    if (!state.summary) return;
    const summaryPeriod = state.summary[state.selectedPeriod];
    const targetKey = state.selectedKey || summaryPeriod?.period_key;
    await loadPeriodKey(state.selectedPeriod, targetKey);
}

async function loadPeriodKey(period, key) {
    const cacheKey = `${period}:${key || ''}`;
    let data = state.cache.get(cacheKey);

    if (!data) {
        try {
            const url = new URL(`${CONFIG.API_BASE}/api/weather/records`);
            url.searchParams.set('period', period);
            if (key) url.searchParams.set('key', key);

            const response = await fetch(url.toString());
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            data = await response.json();
            state.cache.set(`${period}:${data.period_key}`, data);
        } catch (error) {
            console.error('Error fetching period records:', error);
            showStatusBanner('Error al cargar el periodo seleccionado.', true);
            return;
        }
    }

    state.selectedKey = data.period_key;
    updateKeyNavigator(period, data);
    renderRecordsCards(period, data);
}

function startAutoRefresh() {
    if (state.refreshTimer) clearInterval(state.refreshTimer);
    state.refreshTimer = setInterval(() => {
        state.cache.clear();
        fetchSummary();
    }, CONFIG.REFRESH_INTERVAL);
}

// ─── Formatting Helpers ───
function formatDateTime(isoStr) {
    if (!isoStr) return '--';
    const date = new Date(isoStr);
    if (Number.isNaN(date.getTime())) return '--';

    const datePart = new Intl.DateTimeFormat('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    }).format(date);

    const timePart = new Intl.DateTimeFormat('es-ES', {
        hour: '2-digit',
        minute: '2-digit',
    }).format(date);

    return `${datePart} · ${timePart}`;
}

function formatPeriodKeyLabel(period, key, currentKey) {
    if (!key) return '--';
    const isCurrent = currentKey && key === currentKey;

    if (period === 'all_time') {
        return 'Desde el inicio de registros';
    }
    if (period === 'daily') {
        const [y, m, d] = key.split('-').map(Number);
        if (y && m && d) {
            const formatted = new Intl.DateTimeFormat('es-ES', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
            }).format(new Date(y, m - 1, d));
            return isCurrent ? `${formatted} (Hoy)` : formatted;
        }
    }
    if (period === 'weekly') {
        const match = key.match(/^(\d{4})-W(\d{2})$/);
        if (match) {
            const label = `Semana ${Number(match[2])} · ${match[1]}`;
            return isCurrent ? `${label} (Actual)` : label;
        }
    }
    if (period === 'monthly') {
        const [y, m] = key.split('-').map(Number);
        if (y && m >= 1 && m <= 12) {
            const label = `${MONTH_NAMES_ES[m - 1]} ${y}`;
            return isCurrent ? `${label} (Actual)` : label;
        }
    }
    if (period === 'yearly') {
        return isCurrent ? `Año ${key} (Actual)` : `Año ${key}`;
    }
    return key;
}

function formatLux(value) {
    if (value == null) return '-- lux';
    return value >= 1000
        ? `${(value / 1000).toFixed(1)}K lux`
        : `${Number(value).toFixed(0)} lux`;
}

function getUvInfo(uv) {
    if (uv == null) return { text: '--', cls: '' };
    if (uv <= 2) return { text: 'Bajo', cls: 'low' };
    if (uv <= 5) return { text: 'Moderado', cls: 'moderate' };
    if (uv <= 7) return { text: 'Alto', cls: 'high' };
    if (uv <= 10) return { text: 'Muy alto', cls: 'very-high' };
    return { text: 'Extremo', cls: 'extreme' };
}

// ─── UI Rendering ───
function updateKeyNavigator(period, data) {
    const navigator = document.getElementById('keyNavigator');
    const select = document.getElementById('periodKeySelect');
    const prevBtn = document.getElementById('prevKeyBtn');
    const nextBtn = document.getElementById('nextKeyBtn');
    const currentKey = state.summary?.[period]?.period_key;

    const subtitle = document.getElementById('activePeriodLabel');
    if (subtitle) {
        const periodTitle = PERIOD_NAMES[period] || period;
        subtitle.textContent = `${periodTitle} — ${formatPeriodKeyLabel(period, data.period_key, currentKey)}`;
    }

    if (!navigator || !select) return;

    if (period === 'all_time') {
        navigator.classList.add('hidden');
        return;
    }

    navigator.classList.remove('hidden');
    const keys = Array.isArray(data.available_keys) ? [...data.available_keys] : [];
    if (data.period_key && !keys.includes(data.period_key)) {
        keys.unshift(data.period_key);
    }

    select.innerHTML = '';
    keys.forEach(k => {
        const opt = document.createElement('option');
        opt.value = k;
        opt.textContent = formatPeriodKeyLabel(period, k, currentKey);
        if (k === data.period_key) opt.selected = true;
        select.appendChild(opt);
    });

    const idx = select.selectedIndex;
    if (prevBtn) prevBtn.disabled = idx < 0 || idx >= select.options.length - 1;
    if (nextBtn) nextBtn.disabled = idx <= 0;
}

function setMetricField(valId, timeId, entry, unit, decimals = 1, formatter = null) {
    const valEl = document.getElementById(valId);
    const timeEl = document.getElementById(timeId);

    if (valEl) {
        if (entry && entry.value != null) {
            valEl.textContent = formatter
                ? formatter(entry.value)
                : `${Number(entry.value).toFixed(decimals)}${unit ? ` ${unit}` : ''}`;
        } else {
            valEl.textContent = unit ? `-- ${unit}` : '--';
        }
    }

    if (timeEl) {
        if (entry && entry.recorded_at) {
            timeEl.textContent = `📅 ${formatDateTime(entry.recorded_at)}`;
        } else {
            timeEl.textContent = '📅 Sin datos';
        }
    }
}

function renderRecordsCards(period, data) {
    const records = data?.records || {};
    const hasRecords = Object.keys(records).length > 0;

    if (!hasRecords) {
        showStatusBanner(`Todavía no hay registros guardados para ${PERIOD_NAMES[period] || period}.`, false);
    } else {
        hideStatusBanner();
    }

    setMetricField('recTempMaxVal', 'recTempMaxTime', records.temperature_max, '°C', 1);
    setMetricField('recTempMinVal', 'recTempMinTime', records.temperature_min, '°C', 1);

    setMetricField('recHumMaxVal', 'recHumMaxTime', records.humidity_max, '%', 0);
    setMetricField('recHumMinVal', 'recHumMinTime', records.humidity_min, '%', 0);

    setMetricField('recPressMaxVal', 'recPressMaxTime', records.pressure_max, 'hPa', 1);
    setMetricField('recPressMinVal', 'recPressMinTime', records.pressure_min, 'hPa', 1);

    setMetricField('recWindMaxVal', 'recWindMaxTime', records.wind_speed_max, 'km/h', 1);
    setMetricField('recGustMaxVal', 'recGustMaxTime', records.wind_gust_max, 'km/h', 1);

    // Rain: show clear message if 0 mm
    renderRainMetric('recRainSumVal', 'recRainSumTime', records.rain_sum, 'Acumulado sin lluvia');
    renderRainMetric('recRainMaxVal', 'recRainMaxTime', records.rain_max, 'Sin precipitación');

    // UV
    setMetricField('recUvMaxVal', 'recUvMaxTime', records.uv_index_max, '', 0);
    const uvLevelEl = document.getElementById('recUvLevel');
    if (uvLevelEl) {
        const uvVal = records.uv_index_max?.value ?? null;
        const info = getUvInfo(uvVal);
        uvLevelEl.textContent = info.text;
        uvLevelEl.className = `uv-level ${info.cls}`.trim();
    }

    // Illuminance
    setMetricField('recLuxMaxVal', 'recLuxMaxTime', records.illuminance_max, 'lux', 0, formatLux);
}

function renderRainMetric(valId, timeId, entry, zeroLabel) {
    setMetricField(valId, timeId, entry, 'mm', 1);
    const timeEl = document.getElementById(timeId);
    if (timeEl && entry && Number(entry.value) === 0) {
        timeEl.textContent = `📅 ${zeroLabel} (${formatDateTime(entry.recorded_at)})`;
    }
}

function renderComparisonTable(summary) {
    const tbody = document.getElementById('comparisonTableBody');
    if (!tbody || !summary) return;

    const periods = ['daily', 'weekly', 'monthly', 'yearly', 'all_time'];
    const rowsConfig = [
        { label: '🌡️ Temp. máxima', key: 'temperature_max', unit: '°C', decimals: 1 },
        { label: '❄️ Temp. mínima', key: 'temperature_min', unit: '°C', decimals: 1 },
        { label: '💧 Humedad máx.', key: 'humidity_max', unit: '%', decimals: 0 },
        { label: '🏜️ Humedad mín.', key: 'humidity_min', unit: '%', decimals: 0 },
        { label: '🔵 Presión máx.', key: 'pressure_max', unit: 'hPa', decimals: 1 },
        { label: '🔻 Presión mín.', key: 'pressure_min', unit: 'hPa', decimals: 1 },
        { label: '💨 Viento máx.', key: 'wind_speed_max', unit: 'km/h', decimals: 1 },
        { label: '🌬️ Ráfaga máx.', key: 'wind_gust_max', unit: 'km/h', decimals: 1 },
        { label: '🌧️ Lluvia acumulada', key: 'rain_sum', unit: 'mm', decimals: 1 },
        { label: '☀️ Índice UV máx.', key: 'uv_index_max', unit: '', decimals: 0 },
        { label: '💡 Luminosidad máx.', key: 'illuminance_max', unit: 'lux', decimals: 0, formatter: formatLux },
    ];

    tbody.innerHTML = '';

    rowsConfig.forEach(cfg => {
        const tr = document.createElement('tr');
        const labelTd = document.createElement('td');
        labelTd.className = 'cmp-metric-name';
        labelTd.textContent = cfg.label;
        tr.appendChild(labelTd);

        periods.forEach(p => {
            const td = document.createElement('td');
            const entry = summary[p]?.records?.[cfg.key];

            if (entry && entry.value != null) {
                const valSpan = document.createElement('div');
                valSpan.className = 'cmp-value';
                valSpan.textContent = cfg.formatter
                    ? cfg.formatter(entry.value)
                    : `${Number(entry.value).toFixed(cfg.decimals)}${cfg.unit ? ` ${cfg.unit}` : ''}`;

                const timeSpan = document.createElement('div');
                timeSpan.className = 'cmp-time';
                timeSpan.textContent = formatDateTime(entry.recorded_at);

                td.appendChild(valSpan);
                td.appendChild(timeSpan);
            } else {
                const emptySpan = document.createElement('div');
                emptySpan.className = 'cmp-empty';
                emptySpan.textContent = '--';
                td.appendChild(emptySpan);
            }
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}

function showStatusBanner(message, isError) {
    const banner = document.getElementById('recordsStatusBanner');
    if (!banner) return;
    banner.textContent = message;
    banner.classList.remove('hidden');
    banner.classList.toggle('is-error', Boolean(isError));
}

function hideStatusBanner() {
    const banner = document.getElementById('recordsStatusBanner');
    if (!banner) return;
    banner.classList.add('hidden');
    banner.classList.remove('is-error');
}

function updateConnectionStatus(isOnline) {
    const dot = document.querySelector('.pulse-dot');
    const textEl = document.querySelector('.update-text');
    if (dot) dot.classList.toggle('error', !isOnline);
    if (textEl) {
        if (!isOnline) {
            textEl.textContent = 'Sin conexión';
        } else {
            const nowStr = new Intl.DateTimeFormat('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
            }).format(new Date());
            textEl.textContent = `Actualizado ${nowStr}`;
        }
    }
}

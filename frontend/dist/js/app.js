/**
 * Weather Station — Main Application Logic
 *
 * Handles data fetching, UI updates, theme toggling, and animations.
 * Auto-refreshes data every 60 seconds from the FastAPI backend.
 */

// ─── Configuration ───
const CONFIG = {
    // Change this to your actual API URL in production
    API_BASE: window.location.origin,
    REFRESH_INTERVAL: 60_000,  // 60 seconds
    PARTICLE_COUNT: 30,
};

// ─── State ───
const state = {
    currentData: null,
    previousPressure: null,
    selectedRange: '24h',
    theme: localStorage.getItem('theme') || 'dark',
    refreshTimer: null,
    isOnline: true,
};

// ─── Initialization ───
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initParticles();
    initEventListeners();
    fetchCurrentWeather();
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

    // Notify charts module to update chart colors
    if (typeof updateChartTheme === 'function') {
        updateChartTheme(state.theme);
    }
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
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Time range buttons
    const rangeButtons = document.querySelectorAll('.range-btn');
    rangeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            rangeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.selectedRange = btn.dataset.range;

            // Notify charts module
            if (typeof fetchAndUpdateCharts === 'function') {
                fetchAndUpdateCharts(state.selectedRange);
            }
        });
    });
}

// ─── Data Fetching ───
async function fetchCurrentWeather() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/weather/current`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data) {
            state.previousPressure = state.currentData?.pressure ?? null;
            state.currentData = data;
            updateUI(data);
            updateConnectionStatus(true);
        }
    } catch (error) {
        console.error('Error fetching weather data:', error);
        updateConnectionStatus(false);
    }
}

function startAutoRefresh() {
    if (state.refreshTimer) clearInterval(state.refreshTimer);

    state.refreshTimer = setInterval(() => {
        fetchCurrentWeather();
    }, CONFIG.REFRESH_INTERVAL);
}

// ─── UI Updates ───
function updateUI(data) {
    updateTemperature(data);
    updateHumidity(data);
    updatePressure(data);
    updateWind(data);
    updateRain(data);
    updateUV(data);
    updateIlluminance(data);
    updateLastUpdate(data.time);
}

function updateValueWithFlash(elementId, value, decimals = 1) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const formattedValue = value != null ? Number(value).toFixed(decimals) : '--';
    if (el.textContent !== formattedValue) {
        el.textContent = formattedValue;
        el.classList.remove('value-flash');
        // Force reflow to restart animation
        void el.offsetWidth;
        el.classList.add('value-flash');
    }
}

function updateTemperature(data) {
    updateValueWithFlash('currentTemp', data.temperature);

    // Color temperature card based on temp range
    const card = document.getElementById('card-temp');
    if (card && data.temperature != null) {
        const temp = data.temperature;
        if (temp < 0) card.style.setProperty('--temp-hue', '210');
        else if (temp < 10) card.style.setProperty('--temp-hue', '190');
        else if (temp < 20) card.style.setProperty('--temp-hue', '120');
        else if (temp < 30) card.style.setProperty('--temp-hue', '40');
        else card.style.setProperty('--temp-hue', '0');
    }
}

function updateHumidity(data) {
    updateValueWithFlash('currentHumidity', data.humidity, 0);

    const fill = document.getElementById('humidityFill');
    if (fill && data.humidity != null) {
        fill.style.width = `${Math.min(100, data.humidity)}%`;
    }
}

function updatePressure(data) {
    updateValueWithFlash('currentPressure', data.pressure, 1);

    // Pressure trend
    const trendEl = document.getElementById('pressureTrend');
    if (trendEl && data.pressure != null && state.previousPressure != null) {
        const diff = data.pressure - state.previousPressure;

        trendEl.className = 'card-detail';
        const icon = trendEl.querySelector('.trend-icon');
        const text = trendEl.querySelector('.trend-text');

        if (diff > 0.5) {
            trendEl.classList.add('trend-rising');
            if (icon) icon.textContent = '↗';
            if (text) text.textContent = 'Subiendo';
        } else if (diff < -0.5) {
            trendEl.classList.add('trend-falling');
            if (icon) icon.textContent = '↘';
            if (text) text.textContent = 'Bajando';
        } else {
            trendEl.classList.add('trend-stable');
            if (icon) icon.textContent = '→';
            if (text) text.textContent = 'Estable';
        }
    }
}

function updateWind(data) {
    updateValueWithFlash('currentWindSpeed', data.wind_speed, 1);

    const gustEl = document.getElementById('currentWindGust');
    if (gustEl && data.wind_gust != null) {
        gustEl.textContent = `${Number(data.wind_gust).toFixed(1)} km/h`;
    }

    // Compass arrow
    const arrow = document.getElementById('compassArrow');
    if (arrow && data.wind_direction != null) {
        arrow.setAttribute('transform', `rotate(${data.wind_direction}, 60, 60)`);
    }

    // Direction text
    const dirText = document.getElementById('windDirectionText');
    if (dirText && data.wind_direction != null) {
        const dir = data.wind_direction;
        const cardinal = getCardinalDirection(dir);
        dirText.textContent = `${dir.toFixed(0)}° ${cardinal}`;
    }
}

function getCardinalDirection(deg) {
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                        'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO'];
    const idx = Math.round(deg / 22.5) % 16;
    return directions[idx];
}

function updateRain(data) {
    updateValueWithFlash('currentRain', data.rain, 1);

    // Rain drops animation
    const dropsContainer = document.getElementById('rainDrops');
    if (dropsContainer) {
        if (data.rain != null && data.rain > 0) {
            dropsContainer.classList.add('active');
            // Create rain drops if not already there
            if (dropsContainer.children.length === 0) {
                for (let i = 0; i < 15; i++) {
                    const drop = document.createElement('div');
                    drop.classList.add('rain-drop');
                    drop.style.left = `${Math.random() * 100}%`;
                    drop.style.height = `${8 + Math.random() * 16}px`;
                    drop.style.animationDuration = `${0.5 + Math.random() * 1}s`;
                    drop.style.animationDelay = `${Math.random() * 2}s`;
                    dropsContainer.appendChild(drop);
                }
            }
        } else {
            dropsContainer.classList.remove('active');
        }
    }
}

function updateUV(data) {
    const uvNumber = document.getElementById('currentUV');
    if (uvNumber) {
        uvNumber.textContent = data.uv_index != null ? Number(data.uv_index).toFixed(0) : '--';
    }

    // UV gauge marker position (0-14 scale mapped to 0-100%)
    const marker = document.getElementById('uvGaugeMarker');
    if (marker && data.uv_index != null) {
        const pct = Math.min(100, (data.uv_index / 14) * 100);
        marker.style.left = `${pct}%`;
    }

    // UV level text
    const levelEl = document.getElementById('uvLevel');
    if (levelEl && data.uv_index != null) {
        const uv = data.uv_index;
        let level, cssClass;

        if (uv <= 2) { level = 'Bajo'; cssClass = 'low'; }
        else if (uv <= 5) { level = 'Moderado'; cssClass = 'moderate'; }
        else if (uv <= 7) { level = 'Alto'; cssClass = 'high'; }
        else if (uv <= 10) { level = 'Muy alto'; cssClass = 'very-high'; }
        else { level = 'Extremo'; cssClass = 'extreme'; }

        levelEl.textContent = level;
        levelEl.className = `uv-level ${cssClass}`;
    }
}

function updateIlluminance(data) {
    const el = document.getElementById('currentIlluminance');
    if (el && data.illuminance != null) {
        // Format large numbers with K suffix
        const val = data.illuminance;
        el.textContent = val >= 1000 ? `${(val / 1000).toFixed(1)}K` : val.toFixed(0);
    }

    const levelEl = document.getElementById('illuminanceLevel');
    if (levelEl && data.illuminance != null) {
        const textEl = levelEl.querySelector('.illuminance-text');
        if (textEl) {
            const lux = data.illuminance;
            if (lux < 50) textEl.textContent = '🌙 Noche';
            else if (lux < 500) textEl.textContent = '🏠 Interior';
            else if (lux < 10000) textEl.textContent = '🌥️ Nublado';
            else if (lux < 50000) textEl.textContent = '⛅ Parcial';
            else textEl.textContent = '☀️ Pleno sol';
        }
    }
}

function updateLastUpdate(timeStr) {
    const el = document.querySelector('.update-text');
    if (el && timeStr) {
        const date = new Date(timeStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMin = Math.floor(diffMs / 60000);

        if (diffMin < 1) {
            el.textContent = 'Ahora mismo';
        } else if (diffMin < 60) {
            el.textContent = `Hace ${diffMin} min`;
        } else {
            const hours = Math.floor(diffMin / 60);
            el.textContent = `Hace ${hours}h ${diffMin % 60}min`;
        }
    }
}

function updateConnectionStatus(isOnline) {
    state.isOnline = isOnline;
    const dot = document.querySelector('.pulse-dot');
    if (dot) {
        dot.classList.toggle('error', !isOnline);
    }

    if (!isOnline) {
        const el = document.querySelector('.update-text');
        if (el) el.textContent = 'Sin conexión';
    }
}

// ─── Export for charts module ───
window.weatherState = state;
window.weatherConfig = CONFIG;

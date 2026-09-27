/**
 * Weather Station — Chart.js Configuration and Management
 *
 * Creates and updates responsive time-series charts for
 * temperature, humidity, pressure, and wind data.
 */

// ─── Chart Instances ───
let chartTemp = null;
let chartHumidity = null;
let chartPressure = null;
let chartWind = null;

// ─── Chart Theme Colors ───
function getChartColors(theme) {
    const isDark = theme === 'dark';
    return {
        gridColor: isDark ? 'rgba(148, 163, 184, 0.08)' : 'rgba(71, 85, 105, 0.1)',
        textColor: isDark ? '#94a3b8' : '#64748b',
        tooltipBg: isDark ? '#1e293b' : '#ffffff',
        tooltipText: isDark ? '#f1f5f9' : '#0f172a',
        tooltipBorder: isDark ? 'rgba(148, 163, 184, 0.2)' : 'rgba(71, 85, 105, 0.15)',
        // Data colors
        tempLine: '#f97316',
        tempFill: isDark ? 'rgba(249, 115, 22, 0.1)' : 'rgba(249, 115, 22, 0.08)',
        humidityLine: '#06b6d4',
        humidityFill: isDark ? 'rgba(6, 182, 212, 0.1)' : 'rgba(6, 182, 212, 0.08)',
        pressureLine: '#10b981',
        pressureFill: isDark ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.08)',
        windLine: '#22d3ee',
        windFill: isDark ? 'rgba(34, 211, 238, 0.1)' : 'rgba(34, 211, 238, 0.08)',
        gustLine: '#a78bfa',
        gustFill: isDark ? 'rgba(167, 139, 250, 0.05)' : 'rgba(167, 139, 250, 0.05)',
    };
}

// ─── Default Chart Options ───
function getBaseChartOptions(colors) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 800,
            easing: 'easeInOutCubic',
        },
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                backgroundColor: colors.tooltipBg,
                titleColor: colors.tooltipText,
                bodyColor: colors.tooltipText,
                borderColor: colors.tooltipBorder,
                borderWidth: 1,
                cornerRadius: 12,
                padding: 12,
                titleFont: {
                    family: "'Inter', sans-serif",
                    size: 12,
                    weight: 600,
                },
                bodyFont: {
                    family: "'JetBrains Mono', monospace",
                    size: 13,
                },
                displayColors: true,
                boxWidth: 8,
                boxHeight: 8,
                boxPadding: 4,
                usePointStyle: true,
            },
        },
        scales: {
            x: {
                type: 'time',
                time: {
                    tooltipFormat: 'dd MMM HH:mm',
                    displayFormats: {
                        minute: 'HH:mm',
                        hour: 'HH:mm',
                        day: 'dd MMM',
                    },
                },
                grid: {
                    color: colors.gridColor,
                    drawBorder: false,
                },
                ticks: {
                    color: colors.textColor,
                    font: { size: 10, family: "'Inter', sans-serif" },
                    maxRotation: 0,
                    maxTicksLimit: 8,
                },
                border: { display: false },
            },
            y: {
                grid: {
                    color: colors.gridColor,
                    drawBorder: false,
                },
                ticks: {
                    color: colors.textColor,
                    font: { size: 10, family: "'JetBrains Mono', monospace" },
                    padding: 8,
                },
                border: { display: false },
            },
        },
        elements: {
            point: {
                radius: 0,
                hoverRadius: 5,
                hoverBorderWidth: 2,
                hitRadius: 20,
            },
            line: {
                tension: 0.35,
                borderWidth: 2,
            },
        },
    };
}

// ─── Create Charts ───
function initCharts() {
    const theme = window.weatherState?.theme || 'dark';
    const colors = getChartColors(theme);
    const baseOptions = getBaseChartOptions(colors);

    // Temperature chart
    const ctxTemp = document.getElementById('chartTemperature');
    if (ctxTemp) {
        chartTemp = new Chart(ctxTemp.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Temperatura (°C)',
                    data: [],
                    borderColor: colors.tempLine,
                    backgroundColor: colors.tempFill,
                    fill: true,
                    pointBackgroundColor: colors.tempLine,
                }],
            },
            options: {
                ...baseOptions,
                scales: {
                    ...baseOptions.scales,
                    y: {
                        ...baseOptions.scales.y,
                        ticks: {
                            ...baseOptions.scales.y.ticks,
                            callback: (v) => `${v}°C`,
                        },
                    },
                },
            },
        });
    }

    // Humidity chart
    const ctxHum = document.getElementById('chartHumidity');
    if (ctxHum) {
        chartHumidity = new Chart(ctxHum.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Humedad (%)',
                    data: [],
                    borderColor: colors.humidityLine,
                    backgroundColor: colors.humidityFill,
                    fill: true,
                    pointBackgroundColor: colors.humidityLine,
                }],
            },
            options: {
                ...baseOptions,
                scales: {
                    ...baseOptions.scales,
                    y: {
                        ...baseOptions.scales.y,
                        min: 0,
                        max: 100,
                        ticks: {
                            ...baseOptions.scales.y.ticks,
                            callback: (v) => `${v}%`,
                        },
                    },
                },
            },
        });
    }

    // Pressure chart
    const ctxPressure = document.getElementById('chartPressure');
    if (ctxPressure) {
        chartPressure = new Chart(ctxPressure.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Presión (hPa)',
                    data: [],
                    borderColor: colors.pressureLine,
                    backgroundColor: colors.pressureFill,
                    fill: true,
                    pointBackgroundColor: colors.pressureLine,
                }],
            },
            options: {
                ...baseOptions,
                scales: {
                    ...baseOptions.scales,
                    y: {
                        ...baseOptions.scales.y,
                        ticks: {
                            ...baseOptions.scales.y.ticks,
                            callback: (v) => `${v} hPa`,
                        },
                    },
                },
            },
        });
    }

    // Wind chart (speed + gust)
    const ctxWind = document.getElementById('chartWind');
    if (ctxWind) {
        chartWind = new Chart(ctxWind.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Velocidad (km/h)',
                        data: [],
                        borderColor: colors.windLine,
                        backgroundColor: colors.windFill,
                        fill: true,
                        pointBackgroundColor: colors.windLine,
                    },
                    {
                        label: 'Ráfaga (km/h)',
                        data: [],
                        borderColor: colors.gustLine,
                        backgroundColor: colors.gustFill,
                        fill: true,
                        borderDash: [5, 3],
                        borderWidth: 1.5,
                        pointBackgroundColor: colors.gustLine,
                    },
                ],
            },
            options: {
                ...baseOptions,
                plugins: {
                    ...baseOptions.plugins,
                    legend: {
                        display: true,
                        position: 'top',
                        align: 'end',
                        labels: {
                            color: colors.textColor,
                            usePointStyle: true,
                            pointStyle: 'line',
                            font: { size: 11, family: "'Inter', sans-serif" },
                            padding: 16,
                        },
                    },
                },
                scales: {
                    ...baseOptions.scales,
                    y: {
                        ...baseOptions.scales.y,
                        min: 0,
                        ticks: {
                            ...baseOptions.scales.y.ticks,
                            callback: (v) => `${v} km/h`,
                        },
                    },
                },
            },
        });
    }
}

// ─── Fetch and Update Charts ───
async function fetchAndUpdateCharts(range) {
    try {
        const baseUrl = window.weatherConfig?.API_BASE || window.location.origin;
        const response = await fetch(`${baseUrl}/api/weather/history?range=${range}`);

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        updateChartsData(data);
    } catch (error) {
        console.error('Error fetching chart data:', error);
    }
}

function updateChartsData(data) {
    if (!data || !Array.isArray(data) || data.length === 0) return;

    // Map data to Chart.js format { x: timestamp, y: value }
    const tempData = data.map(d => ({ x: new Date(d.time), y: d.temperature })).filter(d => d.y != null);
    const humData = data.map(d => ({ x: new Date(d.time), y: d.humidity })).filter(d => d.y != null);
    const pressData = data.map(d => ({ x: new Date(d.time), y: d.pressure })).filter(d => d.y != null);
    const windData = data.map(d => ({ x: new Date(d.time), y: d.wind_speed })).filter(d => d.y != null);
    const gustData = data.map(d => ({ x: new Date(d.time), y: d.wind_gust })).filter(d => d.y != null);

    if (chartTemp) {
        chartTemp.data.datasets[0].data = tempData;
        chartTemp.update('none');
    }
    if (chartHumidity) {
        chartHumidity.data.datasets[0].data = humData;
        chartHumidity.update('none');
    }
    if (chartPressure) {
        chartPressure.data.datasets[0].data = pressData;
        chartPressure.update('none');
    }
    if (chartWind) {
        chartWind.data.datasets[0].data = windData;
        chartWind.data.datasets[1].data = gustData;
        chartWind.update('none');
    }
}

// ─── Update Chart Theme ───
function updateChartTheme(theme) {
    const colors = getChartColors(theme);
    const charts = [chartTemp, chartHumidity, chartPressure, chartWind];

    charts.forEach(chart => {
        if (!chart) return;

        // Update scales
        chart.options.scales.x.grid.color = colors.gridColor;
        chart.options.scales.x.ticks.color = colors.textColor;
        chart.options.scales.y.grid.color = colors.gridColor;
        chart.options.scales.y.ticks.color = colors.textColor;

        // Update tooltip
        chart.options.plugins.tooltip.backgroundColor = colors.tooltipBg;
        chart.options.plugins.tooltip.titleColor = colors.tooltipText;
        chart.options.plugins.tooltip.bodyColor = colors.tooltipText;
        chart.options.plugins.tooltip.borderColor = colors.tooltipBorder;

        chart.update('none');
    });

    // Update dataset colors
    if (chartTemp) {
        chartTemp.data.datasets[0].borderColor = colors.tempLine;
        chartTemp.data.datasets[0].backgroundColor = colors.tempFill;
        chartTemp.update('none');
    }
    if (chartHumidity) {
        chartHumidity.data.datasets[0].borderColor = colors.humidityLine;
        chartHumidity.data.datasets[0].backgroundColor = colors.humidityFill;
        chartHumidity.update('none');
    }
    if (chartPressure) {
        chartPressure.data.datasets[0].borderColor = colors.pressureLine;
        chartPressure.data.datasets[0].backgroundColor = colors.pressureFill;
        chartPressure.update('none');
    }
    if (chartWind) {
        chartWind.data.datasets[0].borderColor = colors.windLine;
        chartWind.data.datasets[0].backgroundColor = colors.windFill;
        chartWind.data.datasets[1].borderColor = colors.gustLine;
        chartWind.data.datasets[1].backgroundColor = colors.gustFill;

        if (chartWind.options.plugins.legend) {
            chartWind.options.plugins.legend.labels.color = colors.textColor;
        }
        chartWind.update('none');
    }
}

// ─── Initialize on DOM Ready ───
document.addEventListener('DOMContentLoaded', () => {
    initCharts();

    // Fetch initial chart data after a brief delay to let current data load first
    setTimeout(() => {
        const range = window.weatherState?.selectedRange || '24h';
        fetchAndUpdateCharts(range);
    }, 500);
});

const ALERT_LABELS = {
    fall: "跌倒",
    inactivity: "长时间静止",
    cry: "呼救声",
    abnormal_sound: "异常声响",
};

const $ = (id) => document.getElementById(id);

function formatTime(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("zh-CN", { hour12: false });
}

async function getJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

function escapeHtml(text) {
    return String(text ?? "").replace(/[&<>"']/g, (ch) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));
}

async function refreshStatus() {
    try {
        const status = await getJson("/ui/status");
        const state = $("monitor-state");
        state.textContent = status.monitor_online ? "在线" : "离线";
        state.className = "stat-value " + (status.monitor_online ? "online" : "offline");
        $("last-report").textContent = formatTime(status.last_report_at);
        $("report-count").textContent = status.report_count;
        $("alert-count").textContent = status.alert_count;
        $("config-version").textContent = "v" + status.config_version;
    } catch (error) {
        $("monitor-state").textContent = "PC 服务不可用";
        $("monitor-state").className = "stat-value offline";
    }
}

async function refreshAlerts() {
    try {
        const alerts = await getJson("/ui/alerts");
        const list = $("alert-list");
        if (!alerts.length) {
            list.innerHTML = '<li class="empty">暂无告警</li>';
            return;
        }
        list.innerHTML = alerts.slice(0, 20).map((alert) => `
            <li>
                <div class="alert-title">
                    <span>${escapeHtml(ALERT_LABELS[alert.type] || alert.type)}</span>
                    <span>${(alert.confidence * 100).toFixed(0)}%</span>
                </div>
                <div class="alert-meta">${formatTime(alert.reported_at)} · ${escapeHtml(alert.device_id)}</div>
                <div>${escapeHtml(alert.message)}</div>
            </li>`).join("");
    } catch (error) {
        // 下一轮重试
    }
}

async function refreshReports() {
    try {
        const reports = await getJson("/ui/reports");
        const body = $("report-body");
        if (!reports.length) {
            body.innerHTML = '<tr><td colspan="5" class="empty">暂无报告</td></tr>';
            return;
        }
        body.innerHTML = reports.map((report) => `
            <tr>
                <td>${report.id}</td>
                <td>${escapeHtml(report.device_id)}</td>
                <td>${formatTime(report.reported_at)}</td>
                <td><span class="badge ${report.status === "alert" ? "alert" : "normal"}">${report.status === "alert" ? "异常" : "正常"}</span></td>
                <td>${escapeHtml(report.message)}</td>
            </tr>`).join("");
    } catch (error) {
        // 下一轮重试
    }
}

const preview = $("preview");
const previewHint = $("preview-hint");
let previewRetry;

function connectPreview() {
    clearTimeout(previewRetry);
    preview.src = "/ui/preview?ts=" + Date.now();
}

preview.addEventListener("load", () => previewHint.classList.add("hidden"));
preview.addEventListener("error", () => {
    previewHint.classList.remove("hidden");
    previewHint.textContent = "监控端未就绪，5 秒后重试…";
    clearTimeout(previewRetry);
    previewRetry = setTimeout(connectPreview, 5000);
});

connectPreview();
refreshStatus();
refreshAlerts();
refreshReports();
setInterval(() => {
    refreshStatus();
    refreshAlerts();
    refreshReports();
}, 3000);

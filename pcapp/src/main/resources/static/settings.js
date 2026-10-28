const $ = (id) => document.getElementById(id);
const FIELDS_INT = [
    "inactivity_minutes", "fall_confirm_seconds", "report_interval_seconds",
    "clip_pre_seconds", "clip_post_seconds", "clip_retention_days",
];
const FIELDS_FLOAT = ["fall_confidence", "sound_confidence"];

function showToast(message, isError = false) {
    const toast = $("toast");
    toast.textContent = message;
    toast.className = "toast" + (isError ? " error" : "");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => { toast.textContent = ""; }, 4000);
}

function fillForm(config) {
    const form = $("config-form");
    Object.entries(config).forEach(([key, value]) => {
        const input = form.elements.namedItem(key);
        if (input) input.value = value;
    });
    $("config-version").textContent = "v" + config.version;
}

async function loadConfig() {
    try {
        const response = await fetch("/ui/config", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        fillForm(await response.json());
    } catch (error) {
        showToast("读取配置失败：" + error.message, true);
    }
}

$("config-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const payload = {
        sleep_start: form.elements.namedItem("sleep_start").value,
        sleep_end: form.elements.namedItem("sleep_end").value,
    };
    FIELDS_INT.forEach((name) => {
        payload[name] = parseInt(form.elements.namedItem(name).value, 10);
    });
    FIELDS_FLOAT.forEach((name) => {
        payload[name] = parseFloat(form.elements.namedItem(name).value);
    });

    const button = form.querySelector("button");
    button.disabled = true;
    try {
        const response = await fetch("/ui/config", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        fillForm(result);
        showToast(`已保存，配置版本升至 v${result.version}，监控端将在下一轮轮询时生效`);
    } catch (error) {
        showToast("保存失败：" + error.message, true);
    } finally {
        button.disabled = false;
    }
});

loadConfig();

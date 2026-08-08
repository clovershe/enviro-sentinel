const state = { points: [], alerts: [] };
const $ = (id) => document.getElementById(id);

function setConnection(online) {
  $("status-dot").classList.toggle("online", online);
  $("status-text").textContent = online ? "实时连接" : "正在重连";
}

function renderMetrics(point) {
  if (!point) return;
  $("temperature").textContent = Number(point.temperature).toFixed(1);
  $("humidity").textContent = Number(point.humidity).toFixed(1);
  $("air-quality").textContent = point.air_quality;
  $("battery").textContent = Number(point.battery).toFixed(0);
  $("signal").textContent = `信号 ${point.rssi} dBm`;
  $("air-note").textContent = point.air_quality < 80 ? "空气状态良好" : point.air_quality < 120 ? "轻度波动" : "建议检查通风";
  $("device-id").textContent = point.device_id;
  $("sequence").textContent = point.sequence;
  $("last-seen").textContent = new Date(point.observed_at * 1000).toLocaleTimeString("zh-CN", { hour12: false });
}

function renderAlerts() {
  $("alert-count").textContent = state.alerts.length;
  if (!state.alerts.length) {
    $("alerts").innerHTML = '<div class="empty">暂无告警，设备运行正常</div>';
    return;
  }
  $("alerts").innerHTML = state.alerts.slice(0, 20).map((alert) => `
    <div class="alert ${alert.severity}">
      <span class="alert-dot"></span>
      <div><strong>${alert.code}</strong><p>${alert.message}</p></div>
      <time>${new Date(alert.created_at * 1000).toLocaleTimeString("zh-CN", { hour12: false })}</time>
    </div>`).join("");
}

function drawChart() {
  const canvas = $("trend");
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const w = rect.width, h = rect.height, pad = 18;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "rgba(164, 204, 187, .12)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) {
    const y = pad + ((h - pad * 2) / 4) * i;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }
  if (state.points.length < 2) return;
  const values = state.points.map((p) => Number(p.temperature));
  const low = Math.min(...values) - 1, high = Math.max(...values) + 1;
  const x = (i) => pad + i * (w - pad * 2) / Math.max(1, values.length - 1);
  const y = (v) => h - pad - (v - low) / (high - low) * (h - pad * 2);
  const gradient = ctx.createLinearGradient(0, 0, 0, h);
  gradient.addColorStop(0, "rgba(216, 243, 107, .30)");
  gradient.addColorStop(1, "rgba(216, 243, 107, 0)");
  ctx.beginPath(); ctx.moveTo(x(0), h - pad);
  values.forEach((v, i) => ctx.lineTo(x(i), y(v)));
  ctx.lineTo(x(values.length - 1), h - pad); ctx.closePath();
  ctx.fillStyle = gradient; ctx.fill();
  ctx.beginPath();
  values.forEach((v, i) => i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)));
  ctx.strokeStyle = "#d8f36b"; ctx.lineWidth = 2; ctx.stroke();
}

async function loadInitial() {
  const [historyResponse, alertsResponse] = await Promise.all([
    fetch("/api/v1/telemetry/history?limit=60"), fetch("/api/v1/alerts?limit=20")
  ]);
  state.points = await historyResponse.json();
  state.alerts = await alertsResponse.json();
  renderMetrics(state.points.at(-1));
  renderAlerts();
  drawChart();
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/telemetry`);
  socket.onopen = () => setConnection(true);
  socket.onclose = () => { setConnection(false); setTimeout(connectSocket, 2000); };
  socket.onmessage = ({ data }) => {
    const event = JSON.parse(data);
    const point = { ...event.metrics, device_id: event.device_id, sequence: event.sequence, observed_at: event.timestamp };
    state.points.push(point);
    state.points = state.points.slice(-60);
    event.alerts.forEach((alert) => state.alerts.unshift({ ...alert, created_at: event.timestamp }));
    renderMetrics(point); renderAlerts(); drawChart();
  };
}

window.addEventListener("resize", drawChart);
loadInitial().catch(console.error);
connectSocket();

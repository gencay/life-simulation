const number = new Intl.NumberFormat();

async function loadDashboard() {
  const [metricsResponse, historyResponse] = await Promise.all([
    fetch("data/metrics.json", { cache: "no-store" }),
    fetch("data/history.json", { cache: "no-store" }),
  ]);

  if (!metricsResponse.ok || !historyResponse.ok) {
    throw new Error("Simulation data is unavailable.");
  }

  const metrics = await metricsResponse.json();
  const history = await historyResponse.json();
  document.querySelector("#generation").textContent = number.format(metrics.generation);
  document.querySelector("#active-cells").textContent =
    `${number.format(metrics.active_cells)} / ${number.format(metrics.total_cells)}`;
  document.querySelector("#mean-v").textContent =
    Number(metrics.mean_v).toFixed(5);
  document.querySelector("#deviation-v").textContent =
    Number(metrics.standard_deviation_v).toFixed(5);
  document.querySelector("#updated-at").textContent =
    `Observed ${new Date(metrics.updated_at).toLocaleString()}`;
  drawHistory(history);
}

function drawHistory(history) {
  const canvas = document.querySelector("#history-chart");
  const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = 280;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  context.scale(ratio, ratio);
  context.clearRect(0, 0, width, height);

  const padding = { top: 20, right: 20, bottom: 35, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const values = history.map((entry) => Number(entry.active_cells));
  const maximum = Math.max(...values, 1);
  const minimum = Math.min(...values, 0);
  const range = Math.max(maximum - minimum, 1);

  context.strokeStyle = "rgba(148, 163, 184, 0.18)";
  context.fillStyle = "#94a3b8";
  context.font = "11px system-ui";
  for (let line = 0; line <= 4; line += 1) {
    const y = padding.top + (plotHeight * line) / 4;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
    const label = Math.round(maximum - (range * line) / 4);
    context.fillText(number.format(label), 4, y + 4);
  }

  const points = history.map((entry, index) => ({
    x: padding.left + (plotWidth * index) / Math.max(history.length - 1, 1),
    y: padding.top + plotHeight * (1 - (Number(entry.active_cells) - minimum) / range),
  }));

  if (points.length) {
    const gradient = context.createLinearGradient(0, padding.top, 0, height);
    gradient.addColorStop(0, "rgba(94, 234, 212, 0.28)");
    gradient.addColorStop(1, "rgba(94, 234, 212, 0)");
    context.beginPath();
    context.moveTo(points[0].x, padding.top + plotHeight);
    points.forEach((point) => context.lineTo(point.x, point.y));
    context.lineTo(points.at(-1).x, padding.top + plotHeight);
    context.closePath();
    context.fillStyle = gradient;
    context.fill();

    context.beginPath();
    points.forEach((point, index) => {
      if (index === 0) context.moveTo(point.x, point.y);
      else context.lineTo(point.x, point.y);
    });
    context.strokeStyle = "#5eead4";
    context.lineWidth = 2;
    context.stroke();
  }

  context.fillStyle = "#94a3b8";
  context.fillText("Generation", width - 78, height - 8);
}

loadDashboard().catch((error) => {
  document.querySelector("#updated-at").textContent = error.message;
});

window.addEventListener("resize", () => {
  fetch("data/history.json", { cache: "no-store" })
    .then((response) => response.json())
    .then(drawHistory);
});

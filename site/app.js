const number = new Intl.NumberFormat();
const select = (selector) => document.querySelector(selector);
const metricLabels = {
  active_cells: "Active grid sites",
  mean_v: "Mean V concentration",
  standard_deviation_v: "Spatial variation of V",
};
let dashboard = null;
let frameIndex = 0;
let followingLatest = true;
let playback = null;
let refreshing = false;

function setStatus(message, state) {
  select("#sync-status").textContent = message;
  select("#status").dataset.state = state;
}

function stopPlayback() {
  clearInterval(playback);
  playback = null;
  select("#play").textContent = "Play recorded evolution";
}

function showFrame(index) {
  frameIndex = index;
  const frame = dashboard.frames[index];
  const canvas = select("#field-canvas");
  canvas.width = frame.width;
  canvas.height = frame.height;
  const context = canvas.getContext("2d");
  const image = context.createImageData(frame.width, frame.height);
  frame.pixels.forEach((intensity, pixel) => {
    image.data[pixel * 4] = Math.max(5, Math.floor(intensity / 5));
    image.data[pixel * 4 + 1] = Math.min(255, 25 + intensity);
    image.data[pixel * 4 + 2] = Math.min(255, 75 + intensity);
    image.data[pixel * 4 + 3] = 255;
  });
  context.putImageData(image, 0, 0);
  canvas.hidden = false;
  select("#field-image").hidden = true;
  canvas.setAttribute("aria-label", `Concentration field at generation ${frame.generation}`);
  select("#view-mode").textContent = followingLatest
    ? "LATEST PUBLISHED FIELD"
    : "RECORDED EVOLUTION / REPLAY";
  select("#generation").textContent = number.format(frame.generation);
  select("#active-cells").textContent =
    `${number.format(frame.active_cells)} / ${number.format(frame.total_cells)}`;
  select("#mean-v").textContent = Number(frame.mean_v).toFixed(5);
  select("#deviation-v").textContent = Number(frame.standard_deviation_v).toFixed(5);
  const observed = select("#updated-at");
  observed.dateTime = frame.updated_at;
  observed.textContent = `Observed ${new Date(frame.updated_at).toLocaleString()}`;
  select("#timeline").value = index;
  select("#timeline").setAttribute("aria-valuetext", `Generation ${frame.generation}`);
  select("#frame-caption").textContent =
    `Generation ${frame.generation} of ${dashboard.metrics.generation}. ` +
    `Replay covers ${dashboard.frames.length} saved observations ` +
    `(generations ${dashboard.frames[0].generation}-${dashboard.frames.at(-1).generation}).`;
  drawHistory();
}

function drawHistory() {
  if (!dashboard) return;
  const history = dashboard.history;
  const key = select("#chart-metric").value;
  const format = (value) => key === "active_cells"
    ? number.format(Math.round(value))
    : Number(value).toFixed(4);
  const canvas = select("#history-chart");
  const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = 280;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  context.scale(ratio, ratio);
  const padding = { top: 25, right: 20, bottom: 48, left: 65 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maximum = history.reduce((max, item) => Math.max(max, Number(item[key])), 0) || 1;
  const firstGeneration = Number(history[0].generation);
  const generationRange = Math.max(Number(history.at(-1).generation) - firstGeneration, 1);
  const xFor = (generation) =>
    padding.left + plotWidth * (Number(generation) - firstGeneration) / generationRange;

  context.strokeStyle = "rgba(148, 163, 184, 0.18)";
  context.fillStyle = "#94a3b8";
  context.font = "11px system-ui";
  for (let line = 0; line <= 4; line += 1) {
    const y = padding.top + plotHeight * line / 4;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
    context.fillText(format(maximum * (1 - line / 4)), 2, y + 4);
  }
  const ticks = Math.min(4, history.length - 1);
  for (let tick = 0; tick <= ticks; tick += 1) {
    const item = history[Math.round(tick * (history.length - 1) / Math.max(ticks, 1))];
    context.textAlign = "center";
    context.fillText(String(item.generation), xFor(item.generation), height - 28);
  }
  context.fillText("Generation (numerical observations)", width / 2, height - 8);
  context.textAlign = "left";
  context.fillText(metricLabels[key], padding.left, 12);

  const points = history.map((item) => ({
    x: xFor(item.generation),
    y: padding.top + plotHeight * (1 - Number(item[key]) / maximum),
  }));
  context.beginPath();
  points.forEach((point, index) => {
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.strokeStyle = "#5eead4";
  context.lineWidth = 2;
  context.stroke();
  context.fillStyle = "#5eead4";
  if (points.length <= 100) {
    points.forEach((point) => {
      context.beginPath();
      context.arc(point.x, point.y, 3, 0, Math.PI * 2);
      context.fill();
    });
  }
  const selectedX = xFor(dashboard.frames[frameIndex].generation);
  context.setLineDash([4, 4]);
  context.strokeStyle = "#f8fafc";
  context.beginPath();
  context.moveTo(selectedX, padding.top);
  context.lineTo(selectedX, padding.top + plotHeight);
  context.stroke();
  context.setLineDash([]);
  const summary =
    `${history.length} observations. ${metricLabels[key]}: ` +
    `${format(history[0][key])} at generation ${firstGeneration} to ` +
    `${format(history.at(-1)[key])} at generation ${history.at(-1).generation}. ` +
    "Dashed line marks the displayed field.";
  select("#chart-summary").textContent = summary;
  canvas.setAttribute("aria-label", summary);
}

function updateCommentary() {
  const latest = dashboard.metrics;
  const previous = dashboard.history.at(-2);
  const area = (100 * latest.active_cells / latest.total_cells).toFixed(1);
  let change = "This is the first recorded observation; a trend needs more observations.";
  if (previous) {
    const delta = latest.active_cells - Number(previous.active_cells);
    const direction = delta > 0 ? "expanded" : delta < 0 ? "contracted" : "remained unchanged";
    change = `Since generation ${previous.generation}, the above-threshold area has ${direction}` +
      (delta === 0 ? ". " : ` by ${number.format(Math.abs(delta))} grid sites. `);
    const varianceChange = latest.standard_deviation_v - Number(previous.standard_deviation_v);
    change += varianceChange === 0
      ? "Spatial variation is unchanged at the recorded precision."
      : `Spatial variation has ${varianceChange > 0 ? "increased" : "decreased"}.`;
  }
  select("#interpretation").textContent =
    `Latest observation, generation ${latest.generation}: ${area}% of the field has V above 0.10. ` +
    `${change} These describe chemical organization, not the emergence of organisms.`;
  select("#history-table").replaceChildren(...dashboard.history.slice(-12).reverse().map((item) => {
    const row = document.createElement("tr");
    const values = [
      item.generation,
      new Date(item.updated_at).toISOString().replace("T", " ").replace(".000Z", "Z"),
      number.format(item.active_cells),
      Number(item.mean_v).toFixed(5),
      Number(item.standard_deviation_v).toFixed(5),
    ];
    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    return row;
  }));
}

async function refreshDashboard() {
  if (refreshing) return;
  refreshing = true;
  select("#refresh").disabled = true;
  try {
    const response = await fetch(`data/dashboard.json?t=${Date.now()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error(`Data request failed (HTTP ${response.status}).`);
    const next = await response.json();
    if (!next.metrics || !next.frames?.length || !next.history?.length ||
        next.frames.at(-1).generation !== next.metrics.generation ||
        Number(next.history.at(-1).generation) !== next.metrics.generation) {
      throw new Error("Published observations are incomplete or inconsistent.");
    }
    if (next.frames.some((frame) => frame.pixels.length !== frame.width * frame.height)) {
      throw new Error("A published field has an invalid size.");
    }
    if (dashboard && next.metrics.generation < dashboard.metrics.generation) {
      throw new Error("The server returned an older observation; keeping the newer result.");
    }
    const selectedGeneration = dashboard?.frames[frameIndex].generation;
    dashboard = next;
    select("#timeline").max = next.frames.length - 1;
    select("#timeline").disabled = next.frames.length < 2;
    select("#play").disabled = next.frames.length < 2;
    select("#go-live").disabled = false;
    const retainedIndex = next.frames.findIndex((frame) => frame.generation === selectedGeneration);
    showFrame(followingLatest ? next.frames.length - 1 : Math.max(retainedIndex, 0));
    updateCommentary();
    const ageHours = (Date.now() - Date.parse(next.metrics.updated_at)) / 3600000;
    setStatus(
      ageHours > 8
        ? `Latest observation is ${Math.floor(ageHours)} hours old; a scheduled run may be delayed.`
        : `Watching published results. Last checked ${new Date().toLocaleTimeString()}.`,
      ageHours > 8 ? "delayed" : "current",
    );
  } catch (error) {
    setStatus(
      `Update unavailable: ${error.message} ${dashboard ? "Keeping the last loaded observation. " : ""}` +
      "Retrying in one minute.",
      "error",
    );
  } finally {
    refreshing = false;
    select("#refresh").disabled = false;
  }
}

select("#play").addEventListener("click", () => {
  if (playback) {
    stopPlayback();
    return;
  }
  followingLatest = false;
  if (frameIndex === dashboard.frames.length - 1) showFrame(0);
  select("#play").textContent = "Pause replay";
  playback = setInterval(() => {
    showFrame(frameIndex + 1);
    if (frameIndex === dashboard.frames.length - 1) stopPlayback();
  }, 700);
});
select("#go-live").addEventListener("click", () => {
  stopPlayback();
  followingLatest = true;
  showFrame(dashboard.frames.length - 1);
});
select("#timeline").addEventListener("input", (event) => {
  stopPlayback();
  followingLatest = false;
  showFrame(Number(event.target.value));
});
select("#refresh").addEventListener("click", refreshDashboard);
select("#chart-metric").addEventListener("change", drawHistory);
window.addEventListener("resize", drawHistory);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopPlayback();
  else refreshDashboard();
});
setInterval(() => {
  if (!document.hidden) refreshDashboard();
}, 60000);
refreshDashboard();

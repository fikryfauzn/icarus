(function () {
  const DATE_FMT = "YYYY-MM-DD"; // just mental; HTML date is already YYYY-MM-DD

  function toIsoDateInput(d) {
    return d.toISOString().slice(0, 10);
  }

  function today() {
    return new Date();
  }

  function mondayOfWeek(d) {
    const day = d.getDay(); // 0=Sun .. 6=Sat
    const diff = (day === 0 ? -6 : 1) - day; // shift to Monday
    const m = new Date(d);
    m.setDate(d.getDate() + diff);
    return m;
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return res.json();
  }

  function renderDaySummary(data) {
    const lines = [];
    lines.push(`Date: ${data.date}`);
    lines.push("");
    lines.push(`Total sessions:      ${data.total_sessions}`);
    lines.push(`Deep minutes:        ${data.deep_minutes}`);
    lines.push(`Shallow minutes:     ${data.shallow_minutes}`);
    lines.push(`Maintenance minutes: ${data.maintenance_minutes}`);
    lines.push("");
    lines.push("Minutes by domain:");
    const domains = Object.keys(data.minutes_by_domain || {});
    if (domains.length === 0) {
      lines.push("  (none)");
    } else {
      for (const k of domains) {
        lines.push(`  ${k.padEnd(16, " ")} ${String(data.minutes_by_domain[k]).padStart(4, " ")} min`);
      }
    }
    lines.push("");
    lines.push("Session averages:");
    lines.push(`  Focus quality:   ${data.avg_focus_quality ?? "n/a"}`);
    lines.push(`  Progress rating: ${data.avg_progress_rating ?? "n/a"}`);
    lines.push(`  Quality rating:  ${data.avg_quality_rating ?? "n/a"}`);
    lines.push("");
    lines.push("Sleep:");
    lines.push(`  Duration (min):  ${data.sleep_duration_minutes ?? "n/a"}`);
    lines.push(`  Sleep quality:   ${data.sleep_quality ?? "n/a"}`);
    lines.push(`  Energy morning:  ${data.energy_morning ?? "n/a"}`);
    document.getElementById("day-summary-text").textContent = lines.join("\n");
  }

  function renderWeekStats(data) {
    const lines = [];
    lines.push(`Week: ${data.week_start} to ${data.week_end}`);
    lines.push("");
    lines.push(`Total sessions:      ${data.total_sessions}`);
    lines.push(`Deep minutes:        ${data.deep_minutes}`);
    lines.push(`Shallow minutes:     ${data.shallow_minutes}`);
    lines.push(`Maintenance minutes: ${data.maintenance_minutes}`);
    lines.push("");
    lines.push("Minutes by domain:");
    const domains = Object.keys(data.minutes_by_domain || {});
    if (domains.length === 0) {
      lines.push("  (none)");
    } else {
      for (const k of domains) {
        lines.push(`  ${k.padEnd(16, " ")} ${String(data.minutes_by_domain[k]).padStart(4, " ")} min`);
      }
    }
    lines.push("");
    lines.push("Session averages (days with data):");
    lines.push(`  Focus quality:   ${data.avg_focus_quality ?? "n/a"}`);
    lines.push(`  Progress rating: ${data.avg_progress_rating ?? "n/a"}`);
    lines.push(`  Quality rating:  ${data.avg_quality_rating ?? "n/a"}`);
    lines.push("");
    lines.push("Sleep (days with data):");
    lines.push(`  Avg duration (min): ${data.avg_sleep_duration_minutes ?? "n/a"}`);
    lines.push(`  Avg quality:        ${data.avg_sleep_quality ?? "n/a"}`);
    lines.push(`  Avg energy morning: ${data.avg_energy_morning ?? "n/a"}`);

    document.getElementById("week-stats-text").textContent = lines.join("\n");
  }

  let svdChart = null;

  function renderSleepVsDeepwork(data) {
    const labels = data.map(row => row.date);
    const sleep = data.map(row => row.sleep_minutes ?? null);
    const deep = data.map(row => row.deep_minutes);

    const ctx = document.getElementById("svd-chart").getContext("2d");

    if (svdChart) {
      svdChart.destroy();
    }

    svdChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Sleep (minutes)",
            data: sleep,
            yAxisID: "y1"
          },
          {
            label: "Deep work (minutes)",
            data: deep,
            yAxisID: "y2"
          }
        ]
      },
      options: {
        responsive: true,
        interaction: {
          mode: "index",
          intersect: false
        },
        scales: {
          y1: {
            position: "left",
            title: { display: true, text: "Sleep" }
          },
          y2: {
            position: "right",
            title: { display: true, text: "Deep work" },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });

    const lines = [];
    lines.push("Date        Sleep  Deep");
    for (const row of data) {
      const d = row.date;
      const s = row.sleep_minutes == null ? "  -" : String(row.sleep_minutes).padStart(4, " ");
      const w = String(row.deep_minutes).padStart(4, " ");
      lines.push(`${d}   ${s}  ${w}`);
    }
    document.getElementById("svd-text").textContent = lines.join("\n");
  }

  async function loadDaySummary(dateStr) {
    const url = `/api/day-summary?date=${encodeURIComponent(dateStr)}`;
    const data = await fetchJson(url);
    renderDaySummary(data);
  }

  async function loadWeekStats(weekStartStr) {
    const url = `/api/weekly-stats?week_start=${encodeURIComponent(weekStartStr)}`;
    const data = await fetchJson(url);
    renderWeekStats(data);
  }

  async function loadSleepVsDeepwork(startStr, endStr) {
    const url = `/api/sleep-vs-deepwork?start=${encodeURIComponent(startStr)}&end=${encodeURIComponent(endStr)}`;
    const data = await fetchJson(url);
    renderSleepVsDeepwork(data);
  }

  function init() {
    const todayDate = toIsoDateInput(today());
    const monday = toIsoDateInput(mondayOfWeek(today()));
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today().getDate() - 6);
    const svdStartDefault = toIsoDateInput(sevenDaysAgo);

    const dayInput = document.getElementById("day-date");
    const weekInput = document.getElementById("week-start");
    const svdStartInput = document.getElementById("svd-start");
    const svdEndInput = document.getElementById("svd-end");

    dayInput.value = todayDate;
    weekInput.value = monday;
    svdStartInput.value = svdStartDefault;
    svdEndInput.value = todayDate;

    document.getElementById("day-today").addEventListener("click", () => {
      dayInput.value = toIsoDateInput(today());
      loadDaySummary(dayInput.value).catch(console.error);
    });

    document.getElementById("day-refresh").addEventListener("click", () => {
      loadDaySummary(dayInput.value).catch(console.error);
    });

    document.getElementById("week-refresh").addEventListener("click", () => {
      loadWeekStats(weekInput.value).catch(console.error);
    });

    document.getElementById("svd-refresh").addEventListener("click", () => {
      loadSleepVsDeepwork(svdStartInput.value, svdEndInput.value).catch(console.error);
    });

    // Initial loads
    loadDaySummary(dayInput.value).catch(console.error);
    loadWeekStats(weekInput.value).catch(console.error);
    loadSleepVsDeepwork(svdStartInput.value, svdEndInput.value).catch(console.error);
  }

  document.addEventListener("DOMContentLoaded", init);
})();

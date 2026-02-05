const API_URL = "http://localhost:5000";

document.addEventListener("DOMContentLoaded", () => {
  // Tabs
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      document
        .querySelectorAll(".tab-content")
        .forEach((c) => c.classList.add("hidden"));
      tab.classList.add("active");
      document
        .getElementById(`tab-${tab.dataset.tab}`)
        .classList.remove("hidden");
    });
  });

  // Use Current Tab URL
  document.getElementById("use-current-tab").addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      document.getElementById("url").value = tabs[0].url;
    });
  });

  // Add Field
  document
    .getElementById("add-field-btn")
    .addEventListener("click", () => addFieldRow());

  // Initial field row
  addFieldRow("", "");

  // Start Scraping
  document.getElementById("start-btn").addEventListener("click", startScraping);

  // Detect Fields
  document.getElementById("detect-btn").addEventListener("click", detectFields);

  // Download Buttons
  document
    .getElementById("download-json")
    .addEventListener("click", () => downloadResults("json"));
  document
    .getElementById("download-csv")
    .addEventListener("click", () => downloadResults("csv"));
});

function addFieldRow(name = "", selector = "") {
  const container = document.getElementById("fields-container");
  const div = document.createElement("div");
  div.className = "field-row";
  div.innerHTML = `
        <input type="text" placeholder="Field Name (e.g. Title)" class="field-name" value="${name}">
        <input type="text" placeholder="CSS Selector (e.g. h1)" class="field-selector" value="${selector}">
        <button class="remove-field">×</button>
    `;
  div
    .querySelector(".remove-field")
    .addEventListener("click", () => div.remove());
  container.appendChild(div);
}

async function detectFields() {
  const url = document.getElementById("url").value;
  if (!url) return alert("Please enter a URL first");

  const btn = document.getElementById("detect-btn");
  const originalText = btn.innerText;
  btn.innerText = "Analyzing...";
  btn.disabled = true;

  try {
    const res = await fetch(`${API_URL}/detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url,
        use_selenium: document.getElementById("use_selenium").checked,
        use_tor: document.getElementById("use_tor").checked,
      }),
    });
    const data = await res.json();

    if (data.success && data.detected) {
      document.getElementById("fields-container").innerHTML = ""; // Clear existing
      for (const [key, value] of Object.entries(data.detected)) {
        addFieldRow(key, value);
      }
      alert(`Detected ${Object.keys(data.detected).length} fields!`);
      // Switch to fields tab
      document.querySelector('.tab[data-tab="fields"]').click();
      // Switch logic to Manual
      document.querySelector('input[name="mode"][value="manual"]').checked =
        true;
    } else {
      alert("No common fields detected. Please add manually.");
    }
  } catch (e) {
    alert("Error detecting fields: " + e.message);
  } finally {
    btn.innerText = originalText;
    btn.disabled = false;
  }
}

let currentJobId = null;
let pollInterval = null;

async function startScraping() {
  const url = document.getElementById("url").value;
  if (!url) return alert("Please enter a URL");

  const mode = document.querySelector('input[name="mode"]:checked').value;
  const fields = {};
  if (mode === "manual") {
    document.querySelectorAll(".field-row").forEach((row) => {
      const name = row.querySelector(".field-name").value.trim();
      const sel = row.querySelector(".field-selector").value.trim();
      if (name && sel) fields[name] = sel;
    });
    if (Object.keys(fields).length === 0)
      return alert("Please add at least one field for manual mode");
  }

  const payload = {
    url: url,
    mode: mode,
    auto_mode: mode === "auto",
    fields: fields,
    use_selenium: document.getElementById("use_selenium").checked,
    use_tor: document.getElementById("use_tor").checked,
    infinite_scroll: document.getElementById("infinite_scroll").checked,
    scrape_all: document.getElementById("scrape_all").checked,
    max_pages: parseInt(document.getElementById("max_pages").value),
    next_selector: document.getElementById("next_selector").value,
  };

  // UI Update
  document.getElementById("status-area").classList.remove("hidden");
  document.getElementById("status-text").innerHTML =
    '<div class="spinner"></div> Starting scraper...';
  document.getElementById("results-actions").classList.add("hidden");
  document.getElementById("start-btn").disabled = true;

  try {
    const res = await fetch(`${API_URL}/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.job_id) {
      currentJobId = data.job_id;
      pollInterval = setInterval(checkStatus, 1000);
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (e) {
    document.getElementById("status-text").innerText = "Error: " + e.message;
    document.getElementById("start-btn").disabled = false;
  }
}

async function checkStatus() {
  if (!currentJobId) return;

  try {
    const res = await fetch(`${API_URL}/status/${currentJobId}`);
    const data = await res.json();

    if (data.status === "completed") {
      clearInterval(pollInterval);
      document.getElementById("status-text").innerText =
        `✅ Completed! Scraped ${data.results.length} items.`;
      document.getElementById("progress-fill").style.width = "100%";
      document.getElementById("results-actions").classList.remove("hidden");
      document.getElementById("start-btn").disabled = false;
      window.lastResults = data.results; // Store for download
    } else if (data.status === "failed") {
      clearInterval(pollInterval);
      document.getElementById("status-text").innerText =
        `❌ Failed: ${data.error}`;
      document.getElementById("start-btn").disabled = false;
    } else {
      // Running
      const p = data.progress;
      const text = p.total
        ? `Scraping page ${p.page} of ${p.total}...`
        : `Scraping page ${p.page}...`;
      document.getElementById("status-text").innerHTML =
        `<div class="spinner"></div> ${text}`;
      if (p.total > 0) {
        const pct = (p.page / p.total) * 100;
        document.getElementById("progress-fill").style.width = `${pct}%`;
      }
    }
  } catch (e) {
    console.error("Polling error", e);
  }
}

function downloadResults(format) {
  if (!window.lastResults) return;

  let content = "";
  let type = "";
  let ext = "";

  if (format === "json") {
    content = JSON.stringify(window.lastResults, null, 2);
    type = "application/json";
    ext = "json";
  } else if (format === "csv") {
    // Simple CSV converter
    const items = window.lastResults;
    const headers = [...new Set(items.flatMap(Object.keys))];
    content = headers.join(",") + "\n";
    content += items
      .map((item) => {
        return headers
          .map((h) => {
            const val = item[h] || "";
            return `"${String(val).replace(/"/g, '""')}"`;
          })
          .join(",");
      })
      .join("\n");
    type = "text/csv";
    ext = "csv";
  }

  const blob = new Blob([content], { type: type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `scraped_data.${ext}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

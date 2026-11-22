"use strict";

const form = document.getElementById("profile-form");
const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit");
const result = document.getElementById("result");
const cityError = document.getElementById("city-error");
const cityInput = document.getElementById("city");

function setStatus(text) { statusEl.textContent = text; }

function showCityError(message) {
  cityError.hidden = !message;
  cityError.textContent = message || "";
  cityInput.setAttribute("aria-invalid", message ? "true" : "false");
}

// Builds list items with textContent only, so server data is never parsed as HTML.
function renderActions(id, items) {
  const list = document.getElementById(id);
  list.replaceChildren(...items.map((a) => {
    const li = document.createElement("li");
    for (const [cls, tag, text] of [["", "strong", a.title], ["why", "span", a.why], ["impact", "span", `Impact: ${a.impact}`]]) {
      const el = document.createElement(tag);
      if (cls) el.className = cls;
      el.textContent = text;
      li.append(el);
    }
    return li;
  }));
}

function markerPosition(aqi) {
  const stops = [50, 100, 150, 200, 300, 500];
  const seg = 100 / stops.length;
  let low = 0;
  for (let i = 0; i < stops.length; i++) {
    if (aqi <= stops[i]) return i * seg + ((aqi - low) / (stops[i] - low)) * seg;
    low = stops[i];
  }
  return 100;
}

function render(data) {
  document.getElementById("result-title").textContent = `${data.place}: ${data.label}`;
  document.getElementById("summary").textContent = data.summary;
  document.getElementById("marker").style.left = `calc(${markerPosition(data.aqi)}% - 2px)`;
  const narrative = document.getElementById("narrative");
  narrative.hidden = !data.narrative;
  narrative.textContent = data.narrative || "";
  renderActions("routines", data.routines);
  renderActions("indoor", data.indoor);
  renderActions("alternatives", data.alternatives);
  result.hidden = false;
  result.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showCityError("");
  const fd = new FormData(form);
  const city = String(fd.get("city") || "").trim();
  if (city.length < 2) {
    showCityError("Enter your city name.");
    cityInput.focus();
    return;
  }
  const payload = {
    city,
    home: fd.get("home"),
    commute: fd.get("commute"),
    heating: fd.get("heating"),
    groups: fd.getAll("groups"),
    manual_aqi: fd.get("manual_aqi"),
  };

  submitBtn.disabled = true;
  setStatus("Checking today's air quality…");
  try {
    const res = await fetch("/api/advice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
    setStatus("Your plan is ready.");
    render(data);
  } catch (err) {
    setStatus(err.message);
  } finally {
    submitBtn.disabled = false;
  }
});

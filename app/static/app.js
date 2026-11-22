"use strict";

(() => {
  const REQUEST_TIMEOUT_MS = 15000;
  const MIN_CITY_LENGTH = 2;

  const form = document.getElementById("profile-form");
  const statusEl = document.getElementById("status");
  const submitBtn = document.getElementById("submit");
  const result = document.getElementById("result");
  const cityError = document.getElementById("city-error");
  const cityInput = document.getElementById("city");

  const setStatus = (text) => { statusEl.textContent = text; };

  function showCityError(message) {
    cityError.hidden = !message;
    cityError.textContent = message || "";
    cityInput.setAttribute("aria-invalid", message ? "true" : "false");
  }

  function actionItem({ title, why, impact }) {
    const li = document.createElement("li");
    const parts = [
      ["strong", "", title],
      ["span", "why", why],
      ["span", "impact", `Impact: ${impact}`],
    ];
    for (const [tag, cls, text] of parts) {
      const el = document.createElement(tag);
      if (cls) el.className = cls;
      el.textContent = text; // textContent only: server data is never parsed as HTML
      li.append(el);
    }
    return li;
  }

  const renderActions = (id, items) =>
    document.getElementById(id).replaceChildren(...items.map(actionItem));

  function render(data) {
    document.getElementById("result-title").textContent = `${data.place}: ${data.label}`;
    document.getElementById("summary").textContent = data.summary;
    document.getElementById("data-source").textContent =
      `Data source: ${data.data_source}. ${data.disclaimer}`;
    document.getElementById("marker").style.left = `calc(${data.gauge_position}% - 2px)`;
    document.getElementById("gauge").setAttribute("aria-label",
      `AQI ${data.aqi}: ${data.label}`);
    const narrative = document.getElementById("narrative");
    narrative.hidden = !data.narrative;
    narrative.textContent = data.narrative || "";
    renderActions("routines", data.routines);
    renderActions("indoor", data.indoor);
    renderActions("alternatives", data.alternatives);
    result.hidden = false;
    result.focus();
  }

  function buildPayload(city) {
    const fd = new FormData(form);
    return {
      city,
      home: fd.get("home"),
      commute: fd.get("commute"),
      heating: fd.get("heating"),
      groups: fd.getAll("groups"),
      manual_aqi: fd.get("manual_aqi"),
    };
  }

  async function requestAdvice(payload) {
    const res = await fetch("/api/advice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
    return data;
  }

  function friendlyError(err) {
    if (err.name === "TimeoutError") return "The request took too long. Please try again.";
    if (err instanceof TypeError) return "Network problem. Check your connection and try again.";
    return err.message;
  }

  async function onSubmit(event) {
    event.preventDefault();
    showCityError("");
    const city = String(new FormData(form).get("city") || "").trim();
    if (city.length < MIN_CITY_LENGTH) {
      showCityError("Enter your city name.");
      cityInput.focus();
      return;
    }

    submitBtn.disabled = true;
    form.setAttribute("aria-busy", "true");
    setStatus("Checking today's air quality…");
    try {
      const data = await requestAdvice(buildPayload(city));
      setStatus("Your plan is ready.");
      render(data);
    } catch (err) {
      setStatus(friendlyError(err));
    } finally {
      submitBtn.disabled = false;
      form.removeAttribute("aria-busy");
    }
  }

  form.addEventListener("submit", onSubmit);
})();

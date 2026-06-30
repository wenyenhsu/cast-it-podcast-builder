(() => {
  const STORAGE_KEY = "castItTrackedJobs";
  const POLL_MS = 2000;

  function readTrackedJobs() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      return [];
    }
  }

  function writeTrackedJobs(jobs) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  }

  function trackJob(jobId, label, options = {}) {
    if (!jobId) {
      return;
    }
    const { supersedeActive = false, replaceLabel = false } = options;
    const resolvedLabel = label || "Background Job";
    let jobs = readTrackedJobs();

    jobs = jobs.filter((job) => job.id !== jobId);

    if (supersedeActive) {
      jobs = jobs.filter((job) => job.lastData?.is_terminal);
    }

    if (replaceLabel) {
      jobs = jobs.filter((job) => {
        const jobLabel = job.lastData?.label || job.label;
        return jobLabel !== resolvedLabel || job.lastData?.is_terminal === true;
      });
    }

    jobs.unshift({
      id: jobId,
      label: resolvedLabel,
      trackedAt: Date.now(),
    });
    writeTrackedJobs(jobs.slice(0, 8));
    renderTray();
    pollJobs();
  }

  function removeJob(jobId) {
    writeTrackedJobs(readTrackedJobs().filter((job) => job.id !== jobId));
    document.querySelectorAll(`[data-inline-job="${jobId}"]`).forEach((target) => {
      target.hidden = true;
      target.innerHTML = "";
    });
    renderTray();
  }

  function clearAllJobs() {
    writeTrackedJobs([]);
    document.querySelectorAll("[data-inline-job]").forEach((target) => {
      target.hidden = true;
      target.innerHTML = "";
    });
    renderTray();
  }

  function dedupeActiveJobs(jobs) {
    const seenLabels = new Set();
    const deduped = [];
    for (const job of jobs) {
      const label = job.lastData?.label || job.label || "Background Job";
      const isTerminal = job.lastData?.is_terminal === true;
      if (!isTerminal && seenLabels.has(label)) {
        continue;
      }
      if (!isTerminal) {
        seenLabels.add(label);
      }
      deduped.push(job);
    }
    return deduped;
  }

  function statusUrl(jobId) {
    return `/operations/api/jobs/${jobId}/`;
  }

  function statusClass(status) {
    if (status === "succeeded") {
      return "success";
    }
    if (status === "failed") {
      return "danger";
    }
    if (status === "running" || status === "retrying") {
      return "primary";
    }
    return "secondary";
  }

  function renderProgressBar(progress, status) {
    const value = Math.max(0, Math.min(100, Number(progress) || 0));
    return `
      <div class="ops-progress-bar" role="progressbar" aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="100">
        <div class="ops-progress-fill ops-progress-fill-${statusClass(status)}" style="width: ${value}%;"></div>
        <span class="ops-progress-label">${value}%</span>
      </div>
    `;
  }

  function renderTrayItem(job, data) {
    const status = data?.status || "queued";
    const progress = data?.progress ?? 0;
    const label = data?.label || job.label || "Background Job";
    const detail = data?.status_message || data?.error_message || data?.status || "";
    const dismiss = `<button type="button" class="btn btn-sm btn-link p-0 ops-job-dismiss" data-job-id="${job.id}">Dismiss</button>`;

    return `
      <div class="ops-job-card" data-job-id="${job.id}">
        <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
          <div>
            <div class="fw-semibold small">${label}</div>
            <div class="text-secondary ops-job-status">${detail}</div>
          </div>
          <span class="badge text-bg-${statusClass(status)} text-capitalize">${status}</span>
        </div>
        ${renderProgressBar(progress, status)}
        <div class="d-flex justify-content-end mt-2">${dismiss}</div>
      </div>
    `;
  }

  function renderInlineTarget(target, data) {
    if (!target || !data) {
      return;
    }
    target.hidden = false;
    target.innerHTML = `
      <div class="ops-inline-job-progress">
        <div class="d-flex justify-content-between align-items-center gap-2 mb-2">
          <span class="fw-semibold small">${data.label || "Background Job"}</span>
          <span class="badge text-bg-${statusClass(data.status)} text-capitalize">${data.status}</span>
        </div>
        ${renderProgressBar(data.progress, data.status)}
        <div class="text-secondary small mt-2 ops-job-status">${data.status_message || data.error_message || "Working..."}</div>
      </div>
    `;
    if (data.is_terminal && data.status === "succeeded") {
      target.querySelector(".ops-job-status").textContent = "Completed. Refresh to see results.";
    }
  }

  function renderTray() {
    const tray = document.getElementById("ops-job-tray");
    const list = document.getElementById("ops-job-tray-list");
    if (!tray || !list) {
      return;
    }
    const jobs = readTrackedJobs();
    if (!jobs.length) {
      tray.hidden = true;
      list.innerHTML = "";
      const clearAll = document.getElementById("ops-job-tray-clear");
      if (clearAll) {
        clearAll.hidden = true;
      }
      return;
    }
    tray.hidden = false;
    list.innerHTML = jobs
      .map((job) => renderTrayItem(job, job.lastData))
      .join("");
    list.querySelectorAll(".ops-job-dismiss").forEach((button) => {
      button.addEventListener("click", () => removeJob(button.dataset.jobId));
    });
    const clearAll = document.getElementById("ops-job-tray-clear");
    if (clearAll) {
      clearAll.hidden = false;
    }
  }

  async function fetchJob(jobId) {
    const response = await fetch(statusUrl(jobId), {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!response.ok) {
      throw new Error(`Job status request failed (${response.status})`);
    }
    return response.json();
  }

  async function pollJobs() {
    const jobs = readTrackedJobs();
    if (!jobs.length) {
      renderTray();
      return;
    }

    const updated = [];
    for (const job of jobs) {
      try {
        const data = await fetchJob(job.id);
        job.lastData = data;
        updated.push(job);

        document.querySelectorAll(`[data-inline-job="${job.id}"]`).forEach((target) => {
          renderInlineTarget(target, data);
        });
      } catch (error) {
        if (error instanceof Error && error.message.includes("(404)")) {
          continue;
        }
        job.lastData = job.lastData || {
          label: job.label,
          status: "queued",
          progress: 2,
          status_message: "Connecting to job status...",
          error_message: "",
          is_terminal: false,
        };
        updated.push(job);
      }
    }
    writeTrackedJobs(dedupeActiveJobs(updated));
    renderTray();
  }

  function bootstrapJobTracking() {
    const params = new URLSearchParams(window.location.search);
    const abortedJobId = params.get("aborted_job");
    if (abortedJobId) {
      removeJob(abortedJobId);
      params.delete("aborted_job");
      const query = params.toString();
      const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
      window.history.replaceState({}, "", nextUrl);
    }

    const urlJobId = params.get("job");
    const inlineTargets = [...document.querySelectorAll("[data-inline-job]")];
    const inlineLabel =
      inlineTargets[0]?.dataset.inlineJobLabel || "Background Job";

    if (urlJobId) {
      inlineTargets.forEach((target) => {
        target.dataset.inlineJob = urlJobId;
        target.hidden = false;
      });
      trackJob(urlJobId, inlineLabel, {
        supersedeActive: true,
        replaceLabel: true,
      });
      params.delete("job");
      const query = params.toString();
      const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
      window.history.replaceState({}, "", nextUrl);
      return;
    }

    inlineTargets.forEach((target) => {
      const jobId = target.dataset.inlineJob;
      if (!jobId) {
        return;
      }
      const label = target.dataset.inlineJobLabel || "Background Job";
      const alreadyTracked = readTrackedJobs().some((job) => job.id === jobId);
      if (!alreadyTracked) {
        trackJob(jobId, label, { replaceLabel: true });
      }
    });
  }

  function preventDoubleSubmit() {
    document.querySelectorAll("form").forEach((form) => {
      form.addEventListener("submit", () => {
        form.querySelectorAll('button[type="submit"]').forEach((button) => {
          button.disabled = true;
          if (form.dataset.scriptGenerateForm !== undefined) {
            button.classList.remove("btn-primary");
            button.classList.add("btn-secondary");
          }
          if (button.dataset.loadingLabel) {
            button.innerHTML = button.dataset.loadingLabel;
          }
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    writeTrackedJobs(dedupeActiveJobs(readTrackedJobs()));
    bootstrapJobTracking();
    preventDoubleSubmit();
    renderTray();
    pollJobs();
    window.setInterval(pollJobs, POLL_MS);
    const clearAll = document.getElementById("ops-job-tray-clear");
    if (clearAll) {
      clearAll.addEventListener("click", clearAllJobs);
    }
  });

  window.CastItJobs = { trackJob, pollJobs, removeJob, clearAllJobs };
})();

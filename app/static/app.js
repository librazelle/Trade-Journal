(function () {
  const feed = document.getElementById("live-feed");
  const liveStatus = document.getElementById("live-status");

  const emptyParagraph = (text) => {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = text;
    return p;
  };

  // ---------- Tab bawah (mobile). Di desktop semua panel tampil sekaligus. ----------
  const layout = document.querySelector(".layout");
  const tabBar = document.querySelector(".mobile-tabs");
  if (layout && tabBar) {
    const setTab = (name) => {
      layout.dataset.activeTab = name;
      tabBar.querySelectorAll("[data-tab-target]").forEach(button => {
        const active = button.dataset.tabTarget === name;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
      });
      window.scrollTo({ top: 0 });
    };
    tabBar.addEventListener("click", event => {
      const button = event.target.closest("[data-tab-target]");
      if (button) setTab(button.dataset.tabTarget);
    });
    setTab(layout.dataset.activeTab || "calendar");
  }

  // ---------- Tombol segmen (Long/Short, Naik/Turun) ----------
  document.querySelectorAll(".segmented").forEach(group => {
    const field = group.closest(".field");
    const input = field && field.querySelector('input[type="hidden"]');
    if (!input) return;
    group.addEventListener("click", event => {
      const button = event.target.closest("button[data-value]");
      if (!button) return;
      input.value = button.dataset.value;
      group.querySelectorAll("button[data-value]").forEach(item => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
    });
  });

  // ---------- Pilihan cara baca berita (tersimpan di localStorage) ----------
  const readingMode = document.getElementById("reading-mode");
  let currentReadingMode = "original";
  const applyReadingMode = (mode) => {
    currentReadingMode = mode;
    document.querySelectorAll(".news").forEach(article => {
      article.classList.toggle("mode-normal", mode === "normal");
      article.classList.toggle("mode-simple", mode === "simple");
    });
  };
  if (readingMode) {
    const storedMode = localStorage.getItem("tradeLensReadingMode");
    const savedMode = ["original", "normal", "simple"].includes(storedMode) ? storedMode : "original";
    readingMode.value = savedMode;
    applyReadingMode(savedMode);
    readingMode.addEventListener("change", () => {
      localStorage.setItem("tradeLensReadingMode", readingMode.value);
      applyReadingMode(readingMode.value);
    });
  }

  // ---------- Filter kategori berita ----------
  const filterBar = document.querySelector(".news-category-nav");
  const filterCount = document.getElementById("news-filter-count");
  let activeNewsFilter = "all";
  const categoryFor = (article) => {
    const text = (article.innerText || "").toLowerCase();
    const tags = Array.from(article.querySelectorAll(".tags span")).map(el => el.textContent.toLowerCase()).join(" ");
    const haystack = text + " " + tags;
    if (/fomc|federal reserve|\bfed\b|powell|interest rate|rate decision|monetary policy/.test(haystack)) return "fed";
    if (/inflation|consumer price|\bcpi\b|\bppi\b|\bpce\b|price index/.test(haystack)) return "inflation";
    if (/nonfarm|payroll|unemployment|employment|job openings|labor market|labour market|wage/.test(haystack)) return "jobs";
    if (/gdp|gross domestic|productivity|business activity|consumer spending|retail sales|economic growth/.test(haystack)) return "economy";
    if (/geopolit|war |sanction|tariff|trade war|iran|israel|ukraine|russia|missile|conflict/.test(haystack)) return "geopolitics";
    if (/oil|crude|opec|energy|natural gas|brent|wti/.test(haystack)) return "energy";
    return "other";
  };
  const applyNewsFilter = () => {
    if (!feed) return;
    const articles = Array.from(feed.querySelectorAll(".news"));
    let visible = 0;
    articles.forEach(article => {
      const category = categoryFor(article);
      article.dataset.newsCategory = category;
      const show = activeNewsFilter === "all" || category === activeNewsFilter;
      article.hidden = !show;
      if (show) visible += 1;
    });
    if (filterCount) {
      const label = filterBar && filterBar.querySelector('[data-news-filter="' + activeNewsFilter + '"]');
      filterCount.textContent = (label ? label.textContent : "Semua") + " · " + visible + " berita";
    }
  };
  if (filterBar) {
    filterBar.addEventListener("click", event => {
      const button = event.target.closest("[data-news-filter]");
      if (!button) return;
      activeNewsFilter = button.dataset.newsFilter;
      filterBar.querySelectorAll(".news-filter").forEach(item => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      applyNewsFilter();
    });
    filterBar.querySelectorAll(".news-filter").forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.newsFilter === "all"));
    });
    applyNewsFilter();
  }

  // ---------- Status sumber berita (disembunyikan di balik <details>) ----------
  const pane = feed && feed.closest(".wire-pane");
  if (pane) {
    const healthPanel = document.createElement("details");
    healthPanel.className = "source-health-panel";
    const healthSummary = document.createElement("summary");
    healthSummary.textContent = "Status sumber berita";
    const healthChecked = document.createElement("p");
    healthChecked.className = "muted source-health-checked";
    healthChecked.textContent = "Memeriksa status polling...";
    const healthList = document.createElement("div");
    healthList.className = "source-health-list";
    healthPanel.append(healthSummary, healthChecked, healthList);
    pane.insertBefore(healthPanel, pane.querySelector(".priority-news-panel"));

    const refreshSourceHealth = async () => {
      try {
        const response = await fetch("/api/source-health", { cache: "no-store" });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const payload = await response.json();
        healthList.replaceChildren();
        if (!payload.sources || !payload.sources.length) {
          healthChecked.textContent = "Menunggu polling pertama dari server.";
          return;
        }
        payload.sources.forEach(source => {
          const row = document.createElement("article");
          row.className = "source-health-row";
          const name = document.createElement("strong");
          name.textContent = source.label || source.name;
          const badge = document.createElement("span");
          const state = source.status || "STALE";
          badge.className = "source-badge " + String(state).toLowerCase();
          badge.textContent = state;
          const parts = [];
          if (source.last_success_at) {
            parts.push("polling berhasil " + (source.last_success_age_seconds ?? 0) + " detik lalu");
          } else if (source.last_error) {
            parts.push("belum berhasil · " + source.last_error);
          } else {
            parts.push("menunggu polling pertama");
          }
          if (source.last_new_item_delay_min !== null && source.last_new_item_delay_min !== undefined) {
            parts.push("latensi " + source.last_new_item_delay_min + " menit");
          }
          const detail = document.createElement("p");
          detail.className = "muted";
          detail.textContent = parts.join(" · ");
          row.append(name, badge, detail);
          healthList.appendChild(row);
        });
        healthChecked.textContent = "Diperbarui " + new Date(payload.checked_at).toLocaleTimeString("id-ID");
      } catch (_) {
        healthChecked.textContent = "Status sumber tidak dapat diambil dari server.";
      }
    };
    refreshSourceHealth();
    window.setInterval(refreshSourceHealth, 10000);
  }

  // ---------- Kalender ekonomi AS (jadwal resmi BLS) ----------
  const calendarPanel = document.getElementById("calendar-panel");
  if (calendarPanel) initCalendar(calendarPanel);

  function initCalendar(panel) {
    const statusLine = panel.querySelector("#calendar-status");
    const list = panel.querySelector("#calendar-list");
    const pad = (n) => String(n).padStart(2, "0");
    const formatTime = (date, zone) => new Intl.DateTimeFormat("id-ID", {
      timeZone: zone, day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit", hour12: false
    }).format(date);

    // Jarak jauh cukup hari dan jam. Hanya di bawah satu jam countdown memakai mm:ss.
    const countdownText = (remaining) => {
      if (remaining <= 0) return { text: "Rilis sekarang", soon: true };
      if (remaining < 3600) {
        return { text: "Rilis dalam " + pad(Math.floor(remaining / 60)) + ":" + pad(remaining % 60), soon: true };
      }
      const days = Math.floor(remaining / 86400);
      const hours = Math.floor((remaining % 86400) / 3600);
      const minutes = Math.floor((remaining % 3600) / 60);
      if (days === 0) return { text: "Rilis dalam " + hours + " jam " + minutes + " menit", soon: false };
      return { text: "Rilis dalam " + days + " hari " + hours + " jam", soon: false };
    };

    let upcoming = [];

    const updateCountdowns = () => {
      const now = Date.now();
      list.querySelectorAll(".calendar-countdown").forEach(node => {
        const target = Date.parse(node.dataset.scheduledAt);
        if (!Number.isFinite(target)) {
          node.textContent = "Waktu rilis tidak valid";
          node.classList.remove("soon");
          return;
        }
        const { text, soon } = countdownText(Math.max(0, Math.floor((target - now) / 1000)));
        if (node.textContent !== text) node.textContent = text;
        node.classList.toggle("soon", soon);
      });
    };

    const render = () => {
      const now = Date.now();
      upcoming = upcoming.filter(event => Date.parse(event.scheduled_at_utc) >= now);
      list.replaceChildren();
      if (!upcoming.length) {
        list.appendChild(emptyParagraph("Tidak ada jadwal BLS mendatang pada data yang tersedia."));
        return;
      }
      upcoming.slice(0, 8).forEach(event => {
        const impact = ["high", "medium", "low"].includes(event.impact) ? event.impact : "unknown";
        const article = document.createElement("article");
        article.className = "calendar-event " + impact;

        const title = document.createElement("a");
        title.className = "calendar-title";
        title.textContent = event.name || "Rilis ekonomi";
        title.href = event.url || event.source_url || "https://www.bls.gov/schedule/";
        title.target = "_blank";
        title.rel = "noopener noreferrer";

        const date = new Date(event.scheduled_at_utc);
        const meta = document.createElement("div");
        meta.className = "calendar-meta";
        meta.textContent = "WIB " + formatTime(date, "Asia/Jakarta") + " · ET " + formatTime(date, "America/New_York") + " · ";
        const badge = document.createElement("span");
        badge.className = "impact-badge " + impact;
        badge.textContent = impact === "unknown" ? "DAMPAK ?" : impact.toUpperCase();
        meta.appendChild(badge);

        const countdown = document.createElement("div");
        countdown.className = "calendar-countdown";
        countdown.dataset.scheduledAt = event.scheduled_at_utc;

        article.append(title, meta, countdown);
        list.appendChild(article);
      });
      updateCountdowns();
    };

    list.replaceChildren(emptyParagraph("Mengambil jadwal resmi..."));
    fetch("/api/calendar")
      .then(response => {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(payload => {
        upcoming = (payload.events || []).filter(event => event.scheduled_at_utc);
        statusLine.textContent = payload.stale ? "cache lama" : "sumber resmi";
        render();
        window.setInterval(updateCountdowns, 1000);
        window.setInterval(render, 60000);
      })
      .catch(() => {
        statusLine.textContent = "tidak tersedia";
        list.replaceChildren(emptyParagraph("Jadwal BLS gagal dimuat. Feed berita tetap berjalan."));
      });
  }

  // ---------- Berita live lewat SSE ----------
  if (!feed || !window.EventSource) return;
  const setStatus = (text) => { if (liveStatus) liveStatus.textContent = text; };
  const es = new EventSource("/stream/news");
  es.onopen = () => setStatus("tersambung");
  es.onerror = () => setStatus("menyambung ulang");
  es.addEventListener("news", (e) => {
    const empty = feed.querySelector(".empty");
    if (empty) empty.remove();
    feed.insertAdjacentHTML("afterbegin", e.data);
    applyReadingMode(currentReadingMode);
    applyNewsFilter();
  });
})();

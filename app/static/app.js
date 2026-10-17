(function () {
  const feed = document.getElementById("live-feed");
  const liveStatus = document.getElementById("live-status");

  // ---------- Toolbar: market clocks + local drawdown calculator ----------
  const marketClock = document.getElementById("market-clock");
  if (marketClock) initMarketClock(marketClock);

  function initMarketClock(root) {
    const readout = root.querySelector("#clock-readout");
    const buttons = [...root.querySelectorAll("[data-clock-view]")];
    const STORAGE_KEY = "tradeLensDrawdownInputs";
    let view = "drawdown";
    let drawdown = { balance: "", equity: "" };
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      if (saved && typeof saved === "object") drawdown = { ...drawdown, ...saved };
    } catch (_) {}

    const escapeText = value => String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
    const formatMoney = value => new Intl.NumberFormat("en-US", {
      style: "currency", currency: "USD", maximumFractionDigits: 2
    }).format(value);
    const formatClock = (date, zone, withDate = false) => new Intl.DateTimeFormat("id-ID", {
      timeZone: zone, hour: "2-digit", minute: "2-digit", second: "2-digit",
      hourCycle: "h23", ...(withDate ? { weekday: "short", day: "2-digit", month: "short" } : {})
    }).format(date);
    const zoneParts = (date, zone) => {
      const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: zone, hour: "2-digit", minute: "2-digit", hourCycle: "h23"
      }).formatToParts(date);
      return Object.fromEntries(parts.filter(part => part.type !== "literal").map(part => [part.type, Number(part.value)]));
    };
    const sessions = {
      asia: { label: "Sesi Asia", city: "Tokyo", zone: "Asia/Tokyo", open: 9, close: 18 },
      europe: { label: "Sesi Eropa", city: "London", zone: "Europe/London", open: 8, close: 17 },
      newyork: { label: "Sesi New York", city: "New York", zone: "America/New_York", open: 8, close: 17 }
    };

    function render() {
      buttons.forEach(button => {
        const active = button.dataset.clockView === view;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      const now = new Date();
      if (view === "drawdown") {
        const balance = Number(drawdown.balance);
        const equity = Number(drawdown.equity);
        const valid = drawdown.balance !== "" && drawdown.equity !== "" &&
          Number.isFinite(balance) && Number.isFinite(equity) && balance > 0;
        const dd = valid ? Math.max(0, balance - equity) : 0;
        const pct = valid ? dd / balance * 100 : 0;
        const above = valid && equity > balance;
        readout.innerHTML = `
          <div class="clock-label">Drawdown tracker <span>· lokal di perangkat</span></div>
          <div class="drawdown-fields">
            <label>Balance acuan (USD)<input id="dd-balance" inputmode="decimal" type="number" min="0" step="any" value="${escapeText(drawdown.balance)}"></label>
            <label>Equity sekarang (USD)<input id="dd-equity" inputmode="decimal" type="number" min="0" step="any" value="${escapeText(drawdown.equity)}"></label>
          </div>
          <div class="clock-result">
            <strong>${valid ? (above ? "+" + formatMoney(equity - balance) : "-" + formatMoney(dd)) : "Isi angka valid"}</strong>
            <span>${valid ? (above ? "Di atas balance acuan" : "Drawdown " + pct.toFixed(2) + "%") : "Balance acuan harus lebih dari 0"}</span>
          </div>
          <p class="clock-footnote">Hitungan sederhana dari balance acuan ke equity. Bukan data otomatis dari MetaTrader.</p>`;
        ["dd-balance", "dd-equity"].forEach(id => {
          const input = readout.querySelector("#" + id);
          input.addEventListener("change", () => {
            drawdown[id === "dd-balance" ? "balance" : "equity"] = input.value;
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify(drawdown)); } catch (_) {}
            render();
          });
        });
        return;
      }
      const session = sessions[view];
      if (!session) return;
      const parts = zoneParts(now, session.zone);
      const isOpen = parts.hour >= session.open && parts.hour < session.close;
      const minsToClose = (session.close - parts.hour - 1) * 60 + (59 - parts.minute);
      const nextText = isOpen
        ? "Tutup sekitar " + Math.max(0, Math.floor(minsToClose / 60)) + "j " + Math.max(0, minsToClose % 60) + "m lagi"
        : "Di luar jam sesi";
      readout.innerHTML = `
        <div class="clock-label">${session.label} <span>· ${session.city}</span></div>
        <div class="clock-main">${formatClock(now, session.zone)} <span>${session.zone}</span></div>
        <div class="clock-meta">WIB ${formatClock(now, "Asia/Jakarta")} · Jam sesi ${String(session.open).padStart(2,"0")}:00–${String(session.close).padStart(2,"0")}:00 waktu lokal</div>
        <div class="clock-status ${isOpen ? "is-open" : "is-closed"}"><i></i>${isOpen ? "SESI BUKA" : "SESI TUTUP"} <span>${nextText}</span></div>`;
    }
    buttons.forEach(button => button.addEventListener("click", () => {
      view = button.dataset.clockView;
      render();
    }));
    render();
    window.setInterval(() => {
      if (view !== "drawdown") render();
    }, 1000);
  }

  const emptyParagraph = (text) => {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = text;
    return p;
  };

  // ---------- Database lokal perangkat + backup JSON ----------
  // IndexedDB menyimpan entry baru pada origin browser ini. Jangan kirim data lokal ke server.
  const localPanel = document.getElementById("local-storage-panel");
  if (localPanel) initLocalStorage(localPanel);

  function initLocalStorage(panel) {
    const status = panel.querySelector("#local-storage-status");
    const recordsNode = panel.querySelector("#local-records");
    const tradeCount = panel.querySelector("#local-trade-count");
    const reactionCount = panel.querySelector("#local-reaction-count");
    const exportButton = panel.querySelector("#local-backup-export");
    const migrateButton = panel.querySelector("#local-migrate-server");
    const importButton = panel.querySelector("#local-backup-import");
    const importFile = panel.querySelector("#local-backup-file");
    const DB_NAME = "trade-lens-local";
    const DB_VERSION = 1;
    let db;

    const openDb = () => new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) return reject(new Error("Browser ini tidak mendukung IndexedDB."));
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains("records")) {
          const store = database.createObjectStore("records", { keyPath: "uid" });
          store.createIndex("kind", "kind", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Database lokal gagal dibuka."));
    });
    const allRecords = () => new Promise((resolve, reject) => {
      const request = db.transaction("records", "readonly").objectStore("records").getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
    const putRecord = record => new Promise((resolve, reject) => {
      const tx = db.transaction("records", "readwrite");
      tx.objectStore("records").put(record);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error("Gagal menyimpan catatan lokal."));
      tx.onabort = () => reject(tx.error || new Error("Penyimpanan dibatalkan."));
    });
    const safeText = value => value === null || value === undefined || value === "" ? "—" : String(value);
    const renderRecords = async () => {
      const rows = await allRecords();
      rows.sort((a, b) => String(b.savedAt).localeCompare(String(a.savedAt)));
      const trades = rows.filter(row => row.kind === "trade");
      const reactions = rows.filter(row => row.kind === "reaction");
      tradeCount.textContent = trades.length + " trade lokal";
      reactionCount.textContent = reactions.length + " reaksi lokal";
      recordsNode.replaceChildren();
      if (!rows.length) {
        recordsNode.appendChild(emptyParagraph("Belum ada catatan lokal. Trade dan reaksi baru akan tersimpan di perangkat ini."));
        return;
      }
      rows.slice(0, 12).forEach(row => {
        const article = document.createElement("article");
        article.className = "local-record";
        const title = document.createElement("strong");
        const detail = document.createElement("p");
        const when = document.createElement("small");
        if (row.kind === "trade") {
          title.textContent = (row.data.direction || "trade").toUpperCase() + " · " + safeText(row.data.instrument);
          detail.textContent = "Entry " + safeText(row.data.entry_price) + " · SL " + safeText(row.data.sl) + " · TP " + safeText(row.data.tp) + " · Lot " + safeText(row.data.lot);
        } else {
          title.textContent = safeText(row.data.event_type) + " · " + safeText(row.data.instrument);
          detail.textContent = "Bias " + safeText(row.data.expected_direction) + " · " + safeText(row.data.price_before) + " → " + safeText(row.data.price_after_15m);
        }
        when.textContent = safeText(row.data.entry_time || row.data.release_time || row.savedAt);
        article.append(title, detail, when);
        recordsNode.appendChild(article);
      });
      if (rows.length > 12) {
        const note = document.createElement("p");
        note.className = "muted";
        note.textContent = "Menampilkan 12 dari " + rows.length + " catatan lokal. Semua catatan masuk ke backup.";
        recordsNode.appendChild(note);
      }
    };
    const makeUid = () => (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : "tl-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    const backup = async () => {
      const rows = await allRecords();
      const payload = { format: "trade-lens-local-backup", version: 1, exportedAt: new Date().toISOString(), records: rows };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "Trade-Lens-Backup-" + new Date().toISOString().slice(0, 10) + ".json";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      status.textContent = "Backup dibuat. Pindahkan file ke Documents/Trade-Lens.";
    };
    const restore = async file => {
      const payload = JSON.parse(await file.text());
      if (!payload || payload.format !== "trade-lens-local-backup" || payload.version !== 1 || !Array.isArray(payload.records)) {
        throw new Error("Format backup tidak dikenal. Data tidak diubah.");
      }
      if (payload.records.length > 20000) throw new Error("Backup terlalu besar untuk dipulihkan sekaligus.");
      let restored = 0;
      for (const row of payload.records) {
        if (!row || !["trade", "reaction"].includes(row.kind) || !row.data || typeof row.data !== "object") continue;
        const uid = typeof row.uid === "string" ? row.uid : makeUid();
        await putRecord({ uid, kind: row.kind, data: row.data, savedAt: row.savedAt || new Date().toISOString() });
        restored++;
      }
      await renderRecords();
      status.textContent = restored + " catatan dipulihkan. Catatan dengan ID sama diperbarui, bukan digandakan.";
    };

    document.querySelectorAll('form[action="/trades"], form[action="/macro-reactions"]').forEach(form => {
      form.addEventListener("submit", async event => {
        event.preventDefault();
        const isTrade = form.getAttribute("action") === "/trades";
        const data = Object.fromEntries(new FormData(form).entries());
        try {
          await putRecord({ uid: makeUid(), kind: isTrade ? "trade" : "reaction", data, savedAt: new Date().toISOString() });
          await renderRecords();
          status.textContent = "Tersimpan lokal di perangkat ini. Data tidak dikirim ke server.";
          form.reset();
        } catch (error) {
          status.textContent = "Gagal menyimpan lokal: " + (error.message || "error database");
        }
      });
    });
    migrateButton.addEventListener("click", async () => {
      migrateButton.disabled = true;
      status.textContent = "Mengambil jurnal server…";
      try {
        const response = await fetch("/api/local-migration-data", { cache: "no-store" });
        if (!response.ok) throw new Error("Server mengembalikan HTTP " + response.status);
        const payload = await response.json();
        let added = 0;
        for (const row of (payload.trades || [])) {
          await putRecord({
            uid: "server-trade-" + row.id,
            kind: "trade",
            savedAt: row.created_at || new Date().toISOString(),
            data: {
              server_id: row.id, instrument: row.instrument, direction: row.direction,
              entry_price: row.entry_price, entry_time: row.entry_time, lot: row.lot,
              sl: row.sl, tp: row.tp, note: row.note,
              context_json: row.context_json, econ_context_json: row.econ_context_json
            }
          });
          added++;
        }
        for (const row of (payload.reactions || [])) {
          await putRecord({
            uid: "server-reaction-" + row.id,
            kind: "reaction",
            savedAt: row.created_at || new Date().toISOString(),
            data: {
              server_id: row.id, event_type: row.event_type, instrument: row.instrument,
              release_time: row.release_time, expected_direction: row.expected_direction,
              price_before: row.price_before, price_after_15m: row.price_after_15m, note: row.note
            }
          });
          added++;
        }
        await renderRecords();
        status.textContent = added + " catatan server disalin ke database lokal. Data server asli tidak dihapus; ekspor backup sekarang.";
      } catch (error) {
        status.textContent = "Salin dari server gagal: " + (error.message || "error");
      } finally {
        migrateButton.disabled = false;
      }
    });
    exportButton.addEventListener("click", () => backup().catch(error => { status.textContent = "Backup gagal: " + error.message; }));
    importButton.addEventListener("click", () => importFile.click());
    importFile.addEventListener("change", async () => {
      if (!importFile.files || !importFile.files[0]) return;
      try { await restore(importFile.files[0]); }
      catch (error) { status.textContent = "Pemulihan gagal: " + (error.message || "format tidak valid"); }
      finally { importFile.value = ""; }
    });
    openDb().then(async database => {
      db = database;
      let persistence = "browser-managed";
      try {
        if (navigator.storage && navigator.storage.persist) {
          persistence = await navigator.storage.persist() ? "persistent" : "browser-managed";
        }
      } catch (_) {}
      await renderRecords();
      status.textContent = persistence === "persistent"
        ? "Database lokal aktif; browser memberi izin penyimpanan persisten."
        : "Database lokal aktif; ekspor backup rutin karena browser masih dapat menghapus data situs.";
    }).catch(error => {
      status.textContent = "Database lokal tidak tersedia: " + (error.message || "error");
      exportButton.disabled = true;
      importButton.disabled = true;
    });
  }

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


  // ---------- AI news explanation (Gemini) ----------
  const renderAiMarkdown = (container, source) => {
    // Small safe renderer for the limited Markdown produced by the explainer.
    // All content is inserted as text nodes; never interpret model output as HTML.
    const inline = (parent, text) => {
      const parts = text.split(/(\\*\\*[^*]+\\*\\*|\\*[^*]+\\*)/g);
      parts.forEach(part => {
        if (part.startsWith("**") && part.endsWith("**")) {
          const node = document.createElement("strong");
          node.textContent = part.slice(2, -2);
          parent.appendChild(node);
        } else if (part.startsWith("*") && part.endsWith("*")) {
          const node = document.createElement("em");
          node.textContent = part.slice(1, -1);
          parent.appendChild(node);
        } else if (part) {
          parent.appendChild(document.createTextNode(part));
        }
      });
    };
    container.replaceChildren();
    let list = null;
    source.split(/\\r?\\n/).forEach(rawLine => {
      const line = rawLine.trim();
      if (!line) { list = null; return; }
      const heading = line.match(/^\\*\\*(?:\\d+\\.\\s*)?([^*]+):\\*\\*$/);
      if (heading) {
        list = null;
        const h = document.createElement("h4");
        h.className = "ai-section-heading";
        h.textContent = heading[1].replace(/^\\d+\\.\\s*/, "").replace(/:$/, "");
        container.appendChild(h);
        return;
      }
      const item = line.match(/^(?:[-*]\\s+|\\*\\s+\\*\\*)/);
      if (item) {
        if (!list) {
          list = document.createElement("ul");
          list.className = "ai-list";
          container.appendChild(list);
        }
        const li = document.createElement("li");
        inline(li, line.replace(/^(?:[-*]\\s+)/, "").replace(/^\\*\\s+/, ""));
        list.appendChild(li);
        return;
      }
      list = null;
      const p = document.createElement("p");
      inline(p, line);
      container.appendChild(p);
    });
  };

  if (feed) {
    feed.addEventListener("click", async event => {
      const button = event.target.closest("[data-ai-explain]");
      if (!button) return;
      const article = button.closest(".news");
      const panel = article && article.querySelector("[data-ai-explanation]");
      const newsId = article && article.dataset.newsId;
      if (!panel || !newsId) {
        if (panel) { panel.hidden = false; panel.textContent = "ID berita tidak tersedia. Muat ulang halaman."; }
        return;
      }
      if (panel.dataset.loaded === "true") {
        panel.hidden = !panel.hidden;
        button.textContent = panel.hidden ? "Tampilkan ringkasan AI" : "Sembunyikan ringkasan AI";
        return;
      }
      button.disabled = true;
      button.textContent = "AI sedang merangkum...";
      panel.hidden = false;
      panel.textContent = "Gemini sedang merangkum judul dan ringkasan berita yang tersedia...";
      try {
        const response = await fetch("/api/news/" + encodeURIComponent(newsId) + "/explain", {
          method: "POST", headers: { "Accept": "application/json" }, cache: "no-store"
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || "Gagal meminta penjelasan AI.");
        panel.replaceChildren();
        const title = document.createElement("p");
        title.className = "ai-title";
        title.textContent = "AI Summarize · Gemini";
        const scorecard = payload.scorecard;
        if (scorecard) {
          const card = document.createElement("section");
          card.className = "news-scorecard";
          const heading = document.createElement("h4");
          heading.textContent = "News Impact Scorecard";
          card.appendChild(heading);
          const event = document.createElement("p");
          event.textContent = "Kategori: " + (scorecard.event_type || "Belum terklasifikasi");
          card.appendChild(event);
          const assets = document.createElement("div");
          assets.className = "scorecard-assets";
          Object.entries(scorecard.relevance || {}).forEach(([asset, data]) => {
            const row = document.createElement("div");
            row.className = "scorecard-asset";
            const label = document.createElement("strong");
            label.textContent = asset + " · " + (data.relevance || "Belum jelas");
            const reason = document.createElement("p");
            reason.textContent = data.reason || "Tidak ada alasan yang tersedia.";
            row.append(label, reason);
            if (Array.isArray(data.matched_terms) && data.matched_terms.length) {
              const terms = document.createElement("small");
              terms.textContent = "Kata kunci: " + data.matched_terms.join(", ");
              row.appendChild(terms);
            }
            assets.appendChild(row);
          });
          card.appendChild(assets);
          const quality = document.createElement("p");
          quality.textContent = "Kualitas bukti: " + (scorecard.evidence_quality || "Belum dinilai") + ". " + (scorecard.evidence_note || "");
          card.appendChild(quality);
          const direction = document.createElement("p");
          direction.textContent = "Arah: belum ditentukan. " + (scorecard.direction_note || "");
          card.appendChild(direction);
          const method = document.createElement("small");
          method.textContent = scorecard.method || "Heuristik; bukan sinyal trading.";
          card.appendChild(method);
          panel.appendChild(card);
        }
        const copy = document.createElement("div");
        copy.className = "ai-copy ai-markdown";
        renderAiMarkdown(copy, payload.explanation || "Penjelasan kosong.");
        panel.append(title, copy);
        panel.dataset.loaded = "true";
        button.textContent = "Sembunyikan ringkasan AI";
      } catch (error) {
        panel.textContent = error.message || "AI Summarize gagal dimuat. Coba lagi nanti.";
        button.textContent = "Coba ringkas lagi";
      } finally { button.disabled = false; }
    });
  }

  // ---------- Filter kategori berita ----------
  const filterBar = document.querySelector(".news-category-nav");
  const filterCount = document.getElementById("news-filter-count");
  let activeNewsFilter = "all";
  // Artikel boleh masuk ke beberapa kategori sekaligus. Berita tentang tarif,
  // misalnya, bisa relevan untuk geopolitik DAN ekonomi.
  const categoriesFor = (article) => {
    const title = article.querySelector("h3")?.innerText || "";
    const summary = article.querySelector(".original-summary")?.innerText || "";
    const tags = Array.from(article.querySelectorAll(".tags span"))
      .map(el => el.textContent || "").join(" ");
    const haystack = (title + " " + summary + " " + tags).toLowerCase();
    const categories = new Set();
    if (/fomc|federal reserve|\bfed\b|powell|interest rate|rate decision|monetary policy|central bank|policy rate/.test(haystack)) categories.add("fed");
    if (/inflation|consumer price|\bcpi\b|\bppi\b|\bpce\b|price index|cost of living/.test(haystack)) categories.add("inflation");
    if (/nonfarm|payroll|unemployment|employment|job openings|labor market|labour market|wage|jobless claims/.test(haystack)) categories.add("jobs");
    if (/\bgdp\b|gross domestic|productivity|business activity|consumer spending|retail sales|economic growth|recession|economic outlook|manufacturing/.test(haystack)) categories.add("economy");
    if (/geopolit|\bwar\b|sanction|tariff|trade war|iran|israel|ukraine|russia|missile|conflict|invasion|ceasefire|military|diplomatic|election|white house|china-us relations/.test(haystack)) categories.add("geopolitics");
    if (/\boil\b|crude|opec|energy|natural gas|brent|wti|petroleum|fuel prices|electricity prices/.test(haystack)) categories.add("energy");
    if (!categories.size) categories.add("other");
    return categories;
  };
  const applyNewsFilter = () => {
    if (!feed) return;
    const articles = Array.from(feed.querySelectorAll(".news"));
    let visible = 0;
    articles.forEach(article => {
      const categories = categoriesFor(article);
      article.dataset.newsCategories = Array.from(categories).join(" ");
      const show = activeNewsFilter === "all" || categories.has(activeNewsFilter);
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

  // ---------- Historical Event Lab: descriptive stats from recorded observations ----------
  const eventLabButton = document.getElementById("event-lab-refresh");
  if (eventLabButton) {
    const eventSelect = document.getElementById("event-lab-event");
    const instrumentSelect = document.getElementById("event-lab-instrument");
    const eventLabStatus = document.getElementById("event-lab-status");
    const eventLabBody = document.getElementById("event-lab-results");
    const limitationsList = document.getElementById("event-lab-limitations");
    const cell = (value) => {
      const td = document.createElement("td");
      td.textContent = value;
      return td;
    };
    const showEventLab = async () => {
      eventLabButton.disabled = true;
      eventLabStatus.textContent = "Menghitung statistik...";
      eventLabBody.replaceChildren();
      limitationsList.replaceChildren();
      try {
        const params = new URLSearchParams();
        if (eventSelect.value) params.set("event_type", eventSelect.value);
        if (instrumentSelect.value) params.set("instrument", instrumentSelect.value);
        const suffix = params.toString();
        const response = await fetch("/api/research/event-lab" + (suffix ? "?" + suffix : ""), { cache: "no-store" });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const payload = await response.json();
        const results = Array.isArray(payload.results) ? payload.results : [];
        if (!results.length) {
          const row = document.createElement("tr");
          const empty = cell("Belum ada data yang cocok dengan filter.");
          empty.colSpan = 7;
          row.appendChild(empty);
          eventLabBody.appendChild(row);
        } else {
          results.forEach(item => {
            const row = document.createElement("tr");
            row.append(
              cell(item.event_type || "—"),
              cell(item.instrument || "—"),
              cell(String(item.samples ?? 0)),
              cell(Number.isFinite(item.median_change_pct) ? item.median_change_pct.toFixed(5) + "%" : "—"),
              cell(Number.isFinite(item.mean_change_pct) ? item.mean_change_pct.toFixed(5) + "%" : "—"),
              cell([item.positive_samples ?? 0, item.negative_samples ?? 0, item.flat_samples ?? 0].join(" / ")),
              cell(item.bias_aligned_pct === null || item.bias_aligned_pct === undefined ? "N/A" : item.bias_aligned_pct + "% (" + (item.bias_scored_samples ?? 0) + ")")
            );
            row.title = item.sample_warning || "";
            eventLabBody.appendChild(row);
          });
        }
        (payload.limitations || []).forEach(message => {
          const li = document.createElement("li");
          li.textContent = message;
          limitationsList.appendChild(li);
        });
        eventLabStatus.textContent = results.length + " grup statistik · " + (payload.observations ?? 0) + " observasi diperiksa. Arah median bukan sinyal entry.";
      } catch (_) {
        eventLabStatus.textContent = "Statistik gagal dimuat. Periksa koneksi server lalu coba lagi.";
        const row = document.createElement("tr");
        const error = cell("Data tidak tersedia.");
        error.colSpan = 7;
        row.appendChild(error);
        eventLabBody.replaceChildren(row);
      } finally {
        eventLabButton.disabled = false;
      }
    };
    eventLabButton.addEventListener("click", showEventLab);
    eventSelect.addEventListener("change", showEventLab);
    instrumentSelect.addEventListener("change", showEventLab);
  }

  // ---------- Kalender ekonomi AS (jadwal resmi BLS) ----------
  const calendarPanel = document.getElementById("calendar-panel");
  if (calendarPanel) initCalendar(calendarPanel);

  function initCalendar(panel) {
    const statusLine = panel.querySelector("#calendar-status");
    const nextNode = panel.querySelector("#calendar-next");
    const list = panel.querySelector("#calendar-list");
    const pad = n => String(n).padStart(2, "0");
    const formatTime = (date, zone) => new Intl.DateTimeFormat("id-ID", {
      timeZone: zone, day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit", hour12: false
    }).format(date);

    const countdownText = remaining => {
      if (remaining <= 0) return { text: "Waktu rilis terlewati", soon: true };
      const days = Math.floor(remaining / 86400);
      const hours = Math.floor((remaining % 86400) / 3600);
      const minutes = Math.floor((remaining % 3600) / 60);
      if (remaining < 3600) return { text: "Dalam " + pad(Math.floor(remaining / 60)) + " menit", soon: true };
      if (days === 0) return { text: "Dalam " + hours + " jam " + minutes + " menit", soon: false };
      return { text: "Dalam " + days + " hari " + hours + " jam", soon: false };
    };

    let upcoming = [];
    const createEventCard = (event, featured = false) => {
      const impact = ["high", "medium", "low"].includes(event.impact) ? event.impact : "unknown";
      const article = document.createElement("article");
      article.className = "calendar-event " + impact + (featured ? " featured" : "");
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
      return article;
    };

    const updateCountdowns = () => {
      const now = Date.now();
      panel.querySelectorAll(".calendar-countdown").forEach(node => {
        const target = Date.parse(node.dataset.scheduledAt);
        if (!Number.isFinite(target)) {
          node.textContent = "Waktu rilis tidak valid";
          node.classList.remove("soon");
          return;
        }
        const remaining = Math.floor((target - now) / 1000);
        const result = countdownText(remaining);
        if (node.textContent !== result.text) node.textContent = result.text;
        node.classList.toggle("soon", result.soon);
      });
    };

    const render = () => {
      upcoming = upcoming.filter(event => Date.parse(event.scheduled_at_utc) >= Date.now())
        .sort((a, b) => Date.parse(a.scheduled_at_utc) - Date.parse(b.scheduled_at_utc));
      nextNode.replaceChildren();
      list.replaceChildren();
      if (!upcoming.length) {
        nextNode.appendChild(emptyParagraph("Belum ada event mendatang di kalender yang tersedia."));
        return;
      }
      const nextEvent = upcoming[0];
      const kicker = document.createElement("div");
      kicker.className = "calendar-next-kicker";
      kicker.textContent = "EVENT BERIKUTNYA";
      nextNode.append(kicker, createEventCard(nextEvent, true));
      const remaining = upcoming.slice(1, 7);
      if (remaining.length) {
        const label = document.createElement("div");
        label.className = "calendar-upcoming-label";
        label.textContent = "SELANJUTNYA";
        list.appendChild(label);
        remaining.forEach(event => list.appendChild(createEventCard(event)));
      } else {
        list.appendChild(emptyParagraph("Tidak ada event lain yang tersedia."));
      }
      updateCountdowns();
    };

    nextNode.replaceChildren(emptyParagraph("Mengambil jadwal resmi..."));
    fetch("/api/calendar", { cache: "no-store" })
      .then(response => {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(payload => {
        upcoming = (payload.events || []).filter(event => event.scheduled_at_utc);
        statusLine.textContent = payload.stale ? "cache lama" : "sumber resmi";
        render();
        window.setInterval(updateCountdowns, 30000);
        window.setInterval(render, 60000);
      })
      .catch(() => {
        statusLine.textContent = "tidak tersedia";
        nextNode.replaceChildren(emptyParagraph("Jadwal BLS gagal dimuat."));
        list.replaceChildren();
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

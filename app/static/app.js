(function () {
  const feed = document.getElementById("live-feed");
  const status = document.getElementById("live-status");

  // Render calendar values with textContent; source titles are untrusted input.
  const pane = feed && feed.closest(".wire-pane");
  if (pane) {
    const section = document.createElement("section");
    section.className = "calendar-panel";
    const heading = document.createElement("h2");
    heading.textContent = "Kalender ekonomi AS";
    const statusLine = document.createElement("span");
    statusLine.className = "muted calendar-status";
    statusLine.textContent = "memuat jadwal BLS";
    heading.appendChild(document.createTextNode(" "));
    heading.appendChild(statusLine);
    const note = document.createElement("p");
    note.className = "muted calendar-note";
    note.textContent = "Jadwal rilis resmi BLS. Waktu dalam WIB dan US Eastern. Forecast/actual tidak diada-adakan.";
    const list = document.createElement("div");
    list.className = "calendar-list";
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Mengambil jadwal resmi...";
    list.appendChild(empty);
    section.append(heading, note, list);
    pane.insertBefore(section, pane.firstElementChild);

    const formatTime = (date, zone) => new Intl.DateTimeFormat("id-ID", {
      timeZone: zone, day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit", hour12: false
    }).format(date);

    let upcoming = [];
    const render = () => {
      list.replaceChildren();
      const now = Date.now();
      upcoming = upcoming.filter(event => Date.parse(event.scheduled_at_utc) >= now);
      if (!upcoming.length) {
        const p = document.createElement("p");
        p.className = "empty";
        p.textContent = "Tidak ada jadwal BLS mendatang pada data yang tersedia.";
        list.appendChild(p);
        return;
      }
      upcoming.slice(0, 8).forEach(event => {
        const article = document.createElement("article");
        article.className = "calendar-event " + (event.impact || "medium");
        const title = document.createElement("a");
        title.className = "calendar-title";
        title.textContent = event.name || "Rilis ekonomi";
        title.href = event.url || event.source_url || "https://www.bls.gov/schedule/";
        title.target = "_blank";
        title.rel = "noopener noreferrer";
        const meta = document.createElement("div");
        meta.className = "calendar-meta";
        const date = new Date(event.scheduled_at_utc);
        meta.textContent = "WIB " + formatTime(date, "Asia/Jakarta") +
          " · ET " + formatTime(date, "America/New_York") +
          " · dampak " + (event.impact || "unknown").toUpperCase();
        const countdown = document.createElement("div");
        countdown.className = "calendar-countdown";
        const remaining = Math.max(0, Date.parse(event.scheduled_at_utc) - now);
        const hours = Math.floor(remaining / 3600000);
        const minutes = Math.floor((remaining % 3600000) / 60000);
        countdown.textContent = hours > 24
          ? "dalam " + Math.floor(hours / 24) + " hari " + (hours % 24) + " jam"
          : "dalam " + hours + " jam " + minutes + " menit";
        article.append(title, meta, countdown);
        list.appendChild(article);
      });
    };

    fetch("/api/calendar")
      .then(response => {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(payload => {
        upcoming = (payload.events || []).filter(event => event.scheduled_at_utc);
        statusLine.textContent = payload.stale ? "cache lama" : "sumber resmi";
        render();
        window.setInterval(render, 60000);
      })
      .catch(() => {
        statusLine.textContent = "tidak tersedia";
        list.replaceChildren();
        const p = document.createElement("p");
        p.className = "empty";
        p.textContent = "Jadwal BLS gagal dimuat. Feed berita tetap berjalan.";
        list.appendChild(p);
      });
  }

  if (!feed || !window.EventSource) return;
  const setStatus = (text) => { if (status) status.textContent = text; };
  const es = new EventSource("/stream/news");
  es.onopen = () => setStatus("tersambung");
  es.onerror = () => setStatus("menyambung ulang");
  es.addEventListener("news", (e) => {
    const empty = feed.querySelector(".empty");
    if (empty) empty.remove();
    feed.insertAdjacentHTML("afterbegin", e.data);
  });
})();

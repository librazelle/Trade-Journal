(function () {
  const root = document.getElementById("market-monitor");
  if (!root) return;
  const chartHost = document.getElementById("market-chart");
  const status = document.getElementById("market-feed-status");
  const price = document.getElementById("market-last-price");
  const lastTime = document.getElementById("market-last-time");
  const source = document.getElementById("market-source");
  const fetched = document.getElementById("market-fetched-at");
  const timeframe = document.getElementById("market-timeframe");
  const refresh = document.getElementById("market-refresh");
  const tabs = [...root.querySelectorAll("[data-market-symbol]")];
  let symbol = "NASDAQ100";
  let chart = null;
  let candleSeries = null;
  let resizeObserver = null;
  let requestSequence = 0;
  let refreshTimer = null;
  const fmtTime = value => value ? new Intl.DateTimeFormat("id-ID", { timeZone:"Asia/Jakarta", dateStyle:"medium", timeStyle:"medium" }).format(new Date(value)) : "—";
  const fmtPrice = value => Number(value).toLocaleString("en-US", { maximumFractionDigits: 4 });
  function setStatus(text, kind) { status.textContent = text; status.className = "market-feed-status " + (kind || ""); }
  function initChart() {
    if (!window.LightweightCharts) {
      setStatus("CHART LIBRARY OFFLINE", "error");
      chartHost.textContent = "Library chart tidak termuat. Periksa koneksi lalu refresh.";
      return false;
    }
    if (chart) return true;
    chart = LightweightCharts.createChart(chartHost, {
      autoSize: true,
      layout: { background: { type: "solid", color: "#0d1219" }, textColor: "#aeb8c6", attributionLogo: true },
      grid: { vertLines: { color: "#1b2635" }, horzLines: { color: "#1b2635" } },
      rightPriceScale: { borderColor: "#26334a" },
      timeScale: { borderColor: "#26334a", timeVisible: true, secondsVisible: false },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      localization: { locale: "id-ID" }
    });
    candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: "#6fbf94", downColor: "#e27d6a", borderVisible: false,
      wickUpColor: "#6fbf94", wickDownColor: "#e27d6a"
    });
    resizeObserver = new ResizeObserver(() => chart && chart.applyOptions({ width: chartHost.clientWidth, height: chartHost.clientHeight }));
    resizeObserver.observe(chartHost);
    return true;
  }
  async function load() {
    const seq = ++requestSequence;
    refresh.disabled = true;
    setStatus("MENGAMBIL DATA", "warn");
    try {
      const response = await fetch("/api/market-monitor/" + encodeURIComponent(symbol) + "?interval=" + encodeURIComponent(timeframe.value), { cache:"no-store", headers:{Accept:"application/json"} });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || ("HTTP " + response.status));
      if (seq !== requestSequence) return;
      if (!initChart()) return;
      candleSeries.setData(data.candles);
      chart.timeScale().fitContent();
      const latest = data.candles[data.candles.length - 1];
      price.textContent = fmtPrice(latest.close);
      lastTime.textContent = "Candle terakhir: " + fmtTime(data.last_candle_at);
      source.textContent = "Sumber: " + data.source + " (" + data.ticker + ")";
      fetched.textContent = "Diambil: " + fmtTime(data.fetched_at);
      setStatus("DATA TERSEDIA · REALTIME TIDAK TERVERIFIKASI", "warn");
    } catch (error) {
      if (seq !== requestSequence) return;
      setStatus("FEED TIDAK TERSEDIA", "error");
      lastTime.textContent = "Gagal mengambil data: " + (error.message || "kesalahan tidak diketahui");
      source.textContent = "Sumber: belum terkonfirmasi";
    } finally {
      if (seq === requestSequence) refresh.disabled = false;
    }
  }
  tabs.forEach(button => button.addEventListener("click", () => {
    symbol = button.dataset.marketSymbol;
    tabs.forEach(tab => { const active = tab === button; tab.classList.toggle("active", active); tab.setAttribute("aria-pressed", String(active)); });
    load();
  }));
  timeframe.addEventListener("change", load);
  refresh.addEventListener("click", load);
  load();
  refreshTimer = window.setInterval(load, 60000);
  window.addEventListener("beforeunload", () => { if (refreshTimer) clearInterval(refreshTimer); if (resizeObserver) resizeObserver.disconnect(); if (chart) chart.remove(); });
})();

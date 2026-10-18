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
  const symbols = {
    NASDAQ100: { symbol: "OANDA:NAS100USD", label: "Nasdaq 100 CFD (OANDA)" },
    XAUUSD: { symbol: "OANDA:XAUUSD", label: "XAU/USD spot (TradingView provider; compare with your broker)" },
    SP500: { symbol: "OANDA:SPX500USD", label: "S&P 500 CFD (OANDA)" }
  };
  let symbol = "NASDAQ100";
  let frame = null;
  const intervals = { "1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60", "1d": "D" };

  function setStatus(text, kind) {
    status.textContent = text;
    status.className = "market-feed-status " + (kind || "");
  }

  function buildChartUrl() {
    const selected = symbols[symbol];
    const params = new URLSearchParams({
      frameElementId: "trade_lens_tradingview",
      symbol: selected.symbol,
      interval: intervals[timeframe.value] || "15",
      hidesidetoolbar: "0",
      symboledit: "1",
      saveimage: "0",
      toolbarbg: "0d1219",
      theme: "dark",
      style: "1",
      timezone: "Asia/Jakarta",
      withdateranges: "1",
      hideideas: "1",
      locale: "id"
    });
    return "https://www.tradingview.com/widgetembed/?" + params.toString();
  }

  function publishSelectedInstrument() {
    try { window.localStorage.setItem("tradeLensSelectedInstrument", symbol); } catch (_) {}
    window.dispatchEvent(new CustomEvent("trade-lens:instrument-change", { detail: { symbol } }));
  }

  function load() {
    publishSelectedInstrument();
    refresh.disabled = true;
    setStatus("MEMUAT CHART", "warn");
    const selected = symbols[symbol];
    const iframe = document.createElement("iframe");
    iframe.title = "Chart " + selected.label;
    iframe.loading = "eager";
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.allow = "clipboard-write";
    iframe.src = buildChartUrl();
    iframe.style.cssText = "display:block;width:100%;height:100%;min-height:320px;border:0;background:#0d1219";
    iframe.addEventListener("load", () => {
      setStatus("CHART TRADINGVIEW", "ok");
      price.textContent = "Harga ditampilkan di chart";
      lastTime.textContent = "Data dan waktu mengikuti penyedia TradingView";
      source.textContent = "Sumber: TradingView · " + selected.symbol;
      fetched.textContent = "Pembaruan dikelola widget";
      refresh.disabled = false;
    }, { once: true });
    iframe.addEventListener("error", () => {
      setStatus("CHART GAGAL DIMUAT", "error");
      lastTime.textContent = "Widget TradingView tidak berhasil dimuat. Periksa koneksi atau pemblokir konten.";
      source.textContent = "Sumber: TradingView";
      refresh.disabled = false;
    }, { once: true });
    chartHost.replaceChildren(iframe);
    // A remote iframe may never fire an error event when blocked; avoid leaving Refresh disabled.
    window.setTimeout(() => { refresh.disabled = false; }, 10000);
  }

  // Mobile dock uses a dedicated compact TradingView embed.
  // Do not move/resize the main iframe: TradingView keeps its full toolbar after
  // a CSS resize, which makes the previous dock consume too much screen space.
  const chartStage = document.getElementById("market-chart-stage");
  let dock = null;
  let dockFrame = null;
  let docked = false;
  let framePending = false;
  const mobileView = window.matchMedia("(max-width: 1099px)");

  function buildDockChartUrl() {
    const selected = symbols[symbol];
    const params = new URLSearchParams({
      frameElementId: "trade_lens_mobile_chart_dock",
      symbol: selected.symbol,
      interval: intervals[timeframe.value] || "15",
      theme: "dark",
      style: "1",
      timezone: "Asia/Jakarta",
      locale: "id",
      hide_top_toolbar: "1",
      hide_side_toolbar: "1",
      hide_legend: "1",
      hide_bottom_toolbar: "1",
      withdateranges: "0",
      allow_symbol_change: "0",
      saveimage: "0",
      hideideas: "1"
    });
    return "https://www.tradingview.com/widgetembed/?" + params.toString();
  }

  function createDock() {
    if (dock) return;
    dock = document.createElement("aside");
    dock.id = "market-chart-dock";
    dock.setAttribute("aria-label", "Chart market ringkas");
    dock.innerHTML = '<div class="chart-dock-heading"><span><strong>Chart ringkas</strong> · <span class="chart-dock-symbol">Nasdaq 100</span></span><button type="button" class="chart-dock-close" aria-label="Tutup chart ringkas">×</button></div><iframe class="chart-dock-frame" title="Chart ringkas instrumen terpilih" loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe>';
    document.body.appendChild(dock);
    dockFrame = dock.querySelector("iframe");
    dock.querySelector(".chart-dock-close").addEventListener("click", () => {
      setDock(false);
      chartStage.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function updateDockChart() {
    if (!dockFrame) return;
    const selected = symbols[symbol];
    dock.querySelector(".chart-dock-symbol").textContent = selected.label;
    dockFrame.src = buildDockChartUrl();
  }

  function setDock(next) {
    if (next === docked) return;
    docked = next;
    if (docked) {
      createDock();
      updateDockChart();
    } else if (dockFrame) {
      dockFrame.removeAttribute("src");
    }
    document.body.classList.toggle("chart-docked", docked);
  }

  function updateDock() {
    framePending = false;
    if (!mobileView.matches) {
      setDock(false);
      return;
    }
    const rect = chartStage.getBoundingClientRect();
    if (!docked && rect.bottom < 70) setDock(true);
    else if (docked && rect.top > 70) setDock(false);
  }

  function onScrollOrResize() {
    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(updateDock);
  }

  if (chartStage) {
    window.addEventListener("scroll", onScrollOrResize, { passive: true });
    window.addEventListener("resize", onScrollOrResize, { passive: true });
    if (mobileView.addEventListener) mobileView.addEventListener("change", onScrollOrResize);
    else if (mobileView.addListener) mobileView.addListener(onScrollOrResize);
  }

  tabs.forEach(button => button.addEventListener("click", () => {
    symbol = button.dataset.marketSymbol;
    tabs.forEach(tab => {
      const active = tab === button;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-pressed", String(active));
    });
    load();
    if (docked) updateDockChart();
  }));
  timeframe.addEventListener("change", () => {
    load();
    if (docked) updateDockChart();
  });
  refresh.addEventListener("click", load);
  load();
})();
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

  // Mobile chart dock: move the same iframe into a compact floating panel
  // after the chart has been scrolled away. A stage placeholder preserves layout.
  const chartStage = document.getElementById("market-chart-stage");
  if (chartStage && chartHost) {
    const dock = document.createElement("aside");
    dock.id = "market-chart-dock";
    dock.setAttribute("aria-label", "Chart market ringkas");
    dock.innerHTML = '<div class="chart-dock-heading"><span><strong>Chart aktif</strong> · ketuk × untuk kembali ke posisi chart</span><button type="button" class="chart-dock-close" aria-label="Tutup chart ringkas">×</button></div>';
    document.body.appendChild(dock);
    const closeDock = dock.querySelector(".chart-dock-close");
    let docked = false;
    let framePending = false;
    const mobileView = window.matchMedia("(max-width: 1099px)");
    function setDock(next) {
      if (next === docked) return;
      docked = next;
      if (docked) {
        chartStage.style.height = chartHost.getBoundingClientRect().height + "px";
        dock.appendChild(chartHost);
      } else {
        chartStage.appendChild(chartHost);
        chartStage.style.height = "";
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
      // Wait until the chart is almost entirely above the viewport.
      if (!docked && rect.bottom < 90) setDock(true);
      else if (docked && rect.top > 90) setDock(false);
    }
    function onScrollOrResize() {
      if (framePending) return;
      framePending = true;
      window.requestAnimationFrame(updateDock);
    }
    window.addEventListener("scroll", onScrollOrResize, { passive: true });
    window.addEventListener("resize", onScrollOrResize, { passive: true });
    if (mobileView.addEventListener) mobileView.addEventListener("change", onScrollOrResize);
    else if (mobileView.addListener) mobileView.addListener(onScrollOrResize);
    closeDock.addEventListener("click", () => {
      setDock(false);
      chartStage.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  tabs.forEach(button => button.addEventListener("click", () => {
    symbol = button.dataset.marketSymbol;
    tabs.forEach(tab => {
      const active = tab === button;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-pressed", String(active));
    });
    load();
  }));
  timeframe.addEventListener("change", load);
  refresh.addEventListener("click", load);
  load();
})();
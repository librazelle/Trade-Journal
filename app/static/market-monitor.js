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

  function load() {
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
(function () {
  const feed = document.getElementById("live-feed");
  const status = document.getElementById("live-status");
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

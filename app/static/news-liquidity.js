(() => {
  const $ = id => document.getElementById(id);
  const form = $("nl-form"), run = $("nl-run"), status = $("nl-status");
  const fmt = n => Number.isFinite(n) ? n.toLocaleString("en-US",{maximumFractionDigits:3}) : "—";
  const dtfmt = t => new Date(t*1000).toLocaleTimeString("id-ID",{hour:"2-digit",minute:"2-digit",timeZone:"Asia/Jakarta"});
  const range = rows => rows.length ? Math.max(...rows.map(c=>c.high))-Math.min(...rows.map(c=>c.low)) : NaN;
  const setStatus = (s,k="") => {status.textContent=s;status.className="nl-status "+k;};
  const now = new Date(Date.now()-new Date().getTimezoneOffset()*60000);
  $("nl-event-time").value = now.toISOString().slice(0,16);
  function candleRows(rows, eventSec) {
    if(!rows.length) return '<p class="nl-empty">Tidak ada candle pada jendela ini.</p>';
    return '<div class="nl-candle-list">'+rows.slice(-80).map(c=>'<div class="'+(Math.abs(c.time-eventSec)<90?'event-candle':'')+'"><span>'+dtfmt(c.time)+'</span><span>O '+fmt(c.open)+'</span><span>H '+fmt(c.high)+'</span><span>L '+fmt(c.low)+'</span><span>C '+fmt(c.close)+'</span></div>').join("")+'</div>';
  }
  form.addEventListener("submit", async ev => {
    ev.preventDefault(); run.disabled=true; setStatus("Mengambil candle dan menghitung level…");
    try {
      const instrument=$("nl-instrument").value, interval=$("nl-interval").value;
      const eventMs=new Date($("nl-event-time").value).getTime();
      if(!Number.isFinite(eventMs)) throw new Error("Waktu rilis tidak valid.");
      const eventSec=Math.floor(eventMs/1000), windowSec=Number($("nl-window").value)*60;
      const res=await fetch('/api/market-monitor/'+encodeURIComponent(instrument)+'?interval='+encodeURIComponent(interval),{cache:"no-store"});
      const data=await res.json();
      if(!res.ok) throw new Error(data.detail||"Data market tidak tersedia.");
      const candles=(data.candles||[]).filter(c=>c.time>=eventSec-windowSec && c.time<=eventSec+windowSec);
      const pre=candles.filter(c=>c.time<eventSec), post=candles.filter(c=>c.time>=eventSec);
      const allStart=data.candles?.[0]?.time, allEnd=data.candles?.[data.candles.length-1]?.time;
      if(!candles.length) throw new Error("Tidak ada candle di sekitar waktu rilis ini. Endpoint saat ini hanya menyediakan rentang terbaru; pilih event yang waktunya masuk ke rentang candle yang tersedia.");
      $("nl-pre-range").textContent=fmt(range(pre)); $("nl-post-range").textContent=fmt(range(post));
      $("nl-pre-count").textContent=pre.length+" candle sebelum"; $("nl-post-count").textContent=post.length+" candle sesudah";
      const preHigh=pre.length?Math.max(...pre.map(c=>c.high)):NaN, preLow=pre.length?Math.min(...pre.map(c=>c.low)):NaN;
      $("nl-pre-high").textContent=fmt(preHigh); $("nl-pre-low").textContent=fmt(preLow);
      $("nl-source").textContent="Sumber: "+(data.source||"feed publik")+" · "+(data.ticker||instrument);
      $("nl-timeline").innerHTML='<div class="nl-period"><h3>Sebelum rilis</h3>'+candleRows(pre,eventSec)+'</div><div class="nl-period"><h3>Sesudah rilis</h3>'+candleRows(post,eventSec)+'</div>';
      const postHigh=post.length?Math.max(...post.map(c=>c.high)):NaN, postLow=post.length?Math.min(...post.map(c=>c.low)):NaN;
      const highHit=pre.length&&post.length&&postHigh>preHigh, lowHit=pre.length&&post.length&&postLow<preLow;
      $("nl-sweeps").innerHTML=[
        '<div class="nl-sweep '+(highHit?'hit':'')+'"><strong>'+(highHit?'High sebelum rilis ditembus':'Belum ada break high terdeteksi')+'</strong><span>Pre-high '+fmt(preHigh)+' · post-high '+fmt(postHigh)+' · kandidat buy-side liquidity sweep, bukan konfirmasi order flow.</span></div>',
        '<div class="nl-sweep '+(lowHit?'hit':'')+'"><strong>'+(lowHit?'Low sebelum rilis ditembus':'Belum ada break low terdeteksi')+'</strong><span>Pre-low '+fmt(preLow)+' · post-low '+fmt(postLow)+' · kandidat sell-side liquidity sweep, bukan konfirmasi order flow.</span></div>'
      ].join("");
      const eventInRange=eventSec>=allStart&&eventSec<=allEnd;
      setStatus((eventInRange?"Analisis selesai. ":"Catatan: waktu event di luar rentang candle penuh. ")+candles.length+" candle ditemukan. Data tidak dijamin realtime.", "ok");
    } catch(err) { setStatus(err.message||"Gagal memuat data.", "error"); }
    finally { run.disabled=false; }
  });

  const cgFmt = n => Number.isFinite(n) ? n.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}) : "—";
  const cgPct = n => Number.isFinite(n) ? (n>0?"+":"")+n.toFixed(2)+"%" : "—";
  $("nl-cg-run").addEventListener("click", async () => {
    const button=$("nl-cg-run"), cgStatus=$("nl-cg-status");
    button.disabled=true; cgStatus.className="nl-status"; cgStatus.textContent="Memuat data derivatif CoinGlass…";
    try {
      const eventMs=new Date($("nl-event-time").value).getTime();
      if(!Number.isFinite(eventMs)) throw new Error("Isi waktu rilis terlebih dahulu.");
      const windowMs=Number($("nl-window").value)*60*1000;
      const params=new URLSearchParams({
        symbol:$("nl-cg-symbol").value,
        interval:$("nl-interval").value,
        start_time:String(eventMs-windowMs),
        end_time:String(eventMs+windowMs)
      });
      const response=await fetch("/api/news-liquidity/coinglass?"+params.toString(),{cache:"no-store"});
      const data=await response.json();
      if(!response.ok) throw new Error(data.detail||"CoinGlass tidak tersedia.");
      if(!data.configured) {
        cgStatus.textContent=data.message||"CoinGlass belum dikonfigurasi.";
        return;
      }
      const liqs=data.liquidations||[], oi=data.open_interest||[];
      const sum=(rows,key)=>rows.reduce((total,row)=>total+(Number(row[key])||0),0);
      const long=sum(liqs,"aggregated_long_liquidation_usd");
      const short=sum(liqs,"aggregated_short_liquidation_usd");
      const total=long+short;
      $("nl-cg-total").textContent=cgFmt(total);
      $("nl-cg-long").textContent=cgFmt(long);
      $("nl-cg-short").textContent=cgFmt(short);
      $("nl-cg-long-pct").textContent=total?((long/total)*100).toFixed(1)+"% of reported liquidation":"No liquidation rows";
      $("nl-cg-short-pct").textContent=total?((short/total)*100).toFixed(1)+"% of reported liquidation":"No liquidation rows";
      $("nl-cg-split").textContent=liqs.length+" liquidation buckets";
      const ordered=oi.slice().sort((a,b)=>Number(a.time)-Number(b.time));
      const first=ordered[0], last=ordered[ordered.length-1];
      const oiStart=first?Number(first.open):NaN, oiEnd=last?Number(last.close):NaN;
      const oiChange=Number.isFinite(oiStart)&&oiStart!==0&&Number.isFinite(oiEnd)?((oiEnd-oiStart)/oiStart)*100:NaN;
      $("nl-cg-oi").textContent=cgPct(oiChange);
      $("nl-cg-oi-note").textContent=first&&last?"OI close vs first open · "+ordered.length+" buckets":"No OI rows in selected window";
      $("nl-cg-source").textContent="Source: "+data.source+" · "+data.symbol+" · "+(data.exchange_list||[]).join(", ")+" · interval "+data.interval+". Values depend on CoinGlass plan and exchange coverage.";
      cgStatus.className="nl-status ok";
      cgStatus.textContent="Derivatives data loaded. Angka liquidation adalah agregat exchange yang diminta, bukan total seluruh pasar crypto.";
    } catch(err) {
      cgStatus.className="nl-status error";
      cgStatus.textContent=err.message||"Gagal memuat data CoinGlass.";
    } finally {
      button.disabled=false;
    }
  });

})();

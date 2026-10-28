(() => {
  const $ = id => document.getElementById(id);
  let myfxbookData=null;
  const mfNum=n=>Number.isFinite(Number(n))?Number(n).toLocaleString("en-US",{maximumFractionDigits:2}):"—";
  const mfMoney=n=>Number.isFinite(Number(n))?Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:4}):"—";
  $("nl-mf-load").addEventListener("click",async()=>{
    const button=$("nl-mf-load"), label=$("nl-mf-status");
    button.disabled=true;label.className="nl-status";label.textContent="Mengambil data publik Myfxbook…";
    try{
      const response=await fetch("/api/myfxbook/outlook/XAUUSD",{cache:"no-store"});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Data Myfxbook tidak tersedia.");
      myfxbookData=data;
      $("nl-mf-short").textContent=mfNum(data.short_percentage)+"%";
      $("nl-mf-long").textContent=mfNum(data.long_percentage)+"%";
      $("nl-mf-short-detail").textContent=data.short_positions==null?"Jumlah posisi tidak tersedia":mfNum(data.short_positions)+" posisi";
      $("nl-mf-long-detail").textContent=data.long_positions==null?"Jumlah posisi tidak tersedia":mfNum(data.long_positions)+" posisi";
      $("nl-mf-lots").textContent=data.short_lots==null||data.long_lots==null?"—":mfNum(data.short_lots)+" / "+mfNum(data.long_lots);
      $("nl-mf-avg").textContent=data.short_average_price==null||data.long_average_price==null?"—":mfMoney(data.short_average_price)+" / "+mfMoney(data.long_average_price);
      $("nl-mf-source").textContent=(data.notice||"Data sentimen publik.")+" Diambil: "+new Date(data.fetched_at).toLocaleString("id-ID",{timeZone:"Asia/Jakarta"})+" WIB. Sumber: Myfxbook Community Outlook.";
      $("nl-mf-summarize").disabled=false;
      label.className="nl-status ok";label.textContent="Data berhasil dimuat. Ringkasan AI belum dibuat.";
      $("nl-mf-summary").textContent="Klik “Ringkas dengan Gemini” untuk penjelasan sederhana.";
    }catch(err){label.className="nl-status error";label.textContent=err.message||"Gagal mengambil sentiment Myfxbook.";}
    finally{button.disabled=false;}
  });
  $("nl-mf-summarize").addEventListener("click",async()=>{
    if(!myfxbookData)return;
    const button=$("nl-mf-summarize"), label=$("nl-mf-status");
    button.disabled=true;label.className="nl-status";label.textContent="Gemini sedang menjelaskan data sentiment…";
    try{
      const response=await fetch("/api/myfxbook/outlook/summarize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(myfxbookData)});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Gemini tidak bisa membuat ringkasan.");
      $("nl-mf-summary").textContent=data.analysis;
      label.className="nl-status ok";label.textContent="Ringkasan selesai · "+data.model+". Gunakan sebagai konteks, bukan sinyal entry.";
    }catch(err){label.className="nl-status error";label.textContent=err.message||"Gagal membuat ringkasan Gemini.";}
    finally{button.disabled=false;}
  });

  const cgFmt = n => Number.isFinite(n) ? n.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}) : "—";
  const cgPct = n => Number.isFinite(n) ? (n>0?"+":"")+n.toFixed(2)+"%" : "—";
  $("nl-cg-run").addEventListener("click", async () => {
    const button=$("nl-cg-run"), cgStatus=$("nl-cg-status");
    button.disabled=true; cgStatus.className="nl-status"; cgStatus.textContent="Memuat data derivatif CoinGlass…";
    try {
      // Candle/event controls were removed. Query a rolling 24-hour window.
      const endMs=Date.now();
      const startMs=endMs-24*60*60*1000;
      const params=new URLSearchParams({
        symbol:$("nl-cg-symbol").value,
        interval:"5m",
        start_time:String(startMs),
        end_time:String(endMs)
      });
      const response=await fetch("/api/news-liquidity/coinglass?"+params.toString(),{cache:"no-store"});
      const data=await response.json();
      if(!response.ok) throw new Error(data.detail||"CoinGlass tidak tersedia.");
      const oi=data.open_interest||[];
      $("nl-cg-total").textContent="N/A";
      $("nl-cg-split").textContent="Riwayat liquidation tidak disediakan endpoint publik Binance";
      $("nl-cg-long").textContent=Number.isFinite(Number(data.funding_rate))?(Number(data.funding_rate)*100).toFixed(4)+"%":"—";
      $("nl-cg-long-pct").textContent="Funding rate terbaru";
      $("nl-cg-short").textContent=Number.isFinite(Number(data.price_change_percent_24h))?((Number(data.price_change_percent_24h)>0?"+":"")+Number(data.price_change_percent_24h).toFixed(2)+"%"):"—";
      $("nl-cg-short-pct").textContent="Perubahan harga 24 jam";
      const ordered=oi.slice().sort((a,b)=>Number(a.time)-Number(b.time));
      const first=ordered[0], last=ordered[ordered.length-1];
      const oiStart=first?Number(first.open_interest_value):NaN, oiEnd=last?Number(last.open_interest_value):NaN;
      const oiChange=Number.isFinite(oiStart)&&oiStart!==0&&Number.isFinite(oiEnd)?((oiEnd-oiStart)/oiStart)*100:NaN;
      $("nl-cg-oi").textContent=cgPct(oiChange);
      $("nl-cg-oi-note").textContent=first&&last?"Perubahan nilai OI · "+ordered.length+" titik":"Data OI tidak tersedia pada rentang ini";
      $("nl-cg-source").textContent="Sumber: "+data.source+" · "+data.pair+" · interval "+data.interval+". Harga terakhir: "+(data.last_price==null?"—":cgFmt(Number(data.last_price)))+"; volume quote 24 jam: "+(data.quote_volume_24h==null?"—":cgFmt(Number(data.quote_volume_24h)))+".";
      cgStatus.className="nl-status ok";
      cgStatus.textContent="Data publik Binance berhasil dimuat tanpa API key. Riwayat liquidation tidak tersedia pada endpoint publik ini; metrik tersebut sengaja tidak direka.";
    } catch(err) {
      cgStatus.className="nl-status error";
      cgStatus.textContent=err.message||"Gagal memuat data CoinGlass.";
    } finally {
      button.disabled=false;
    }
  });

  // Myfxbook exposes a current public snapshot, not historical interval data.
  // This selector controls refresh cadence only; provider data may lag by 60 minutes.
  const mfInterval = $("nl-mf-interval");
  let mfRefreshTimer = null;
  const scheduleMyfxbookRefresh = () => {
    if (mfRefreshTimer) clearInterval(mfRefreshTimer);
    const intervalMs = Number(mfInterval.value);
    if (Number.isFinite(intervalMs) && intervalMs >= 300000) {
      mfRefreshTimer = setInterval(() => {
        const button = $("nl-mf-load");
        if (button && !button.disabled) button.click();
      }, intervalMs);
    }
  };
  mfInterval.addEventListener("change", scheduleMyfxbookRefresh);
  scheduleMyfxbookRefresh();

})();

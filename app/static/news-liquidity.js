(() => {
  const $ = id => document.getElementById(id);
  const form = $("nl-form"), run = $("nl-run"), status = $("nl-status");
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
      const eventMs=new Date($("nl-event-time").value).getTime();
      if(!Number.isFinite(eventMs)) throw new Error("Isi waktu rilis terlebih dahulu.");
      const windowMs=Number($("nl-window").value)*60*1000;
      const params=new URLSearchParams({
        symbol:$("nl-cg-symbol").value,
        interval:$("nl-interval").value==="60m"?"1h":$("nl-interval").value,
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

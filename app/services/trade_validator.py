"""Rule-based pre-trade checklist. It reviews process, not market direction."""
from math import isfinite


def _number(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def validate_setup(*, instrument="", direction="", entry="", stop_loss="", take_profit="",
                   risk_pct="", max_risk_pct="", htf_bias="", setup="",
                   trigger_confirmed="", liquidity_checked="", news_checked="", rr_min=""):
    """Return deterministic checklist status; never invent a win probability."""
    blockers, warnings, passed = [], [], []
    direction = (direction or "").strip().lower()
    if direction not in {"long", "short"}:
        blockers.append("Arah harus dipilih: long atau short.")
    entry_n, sl_n, tp_n = _number(entry), _number(stop_loss), _number(take_profit)
    if entry_n is None or entry_n <= 0:
        blockers.append("Harga entry harus berupa angka positif yang valid.")
    if sl_n is None or sl_n <= 0:
        blockers.append("Stop-loss wajib ditentukan sebelum entry.")
    if tp_n is None or tp_n <= 0:
        blockers.append("Take-profit wajib ditentukan sebelum entry.")
    if entry_n is not None and sl_n is not None and tp_n is not None and direction in {"long", "short"}:
        if direction == "long" and not (sl_n < entry_n < tp_n):
            blockers.append("Untuk long, SL harus di bawah entry dan TP di atas entry.")
        elif direction == "short" and not (tp_n < entry_n < sl_n):
            blockers.append("Untuk short, TP harus di bawah entry dan SL di atas entry.")
        else:
            passed.append("Geometri entry, SL, dan TP konsisten dengan arah trade.")

    risk_n, max_risk_n = _number(risk_pct), _number(max_risk_pct)
    if risk_n is None or risk_n <= 0:
        blockers.append("Risiko per trade (%) wajib dihitung sebelum entry.")
    if max_risk_n is None or max_risk_n <= 0:
        blockers.append("Batas risiko pribadi (%) wajib ditetapkan.")
    elif risk_n is not None and risk_n > max_risk_n:
        blockers.append(f"Risiko {risk_n:g}% melebihi batas pribadi {max_risk_n:g}%.")
    elif risk_n is not None and risk_n > 0:
        passed.append("Risiko berada dalam batas yang dimasukkan.")

    htf_bias = (htf_bias or "").strip().lower()
    if htf_bias not in {"bullish", "bearish", "neutral"}:
        warnings.append("Bias HTF belum dicatat.")
    elif direction == "long" and htf_bias == "bearish":
        warnings.append("Arah long berlawanan dengan bias HTF bearish; butuh alasan setup eksplisit.")
    elif direction == "short" and htf_bias == "bullish":
        warnings.append("Arah short berlawanan dengan bias HTF bullish; butuh alasan setup eksplisit.")
    else:
        passed.append("Bias HTF dicatat dan tidak berkonflik secara langsung.")

    if not (setup or "").strip():
        warnings.append("Nama/alasan setup belum dicatat.")
    else:
        passed.append("Setup dicatat.")
    if (trigger_confirmed or "").strip().lower() != "yes":
        warnings.append("Trigger entry belum dikonfirmasi.")
    else:
        passed.append("Trigger entry dikonfirmasi oleh pengguna.")
    if (liquidity_checked or "").strip().lower() != "yes":
        warnings.append("Struktur/liquidity belum diperiksa atau belum dicatat.")
    else:
        passed.append("Struktur/liquidity ditandai sudah diperiksa.")
    if (news_checked or "").strip().lower() != "yes":
        warnings.append("Risiko berita belum diperiksa.")
    else:
        passed.append("Risiko berita ditandai sudah diperiksa.")

    min_rr = _number(rr_min)
    rr = None
    if entry_n is not None and sl_n is not None and tp_n is not None and entry_n > 0 and sl_n > 0 and tp_n > 0 and direction in {"long", "short"}:
        risk_distance = abs(entry_n - sl_n)
        reward_distance = abs(tp_n - entry_n)
        if risk_distance > 0:
            rr = reward_distance / risk_distance
            if min_rr is not None and min_rr > 0 and rr < min_rr:
                warnings.append(f"R:R {rr:.2f}:1 di bawah minimum pribadi {min_rr:.2f}:1.")
            else:
                passed.append(f"R:R berdasarkan jarak harga: {rr:.2f}:1.")
        else:
            blockers.append("Jarak entry ke SL tidak boleh nol.")

    if blockers:
        status, summary = "BLOCKED", "Jangan lanjut sebelum blocker diperbaiki."
    elif warnings:
        status, summary = "REVIEW REQUIRED", "Ada bagian checklist yang belum cukup kuat atau belum terdokumentasi."
    else:
        status, summary = "READY FOR YOUR DECISION", "Checklist lolos. Ini bukan sinyal entry atau jaminan profit."
    return {
        "status": status, "summary": summary,
        "instrument": (instrument or "").strip().upper() or "Tidak dipilih",
        "direction": direction or "Tidak dipilih",
        "risk_pct": risk_n, "max_risk_pct": max_risk_n,
        "risk_reward": round(rr, 4) if rr is not None else None,
        "blockers": blockers, "warnings": warnings, "passed": passed,
        "win_probability": None,
        "limitations": [
            "Checklist deterministik, bukan model prediksi harga.",
            "Win probability tidak diestimasi tanpa dataset historis yang relevan.",
            "Struktur, berita, dan trigger tetap perlu bukti chart yang bisa diverifikasi.",
        ],
    }

"""Historical event study helpers built only from recorded price observations.

Returns are descriptive statistics, not a forecast. The sample is explicitly
limited to the manually recorded before/15-minute-after observations.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import median, pstdev
from typing import Iterable


MIN_SAMPLE_FOR_CONTEXT = 10


def summarize_reactions(rows: Iterable[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        try:
            event = str(row["event_type"]).strip()
            instrument = str(row["instrument"]).strip().upper()
            before = float(row["price_before"])
            after = float(row["price_after_15m"])
            direction = str(row["expected_direction"]).strip().lower()
        except (KeyError, TypeError, ValueError):
            continue
        if not event or not instrument or before <= 0 or after <= 0:
            continue
        if direction not in {"up", "down"}:
            continue
        change_pct = ((after - before) / before) * 100.0
        groups[(event, instrument)].append({
            "change_pct": change_pct,
            "expected_direction": direction,
            "aligned": (change_pct > 0 and direction == "up")
            or (change_pct < 0 and direction == "down"),
            "flat": change_pct == 0,
        })

    result = []
    for (event, instrument), samples in sorted(
        groups.items(), key=lambda item: (-len(item[1]), item[0][0], item[0][1])
    ):
        changes = [sample["change_pct"] for sample in samples]
        count = len(changes)
        non_flat = [sample for sample in samples if not sample["flat"]]
        aligned_count = sum(1 for sample in non_flat if sample["aligned"])
        result.append({
            "event_type": event,
            "instrument": instrument,
            "samples": count,
            "median_change_pct": round(median(changes), 5),
            "mean_change_pct": round(sum(changes) / count, 5),
            "dispersion_pct": round(pstdev(changes), 5) if count > 1 else 0.0,
            "positive_samples": sum(1 for value in changes if value > 0),
            "negative_samples": sum(1 for value in changes if value < 0),
            "flat_samples": sum(1 for value in changes if value == 0),
            "bias_aligned_pct": round(100 * aligned_count / len(non_flat), 1) if non_flat else None,
            "bias_scored_samples": len(non_flat),
            "sample_warning": (
                "Sampel sangat kecil; jangan menarik kesimpulan." if count < 5 else
                "Sampel terbatas; statistik masih rentan terhadap outlier." if count < MIN_SAMPLE_FOR_CONTEXT else
                "Statistik deskriptif dari data tercatat; bukan bukti kemampuan prediksi."
            ),
            "method": "Persentase perubahan = (harga +15 menit - harga sebelum) / harga sebelum × 100. Tidak dikoreksi spread, volatilitas, atau kondisi pasar.",
        })
    return result

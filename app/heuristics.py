"""
Heuristic functions for reorder recommendations.

Functions:
 - safety_stock(sigma, lead_time_days, z): compute safety stock using z * sigma * sqrt(lead_time)
 - reorder_point(avg_daily, safety_stock, lead_time_days): avg_daily * lead_time + safety_stock
 - recommended_qty_up_to_target(current_stock, target_stock, min_order_qty=1, pack_size=1): simple top-up with rounding to pack size
 - days_of_cover(current_stock, avg_daily): current_stock / avg_daily (handles avg_daily==0)
 - compute_recommendation(...) : main function that returns dict with fields:
     sku, recommended_qty, reorder_by_date, confidence (0..1), rationale (string)
     It accepts either a prompt-based LLM function (callable) or falls back to a template.
"""
from datetime import datetime, timedelta
import math
from typing import Callable, Optional, Dict, Any


def safety_stock(sigma: float, lead_time_days: float, z: float = 1.65) -> float:
    if lead_time_days <= 0:
        return 0.0
    return float(z * sigma * math.sqrt(lead_time_days))


def reorder_point(avg_daily: float, safety: float, lead_time_days: float) -> float:
    return float(avg_daily * lead_time_days + safety)


def recommended_qty_up_to_target(current_stock: float, target_stock: float, min_order_qty: int = 1, pack_size: int = 1) -> int:
    """
    Order-up-to target with rounding:
      raw_qty = max(0, target_stock - current_stock)
      rounded_qty = round up raw_qty to nearest multiple of pack_size
      then ensure at least min_order_qty if rounded_qty > 0
    """
    qty = max(0.0, float(target_stock) - float(current_stock))
    # round up to nearest multiple of pack_size
    if pack_size <= 1:
        qty_rounded = int(math.ceil(qty))
    else:
        qty_rounded = int(math.ceil(qty / float(pack_size)) * pack_size)
    if qty_rounded == 0:
        return 0
    return max(int(min_order_qty), qty_rounded)


def days_of_cover(current_stock: float, avg_daily: float) -> Optional[float]:
    if avg_daily <= 0:
        return None
    return float(current_stock) / float(avg_daily)


def default_rationale_template(info: Dict[str, Any]) -> str:
    return (
        f"Demand (avg daily) ≈ {info['avg_daily']:.2f}. Using lead time {info['lead_time_days']} days "
        f"and demand volatility (sigma) ≈ {info['sigma']:.2f}, safety stock ≈ {info['safety_stock']:.1f}. "
        f"Reorder point ≈ {info['reorder_point']:.1f}. Current stock is {info['current_stock']}, so recommended "
        f"order is {info['recommended_qty']} units to top up to target {info['target_stock']}."
    )


def compute_recommendation(
    sku: str,
    avg_daily: float,
    sigma: float,
    lead_time_days: int,
    current_stock: float,
    target_stock: float,
    as_of_date: Optional[datetime] = None,
    z: float = 1.65,
    min_order_qty: int = 1,
    llm_callable: Optional[Callable[[str], str]] = None,
    pack_size: int = 1,
) -> Dict[str, Any]:
    """
    Compute recommendation for one SKU and return structured dict.
    """
    as_of_date = as_of_date or datetime.utcnow()
    safety = safety_stock(sigma, lead_time_days, z=z)
    rop = reorder_point(avg_daily, safety, lead_time_days)

    rec_qty = recommended_qty_up_to_target(current_stock, target_stock, min_order_qty=min_order_qty, pack_size=pack_size)

    # determine reorder_by_date
    if current_stock < rop:
        reorder_by = as_of_date.date()
        reorder_reason = "current_stock_below_reorder_point"
    else:
        cover = days_of_cover(current_stock, avg_daily)
        if cover is None:
            reorder_by = None
            reorder_reason = "no_demand"
        else:
            days_until_reorder = max(0.0, cover - (rop / avg_daily) if avg_daily > 0 else float('inf'))
            latest_order_in_days = days_until_reorder - float(lead_time_days)
            if latest_order_in_days <= 0:
                reorder_by = as_of_date.date()
                reorder_reason = "within_lead_time"
            else:
                reorder_by = (as_of_date + timedelta(days=latest_order_in_days)).date()
                reorder_reason = "scheduled"

    diff = max(0.0, rop - current_stock)
    denom = (rop + 1.0)
    raw_conf = 0.5 + (diff / denom)
    confidence = max(0.0, min(0.99, raw_conf))

    info = {
        "sku": sku,
        "avg_daily": float(avg_daily),
        "sigma": float(sigma),
        "lead_time_days": int(lead_time_days),
        "safety_stock": float(safety),
        "reorder_point": float(rop),
        "current_stock": float(current_stock),
        "target_stock": float(target_stock),
        "recommended_qty": int(rec_qty),
        "as_of_date": str(as_of_date.date()),
        "reorder_reason": reorder_reason,
        "pack_size": int(pack_size),
    }

    rationale = None
    if llm_callable is not None:
        try:
            prompt = (
                f"Provide a short (<= 40 words) human-friendly explanation for a reorder recommendation.\n"
                f"SKU: {sku}\n"
                f"Avg daily demand: {info['avg_daily']:.2f}\n"
                f"Demand sigma: {info['sigma']:.2f}\n"
                f"Lead time (days): {info['lead_time_days']}\n"
                f"Safety stock: {info['safety_stock']:.1f}\n"
                f"Reorder point: {info['reorder_point']:.1f}\n"
                f"Current stock: {info['current_stock']}\n"
                f"Pack size: {info['pack_size']}\n"
                f"Recommended order: {info['recommended_qty']}\n"
                f"Target (order-up-to): {info['target_stock']}\n"
                f"Return a single-sentence rationale."
            )
            rationale = llm_callable(prompt).strip()
        except Exception:
            rationale = None

    if not rationale:
        rationale = default_rationale_template(info)

    result = {
        "sku": sku,
        "recommended_qty": int(rec_qty),
        "reorder_by_date": str(reorder_by) if reorder_by is not None else None,
        "confidence": round(float(confidence), 2),
        "rationale": rationale,
        "debug": info,
    }
    return result

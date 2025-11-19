import math
from app.heuristics import safety_stock, reorder_point, recommended_qty_up_to_target, compute_recommendation

def test_safety_stock_zero_lead_time():
    assert safety_stock(2.0, 0) == 0.0

def test_reorder_point_simple():
    s = safety_stock(1.0, 4, z=1.0)   # z=1.0 for simple math
    # safety = 1 * 1 * sqrt(4) = 2.0
    assert math.isclose(s, 2.0, rel_tol=1e-6)
    rop = reorder_point(3.0, s, 4)
    # expected 3*4 + 2 = 14
    assert math.isclose(rop, 14.0, rel_tol=1e-6)

def test_compute_recommendation_order_needed():
    rec = compute_recommendation(
        sku="TEST",
        avg_daily=5.0,
        sigma=2.0,
        lead_time_days=7,
        current_stock=10,
        target_stock=100,
        as_of_date=None,
        z=1.65,
        min_order_qty=1,
        llm_callable=None,
    )
    # should be an integer recommendation and reorder_by_date present if current_stock < rop
    assert isinstance(rec["recommended_qty"], int)
    assert rec["reorder_by_date"] is not None
    assert "rationale" in rec

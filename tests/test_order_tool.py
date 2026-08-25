from src.order_tool import lookup_order, normalize_order_id


def test_lookup_known_order():
    res = lookup_order("ORD-1007")
    assert res["found"] is True
    assert res["order_id"] == "ORD-1007"
    # safe fields present
    assert res.get("carrier") == "UPS"
    assert "internal" not in res


def test_cancelled_clears_eta_and_shipping():
    res = lookup_order("ORD-1004")
    assert res["found"] is True
    assert res["status"] == "cancelled"
    assert res["estimated_delivery"] is None
    assert res["carrier"] is None and res["tracking_number"] is None


def test_unknown_order():
    res = lookup_order("ORD-9999")
    assert res["found"] is False
    assert res["requested_id"] == "ORD-9999"


def test_normalize_order_id():
    assert normalize_order_id(" ord-1007 ") == "ORD-1007"
    assert normalize_order_id("ord-1007.") == "ORD-1007"

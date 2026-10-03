"""Single source of truth for catalog stock calculations."""


def stock_info(product):
    product = product if isinstance(product, dict) else {}
    by_size = product.get("stock_by_size")
    if isinstance(by_size, dict) and by_size:
        total = 0
        clean = {}
        for size, value in by_size.items():
            try:
                qty = max(0, int(value or 0))
            except Exception:
                qty = 0
            clean[str(size)] = qty
            total += qty
        return total, clean, True

    raw = product.get("total_stock", product.get("stock"))
    if raw not in (None, ""):
        try:
            return max(0, int(raw)), {}, True
        except Exception:
            return None, {}, False

    return None, {}, False

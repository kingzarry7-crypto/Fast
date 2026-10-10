"""Read-only Shopify inventory health checks for King Zarry AI.

This module detects low/out-of-stock variants and prepares recommendations.
It deliberately does not purchase stock or change quantities; replenishment must
be approved and executed through a configured supplier/fulfillment integration.
"""
from __future__ import annotations

from typing import Any, Dict, List

DEFAULT_LOW_STOCK_THRESHOLD = 5


def inventory_snapshot(user_id: str, threshold: int = DEFAULT_LOW_STOCK_THRESHOLD) -> Dict[str, Any]:
    from connector_api import _provider_account, _shopify_request, _shopify_token

    account = _provider_account(str(user_id), "shopify")
    if not account:
        return {"status": "not_connected", "connected": False, "items": [], "low_stock_count": 0}
    store, token = _shopify_token(str(user_id), "")
    query = """
    query KZInventoryWatch {
      products(first: 50, sortKey: UPDATED_AT, reverse: true) {
        nodes {
          id title status
          variants(first: 100) {
            nodes {
              id title sku inventoryQuantity
              inventoryItem { tracked }
            }
          }
        }
      }
    }
    """
    response = _shopify_request(store, token, query)
    products = (((response.get("data") or {}).get("products") or {}).get("nodes") or [])
    items: List[Dict[str, Any]] = []
    out_of_stock = 0
    low_stock = 0
    for product in products:
        for variant in (((product.get("variants") or {}).get("nodes")) or []):
            inventory_item = variant.get("inventoryItem") or {}
            if inventory_item.get("tracked") is False:
                continue
            quantity = variant.get("inventoryQuantity")
            if quantity is None:
                continue
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                continue
            if quantity <= int(threshold):
                is_out = quantity <= 0
                out_of_stock += int(is_out)
                low_stock += int(not is_out)
                items.append({
                    "product_id": product.get("id"),
                    "product": str(product.get("title") or "Untitled product")[:180],
                    "variant_id": variant.get("id"),
                    "variant": str(variant.get("title") or "Default")[:120],
                    "sku": str(variant.get("sku") or "")[:100],
                    "quantity": quantity,
                    "status": "out_of_stock" if is_out else "low_stock",
                })
    items.sort(key=lambda row: (row["quantity"] > 0, row["quantity"], row["product"]))
    return {
        "status": "completed",
        "connected": True,
        "store": store,
        "threshold": int(threshold),
        "products_checked": len(products),
        "low_stock_count": low_stock,
        "out_of_stock_count": out_of_stock,
        "items": items[:100],
        "purchase_or_quantity_changed": False,
        "note": "Read-only inventory check. No stock was purchased or changed.",
    }


def format_inventory_snapshot(result: Dict[str, Any]) -> str:
    if result.get("status") == "not_connected":
        return "Shopify is not connected to this KZ account."
    items = result.get("items") or []
    lines = [
        "🛍️ SHOPIFY STOCK WATCH",
        "",
        f"Store: {result.get('store') or 'Connected Shopify store'}",
        f"Products checked: {result.get('products_checked', 0)}",
        f"Out of stock: {result.get('out_of_stock_count', 0)}",
        f"Low stock (≤ {result.get('threshold', DEFAULT_LOW_STOCK_THRESHOLD)}): {result.get('low_stock_count', 0)}",
        "",
    ]
    if not items:
        lines.append("No tracked variants are at or below the low-stock threshold.")
    else:
        for item in items[:20]:
            label = "OUT OF STOCK" if item["quantity"] <= 0 else "LOW STOCK"
            sku = f" · SKU {item['sku']}" if item.get("sku") else ""
            lines.append(f"• {label}: {item['product']} / {item['variant']} — {item['quantity']} left{sku}")
        if len(items) > 20:
            lines.append(f"Showing 20 of {len(items)} low-stock variants.")
    lines.extend([
        "",
        "No stock was purchased or changed. I can prepare a replenishment recommendation for your approval, but an actual purchase requires a connected supplier/fulfillment service.",
    ])
    return "\n".join(lines)

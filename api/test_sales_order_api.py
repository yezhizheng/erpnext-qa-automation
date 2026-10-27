"""Core Sales Order REST API tests for ERPNext/Frappe."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest

from api.base_api import BaseAPI
from config.config import settings


pytestmark = pytest.mark.api


@pytest.fixture(scope="module")
def api() -> BaseAPI:
    assert settings.password, "Set ERPNEXT_PASSWORD in .env or the process environment"
    client = BaseAPI(settings.base_url, settings.timeout_ms // 1000)
    client.login(settings.username, settings.password)
    return client


def _first_name(api: BaseAPI, doctype: str, filters: list[list[object]] | None = None) -> str:
    params = {"fields": json.dumps(["name"]), "limit_page_length": 1}
    if filters:
        params["filters"] = json.dumps(filters)
    response = api.get(f"/api/resource/{doctype}", params=params)
    assert response.status_code == 200, response.text
    rows = BaseAPI.json_body(response).get("data", [])
    assert rows, f"ERPNext has no {doctype} records; seed test data before running API tests"
    return rows[0]["name"]


@pytest.fixture(scope="module")
def test_data(api: BaseAPI) -> dict[str, str]:
    """Create isolated business data so API tests do not depend on demo data."""
    suffix = datetime.now().strftime("%Y%m%d%H%M%S%f")
    customer_group = _first_name(api, "Customer Group", [["Customer Group", "is_group", "=", 0]])
    territory = _first_name(api, "Territory")
    item_group = _first_name(api, "Item Group", [["Item Group", "is_group", "=", 0]])
    uom = _first_name(api, "UOM")

    customer_response = api.post(
        "/api/resource/Customer",
        json={
            "doctype": "Customer",
            "customer_name": f"API Test Customer {suffix}",
            "customer_type": "Company",
            "customer_group": customer_group,
            "territory": territory,
        },
    )
    assert customer_response.status_code == 200, customer_response.text
    customer = BaseAPI.json_body(customer_response)["data"]["name"]

    item_response = api.post(
        "/api/resource/Item",
        json={
            "doctype": "Item",
            "item_code": f"API-TEST-{suffix}",
            "item_name": f"API Test Item {suffix}",
            "item_group": item_group,
            "stock_uom": uom,
            "is_stock_item": 0,
        },
    )
    assert item_response.status_code == 200, item_response.text
    item = BaseAPI.json_body(item_response)["data"]["name"]
    return {"customer": customer, "item": item}


def _sales_order_payload(customer: str, item_code: str, **overrides):
    payload = {
        "doctype": "Sales Order",
        "customer": customer,
        "transaction_date": str(date.today()),
        "delivery_date": str(date.today() + timedelta(days=7)),
        "items": [{"item_code": item_code, "qty": 1, "rate": 50}],
    }
    payload.update(overrides)
    return payload


def test_create_sales_order_as_draft(api: BaseAPI, test_data: dict[str, str]):
    response = api.post(
        "/api/resource/Sales Order",
        json=_sales_order_payload(test_data["customer"], test_data["item"]),
    )
    assert response.status_code == 200, response.text
    order = BaseAPI.json_body(response).get("data", {})
    assert order.get("status") == "Draft", order


def test_sales_order_rejects_negative_rate(api: BaseAPI, test_data: dict[str, str]):
    payload = _sales_order_payload(test_data["customer"], test_data["item"])
    payload["items"][0]["rate"] = -50
    response = api.post("/api/resource/Sales Order", json=payload)
    assert response.status_code in (400, 417, 422), response.text
    error = BaseAPI.error_text(response)
    assert any(term in error for term in ("rate", "negative", "greater than", "zero", "grand total")), error


def test_sales_order_rejects_invalid_delivery_date(api: BaseAPI, test_data: dict[str, str]):
    payload = _sales_order_payload(test_data["customer"], test_data["item"], delivery_date="2024-02-30")
    response = api.post("/api/resource/Sales Order", json=payload)
    assert response.status_code in (400, 417, 422), response.text
    error = BaseAPI.error_text(response)
    assert any(term in error for term in ("date", "valid", "invalid", "2024-02-30")), error


"""Seed deterministic ERPNext Sales Invoice data for Sales Analytics tests.

Configuration is loaded from the project-root .env file or environment:
    ERPNEXT_BASE_URL       default: http://localhost:8080
    ERPNEXT_USERNAME       required
    ERPNEXT_PASSWORD       required
    ERPNEXT_COMPANY        default: first company whose currency is CNY
    ERPNEXT_CUSTOMER_NAME  default: API 测试客户 2026102612
    ERPNEXT_VERIFY_SSL     default: true
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv


LOGGER = logging.getLogger(__name__)


class ERPNextAPIError(RuntimeError):
    """Raised when ERPNext returns an unexpected response."""


class ERPNextClient:
    def __init__(self, base_url: str, session: requests.Session) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.verify_ssl = os.getenv("ERPNEXT_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=30,
            verify=self.verify_ssl,
            **kwargs,
        )
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:2000]}
        if not response.ok:
            raise ERPNextAPIError(
                f"{method} {path} returned HTTP {response.status_code}: "
                f"{json.dumps(body, ensure_ascii=False)[:3000]}"
            )
        return body

    def list_docs(
        self,
        doctype: str,
        *,
        fields: list[str] | None = None,
        filters: list[list[Any]] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        params = {
            "fields": json.dumps(fields or ["name"]),
            "filters": json.dumps(filters or []),
            "limit_page_length": limit,
        }
        path = f"/api/resource/{quote(doctype, safe='')}"
        return self.request("GET", path, params=params).get("data", [])

    def get_doc(self, doctype: str, name: str) -> dict[str, Any]:
        path = f"/api/resource/{quote(doctype, safe='')}/{quote(name, safe='')}"
        return self.request("GET", path)["data"]

    def create_doc(self, doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = f"/api/resource/{quote(doctype, safe='')}"
        return self.request("POST", path, json=payload)["data"]

    def submit_doc(self, doctype: str, name: str) -> dict[str, Any]:
        doc = self.get_doc(doctype, name)
        body = self.request(
            "POST",
            "/api/method/frappe.client.submit",
            data={"doc": json.dumps(doc, ensure_ascii=False)},
        )
        return body.get("message", body)

    def run_sales_analytics(self, filters: dict[str, Any]) -> dict[str, Any]:
        return self.request(
            "GET",
            "/api/method/frappe.desk.query_report.run",
            params={
                "report_name": "Sales Analytics",
                "filters": json.dumps(filters, ensure_ascii=False),
                "ignore_prepared_report": 1,
                "are_default_filters": 0,
            },
        )["message"]


@dataclass(frozen=True)
class InvoiceSpec:
    posting_date: str
    qty: float
    rate: float
    currency: str = "CNY"
    conversion_rate: float = 1.0
    submit: bool = True


INVOICE_SPECS = [
    InvoiceSpec("2026-01-10", 1, 100),
    InvoiceSpec("2026-01-20", 2, 120),
    InvoiceSpec("2026-02-08", 1, 300),
    InvoiceSpec("2026-02-18", 1, 400, submit=False),
    InvoiceSpec("2026-03-05", 2, 50, "USD", 7.20),
    InvoiceSpec("2026-03-22", 1, 60, "USD", 7.20, submit=False),
    InvoiceSpec("2026-04-12", 1, 500),
    InvoiceSpec("2026-04-25", 1, 600, submit=False),
    InvoiceSpec("2026-05-15", 2, 350),
    InvoiceSpec("2026-06-16", 1, 800),
    InvoiceSpec("2026-07-17", 3, 300),
]


@dataclass(frozen=True)
class SeedResult:
    company: str
    customer: str
    invoice_names: list[str]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def login(base_url: str, username: str, password: str) -> requests.Session:
    """Log in through Frappe and return the authenticated cookie session."""
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "X-Frappe-CSRF-Token": "fetch"})
    response = session.post(
        f"{base_url.rstrip('/')}/api/method/login",
        json={"usr": username, "pwd": password},
        timeout=30,
    )
    if not response.ok:
        raise ERPNextAPIError(f"Login failed with HTTP {response.status_code}: {response.text[:1000]}")
    if not session.cookies.get("sid"):
        raise ERPNextAPIError("Login returned success but no Frappe sid cookie was issued")
    session.headers.pop("X-Frappe-CSRF-Token", None)
    LOGGER.info("Logged in as %s; session cookie acquired", username)
    return session


def first_leaf(client: ERPNextClient, doctype: str) -> str:
    rows = client.list_docs(
        doctype,
        fields=["name"],
        filters=[[doctype, "is_group", "=", 0]],
        limit=1,
    )
    if not rows:
        raise ERPNextAPIError(f"No non-group {doctype} exists")
    return rows[0]["name"]


def first_doc(client: ERPNextClient, doctype: str) -> str:
    rows = client.list_docs(doctype, fields=["name"], limit=1)
    if not rows:
        raise ERPNextAPIError(f"No {doctype} exists")
    return rows[0]["name"]


def resolve_company(client: ERPNextClient) -> dict[str, Any]:
    requested = os.getenv("ERPNEXT_COMPANY")
    filters = [["Company", "name", "=", requested]] if requested else [["Company", "default_currency", "=", "CNY"]]
    rows = client.list_docs(
        "Company",
        fields=["name", "default_currency"],
        filters=filters,
        limit=1,
    )
    if not rows:
        raise ERPNextAPIError(
            "No matching CNY company found. Set ERPNEXT_COMPANY to a valid company; "
            "USD conversion in this seed expects the company currency to be CNY."
        )
    if rows[0]["default_currency"] != "CNY":
        raise ERPNextAPIError("Selected company must use CNY as its default currency")
    return rows[0]


def ensure_customer(client: ERPNextClient, customer_name: str) -> str:
    rows = client.list_docs(
        "Customer",
        fields=["name", "customer_name"],
        filters=[["Customer", "customer_name", "=", customer_name]],
        limit=1,
    )
    if rows:
        LOGGER.info("Reuse Customer: %s", rows[0]["name"])
        return rows[0]["name"]

    customer = client.create_doc(
        "Customer",
        {
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Company",
            "customer_group": first_leaf(client, "Customer Group"),
            "territory": first_doc(client, "Territory"),
        },
    )
    LOGGER.info("Created Customer: %s", customer["name"])
    return customer["name"]


def ensure_item(client: ERPNextClient) -> str:
    item_code = "API-SALES-ANALYTICS-2026"
    rows = client.list_docs(
        "Item",
        fields=["name", "item_code"],
        filters=[["Item", "item_code", "=", item_code]],
        limit=1,
    )
    if rows:
        LOGGER.info("Reuse Item: %s", rows[0]["name"])
        return rows[0]["name"]

    item = client.create_doc(
        "Item",
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": "API Sales Analytics Test Item",
            "item_group": first_leaf(client, "Item Group"),
            "stock_uom": first_doc(client, "UOM"),
            "is_stock_item": 0,
        },
    )
    LOGGER.info("Created Item: %s", item["name"])
    return item["name"]


def create_invoice(
    client: ERPNextClient,
    *,
    company: str,
    customer: str,
    item_code: str,
    spec: InvoiceSpec,
    batch_id: str,
    index: int,
) -> dict[str, Any]:
    posting_date = datetime.strptime(spec.posting_date, "%Y-%m-%d").date()
    invoice = client.create_doc(
        "Sales Invoice",
        {
            "doctype": "Sales Invoice",
            "company": company,
            "customer": customer,
            "posting_date": spec.posting_date,
            "set_posting_time": 1,
            "due_date": str(posting_date + timedelta(days=30)),
            "currency": spec.currency,
            "conversion_rate": spec.conversion_rate,
            "remarks": f"Sales Analytics seed {batch_id} #{index:02d}",
            "items": [{"item_code": item_code, "qty": spec.qty, "rate": spec.rate}],
        },
    )
    if spec.submit:
        invoice = client.submit_doc("Sales Invoice", invoice["name"])
    LOGGER.info(
        "%s %s date=%s currency=%s amount=%s conversion=%s",
        "SUBMITTED" if spec.submit else "DRAFT",
        invoice["name"],
        spec.posting_date,
        spec.currency,
        spec.qty * spec.rate,
        spec.conversion_rate,
    )
    return invoice


def create_credit_note(
    client: ERPNextClient,
    *,
    source_invoice_name: str,
    posting_date: str,
    batch_id: str,
) -> dict[str, Any]:
    source = client.get_doc("Sales Invoice", source_invoice_name)
    source_item = source["items"][0]
    credit_note = client.create_doc(
        "Sales Invoice",
        {
            "doctype": "Sales Invoice",
            "company": source["company"],
            "customer": source["customer"],
            "posting_date": posting_date,
            "set_posting_time": 1,
            "due_date": posting_date,
            "is_return": 1,
            "return_against": source["name"],
            "currency": source["currency"],
            "conversion_rate": source["conversion_rate"],
            "remarks": f"Sales Analytics negative-value seed {batch_id}",
            "items": [
                {
                    "item_code": source_item["item_code"],
                    "qty": -1,
                    "rate": source_item["rate"],
                    "sales_invoice_item": source_item["name"],
                }
            ],
        },
    )
    credit_note = client.submit_doc("Sales Invoice", credit_note["name"])
    LOGGER.info("SUBMITTED CREDIT %s date=%s negative total", credit_note["name"], posting_date)
    return credit_note


def verify_analytics(
    client: ERPNextClient,
    *,
    company: str,
    customer: str,
) -> dict[str, Any]:
    report = client.run_sales_analytics(
        {
            "tree_type": "Customer",
            "entity": [customer],
            "doc_type": "Sales Invoice",
            "value_quantity": "Value",
            "from_date": "2026-01-01",
            "to_date": "2026-12-31",
            "company": company,
            "range": "Monthly",
            "curves": "all",
        }
    )
    LOGGER.info(
        "Sales Analytics result:\n%s",
        json.dumps(report.get("result", []), ensure_ascii=False, indent=2, default=str),
    )
    rows = report.get("result", [])
    if not rows:
        raise ERPNextAPIError("Sales Analytics returned no rows for the seeded customer")
    return report


def generate_invoices(client: ERPNextClient) -> SeedResult:
    """Prepare master data and create 12 invoices across the 2026 calendar year."""
    company = resolve_company(client)["name"]
    customer = ensure_customer(
        client,
        os.getenv("ERPNEXT_CUSTOMER_NAME", "API 测试客户 2026102612"),
    )
    item_code = ensure_item(client)
    batch_id = datetime.now().strftime("%Y%m%d%H%M%S")

    created: list[dict[str, Any]] = []
    for index, spec in enumerate(INVOICE_SPECS, start=1):
        created.append(
            create_invoice(
                client,
                company=company,
                customer=customer,
                item_code=item_code,
                spec=spec,
                batch_id=batch_id,
                index=index,
            )
        )

    first_submitted = next(
        invoice for invoice, spec in zip(created, INVOICE_SPECS, strict=True) if spec.submit
    )
    credit_note = create_credit_note(
        client,
        source_invoice_name=first_submitted["name"],
        posting_date="2026-08-18",
        batch_id=batch_id,
    )
    names = [invoice["name"] for invoice in created] + [credit_note["name"]]
    return SeedResult(company=company, customer=customer, invoice_names=names)


def main() -> int:
    load_dotenv()
    base_url = os.getenv("ERPNEXT_BASE_URL", "http://localhost:8080")
    session = login(base_url, require_env("ERPNEXT_USERNAME"), require_env("ERPNEXT_PASSWORD"))
    client = ERPNextClient(base_url, session)
    result = generate_invoices(client)
    verify_analytics(client, company=result.company, customer=result.customer)
    LOGGER.info("Created 12 Sales Invoices: 9 submitted (including one credit note) and 3 drafts")
    LOGGER.info("Invoice names: %s", ", ".join(result.invoice_names))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except (requests.RequestException, ERPNextAPIError) as exc:
        LOGGER.exception("Sales Invoice seed failed: %s", exc)
        raise SystemExit(1) from exc

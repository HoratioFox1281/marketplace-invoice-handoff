from fastapi.testclient import TestClient

from marketplace_invoice.infrai_pdf import InfraiPdfClient
from marketplace_invoice.invoice_handoff import app, get_pdf_client


class RecordingPdfClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate_invoice(self, html: str, idempotency_key: str) -> dict[str, str]:
        self.calls.append((html, idempotency_key))
        return {"url": "https://example.com/invoices/INV-1042.pdf"}

    async def close(self) -> None:
        return None


def paid_order() -> dict[str, object]:
    return {
        "order_id": "order_1042",
        "invoice_number": "INV-1042",
        "currency": "USD",
        "status": "paid",
        "seller": {"display_name": "Tiny Tools", "legal_name": "Tiny Tools LLC", "logo_url": "https://example.com/logo.png", "tax_id": "US-12"},
        "buyer": {"name": "Jamie Chen", "billing_email": "jamie@example.com", "billing_address": "18 Market Street"},
        "lines": [{"description": "Lifetime workspace", "quantity": 2, "unit_price": "24.50"}],
    }


def test_paid_order_becomes_invoice_handoff() -> None:
    recorder = RecordingPdfClient()
    app.dependency_overrides[get_pdf_client] = lambda: recorder
    response = TestClient(app).post("/orders/invoice", json=paid_order())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["state"] == "invoice_ready"
    assert "Total: 49.00 USD" in recorder.calls[0][0]
    assert recorder.calls[0][1] == "invoice-order_1042-INV-1042"


def test_pending_order_is_not_handed_off() -> None:
    recorder = RecordingPdfClient()
    app.dependency_overrides[get_pdf_client] = lambda: recorder
    order = paid_order()
    order["status"] = "pending"
    response = TestClient(app).post("/orders/invoice", json=order)
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert recorder.calls == []

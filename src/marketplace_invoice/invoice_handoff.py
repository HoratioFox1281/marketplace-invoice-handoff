from __future__ import annotations

import html
import os
from decimal import Decimal
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from .infrai_pdf import InfraiError, InfraiPdfClient


class SellerAssets(BaseModel):
    display_name: str = Field(min_length=1)
    legal_name: str = Field(min_length=1)
    logo_url: HttpUrl
    tax_id: str = Field(min_length=1)


class BuyerUpdate(BaseModel):
    name: str = Field(min_length=1)
    billing_email: str = Field(min_length=3)
    billing_address: str = Field(min_length=1)


class OrderLine(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class MarketplaceOrder(BaseModel):
    order_id: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    status: Literal["pending", "paid", "cancelled"]
    seller: SellerAssets
    buyer: BuyerUpdate
    lines: list[OrderLine] = Field(min_length=1)


class InvoiceHandoff(BaseModel):
    order_id: str
    state: Literal["invoice_ready"]
    invoice: dict[str, Any]


def render_invoice(order: MarketplaceOrder) -> str:
    rows = []
    total = Decimal("0")
    for line in order.lines:
        amount = line.unit_price * line.quantity
        total += amount
        rows.append(
            "<tr>"
            f"<td>{html.escape(line.description)}</td>"
            f"<td>{line.quantity}</td>"
            f"<td>{line.unit_price:.2f} {html.escape(order.currency)}</td>"
            f"<td>{amount:.2f} {html.escape(order.currency)}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;color:#20242a;margin:42px}} header{{display:flex;justify-content:space-between}}
img{{max-height:54px;max-width:180px}} table{{width:100%;border-collapse:collapse;margin-top:28px}}
th,td{{padding:10px;border-bottom:1px solid #d9dde3;text-align:left}} .total{{text-align:right;font-size:20px}}
</style></head><body>
<header><div><img src="{html.escape(str(order.seller.logo_url))}" alt="seller logo"><h1>Invoice {html.escape(order.invoice_number)}</h1></div>
<div><strong>{html.escape(order.seller.legal_name)}</strong><br>Tax ID: {html.escape(order.seller.tax_id)}</div></header>
<p>Order: {html.escape(order.order_id)}</p>
<h2>Bill to</h2><p>{html.escape(order.buyer.name)}<br>{html.escape(order.buyer.billing_email)}<br>{html.escape(order.buyer.billing_address)}</p>
<table><thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Amount</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p class="total"><strong>Total: {total:.2f} {html.escape(order.currency)}</strong></p>
</body></html>"""


def get_pdf_client() -> InfraiPdfClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
    return InfraiPdfClient(api_key)


app = FastAPI(title="Marketplace invoice handoff")


@app.post("/orders/invoice", response_model=InvoiceHandoff)
async def handoff_order(
    order: MarketplaceOrder,
    pdf_client: InfraiPdfClient = Depends(get_pdf_client),
) -> InvoiceHandoff:
    if order.status != "paid":
        raise HTTPException(status_code=409, detail="Only paid orders can be handed off")

    try:
        invoice = await pdf_client.generate_invoice(
            render_invoice(order),
            idempotency_key=f"invoice-{order.order_id}-{order.invoice_number}",
        )
    except InfraiError as error:
        status_code = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=error.detail) from error
    finally:
        await pdf_client.close()

    return InvoiceHandoff(order_id=order.order_id, state="invoice_ready", invoice=invoice)

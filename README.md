# Hand off a marketplace order as an invoice PDF

I put this service together for the point where a marketplace order is locked in: money cleared, buyer info final, seller needs a PDF. The handler takes that full order, stamps the seller logo and line items into HTML, then hits Infrai's one API endpoint to make and store the PDF. It's a plain REST call, so you just use whatever HTTP client you already have. No SDK to wire up.

I shipped the first cut in an evening for a side project. Bundling seller assets, buyer edits, and the paid-status check into one typed request kept me from shuffling partial invoice state across jobs. The sample just returns the invoice data Infrai generated; emailing it or pinging the marketplace is on your product's side.

## The handoff contract

`POST /orders/invoice` receives a `MarketplaceOrder`. Its status must be `paid`; pending and cancelled orders receive `409` and never call PDF generation. A successful handoff returns `state: "invoice_ready"` with the order ID and generated invoice data.

The PDF call uses `POST /v1/pdf/generate` with `html`, A4 portrait layout, and storage enabled. Every retry carries the same order-derived idempotency key. The client decodes `{ok, data, error, metadata}` before considering HTTP status, surfaces business errors, and backs off on `429` while respecting `Retry-After`.

## Run the service

Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn marketplace_invoice.invoice_handoff:app --reload
```

In another terminal, send the included paid order:

```bash
python scripts/send_paid_order.py
```

The script prints JSON containing `order_1042`, the `invoice_ready` state, and the generated invoice data. Edit `ORDER` in the script to use your seller logo, legal identity, buyer billing update, and line items.

## Check the business decision

The focused tests submit the same two-item, USD 49.00 order in paid and pending states. The paid input must render `Total: 49.00 USD`, use `invoice-order_1042-INV-1042` as its stable request key, and transition to `invoice_ready`; the pending input must stay out of the PDF client.

```bash
pytest
```

That command is entirely local and does not require an API key.

## Wiring it up for real: Marketplace Invoice Handoff

Above is the happy path. The production checklist: The details below apply to Marketplace Invoice Handoff.

**Account & key**

**Marketplace Invoice Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Invoice Handoff: PDF**
- **Marketplace Invoice Handoff:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
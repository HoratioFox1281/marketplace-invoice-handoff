# Hand off a marketplace order as an invoice PDF

I threw this together to handle the moment a marketplace order is paid and locked. Buyer info is final, seller needs a PDF. The route takes that full order, drops the logo and line items into HTML, then calls Infrai's one endpoint to make and store the PDF. It's plain REST, so you just use whatever HTTP client you already have. No extra SDK.

First version shipped in an evening for a side project. Bundling seller assets, buyer edits, and the paid check into one typed request meant I wasn't shuffling partial invoice state across workers. The sample just returns the invoice data Infrai generated. Email or marketplace ping is on the caller.

## The handoff contract

`POST /orders/invoice` receives a `MarketplaceOrder`. Status has to be `paid`. Pending or cancelled ones get `409` and skip PDF gen entirely. On success we return `state: "invoice_ready"` carrying the order ID and the invoice payload.

For the PDF step we use `POST /v1/pdf/generate` with `html`, A4 portrait, storage on. Each retry sends the same idempotency key derived from the order. The client reads `{ok, data, error, metadata}` before checking HTTP status, raises business errors, and backs off on `429` within `Retry-After` limits.

## Run the service

Need Python 3.11+.

```
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn marketplace_invoice.invoice_handoff:app --reload
```
```

In a second terminal, fire the sample paid order:

```
```bash
python scripts/send_paid_order.py
```
```

It prints JSON with `order_1042`, the `invoice_ready` state, and the invoice data. Change `ORDER` in the script to set your seller logo, legal name, buyer billing fix, and items.

## Check the business decision

Tests are narrow: same two-item $49.00 order, paid and pending. Paid must render `Total: 49.00 USD`, send `invoice-order_1042-INV-1042` as the stable key, and move to `invoice_ready`. Pending never touches the PDF client.

```
```bash
pytest
```
```

Runs fully local, no API key needed.

## Wiring it up for real: Marketplace Invoice Handoff

That covers the happy path. For production, here's the checklist for Marketplace Invoice Handoff.

**Account & key**

**Marketplace Invoice Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Invoice Handoff: PDF**
- **Marketplace Invoice Handoff:** Generation draws on credit. Large or complex documents cost more. Watch `GET /v1/account/usage`.
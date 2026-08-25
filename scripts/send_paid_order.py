import asyncio
import json
import os

import httpx


ORDER = {
    "order_id": "order_1042",
    "invoice_number": "INV-1042",
    "currency": "USD",
    "status": "paid",
    "seller": {
        "display_name": "Tiny Tools",
        "legal_name": "Tiny Tools LLC",
        "logo_url": "https://example.com/logo.png",
        "tax_id": "US-12-3456789",
    },
    "buyer": {
        "name": "Jamie Chen",
        "billing_email": "jamie@example.com",
        "billing_address": "18 Market Street, Portland, OR",
    },
    "lines": [{"description": "Lifetime workspace", "quantity": 1, "unit_price": "49.00"}],
}


async def main() -> None:
    base_url = os.environ.get("SERVICE_URL", "http://127.0.0.1:8000")
    async with httpx.AsyncClient(base_url=base_url, timeout=40.0) as client:
        response = await client.request(method="POST", url="/orders/invoice", json=ORDER)
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())

import os
import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client

app = FastAPI()

# Locate templates directory relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

# Initialize Supabase Client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Stripe API
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51P_YOUR_DEFAULT_STRIPE_SECRET_KEY")


@app.get("/", response_class=HTMLResponse)
async def read_hub(request: Request):
    """Renders the main catalog hub."""
    try:
        response = supabase.table("products").select("*").execute()
        products = response.data or []
        
        return templates.TemplateResponse(
            request=request,
            name="hub.html",
            context={"products": products}
        )
    except Exception as err:
        return HTMLResponse(content=f"<h1>Error loading storefront hub</h1><p>{str(err)}</p>", status_code=500)


@app.get("/item/{item_slug}", response_class=HTMLResponse)
async def read_item(request: Request, item_slug: str):
    """Renders an individual product detail page."""
    try:
        response = supabase.table("products").select("*").eq("slug", item_slug).execute()
        product_data = response.data

        if not product_data:
            raise HTTPException(status_code=404, detail="Product not found.")

        item = product_data[0]

        return templates.TemplateResponse(
            request=request,
            name="item.html",
            context={"item": item}
        )
    except Exception as err:
        return HTMLResponse(content=f"<h1>Error loading product page</h1><p>{str(err)}</p>", status_code=500)


@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    """Generates a dynamic multi-item Stripe Checkout session."""
    try:
        data = await request.json()
        cart_items = data.get("items", [])

        if not cart_items:
            return JSONResponse(status_code=400, content={"error": "Cart is empty"})

        line_items = []
        for item in cart_items:
            line_items.append({
                "price_data": {
                    "currency": "gbp",
                    "product_data": {
                        "name": item.get("name", "Store Item"),
                    },
                    "unit_amount": int(float(item.get("price", 0)) * 100),
                },
                "quantity": int(item.get("quantity", 1)),
            })

        base_url = str(request.base_url)

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=f"{base_url}?success=true",
            cancel_url=f"{base_url}?canceled=true",
        )

        return JSONResponse(content={"url": session.url})

    except Exception as err:
        return JSONResponse(status_code=400, content={"error": str(err)})

import os
import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client

app = FastAPI()

# Locate the templates directory directly inside the api folder
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

# Initialize Supabase Client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Stripe (Replace sk_test_... with your key or use an environment variable)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51P_YOUR_DEFAULT_STRIPE_SECRET_KEY")


# 1. Main Directory Website Route
@app.get("/", response_class=HTMLResponse)
async def read_hub(request: Request):
    try:
        # Fetch all items from your Supabase table
        response = supabase.table("products").select("*").execute()
        products = response.data

        # Explicit modern syntax ensures it works across all FastAPI/Starlette versions
        return templates.TemplateResponse(
            request=request,
            name="hub.html",
            context={"products": products}
        )
    except Exception as err:
        return f"<h1>Error loading storefront hub</h1><p>{str(err)}</p>"


# 2. Individual Sub-Website Route
@app.get("/item/{item_slug}", response_class=HTMLResponse)
async def read_item(request: Request, item_slug: str):
    try:
        response = supabase.table("products").select("*").eq("slug", item_slug).execute()
        product_data = response.data

        if not product_data:
            raise HTTPException(status_code=404, detail="Sub-website for this item does not exist.")

        item = product_data[0]

        # Explicit modern syntax applied here as well
        return templates.TemplateResponse(
            request=request,
            name="item.html",
            context={"item": item}
        )
    except Exception as err:
        return f"<h1>Error loading item storefront</h1><p>{str(err)}</p>"


# 3. Dynamic Multi-Item Stripe Checkout Endpoint
@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
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
                        "name": item.get("name", "Product"),
                    },
                    # Stripe expects prices in pence (£29.99 = 2999)
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

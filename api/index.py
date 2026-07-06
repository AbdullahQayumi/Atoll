import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
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

# 1. Main Directory Website Route
@app.get("/", response_class=HTMLResponse)
async def read_hub(request: Request):
    try:
        # Fetch all items from your Supabase table
        response = supabase.table("products").select("*").execute()
        products = response.data
        return templates.TemplateResponse("hub.html", {"request": request, "products": products})
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
        return templates.TemplateResponse("item.html", {"request": request, "item": item})
    except Exception as err:
        return f"<h1>Error loading item storefront</h1><p>{str(err)}</p>"

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client

app = FastAPI()

# Locate the templates directory relative to this script
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

# Initialize Supabase Client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Gracefully initialize if variables are missing during local testing builds
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# 1. Main Directory Website Route
@app.get("/", response_class=HTMLResponse)
async def read_hub(request: Request):
    if not supabase:
        return "Database credentials missing."
    
    # Fetch all items from Supabase
    response = supabase.table("products").select("*").execute()
    products = response.data
    
    return templates.TemplateResponse("hub.html", {"request": request, "products": products})

# 2. Individual Sub-Website Route
@app.get("/item/{item_slug}", response_class=HTMLResponse)
async def read_item(request: Request, item_slug: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database setup incomplete.")
    
    # Query database for the specific item slug
    response = supabase.table("products").select("*").eq("slug", item_slug).execute()
    product_data = response.data
    
    if not product_data:
        raise HTTPException(status_code=404, detail="Sub-website for this item does not exist.")
    
    # Pass the matching record to our individual item layout
    item = product_data[0]
    return templates.TemplateResponse("item.html", {"request": request, "item": item})
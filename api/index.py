import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client

app = FastAPI()

# Locate the templates directory directly inside the api folder
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")

# Error-safe template initialization
try:
    templates = Jinja2Templates(directory=templates_dir)
except Exception as template_error:
    templates = None
    TEMPLATE_INIT_ERROR = str(template_error)

# Initialize Supabase Client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        DB_INIT_ERROR = None
    except Exception as db_err:
        supabase = None
        DB_INIT_ERROR = str(db_err)
else:
    supabase = None
    DB_INIT_ERROR = "Environment variables SUPABASE_URL or SUPABASE_KEY are completely missing in Vercel settings."

# 1. Main Directory Website Route
@app.get("/", response_class=HTMLResponse)
async def read_hub(request: Request):
    # Diagnostic Check 1: Did templates fail?
    if templates is None:
        return f"<h1>Template Folder Error</h1><p>FastAPI cannot find your HTML folder. Details: {TEMPLATE_INIT_ERROR}</p>"
    
    # Diagnostic Check 2: Did Supabase fail connection?
    if supabase is None:
        return f"<h1>Database Connection Error</h1><p>{DB_INIT_ERROR}</p>"
    
    try:
        # Fetch all items from Supabase
        response = supabase.table("products").select("*").execute()
        products = response.data
        return templates.TemplateResponse("hub.html", {"request": request, "products": products})
    except Exception as run_error:
        # If the query itself crashes (e.g. table doesn't exist)
        return f"<h1>Supabase Fetch Error</h1><p>Connected to Supabase, but the query failed: {str(run_error)}</p>"


# 2. Individual Sub-Website Route
@app.get("/item/{item_slug}", response_class=HTMLResponse)
async def read_item(request: Request, item_slug: str):
    if templates is None:
        return f"<h1>Template Folder Error</h1><p>{TEMPLATE_INIT_ERROR}</p>"
    if supabase is None:
        return f"<h1>Database Connection Error</h1><p>{DB_INIT_ERROR}</p>"
    
    try:
        response = supabase.table("products").select("*").eq("slug", item_slug).execute()
        product_data = response.data
        
        if not product_data:
            raise HTTPException(status_code=404, detail="Sub-website for this item does not exist.")
        
        item = product_data[0]
        return templates.TemplateResponse("item.html", {"request": request, "item": item})
    except Exception as run_error:
        return f"<h1>Supabase Item Fetch Error</h1><p>Failed fetching slug '{item_slug}': {str(run_error)}</p>"

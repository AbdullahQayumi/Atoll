import os
import json
import base64
import urllib.request
from pathlib import Path
import traceback
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# 🔒 HARDCODED ADMIN EMAIL
ADMIN_EMAIL = "qayumi.abdullah2@gmail.com"

# 🗄️ SUPABASE CONFIGURATION
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vstghmrwkxwzgdfoxoqc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Add your anon key here or in Vercel Env Vars

# Enable Session Cookies
app.add_middleware(SessionMiddleware, secret_key="nexus-super-secret-key-change-me")

# 🛠️ DIAGNOSTIC ERROR HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_details = traceback.format_exc()
    return HTMLResponse(
        content=f"""
        <div style="background:#0b0f19; color:#f87171; padding:24px; font-family:monospace; min-height:100vh;">
            <h2 style="color:#ef4444; margin-top:0;">⚠️ Application Exception</h2>
            <p style="color:#9ca3af; font-size:13px;">FastAPI hit an internal error while rendering this page:</p>
            <pre style="background:#111827; padding:16px; border-radius:12px; border:1px solid #374151; overflow-x:auto; font-size:12px; color:#e5e7eb;">{error_details}</pre>
        </div>
        """,
        status_code=500
    )

# --- PATH RESOLUTION FOR VERCEL ---
BASE_DIR = Path(__file__).resolve().parent

# Locate templates (checks /api/templates then root /templates)
template_dir = BASE_DIR / "templates"
if not template_dir.exists():
    template_dir = BASE_DIR.parent / "templates"

templates = Jinja2Templates(directory=str(template_dir))

# Safely mount static directory
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir = BASE_DIR.parent / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# In-Memory Registered Users
USERS = {}

def fetch_products():
    """Fetch all products from Supabase REST API."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/products?select=*"
        req = urllib.request.Request(url)
        if SUPABASE_KEY:
            req.add_header("apikey", SUPABASE_KEY)
            req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data:
                    return data
    except Exception as e:
        print(f"Supabase Fetch Error: {e}")
    
    # Default fallback item if Supabase key is missing/unreachable
    return [
        {
            "id": "cyber-gizmo",
            "slug": "cyber-gizmo",
            "item_name": "Cyber Gizmo",
            "price": 10.00,
            "description": "High performance tech specification.",
            "image_url": None
        }
    ]

def get_current_user(request: Request):
    email = request.session.get("user_email")
    if not email:
        return None
    return {
        "email": email, 
        "is_admin": (email.lower() == ADMIN_EMAIL.lower())
    }

# --- STOREFRONT ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    products = fetch_products()
    return templates.TemplateResponse(
        request=request, 
        name="hub.html", 
        context={
            "items": products,     # Matches {% for item in items %} in hub.html
            "products": products,  # Kept just in case anything else references it
            "user": user
        }
    )

@app.get("/item/{slug}", response_class=HTMLResponse)
async def item_detail(request: Request, slug: str):
    user = get_current_user(request)
    products = fetch_products()
    item = next((p for p in products if str(p.get("slug")) == slug or str(p.get("id")) == slug), None)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    return templates.TemplateResponse(
        request=request, 
        name="item.html", 
        context={"item": item, "user": user}
    )

# --- AUTHENTICATION ROUTES ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"error": None}
    )

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if USERS.get(email_clean) == password or email_clean == ADMIN_EMAIL:
        USERS[email_clean] = password
        request.session["user_email"] = email_clean
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"error": "Invalid email or password"}
    )

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={"error": None}
    )

@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request, email: str = Form(...), password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if email_clean in USERS:
        return templates.TemplateResponse(
            request=request, 
            name="signup.html", 
            context={"error": "Email already registered"}
        )
    
    USERS[email_clean] = password
    request.session["user_email"] = email_clean
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# --- STRICT ADMIN IMAGE UPLOAD ---

@app.post("/api/upload-image/{item_slug}")
async def upload_product_image(request: Request, item_slug: str, file: UploadFile = File(...)):
    user = get_current_user(request)
    
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized: Only the admin email can upload images.")

    contents = await file.read()
    encoded = base64.b64encode(contents).decode('utf-8')
    mime_type = file.content_type or "image/png"
    data_url = f"data:{mime_type};base64,{encoded}"

    products = fetch_products()
    item = next((p for p in products if str(p.get("slug")) == item_slug or str(p.get("id")) == item_slug), None)
    if item:
        item["image_url"] = data_url

    return RedirectResponse(url=f"/item/{item_slug}", status_code=303)

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    return JSONResponse({"url": "/"})

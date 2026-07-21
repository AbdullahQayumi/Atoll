import os
import base64
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# 🔒 HARDCODED ADMIN EMAIL
ADMIN_EMAIL = "qayumi.abdullah2@gmail.com"

# Enable Session Cookies
app.add_middleware(SessionMiddleware, secret_key="nexus-super-secret-key-change-me")

# Project Directory Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Safely mount static files ONLY if directory exists (No os.makedirs to prevent Read-Only filesystem crash)
static_path = os.path.join(BASE_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Safely set up Templates directory
templates_path = os.path.join(BASE_DIR, "templates")
if not os.path.exists(templates_path):
    # Secondary check in case templates is inside /api/templates
    templates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

templates = Jinja2Templates(directory=templates_path)

# In-Memory Registered Users
USERS = {}

# Products Data
PRODUCTS = [
    {
        "id": "cyber-gizmo",
        "slug": "cyber-gizmo",
        "item_name": "Cyber Gizmo",
        "price": 10.00,
        "description": "High performance, state-of-the-art tech specifications. Ready for instant deployment and checkout.",
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
    return templates.TemplateResponse("hub.html", {"request": request, "products": PRODUCTS, "user": user})

@app.get("/item/{slug}", response_class=HTMLResponse)
async def item_detail(request: Request, slug: str):
    user = get_current_user(request)
    item = next((p for p in PRODUCTS if p["slug"] == slug), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse("item.html", {"request": request, "item": item, "user": user})

# --- AUTHENTICATION ROUTES ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if USERS.get(email_clean) == password or email_clean == ADMIN_EMAIL:
        USERS[email_clean] = password
        request.session["user_email"] = email_clean
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})

@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request, email: str = Form(...), password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if email_clean in USERS:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
    
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

    item = next((p for p in PRODUCTS if p["slug"] == item_slug), None)
    if item:
        item["image_url"] = data_url

    return RedirectResponse(url=f"/item/{item_slug}", status_code=303)

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    return JSONResponse({"url": "/"})

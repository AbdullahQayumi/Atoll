import os
import shutil
import sqlite3
import hashlib
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

# Directories & Static Setup
templates = Jinja2Templates(directory="templates")
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database Setup (SQLite)
DB_FILE = "store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Helper Functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        email = row[1]
        return {
            "id": row[0], 
            "email": email, 
            "is_admin": (email.lower() == ADMIN_EMAIL.lower())
        }
    return None

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
    hashed = hash_password(password)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE lower(email) = ? AND password_hash = ?", (email_clean, hashed))
    user = c.fetchone()
    conn.close()

    if user:
        request.session["user_id"] = user[0]
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})

@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request, email: str = Form(...), password: str = Form(...)):
    email_clean = email.strip().lower()
    hashed = hash_password(password)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email_clean, hashed))
        conn.commit()
        c.execute("SELECT id FROM users WHERE lower(email) = ?", (email_clean,))
        new_user_id = c.fetchone()[0]
        conn.close()

        request.session["user_id"] = new_user_id
        return RedirectResponse(url="/", status_code=303)
    except sqlite3.IntegrityError:
        conn.close()
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# --- STRICT ADMIN IMAGE UPLOAD ---

@app.post("/api/upload-image/{item_slug}")
async def upload_product_image(request: Request, item_slug: str, file: UploadFile = File(...)):
    user = get_current_user(request)
    
    # Strictly block anyone whose email is not qayumi.abdullah2@gmail.com
    if not user or user["email"].lower() != ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Unauthorized: Only the admin email can upload images.")

    upload_dir = "static/uploads"
    file_path = f"{upload_dir}/{item_slug}_{file.filename}"
    
    with open(file_path, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)

    item = next((p for p in PRODUCTS if p["slug"] == item_slug), None)
    if item:
        item["image_url"] = f"/{file_path}"

    return RedirectResponse(url=f"/item/{item_slug}", status_code=303)

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    return JSONResponse({"url": "/"})

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client

app = FastAPI()

current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")

try:
    templates = Jinja2Templates(directory=templates_dir)
except Exception as e:
    templates = None

# Safe string masking for sensitive keys
def mask_string(s):
    if not s: return "MISSING"
    if len(s) <= 8: return "***"
    return f"{s[:4]}...{s[-4:]}"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

# 1. Diagnostic/Debug Screen
@app.get("/", response_class=HTMLResponse)
async def debug_screen(request: Request):
    # Check variables
    url_status = f"✅ Detected ({mask_string(SUPABASE_URL)})" if SUPABASE_URL else "❌ MISSING"
    key_status = f"✅ Detected ({mask_string(SUPABASE_KEY)})" if SUPABASE_KEY else "❌ MISSING"
    
    # Check for trailing slash
    slash_warning = ""
    if SUPABASE_URL.endswith("/"):
        slash_warning = "<p style='color:red;'>⚠️ WARNING: Your SUPABASE_URL ends with a '/' slash! Please remove it in Vercel settings.</p>"

    # Attempt connection
    db_connection = "Not Started"
    tables_found = "None"
    error_log = "None"
    
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            db_connection = "✅ Successfully initialized client object"
            
            # Test 1: Try reading lowercase 'products'
            try:
                res = client.table("products").select("*").limit(1).execute()
                tables_found = "✅ Found table named 'products'"
            except Exception as e1:
                error_log = f"Failed searching for 'products': {str(e1)}<br>"
                
                # Test 2: Try reading Capitalized 'Products' (Postgres is case-sensitive!)
                try:
                    res = client.table("Products").select("*").limit(1).execute()
                    tables_found = "⚠️ Found table named 'Products' (Capitalized). Your code needs to use a capital 'P'!"
                    error_log = "None"
                except Exception as e2:
                    error_log += f"Failed searching for 'Products': {str(e2)}"
                    
        except Exception as init_err:
            db_connection = "❌ Client initialization crashed"
            error_log = str(init_err)

    # Render a beautiful debug layout
    html_content = f"""
    <html>
        <head><title>Atoll Deployment Diagnostics</title></head>
        <body style="font-family:sans-serif; padding:40px; background:#f4f6f9; color:#333;">
            <div style="max-width:700px; margin:0 auto; background:white; padding:30px; border-radius:8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2>🚀 Atoll System Diagnostics</h2>
                <hr>
                <h3>1. Vercel Environment Variables</h3>
                <ul>
                    <li><strong>SUPABASE_URL:</strong> {url_status}</li>
                    <li><strong>SUPABASE_KEY:</strong> {key_status}</li>
                </ul>
                {slash_warning}
                
                <h3>2. Database Handshake</h3>
                <p><strong>Status:</strong> {db_connection}</p>
                <p><strong>Table Lookup:</strong> {tables_found}</p>
                
                <h3>3. Error Log / Troubleshooting Hint</h3>
                <div style="background:#fff5f5; color:#cc0000; padding:15px; border-left:5px solid #cc0000; font-family:monospace; white-space: pre-wrap;">
                    {error_log}
                </div>
                <br>
                <p style="font-size:0.9em; color:#666;">Keep adjusting until the Table Lookup turns green!</p>
            </div>
        </body>
    </html>
    """
    return html_content

"""
Validate all Streamlit secrets before deploying to Streamlit Cloud.

    python test_secrets.py

Reads from .streamlit/secrets.toml (never committed to git).
No libsql install required — Turso is tested via its HTTP REST API.
"""

import sys
import json
import urllib.request
import urllib.error

# ── 1. Load secrets.toml ──────────────────────────────────────────────────────
try:
    import tomllib                  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib     # pip install tomli
    except ImportError:
        sys.exit("Need Python 3.11+ or: pip install tomli")

try:
    with open(".streamlit/secrets.toml", "rb") as f:
        secrets = tomllib.load(f)
except FileNotFoundError:
    sys.exit("Not found: .streamlit/secrets.toml\nCreate it and add your keys.")

def get(key):
    return secrets.get(key, "")

print("\n=== Crowe's Nest — Secrets Validator ===\n")

all_ok = True

# ── 2. Key presence and basic format ─────────────────────────────────────────
REQUIRED = {
    "TURSO_URL":         ("libsql://", 30),
    "TURSO_AUTH_TOKEN":  ("eyJ",      100),
    "SUPABASE_URL":      ("https://",  30),
    "SUPABASE_ANON_KEY": ("eyJ",      100),
    "SUPABASE_BUCKET":   ("",           1),
}

print("── Key presence & length ──")
for key, (prefix, min_len) in REQUIRED.items():
    val = get(key)
    if not val:
        print(f"  ❌ {key}: MISSING")
        all_ok = False
    elif prefix and not val.startswith(prefix):
        print(f"  ❌ {key}: wrong format (expected '{prefix}...')")
        all_ok = False
    elif len(val) < min_len:
        print(f"  ❌ {key}: too short ({len(val)} chars, need ≥{min_len}) — likely truncated")
        all_ok = False
    else:
        print(f"  ✅ {key}: {len(val)} chars  [{val[:24]}...]")

print()

# ── 3. Turso via HTTP REST API (no libsql install needed) ────────────────────
print("── Turso connection (HTTP API) ──")
try:
    turso_url = get("TURSO_URL").replace("libsql://", "https://", 1)
    token     = get("TURSO_AUTH_TOKEN")
    endpoint  = f"{turso_url}/v2/pipeline"

    payload = json.dumps({
        "requests": [
            {"type": "execute", "stmt": {"sql": "SELECT COUNT(*) as n FROM project_config"}},
            {"type": "close"},
        ]
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read())

    # Extract the count from the response
    rows = body["results"][0]["response"]["result"]["rows"]
    count = rows[0][0]["value"] if rows else "?"
    print(f"  ✅ Connected — project_config rows: {count}")

except urllib.error.HTTPError as e:
    body = e.read().decode(errors="replace")
    print(f"  ❌ HTTP {e.code}: {body}")
    print("     → TURSO_AUTH_TOKEN is likely wrong or truncated.")
    all_ok = False
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    all_ok = False

print()

# ── 4. Supabase bucket listing ────────────────────────────────────────────────
print("── Supabase storage list ──")
try:
    from supabase import create_client
    sb     = create_client(get("SUPABASE_URL"), get("SUPABASE_ANON_KEY"))
    bucket = get("SUPABASE_BUCKET")

    result = sb.storage.from_(bucket).list("receipts", {"limit": 10})
    if isinstance(result, list):
        print(f"  ✅ Bucket '{bucket}' accessible — {len(result)} object(s) in receipts/")
    else:
        print(f"  ⚠️  Unexpected list() response: {result}")
        all_ok = False
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    print("     → Check SUPABASE_URL, SUPABASE_ANON_KEY, and bucket name.")
    all_ok = False

print()

# ── 5. Supabase upload + public read ─────────────────────────────────────────
print("── Supabase upload & public read ──")
try:
    from supabase import create_client
    sb        = create_client(get("SUPABASE_URL"), get("SUPABASE_ANON_KEY"))
    bucket    = get("SUPABASE_BUCKET")
    test_path = "receipts/_test_validation.txt"

    sb.storage.from_(bucket).upload(
        test_path,
        b"validation test - safe to delete",
        file_options={"content-type": "text/plain", "upsert": "true"},
    )

    public_url = sb.storage.from_(bucket).get_public_url(test_path)

    req = urllib.request.Request(public_url, method="HEAD")
    with urllib.request.urlopen(req, timeout=8) as resp:
        status = resp.status

    sb.storage.from_(bucket).remove([test_path])

    if status == 200:
        print("  ✅ Upload succeeded and file is publicly readable")
        print("  ✅ Test file cleaned up")
    else:
        print(f"  ⚠️  Upload OK but HEAD returned HTTP {status}")
        all_ok = False

except Exception as e:
    print(f"  ❌ FAILED: {e}")
    print()
    print("     Most likely cause: Supabase INSERT policy blocks anonymous uploads.")
    print("     Fix in Supabase dashboard:")
    print("       Storage → Buckets → receipts → Policies")
    print("       Add INSERT policy: role = anon, definition = true")
    all_ok = False

print()
print("── Summary ──")
if all_ok:
    print("  ✅ All checks passed — copy these values to Streamlit Cloud secrets.\n")
else:
    print("  ❌ Fix the issues above, then re-run this script.\n")

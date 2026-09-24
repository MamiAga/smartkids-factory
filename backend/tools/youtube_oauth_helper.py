#!/usr/bin/env python3
"""
SmartKids YouTube OAuth Setup & Token Verification Tool
======================================================
Strict Rules Adhered:
1. Pure Python standard library (no pip / external packages required).
2. Never prints raw refresh token to stdout (strictly masked: e.g. 1//****abcd).
3. Reads client_id/client_secret from user-provided Desktop OAuth client JSON.
4. Requests offline access, prompt=consent, and YouTube upload/read scopes.
5. Verifies channel identity via GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true.
6. Saves raw tokens ONLY to git-ignored local file with 0600 permissions.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def mask_token(token: str) -> str:
    """Masks sensitive token showing only prefix and suffix."""
    if not token:
        return "[EMPTY]"
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}****{token[-4:]}"

def parse_client_secret(file_path: str):
    """Loads client_id and client_secret from Google Desktop or Web client JSON."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Client secret file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    config = data.get("installed") or data.get("web")
    if not config:
        raise ValueError("Invalid client JSON format. Expected 'installed' or 'web' root key.")
    
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    redirect_uris = config.get("redirect_uris", [])
    
    if not client_id or not client_secret:
        raise ValueError("client_id or client_secret missing from JSON.")
    
    return client_id, client_secret, redirect_uris

class OAuthCallbackServer:
    """Lightweight local HTTP server to capture OAuth redirect code."""
    def __init__(self, port=8088):
        self.port = port
        self.code = None
        self.server = None
        self.thread = None

    def start(self):
        handler_self = self
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                if "code" in params:
                    handler_self.code = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<h1>SmartKids OAuth Successful!</h1><p>You can return to the terminal now.</p>")
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    err = params.get("error", ["Unknown error"])[0]
                    self.wfile.write(f"<h1>OAuth Failed: {err}</h1>".encode("utf-8"))

            def log_message(self, format, *args):
                pass

        try:
            self.server = HTTPServer(("127.0.0.1", self.port), CallbackHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return True
        except Exception:
            return False

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

def build_auth_url(client_id: str, redirect_uri: str, scopes: list) -> str:
    """Builds authorization URL with offline access and prompt=consent."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true"
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str):
    """Exchanges authorization code for access_token and refresh_token."""
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Token Exchange Error ({e.code}): {err_body}")

def test_youtube_channel_identity(access_token: str):
    """Tests GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true."""
    url = f"{YOUTUBE_CHANNELS_URL}?part=snippet&mine=true"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"YouTube Channels API Error ({e.code}): {err_body}")

def refresh_access_token(client_id: str, client_secret: str, refresh_token: str):
    """Verifies that the refresh token can successfully obtain a new access_token."""
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Token Refresh Test Error ({e.code}): {err_body}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SmartKids YouTube OAuth Setup Tool")
    parser.add_argument("--client-secret-file", "-f", default="client_secret.json",
                        help="Path to Google Desktop OAuth client JSON (default: client_secret.json)")
    parser.add_argument("--port", "-p", type=int, default=8088,
                        help="Local callback server port (default: 8088)")
    parser.add_argument("--redirect-uri", "-r", default=None,
                        help="Explicit redirect URI (default: http://localhost:<port>/)")
    parser.add_argument("--auth-code", "-c", default=None,
                        help="Provide authorization code directly (skips interactive browser prompt)")
    parser.add_argument("--test-token-file", "-t", default=None,
                        help="Test channel identity using an existing token JSON file")
    args = parser.parse_args()

    print("=" * 70)
    print(" SmartKids YouTube OAuth Setup & Channel Verification")
    print("=" * 70)

    # Mode A: Test existing token file if requested
    if args.test_token_file:
        print(f"\n[1/3] Reading existing token file: {args.test_token_file}")
        with open(args.test_token_file, "r", encoding="utf-8") as tf:
            tok_data = json.load(tf)
        acc_token = tok_data.get("access_token")
        ref_token = tok_data.get("refresh_token")
        c_id = tok_data.get("client_id")
        c_sec = tok_data.get("client_secret")

        if not acc_token and ref_token and c_id and c_sec:
            print("[INFO] Access token missing or expired. Refreshing using refresh_token...")
            ref_resp = refresh_access_token(c_id, c_sec, ref_token)
            acc_token = ref_resp["access_token"]
            print(f"[OK] New access_token acquired (expires in: {ref_resp.get('expires_in')}s)")

        print("\n[2/3] Calling YouTube Channels API (GET .../channels?part=snippet&mine=true)...")
        ch_data = test_youtube_channel_identity(acc_token)
        items = ch_data.get("items", [])
        if not items:
            print("[WARNING] Call succeeded but no channel was found for this Google account.")
            print("Please ensure your Google account has a YouTube channel created.")
            sys.exit(1)
        
        channel = items[0]
        snippet = channel.get("snippet", {})
        print("\n[3/3] CHANNEL VERIFICATION RESULT:")
        print(f"  Channel ID:    {channel.get('id')}")
        print(f"  Channel Title: {snippet.get('title')}")
        print(f"  Custom URL:    {snippet.get('customUrl', 'N/A')}")
        print(f"  Published At:  {snippet.get('publishedAt')}")
        print(f"  Refresh Token: {mask_token(ref_token)}")
        print("\nYOUTUBE_OAUTH_VERIFIED=true")
        return

    # Mode B: Full OAuth flow from client secret JSON
    if not os.path.exists(args.client_secret_file):
        print(f"\n[ERROR] Client JSON file not found: {args.client_secret_file}")
        print("\nPlease follow these steps:")
        print("  1. Place your downloaded Google OAuth Desktop Client JSON file at:")
        print(f"     {os.path.abspath(args.client_secret_file)}")
        print("  2. Run this script again:")
        print(f"     python3 backend/tools/youtube_oauth_helper.py --client-secret-file {args.client_secret_file}")
        print("\nNote: .gitignore has already been updated to ensure client_secret*.json is NEVER committed to git.")
        sys.exit(1)

    try:
        client_id, client_secret, json_redirects = parse_client_secret(args.client_secret_file)
    except Exception as e:
        print(f"\n[ERROR] Failed to parse {args.client_secret_file}: {e}")
        sys.exit(1)

    redirect_uri = args.redirect_uri
    if not redirect_uri:
        if 'http://localhost' in json_redirects:
            redirect_uri = 'http://localhost'
        else:
            redirect_uri = f'http://localhost:{args.port}/' 
    auth_url = build_auth_url(client_id, redirect_uri, DEFAULT_SCOPES)

    code = args.auth_code
    if code:
        if 'code=' in code:
            parsed = urllib.parse.urlparse(code)
            qs = urllib.parse.parse_qs(parsed.query)
            code = qs.get('code', [code])[0]

    if not code:
        cb_server = OAuthCallbackServer(port=args.port)
        server_started = cb_server.start()
        
        print("\n" + "-" * 70)
        print("STEP 1: Open the following URL in your browser to authorize:")
        print("-" * 70)
        print(auth_url)
        print("-" * 70)
        
        if server_started:
            print(f"[INFO] Local callback listener running at {redirect_uri}")
            print("After granting permission in your browser, Google will redirect.")
            print("If your browser is on another machine or cannot connect to localhost,")
            print("simply COPY the 'code' parameter (or the full redirect URL) from your browser address bar.")
        
        print("\nEnter the authorization code (or paste the full redirected URL):")
        try:
            while not cb_server.code and not code:
                user_input = input("Code or URL > ").strip()
                if user_input:
                    if "code=" in user_input:
                        parsed = urllib.parse.urlparse(user_input)
                        qs = urllib.parse.parse_qs(parsed.query)
                        code = qs.get("code", [user_input])[0]
                    else:
                        code = user_input
                    break
                if cb_server.code:
                    code = cb_server.code
                    break
        except (KeyboardInterrupt, EOFError):
            print("\nAborted by user.")
            cb_server.stop()
            sys.exit(1)
        finally:
            cb_server.stop()

    if not code:
        print("[ERROR] No authorization code received.")
        sys.exit(1)

    print("\nSTEP 2: Exchanging code for tokens...")
    try:
        token_response = exchange_code_for_tokens(client_id, client_secret, code, redirect_uri)
    except Exception as e:
        print(f"[ERROR] Token exchange failed: {e}")
        sys.exit(1)

    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in")
    granted_scope = token_response.get("scope", "")

    if not access_token:
        print("[ERROR] Google did not return an access_token.")
        sys.exit(1)

    print("\nSTEP 3: Verifying Token Properties:")
    print(f"  Access Token:     {mask_token(access_token)} (Length: {len(access_token)})")
    if refresh_token:
        print(f"  Refresh Token:    {mask_token(refresh_token)} (Length: {len(refresh_token)}) [OK]")
    else:
        print("  Refresh Token:    [NOT RETURNED] (Ensure prompt=consent is used and access_type=offline)")
    print(f"  Expires In:       {expires_in} seconds (~{round(expires_in/60, 1)} minutes)")
    print(f"  Granted Scope:    {granted_scope}")

    # Step 4: Testing YouTube Channel Identity
    print("\nSTEP 4: Testing YouTube API (GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true)...")
    try:
        ch_resp = test_youtube_channel_identity(access_token)
        items = ch_resp.get("items", [])
        if not items:
            print("\n[WARNING] API call succeeded (HTTP 200), but 0 channels were returned for this account.")
            print("Please open https://www.youtube.com and create a channel for this Google account.")
        else:
            ch = items[0]
            snippet = ch.get("snippet", {})
            print("\n" + "=" * 70)
            print(" YOUTUBE CHANNEL IDENTITY VERIFIED:")
            print("=" * 70)
            print(f"  Channel ID:    {ch.get('id')}")
            print(f"  Channel Title: {snippet.get('title')}")
            print(f"  Custom URL:    {snippet.get('customUrl', 'N/A')}")
            print(f"  Created At:    {snippet.get('publishedAt')}")
            print("=" * 70)
            print("\nYOUTUBE_OAUTH_VERIFIED=true\n")
    except Exception as e:
        print(f"\n[ERROR] YouTube API verification failed: {e}")
        sys.exit(1)

    # Save to local token JSON (strictly ignored in git)
    save_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "access_token": access_token,
        "expires_in": expires_in,
        "granted_scope": granted_scope,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    
    out_file = "token_youtube_offline.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = 0o600  # Only readable by current user
    fd = os.open(out_file, flags, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    
    print(f"[SECURITY] Raw tokens saved securely to local file (0600 permissions):")
    print(f"           {os.path.abspath(out_file)}")
    print("           (Matches 'token*.json' in .gitignore and will never be committed to git)")

if __name__ == "__main__":
    main()

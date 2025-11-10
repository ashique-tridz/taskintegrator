import frappe
import requests
from frappe.utils import now


# -----------------------------------------------------
# 1️⃣ START AUTHORIZATION
# -----------------------------------------------------
@frappe.whitelist(allow_guest=True)
def start_auth():
    """
    Redirects the user to Asana's OAuth authorization URL.
    """
    state = frappe.local.session.data.get("csrf_token")

    settings_list = frappe.get_all(
        "Integration Settings",
        filters={"enabled": True, "integration_name": "Asana"},
        limit_page_length=1
    )
    if not settings_list:
        frappe.throw("Integration Settings for Asana not found or disabled")

    settings = frappe.get_doc("Integration Settings", settings_list[0].name)

    asana_auth_url = (
        "https://app.asana.com/-/oauth_authorize"
        f"?response_type=code"
        f"&client_id={settings.client_id}"
        f"&redirect_uri={settings.redirect_uri}"
        f"&state={state}"
        f"&scope=default"
    )

    # Redirect to Asana
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = asana_auth_url


# -----------------------------------------------------
# 2️⃣ OAUTH CALLBACK (EXCHANGE CODE → TOKENS)
# -----------------------------------------------------
@frappe.whitelist(allow_guest=True)
def oauth_callback():
    """
    Handles OAuth callback from Asana, exchanges authorization code for tokens.
    """
    args = frappe.local.request.args
    code = args.get("code")
    state = args.get("state")

    if not code:
        return "Authorization code missing."

    session_state = frappe.local.session.data.get("csrf_token")
    # Optionally verify state for CSRF protection
    # if not state or state != session_state:
    #     return "Invalid or missing state parameter."

    settings_list = frappe.get_all(
        "Integration Settings",
        filters={"enabled": True, "integration_name": "Asana"},
        limit_page_length=1
    )
    if not settings_list:
        return "Integration Settings not found or disabled."

    settings = frappe.get_doc("Integration Settings", settings_list[0].name)

    token_url = "https://app.asana.com/-/oauth_token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "redirect_uri": settings.redirect_uri,
        "code": code
    }

    resp = requests.post(token_url, data=payload)
    if not resp.ok:
        return f"Token exchange failed: {resp.text}"

    token_data = resp.json()

    # Save tokens in Integration Settings
    settings.access_token = token_data.get("access_token")
    settings.refresh_token = token_data.get("refresh_token")
    settings.last_sync = now()
    settings.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.msgprint("Asana OAuth setup completed successfully.")
    return "OAuth connection successful!"


# -----------------------------------------------------
# 3️⃣ REFRESH ACCESS TOKEN
# -----------------------------------------------------
@frappe.whitelist()
def refresh_asana_token():
    """
    Refresh the Asana OAuth access token using the stored refresh_token.
    """
    settings_list = frappe.get_all(
        "Integration Settings",
        filters={"enabled": True, "integration_name": "Asana"},
        limit_page_length=1
    )
    if not settings_list:
        frappe.throw("Integration Settings for Asana not found or disabled")

    settings = frappe.get_doc("Integration Settings", settings_list[0].name)

    if not settings.refresh_token:
        frappe.throw("Refresh token not found. Please reconnect Asana OAuth.")

    token_url = "https://app.asana.com/-/oauth_token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "refresh_token": settings.refresh_token,
    }

    resp = requests.post(token_url, data=payload)
    if not resp.ok:
        frappe.throw(f"Failed to refresh access token: {resp.text}")

    token_data = resp.json()

    # Update Integration Settings with new tokens
    settings.access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token")
    if new_refresh_token:
        settings.refresh_token = new_refresh_token

    settings.last_sync = now()
    settings.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.msgprint("Asana access token refreshed successfully.")
    return {
        "access_token": settings.access_token,
        "refresh_token": settings.refresh_token,
        "expires_in": token_data.get("expires_in")
    }


# -----------------------------------------------------
# 4️⃣ SAFE REQUEST HELPER (AUTO-REFRESH ON 401)
# -----------------------------------------------------
def get_asana_headers():
    """
    Returns the current Asana API authorization headers.
    """
    settings = frappe.get_doc("Integration Settings", {"integration_name": "Asana"})
    return {"Authorization": f"Bearer {settings.access_token}"}


def safe_asana_request(url, method="GET", **kwargs):
    """
    Makes a safe Asana API request that auto-refreshes tokens if expired.
    """
    headers = get_asana_headers()
    response = requests.request(method, url, headers=headers, **kwargs)

    # Handle expired token (401 Unauthorized)
    if response.status_code == 401:
        frappe.logger().warning("Asana token expired — refreshing...")
        refresh_asana_token()
        headers = get_asana_headers()
        response = requests.request(method, url, headers=headers, **kwargs)

    return response


# -----------------------------------------------------
# 5️⃣ EXAMPLE: FETCH ASANA USER PROFILE
# -----------------------------------------------------
@frappe.whitelist()
def get_asana_user():
    """
    Example function: Fetch the authenticated Asana user's details.
    """
    url = "https://app.asana.com/api/1.0/users/me"
    resp = safe_asana_request(url)
    if not resp.ok:
        frappe.throw(f"Failed to fetch user: {resp.text}")
    
    print(resp.json())

    return resp.json()

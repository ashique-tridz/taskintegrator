import frappe
import requests
import uuid

from frappe.utils import now

@frappe.whitelist(allow_guest=True)
def start_auth():
    """
    Redirect user to Asana OAuth authorize URL directly (no JSON response).
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

    # Return an HTTP redirect (Frappe will set status=302)
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = asana_auth_url


import requests

@frappe.whitelist(allow_guest=True)
def oauth_callback():
    """
    Handle OAuth callback from Asana, exchange code for access token, and save tokens.
    """

    args = frappe.local.request.args
    code = args.get("code")
    state = args.get("state")

    if not code:
        return "Authorization code missing."

    session_state = frappe.local.session.data.get("csrf_token")

    # if not state or state != session_state:
    #     return "Invalid or missing state parameter."

    # Fetch integration settings
    settings_list = frappe.get_all("Integration Settings", filters={"enabled": True, "integration_name": "Asana"}, limit_page_length=1)
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

    # Save tokens securely in Integration Settings
    settings.access_token = token_data.get("access_token")
    settings.refresh_token = token_data.get("refresh_token")
    settings.last_sync = now()
    settings.save()
    frappe.db.commit()

    frappe.msgprint("OAuth setup completed successfully.")
    return
    # Redirect to a integration settings page
    # redirect_url = f"app/integration-settings/"
    # redirect_url = f"app/integration-settings/{settings.name}"
    # return frappe.local.response.update({"type": "redirect", "location": redirect_url})
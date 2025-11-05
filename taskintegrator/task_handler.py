# taskintegrator/asana_handler.py
import frappe
import requests
from urllib.parse import urljoin

class TaskHandler:
    def __init__(self, integration_settings_doc):
        self.settings = integration_settings_doc
        if not self.settings.base_url:
            raise ValueError("Base URL missing in Integration Settings")
        if self.settings.integration_name == "Asana":
            self.base_url = self.settings.base_url or "https://app.asana.com/api/1.0"
        self.base_url = self.settings.base_url
        self.token = self.settings.api_token
        if not self.token:
            raise ValueError("Asana API token missing in Integration Settings")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    def get_tasks(self, modified_since=None, limit=100):
        """Return list of tasks modified since datetime (ISO8601 str)."""
        params = {}
        if self.settings.workspace_gid:
            params["workspace"] = self.settings.workspace_gid
        if modified_since:
            params["modified_since"] = modified_since  # Asana accepts ISO8601
        params["limit"] = limit

        url = urljoin(self.base_url + "/", "tasks")
        frappe.logger("taskintegrator").info(f"Asana get_tasks URL: {url} params:{params}")
        r = requests.get(url, headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Asana returns list under 'data'
        return data.get("data", [])

    def get_task_details(self, gid, opt_fields=None):
        opt_fields = opt_fields or ["name","notes","due_on","completed","modified_at","assignee","gid"]
        params = {"opt_fields": ",".join(opt_fields)}
        url = urljoin(self.base_url + "/", f"tasks/{gid}")
        r = requests.get(url, headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("data")

import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from .constants import JIRA_SERVER_URL, JIRA_USERNAME, JIRA_API_TOKEN, JIRA_PROJECT_KEY

load_dotenv()


class JiraConnection:
    def __init__(self):
        self.server_url = JIRA_SERVER_URL
        self.auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)
        self.project_key = JIRA_PROJECT_KEY
        self.base_url = f"{self.server_url}/rest/api/3"

        # Verify connection
        self._verify_connection()

    def _verify_connection(self):
        """Verify JIRA connection and project access."""
        try:
            response = requests.get(f"{self.base_url}/project/{self.project_key}", auth=self.auth, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to JIRA: {e}") from e

    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to JIRA API."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        response = requests.request(
            method=method, url=url, auth=self.auth, headers=headers, json=data, params=params, timeout=30
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        if response.content:
            return response.json()
        return None

    def _search_issues(self, jql, fields=None, max_results=50):
        """Search for issues using JQL."""
        data = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields or ["summary", "description", "status", "issuetype"],
        }

        result = self._make_request("POST", "/search", data=data)
        return result.get("issues", []) if result else []

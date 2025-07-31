import datetime

from .connection import JiraConnection
from .constants import ISSUE_TYPE_TASK, STATUS_TODO
from .exceptions import TaskNotFoundError


class CoreTaskOperations:
    def __init__(self, connection: JiraConnection):
        self.connection = connection

    def add_task(self, project_name, title, description):
        """Create a new task/issue in the project."""
        data = {
            "fields": {
                "project": {"key": self.connection.project_key},
                "issuetype": {"name": ISSUE_TYPE_TASK},
                "summary": title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
                },
            }
        }

        result = self.connection._make_request("POST", "/issue", data=data)
        issue_key = result["key"] if result else None

        return result, f"Added new task '{title}' to {project_name} (Key: {issue_key})"

    def get_next_task(self, project_name):
        """Retrieve the next available task not in progress or completed."""
        jql = (
            f'project = {self.connection.project_key} AND status = "{STATUS_TODO}" ORDER BY priority DESC, created ASC'
        )
        issues = self.connection._search_issues(jql, max_results=1)

        if issues:
            issue = issues[0]
            return issue, f"Next available task: {issue['fields']['summary']} - {self._get_description_text(issue)}"

        return None, f"No available tasks found in '{project_name}'."

    def update_task_description(self, project_name, title, description):
        """Update the task's description."""
        # Find the issue by title
        jql = f'project = {self.connection.project_key} AND summary ~ "{title}"'
        issues = self.connection._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        issue = issues[0]
        issue_key = issue["key"]

        # Get current description
        current_description = self._get_description_text(issue)

        # Add timestamp and new description
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if current_description:
            updated_description = f"{current_description}\n\n--- Updated on {timestamp} ---\n{description}"
        else:
            updated_description = f"--- Created on {timestamp} ---\n{description}"

        # Update the issue
        data = {
            "fields": {
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": updated_description}]}],
                }
            }
        }

        self.connection._make_request("PUT", f"/issue/{issue_key}", data=data)

        return issue, f"Description updated for task '{title}' in project '{project_name}'."

    def _get_description_text(self, issue):
        """Extract plain text from JIRA description format."""
        description = issue["fields"].get("description")
        if not description:
            return ""

        # Extract text from Atlassian Document Format
        text_parts = []
        if "content" in description:
            for content_block in description["content"]:
                if content_block.get("type") == "paragraph" and "content" in content_block:
                    for text_node in content_block["content"]:
                        if text_node.get("type") == "text":
                            text_parts.append(text_node.get("text", ""))

        return " ".join(text_parts)

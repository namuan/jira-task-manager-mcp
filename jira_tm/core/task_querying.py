from .connection import JiraConnection
from .constants import STATUS_DONE, STATUS_IN_PROGRESS


class TaskQueryManager:
    def __init__(self, connection: JiraConnection):
        self.connection = connection

    def get_tasks(self, project_name, filter_type="all"):
        """Retrieve tasks with filters like all, WIP, done."""
        # Build JQL based on filter
        base_jql = f"project = {self.connection.project_key}"

        if filter_type == "wip":
            jql = f'{base_jql} AND status = "{STATUS_IN_PROGRESS}"'
        elif filter_type == "done":
            jql = f'{base_jql} AND status = "{STATUS_DONE}"'
        else:  # all
            jql = base_jql

        issues = self.connection._search_issues(jql)

        # Convert to task dictionaries
        filtered_tasks = []
        for issue in issues:
            status = issue["fields"]["status"]["name"]
            task_dict = {
                "name": issue["fields"]["summary"],
                "description": self._get_description_text(issue),
                "status": self._normalize_status(status),
                "id": issue["key"],
            }
            filtered_tasks.append(task_dict)

        message = self._generate_result_message(filtered_tasks, filter_type, project_name)
        return filtered_tasks, message

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

    def _normalize_status(self, jira_status):
        """Normalize JIRA status to internal status format."""
        if jira_status == STATUS_DONE:
            return "done"
        elif jira_status == STATUS_IN_PROGRESS:
            return "wip"
        else:
            return "todo"

    def _generate_result_message(self, filtered_tasks, filter_type, project_name):
        """Generate appropriate result message based on filter and results."""
        if not filtered_tasks:
            no_tasks_messages = {
                "all": f"No tasks found in project '{project_name}'.",
                "wip": f"No work in progress tasks found in project '{project_name}'.",
                "done": f"No completed tasks found in project '{project_name}'.",
            }
            return no_tasks_messages.get(
                filter_type, f"No tasks found with filter '{filter_type}' in project '{project_name}'."
            )
        else:
            task_count = len(filtered_tasks)
            found_tasks_messages = {
                "all": f"Found {task_count} task(s) in project '{project_name}'.",
                "wip": f"Found {task_count} work in progress task(s) in project '{project_name}'.",
                "done": f"Found {task_count} completed task(s) in project '{project_name}'.",
            }
            return found_tasks_messages.get(
                filter_type, f"Found {task_count} task(s) with filter '{filter_type}' in project '{project_name}'"
            )

    def delete_all_tasks(self, project_name: str) -> str:
        """Delete all tasks in a project."""
        # Search all issues in the project
        jql = f"project = {self.connection.project_key}"
        issues = self.connection._search_issues(jql, max_results=1000)

        deleted_count = 0
        for issue in issues:
            issue_key = issue["key"]
            # Delete with subtasks
            self.connection._make_request("DELETE", f"/issue/{issue_key}?deleteSubtasks=true")
            deleted_count += 1

        return f"All {deleted_count} tasks in project '{project_name}' have been deleted."

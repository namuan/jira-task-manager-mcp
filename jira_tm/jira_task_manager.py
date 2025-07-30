import datetime
import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_SERVER_URL = os.getenv("JIRA_SERVER_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Status mappings
STATUS_TODO = "To Do"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"

# Issue types
ISSUE_TYPE_TASK = "Task"
ISSUE_TYPE_SUBTASK = "Sub-task"


class TaskNotFoundError(Exception):
    def __init__(self, project_name, title):
        self.project_name = project_name
        self.title = title
        super().__init__(f"Task '{title}' not found in project '{project_name}'.")


class ChecklistNotFoundError(Exception):
    def __init__(self, checklist_name, title):
        self.checklist_name = checklist_name
        self.title = title
        super().__init__(f"Checklist '{checklist_name}' not found for task '{title}'.")


class ChecklistItemNotFoundError(Exception):
    def __init__(self, title):
        self.title = title
        super().__init__(f"No unchecked checklist items found for task '{title}'.")


class JiraTaskManager:
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

    def _get_transitions(self, issue_key):
        """Get available transitions for an issue."""
        result = self._make_request("GET", f"/issue/{issue_key}/transitions")
        return result.get("transitions", []) if result else []

    def _transition_issue(self, issue_key, transition_id):
        """Transition an issue to a new status."""
        data = {"transition": {"id": transition_id}}
        return self._make_request("POST", f"/issue/{issue_key}/transitions", data=data)

    def _find_transition_id(self, issue_key, target_status):
        """Find transition ID for target status."""
        transitions = self._get_transitions(issue_key)
        for transition in transitions:
            if transition["to"]["name"] == target_status:
                return transition["id"]
        return None

    def add_task(self, project_name, title, description):
        """Create a new task/issue in the project."""
        data = {
            "fields": {
                "project": {"key": self.project_key},
                "issuetype": {"name": ISSUE_TYPE_TASK},
                "summary": title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
                },
            }
        }

        result = self._make_request("POST", "/issue", data=data)
        issue_key = result["key"] if result else None

        return result, f"Added new task '{title}' to {project_name} (Key: {issue_key})"

    def get_next_task(self, project_name):
        """Retrieve the next available task not in progress or completed."""
        jql = f'project = {self.project_key} AND status = "{STATUS_TODO}" ORDER BY priority DESC, created ASC'
        issues = self._search_issues(jql, max_results=1)

        if issues:
            issue = issues[0]
            return issue, f"Next available task: {issue['fields']['summary']} - {self._get_description_text(issue)}"

        return None, f"No available tasks found in '{project_name}'."

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

    def mark_as_in_progress(self, project_name, title):
        """Transition task to 'In Progress' status."""
        # Find the issue by title
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        issue = issues[0]
        issue_key = issue["key"]

        # Find transition ID for "In Progress"
        transition_id = self._find_transition_id(issue_key, STATUS_IN_PROGRESS)
        if not transition_id:
            return issue, f"Cannot transition task '{title}' to In Progress (transition not available)"

        # Perform transition
        self._transition_issue(issue_key, transition_id)

        return issue, f"Task '{title}' in project '{project_name}' marked as in progress."

    def mark_as_completed(self, project_name, title):
        """Transition task to 'Done' status."""
        # Find the issue by title
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        issue = issues[0]
        issue_key = issue["key"]

        # Find transition ID for "Done"
        transition_id = self._find_transition_id(issue_key, STATUS_DONE)
        if not transition_id:
            return issue, f"Cannot transition task '{title}' to Done (transition not available)"

        # Perform transition
        self._transition_issue(issue_key, transition_id)

        return issue, f"Task '{title}' in project '{project_name}' has been completed."

    def update_task_description(self, project_name, title, description):
        """Update the task's description."""
        # Find the issue by title
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

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

        self._make_request("PUT", f"/issue/{issue_key}", data=data)

        return issue, f"Description updated for task '{title}' in project '{project_name}'."

    def update_task_with_checklist(self, project_name, title, checklist_items):
        """Add or append checklist items as subtasks."""
        # Find the parent issue by title
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        parent_issue = issues[0]
        parent_key = parent_issue["key"]

        # Create subtasks for each checklist item
        created_subtasks = []
        for item in checklist_items:
            data = {
                "fields": {
                    "project": {"key": self.project_key},
                    "parent": {"key": parent_key},
                    "issuetype": {"name": ISSUE_TYPE_SUBTASK},
                    "summary": item,
                }
            }

            result = self._make_request("POST", "/issue", data=data)
            if result:
                created_subtasks.append(result["key"])

        return (
            parent_issue,
            f"Created {len(created_subtasks)} checklist items as subtasks for task '{title}' in project '{project_name}'.",
        )

    def complete_checklist_item(self, project_name, title, checklist_item_name):
        """Complete a checklist item (transition subtask to 'Done')."""
        # Find the parent issue
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        parent_key = issues[0]["key"]

        # Find the subtask by name
        jql = f'parent = {parent_key} AND summary ~ "{checklist_item_name}"'
        subtasks = self._search_issues(jql, max_results=1)

        if not subtasks:
            raise ChecklistNotFoundError(checklist_item_name, title)

        subtask = subtasks[0]
        subtask_key = subtask["key"]

        # Find transition ID for "Done"
        transition_id = self._find_transition_id(subtask_key, STATUS_DONE)
        if not transition_id:
            return subtask, f"Cannot complete checklist item '{checklist_item_name}' (transition not available)"

        # Perform transition
        self._transition_issue(subtask_key, transition_id)

        return (
            subtask,
            f"Checklist item '{checklist_item_name}' in task '{title}' in project '{project_name}' completed.",
        )

    def get_next_unchecked_checklist_item(self, project_name, title):
        """Get the first incomplete checklist item/subtask."""
        # Find the parent issue
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        parent_key = issues[0]["key"]

        # Find incomplete subtasks
        jql = f'parent = {parent_key} AND status != "{STATUS_DONE}" ORDER BY created ASC'
        subtasks = self._search_issues(jql, max_results=1)

        if not subtasks:
            raise ChecklistItemNotFoundError(title)

        subtask = subtasks[0]
        item_name = subtask["fields"]["summary"]

        return subtask, f"Next unchecked checklist item for task '{title}': {item_name}"

    def get_tasks(self, project_name, filter_type="all"):
        """Retrieve tasks with filters like all, WIP, done."""
        # Build JQL based on filter
        base_jql = f"project = {self.project_key}"

        if filter_type == "wip":
            jql = f'{base_jql} AND status = "{STATUS_IN_PROGRESS}"'
        elif filter_type == "done":
            jql = f'{base_jql} AND status = "{STATUS_DONE}"'
        else:  # all
            jql = base_jql

        issues = self._search_issues(jql)

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

    def get_task_status(self, project_name, title):
        """Get the current status of a task."""
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        issue = issues[0]
        status = issue["fields"]["status"]["name"]

        return issue, f"Task '{title}' status: {status}"

    def set_task_status(self, project_name, title, target_status):
        """Set a specific status for a task."""
        # Find the issue by title
        jql = f'project = {self.project_key} AND summary ~ "{title}"'
        issues = self._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        issue = issues[0]
        issue_key = issue["key"]

        # Find transition ID for target status
        transition_id = self._find_transition_id(issue_key, target_status)
        if not transition_id:
            return issue, f"Cannot transition task '{title}' to {target_status} (transition not available)"

        # Perform transition
        self._transition_issue(issue_key, transition_id)

        return issue, f"Task '{title}' status set to {target_status}."

    def delete_all_tasks(self, project_name: str) -> str:
        """Delete all tasks in a project."""
        # Search all issues in the project
        jql = f"project = {self.project_key}"
        issues = self._search_issues(jql, max_results=1000)

        deleted_count = 0
        for issue in issues:
            issue_key = issue["key"]
            # Delete with subtasks
            self._make_request("DELETE", f"/issue/{issue_key}?deleteSubtasks=true")
            deleted_count += 1

        return f"All {deleted_count} tasks in project '{project_name}' have been deleted."


if __name__ == "__main__":
    # Testing
    jm = JiraTaskManager()

    project_name = "Test Project"
    new_task_title = f"New Task at {datetime.datetime.now()}"
    jm.add_task(project_name, new_task_title, "This is a test task.")
    t1, _ = jm.get_next_task(project_name)
    print(f"Next task: {t1['fields']['summary'] if t1 else 'None'}")

    if t1:
        jm.update_task_with_checklist(project_name, new_task_title, ["Item 1", "Item 2", "Item 3"])
        print("Checklist set.")

        # Test getting next unchecked item
        _, next_item_msg = jm.get_next_unchecked_checklist_item(project_name, new_task_title)
        print(next_item_msg)

        _, m = jm.complete_checklist_item(project_name, new_task_title, "Item 1")
        print(m)

        # Test getting next unchecked item after completing one
        _, next_item_msg2 = jm.get_next_unchecked_checklist_item(project_name, new_task_title)
        print(next_item_msg2)

        # Test get_tasks with different filters
        print("\n=== Testing 1 method ===")

        # Get all tasks
        all_tasks, msg = jm.get_tasks(project_name, "all")
        print(f"All tasks: {msg}")
        for task in all_tasks:
            print(f"  - {task['name']} (Status: {task['status']})")

        # Mark task as in progress and test WIP filter
        jm.mark_as_in_progress(project_name, new_task_title)
        wip_tasks, msg = jm.get_tasks(project_name, "wip")
        print(f"\nWIP tasks: {msg}")
        for task in wip_tasks:
            print(f"  - {task['name']} (Status: {task['status']})")

        # Complete task and test done filter
        jm.mark_as_completed(project_name, new_task_title)
        done_tasks, msg = jm.get_tasks(project_name, "done")
        print(f"\nCompleted tasks: {msg}")
        for task in done_tasks:
            print(f"  - {task['name']} (Status: {task['status']})")

        # Test next available task
        _, m1 = jm.get_next_task(project_name)
        print(f"\nNext available task: {m1}")

        # Test update_task_description with timestamp preservation
        print("\n=== Testing update_task_description ===")
        test_task_title = f"Description Test Task at {datetime.datetime.now()}"
        jm.add_task(project_name, test_task_title, "Initial description")

        # Update description first time
        jm.update_task_description(project_name, test_task_title, "First update to the description")
        print("First description update completed")

        # Update description second time to test preservation
        jm.update_task_description(project_name, test_task_title, "Second update to the description")
        print("Second description update completed")

        input("Press Enter to continue...")
        jm.delete_all_tasks(project_name)

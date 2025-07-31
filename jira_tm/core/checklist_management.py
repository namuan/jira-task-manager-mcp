from .connection import JiraConnection
from .constants import ISSUE_TYPE_SUBTASK, STATUS_DONE
from .exceptions import TaskNotFoundError, ChecklistNotFoundError, ChecklistItemNotFoundError


class ChecklistManager:
    def __init__(self, connection: JiraConnection):
        self.connection = connection

    def update_task_with_checklist(self, project_name, title, checklist_items):
        """Add or append checklist items as subtasks."""
        # Find the parent issue by title
        jql = f'project = {self.connection.project_key} AND summary ~ "{title}"'
        issues = self.connection._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        parent_issue = issues[0]
        parent_key = parent_issue["key"]

        # Create subtasks for each checklist item
        created_subtasks = []
        for item in checklist_items:
            data = {
                "fields": {
                    "project": {"key": self.connection.project_key},
                    "parent": {"key": parent_key},
                    "issuetype": {"name": ISSUE_TYPE_SUBTASK},
                    "summary": item,
                }
            }

            result = self.connection._make_request("POST", "/issue", data=data)
            if result:
                created_subtasks.append(result["key"])

        return (
            parent_issue,
            f"Created {len(created_subtasks)} checklist items as subtasks for task '{title}' in project '{project_name}'.",
        )

    def complete_checklist_item(self, project_name, title, checklist_item_name):
        """Complete a checklist item (transition subtask to 'Done')."""
        # Find the parent issue
        jql = f'project = {self.connection.project_key} AND summary ~ "{title}"'
        issues = self.connection._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        parent_key = issues[0]["key"]

        # Find the subtask by name
        jql = f'parent = {parent_key} AND summary ~ "{checklist_item_name}"'
        subtasks = self.connection._search_issues(jql, max_results=1)

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
        jql = f'project = {self.connection.project_key} AND summary ~ "{title}"'
        issues = self.connection._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        parent_key = issues[0]["key"]

        # Find incomplete subtasks
        jql = f'parent = {parent_key} AND status != "{STATUS_DONE}" ORDER BY created ASC'
        subtasks = self.connection._search_issues(jql, max_results=1)

        if not subtasks:
            raise ChecklistItemNotFoundError(title)

        subtask = subtasks[0]
        item_name = subtask["fields"]["summary"]

        return subtask, f"Next unchecked checklist item for task '{title}': {item_name}"

    def _find_transition_id(self, issue_key, target_status):
        """Find transition ID for target status."""
        transitions = self._get_transitions(issue_key)
        for transition in transitions:
            if transition["to"]["name"] == target_status:
                return transition["id"]
        return None

    def _get_transitions(self, issue_key):
        """Get available transitions for an issue."""
        result = self.connection._make_request("GET", f"/issue/{issue_key}/transitions")
        return result.get("transitions", []) if result else []

    def _transition_issue(self, issue_key, transition_id):
        """Transition an issue to a new status."""
        data = {"transition": {"id": transition_id}}
        return self.connection._make_request("POST", f"/issue/{issue_key}/transitions", data=data)

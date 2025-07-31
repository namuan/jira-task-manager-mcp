from .connection import JiraConnection
from .constants import STATUS_DONE, STATUS_IN_PROGRESS
from .exceptions import TaskNotFoundError


class TaskStatusManager:
    def __init__(self, connection: JiraConnection):
        self.connection = connection

    def mark_as_in_progress(self, project_name, title):
        """Transition task to 'In Progress' status."""
        return self._set_task_status(project_name, title, STATUS_IN_PROGRESS)

    def mark_as_completed(self, project_name, title):
        """Transition task to 'Done' status."""
        return self._set_task_status(project_name, title, STATUS_DONE)

    def get_task_status(self, project_name, title):
        """Get the current status of a task."""
        jql = f'project = {self.connection.project_key} AND summary ~ "{title}"'
        issues = self.connection._search_issues(jql, max_results=1)

        if not issues:
            raise TaskNotFoundError(project_name, title)

        issue = issues[0]
        status = issue["fields"]["status"]["name"]

        return issue, f"Task '{title}' status: {status}"

    def set_task_status(self, project_name, title, target_status):
        """Set a specific status for a task."""
        return self._set_task_status(project_name, title, target_status)

    def _set_task_status(self, project_name, title, target_status):
        """Internal method to set task status."""
        # Find the issue by title
        jql = f'project = {self.connection.project_key} AND summary ~ "{title}"'
        issues = self.connection._search_issues(jql, max_results=1)

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

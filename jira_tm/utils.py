from .constants import STATUS_TODO, STATUS_IN_PROGRESS, STATUS_DONE


def normalize_status(jira_status):
    """Normalize JIRA status to internal status format."""
    if jira_status == STATUS_DONE:
        return "done"
    elif jira_status == STATUS_IN_PROGRESS:
        return "wip"
    else:
        return "todo"

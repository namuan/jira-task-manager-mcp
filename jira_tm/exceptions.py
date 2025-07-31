# Exception Classes
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

import datetime
from .connection import JiraConnection
from .core_tasks import CoreTaskOperations
from .status_management import TaskStatusManager
from .checklist_management import ChecklistManager
from .task_querying import TaskQueryManager


class JiraTaskManager:
    def __init__(self):
        self.connection = JiraConnection()
        self.core_tasks = CoreTaskOperations(self.connection)
        self.status_manager = TaskStatusManager(self.connection)
        self.checklist_manager = ChecklistManager(self.connection)
        self.query_manager = TaskQueryManager(self.connection)

    # Core Task Operations
    def add_task(self, project_name, title, description):
        """Create a new task/issue in the project."""
        return self.core_tasks.add_task(project_name, title, description)

    def get_next_task(self, project_name):
        """Retrieve the next available task not in progress or completed."""
        return self.core_tasks.get_next_task(project_name)

    def update_task_description(self, project_name, title, description):
        """Update the task's description."""
        return self.core_tasks.update_task_description(project_name, title, description)

    # Task Status Management
    def mark_as_in_progress(self, project_name, title):
        """Transition task to 'In Progress' status."""
        return self.status_manager.mark_as_in_progress(project_name, title)

    def mark_as_completed(self, project_name, title):
        """Transition task to 'Done' status."""
        return self.status_manager.mark_as_completed(project_name, title)

    def get_task_status(self, project_name, title):
        """Get the current status of a task."""
        return self.status_manager.get_task_status(project_name, title)

    def set_task_status(self, project_name, title, target_status):
        """Set a specific status for a task."""
        return self.status_manager.set_task_status(project_name, title, target_status)

    # Checklist Management
    def update_task_with_checklist(self, project_name, title, checklist_items):
        """Add or append checklist items as subtasks."""
        return self.checklist_manager.update_task_with_checklist(project_name, title, checklist_items)

    def complete_checklist_item(self, project_name, title, checklist_item_name):
        """Complete a checklist item (transition subtask to 'Done')."""
        return self.checklist_manager.complete_checklist_item(project_name, title, checklist_item_name)

    def get_next_unchecked_checklist_item(self, project_name, title):
        """Get the first incomplete checklist item/subtask."""
        return self.checklist_manager.get_next_unchecked_checklist_item(project_name, title)

    # Task Querying and Filtering
    def get_tasks(self, project_name, filter_type="all"):
        """Retrieve tasks with filters like all, WIP, done."""
        return self.query_manager.get_tasks(project_name, filter_type)

    def delete_all_tasks(self, project_name: str) -> str:
        """Delete all tasks in a project."""
        return self.query_manager.delete_all_tasks(project_name)


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

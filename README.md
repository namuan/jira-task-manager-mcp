# JIRA Task Manager MCP

LLM Task management System that integrates as an MCP Server and uses JIRA for managing tasks/issues.

[//]: # (TODO: Add Image/Demo Video)

## Features

- Create and manage tasks in JIRA projects
- Update task descriptions
- Mark tasks as in-progress or completed
- Get next available task
- Get filtered list of tasks (all, work-in-progress, or completed)
- Add and manage checklists for tasks (implemented as subtasks)
- Get next unchecked checklist item for focused work

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv)
- A JIRA account with API access (JIRA Cloud or Server)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/namuan/jira-task-manager-mcp.git
   cd jira-task-manager-mcp
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root with your JIRA credentials:

   ```env
   JIRA_SERVER_URL=https://your-domain.atlassian.net
   JIRA_USERNAME=your_jira_username
   JIRA_API_TOKEN=your_jira_api_token
   JIRA_PROJECT_KEY=your_jira_project_key
   HOST=127.0.0.1  # Optional, defaults to 127.0.0.1
   PORT=8050      # Optional, defaults to 8050
   ```

4. Run the application

   ```bash
   jira-task-manager-mcp
   ```

   or

   ```bash
   make run
   ```

## MCP Integration

Add the following entry to your MCP client:

```json
{
  "mcpServers": {
    "jira-task-manager": {
      "type": "sse",
      "url": "http://localhost:8050/sse",
      "note": "For SSE connections, add this URL directly in your MCP Client"
    }
  }
}
```

## Usage

Ask MCP Client to use `JIRA task manager` along with the instructions to use one of these tools.

- `add_task`: Create a new task
- `update_task_description`: Update a task's description
- `get_next_available_task`: Get the next available task
- `get_tasks`: Get a list of tasks with optional filtering (all, wip, done)
- `mark_as_in_progress`: Mark a task as in progress
- `mark_as_completed`: Mark a task as completed
- `update_task_with_checklist`: Add or update a checklist for a task
- `complete_checklist_item`: Mark a specific checklist item as completed
- `get_next_unchecked_checklist_item`: Get the next unchecked checklist item for a task

## Development

### Setup Development Environment

This project uses `uv` for dependency management. Run the following command to set up your development environment:

```bash
make install
```

This will:

- Create a virtual environment using uv
- Install project dependencies
- Set up pre-commit hooks

### Development Commands

The project includes several helpful make commands:

```bash
make help     # Show all available commands with descriptions
make check    # Run code quality tools (lock file check and pre-commit)
make run      # Run the application
make build    # Build wheel file
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

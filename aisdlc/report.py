"""Status report generation for an AISDLC project."""
from __future__ import annotations

from collections import Counter

from .models import Phase, Project


def generate_status_report(project: Project) -> str:
    counts = Counter(t.phase for t in project.tasks)
    lines = [
        f"Status Report: {project.name}",
        "=" * 48,
        f"Tasks total:    {project.total_tasks}",
        f"Completed:      {project.completed_tasks}",
        f"Completion:     {project.completion_percent}%",
        f"Blocked:        {len(project.blocked_tasks)}",
        "",
        "Tasks by phase:",
    ]
    for phase in Phase:
        lines.append(f"  {phase.value:<14} {counts.get(phase, 0)}")
    if project.blocked_tasks:
        lines.append("")
        lines.append("Blocked tasks:")
        for task in project.blocked_tasks:
            lines.append(
                f"  - #{task.id} '{task.title}' at {task.phase.value}: "
                f"{task.blocked_reason}"
            )
    if project.tasks:
        lines.append("")
        lines.append("Task detail:")
        for task in project.tasks:
            lines.append(
                f"  - #{task.id} [{task.status.value}] {task.title} "
                f"(phase={task.phase.value}, assignee={task.assignee})"
            )
    return "\n".join(lines)


def project_summary(project: Project) -> dict:
    """Machine-readable summary, used by tests and future API / UI layers."""
    counts = Counter(t.phase.value for t in project.tasks)
    return {
        "name": project.name,
        "total": project.total_tasks,
        "completed": project.completed_tasks,
        "completion_percent": project.completion_percent,
        "blocked": len(project.blocked_tasks),
        "by_phase": {phase.value: counts.get(phase.value, 0) for phase in Phase},
    }

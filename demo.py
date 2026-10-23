#!/usr/bin/env python3
"""End-to-end demo for the TekunoAI AISDLC Management System.

Run from the repository root:

    python3 demo.py

Creates a sample project, runs every task through the full SDLC pipeline
with the agent coordinator, shows a blocked task when a quality gate fails,
and prints the final status report.
"""
from aisdlc import AgentCoordinator, Project, generate_status_report


def main() -> None:
    print("TekunoAI AISDLC Management System - Demo")
    print("MVP prototype in active development")
    print("=" * 48)
    print()

    project = Project(
        name="AISDLC Platform MVP",
        description="Core pipeline for the TekunoAI AISDLC product",
    )
    project.create_task(
        "Agent task assignment",
        description="Coordinator assigns each task to a phase-specific agent.",
        priority="high",
        acceptance_criteria=[
            "Task is assigned to the agent matching its current phase",
            "Assignee is recorded on the task",
        ],
    )
    project.create_task(
        "Quality gate checks",
        description="A task advances only when its phase quality gate passes.",
        priority="critical",
        acceptance_criteria=[
            "Gate failure blocks the task with a recorded reason",
            "Gate pass advances the task to the next phase",
        ],
    )
    project.create_task(
        "Pipeline status dashboard data",
        description="Status report with counts by phase and completion percent.",
        priority="medium",
        acceptance_criteria=[
            "Report lists tasks by phase",
            "Report shows blocked tasks and reasons",
        ],
    )

    coordinator = AgentCoordinator()
    coordinator.run_project(project)

    print("Pipeline events:")
    for event in coordinator.events:
        print(f"  {event}")
    print()

    # Demonstrate gate failure handling: a task with no acceptance criteria
    # must block at the requirements gate instead of advancing.
    print("Blocked-task example:")
    blocked_project = Project(name="Gate Failure Demo")
    bad = blocked_project.create_task(
        "Vague feature request",
        description="",
        priority="low",
        acceptance_criteria=[],
    )
    coordinator2 = AgentCoordinator()
    coordinator2.run_task(bad)
    for event in coordinator2.events:
        print(f"  {event}")
    print(f"  Result: status={bad.status.value}, reason={bad.blocked_reason}")
    print()

    print(generate_status_report(project))
    print()
    print("Demo complete.")


if __name__ == "__main__":
    main()

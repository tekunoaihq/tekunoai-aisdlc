"""Unit tests for the TekunoAI AISDLC prototype. Standard library only."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aisdlc import (
    AgentCoordinator,
    Phase,
    Project,
    Task,
    TaskStatus,
    check_gate,
    generate_status_report,
    project_summary,
)


def make_valid_task(**overrides) -> Task:
    kwargs = dict(
        title="Implement login",
        description="Users can log in with email and password.",
        priority="high",
        acceptance_criteria=["Valid credentials log the user in"],
        estimate_hours=6.0,
    )
    kwargs.update(overrides)
    return Task(**kwargs)


class TestPhases(unittest.TestCase):
    def test_phase_order(self):
        self.assertEqual(
            [p.value for p in Phase],
            [
                "requirements",
                "planning",
                "design",
                "coding",
                "testing",
                "review",
                "deployment",
                "done",
            ],
        )

    def test_next_phase(self):
        self.assertIs(Phase.REQUIREMENTS.next_phase, Phase.PLANNING)
        self.assertIs(Phase.DEPLOYMENT.next_phase, Phase.DONE)
        self.assertIsNone(Phase.DONE.next_phase)


class TestQualityGates(unittest.TestCase):
    def test_requirements_gate_blocks_without_criteria(self):
        task = Task(title="Vague", description="", acceptance_criteria=[])
        result = check_gate(task)
        self.assertFalse(result.passed)
        self.assertIn("no acceptance criteria defined", result.reasons)

    def test_requirements_gate_passes_with_criteria(self):
        self.assertTrue(check_gate(make_valid_task()).passed)

    def test_testing_gate_requires_pass_rate(self):
        task = make_valid_task()
        task.phase = Phase.TESTING
        task.test_pass_rate = 0.5
        self.assertFalse(check_gate(task).passed)
        task.test_pass_rate = 0.95
        self.assertTrue(check_gate(task).passed)


class TestCoordinator(unittest.TestCase):
    def test_assign_task_sets_phase_agent(self):
        task = make_valid_task()
        coordinator = AgentCoordinator()
        assignee = coordinator.assign_task(task)
        self.assertEqual(assignee, "RequirementsAgent")
        self.assertEqual(task.assignee, "RequirementsAgent")

    def test_run_task_completes_valid_task(self):
        task = make_valid_task()
        AgentCoordinator().run_task(task)
        self.assertTrue(task.is_done)
        self.assertEqual(task.status, TaskStatus.DONE)
        self.assertIn("design_doc", task.artifacts)
        self.assertIn("implementation", task.artifacts)
        self.assertIn("release_notes", task.artifacts)
        self.assertGreaterEqual(task.approvals, 1)
        self.assertEqual(task.test_pass_rate, 1.0)

    def test_run_task_blocks_invalid_task(self):
        task = Task(title="Vague", description="", acceptance_criteria=[])
        AgentCoordinator().run_task(task)
        self.assertFalse(task.is_done)
        self.assertEqual(task.status, TaskStatus.BLOCKED)
        self.assertIsNotNone(task.blocked_reason)
        self.assertEqual(task.phase, Phase.REQUIREMENTS)

    def test_run_project_completes_all_valid_tasks(self):
        project = Project(name="Demo")
        project.add_task(make_valid_task(title="Task A"))
        project.add_task(make_valid_task(title="Task B"))
        AgentCoordinator().run_project(project)
        self.assertEqual(project.completed_tasks, 2)
        self.assertEqual(project.completion_percent, 100.0)


class TestReport(unittest.TestCase):
    def test_status_report_and_summary(self):
        project = Project(name="Report Demo")
        project.add_task(make_valid_task(title="Only task"))
        AgentCoordinator().run_project(project)
        report = generate_status_report(project)
        self.assertIn("Report Demo", report)
        self.assertIn("100.0%", report)
        summary = project_summary(project)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["by_phase"]["done"], 1)
        self.assertEqual(summary["blocked"], 0)

    def test_empty_project_report(self):
        project = Project(name="Empty")
        self.assertEqual(project.completion_percent, 0.0)
        self.assertIn("Tasks total:    0", generate_status_report(project))


if __name__ == "__main__":
    unittest.main()

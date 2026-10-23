"""AI agent coordinator for the AISDLC pipeline.

Each SDLC phase has a phase-specific agent. The coordinator assigns tasks
to agents, asks the current phase's agent to do its work, checks the
quality gate, and either advances the task or marks it blocked with the
gate failure reason.

In this MVP the agents' "work" is a deterministic simulation that produces
the artifact / signal the next gate checks for. The agent interface
(`do_work`) is the seam where LLM-backed actions will be plugged in later
without changing the coordinator or the gates.
"""
from __future__ import annotations

from .gates import check_gate
from .models import Phase, Project, Task, TaskStatus


class PhaseAgent:
    """Base agent: one per phase. Subclasses produce that phase's output."""

    phase: Phase = Phase.REQUIREMENTS

    @property
    def name(self) -> str:
        return f"{self.phase.value.capitalize()}Agent"

    def do_work(self, task: Task) -> None:
        raise NotImplementedError


class RequirementsAgent(PhaseAgent):
    phase = Phase.REQUIREMENTS

    def do_work(self, task: Task) -> None:
        # Work is already captured on the task (description + criteria).
        # A future LLM version will draft criteria from a raw request here.
        task.log(f"{self.name}: reviewed requirements")


class PlanningAgent(PhaseAgent):
    phase = Phase.PLANNING

    def do_work(self, task: Task) -> None:
        if task.estimate_hours <= 0:
            # Simple heuristic estimate so planning can complete.
            task.estimate_hours = 4.0 if task.priority in ("low", "medium") else 8.0
        task.log(f"{self.name}: estimated {task.estimate_hours}h")


class DesignAgent(PhaseAgent):
    phase = Phase.DESIGN

    def do_work(self, task: Task) -> None:
        task.artifacts["design_doc"] = (
            f"Design for '{task.title}': components, data flow, and interfaces "
            f"covering {len(task.acceptance_criteria)} acceptance criteria."
        )
        task.log(f"{self.name}: produced design_doc")


class CodingAgent(PhaseAgent):
    phase = Phase.CODING

    def do_work(self, task: Task) -> None:
        task.artifacts["implementation"] = (
            f"Implementation of '{task.title}' per design_doc."
        )
        task.log(f"{self.name}: produced implementation")


class TestingAgent(PhaseAgent):
    phase = Phase.TESTING

    def do_work(self, task: Task) -> None:
        # Deterministic simulated test run for the prototype: tasks with an
        # implementation and acceptance criteria pass their checks.
        if "implementation" in task.artifacts and task.acceptance_criteria:
            task.test_pass_rate = 1.0
        else:
            task.test_pass_rate = 0.5
        task.log(f"{self.name}: test pass rate {task.test_pass_rate:.0%}")


class ReviewAgent(PhaseAgent):
    phase = Phase.REVIEW

    def do_work(self, task: Task) -> None:
        if task.test_pass_rate >= 0.8:
            task.approvals = max(task.approvals, 1)
        task.log(f"{self.name}: approvals={task.approvals}")


class DeploymentAgent(PhaseAgent):
    phase = Phase.DEPLOYMENT

    def do_work(self, task: Task) -> None:
        task.artifacts["release_notes"] = (
            f"Release notes for '{task.title}': shipped per acceptance criteria."
        )
        task.log(f"{self.name}: produced release_notes")


def _default_agents() -> dict[Phase, PhaseAgent]:
    agents: list[PhaseAgent] = [
        RequirementsAgent(),
        PlanningAgent(),
        DesignAgent(),
        CodingAgent(),
        TestingAgent(),
        ReviewAgent(),
        DeploymentAgent(),
    ]
    return {a.phase: a for a in agents}


class AgentCoordinator:
    """Assigns tasks to phase agents and drives them through the pipeline."""

    def __init__(self, agents: dict[Phase, PhaseAgent] | None = None):
        self.agents = agents or _default_agents()
        self.events: list[str] = []

    def _emit(self, message: str) -> None:
        self.events.append(message)

    def assign_task(self, task: Task) -> str:
        """Assign the task to the agent for its current phase."""
        agent = self.agents.get(task.phase)
        assignee = agent.name if agent else "Unassigned"
        task.assignee = assignee
        task.status = TaskStatus.IN_PROGRESS
        self._emit(f"Assigned task #{task.id} '{task.title}' to {assignee}")
        return assignee

    def step_task(self, task: Task) -> bool:
        """Do one phase of work + gate check. Returns True if task advanced."""
        if task.is_done:
            return False
        agent = self.agents.get(task.phase)
        if agent is None:  # DONE has no agent
            return False
        if not task.assignee:
            self.assign_task(task)
        agent.do_work(task)
        result = check_gate(task)
        if result.passed:
            self._emit(
                f"Task #{task.id} passed {task.phase.value} gate"
            )
            task.blocked_reason = None
            task.status = (
                TaskStatus.DONE if task.phase.next_phase is Phase.DONE
                else TaskStatus.IN_PROGRESS
            )
            task.advance()
            # Re-assign to the next phase's agent for the next step.
            if not task.is_done:
                self.assign_task(task)
            return True
        task.status = TaskStatus.BLOCKED
        task.blocked_reason = "; ".join(result.reasons)
        self._emit(
            f"Task #{task.id} BLOCKED at {task.phase.value}: {task.blocked_reason}"
        )
        return False

    def run_task(self, task: Task, max_steps: int = 20) -> Task:
        """Drive one task to DONE or until it blocks."""
        self.assign_task(task)
        steps = 0
        while not task.is_done and task.status is not TaskStatus.BLOCKED:
            if steps >= max_steps:
                task.status = TaskStatus.BLOCKED
                task.blocked_reason = "exceeded max pipeline steps"
                break
            self.step_task(task)
            steps += 1
        return task

    def run_project(self, project: Project) -> Project:
        for task in project.tasks:
            self.run_task(task)
        return project

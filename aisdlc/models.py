"""Core data models for the TekunoAI AISDLC Management System.

Standard library only. Models the SDLC pipeline, its tasks, and projects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import count


class Phase(str, Enum):
    """Ordered software development lifecycle phases."""

    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    DESIGN = "design"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    DONE = "done"

    @property
    def next_phase(self) -> "Phase | None":
        phases = list(Phase)
        idx = phases.index(self)
        return phases[idx + 1] if idx + 1 < len(phases) else None


# Phases a task must pass a quality gate to leave (DONE is terminal).
GATED_PHASES = [p for p in Phase if p is not Phase.DONE]


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


_id_counter = count(1)


@dataclass
class Task:
    title: str
    description: str = ""
    priority: str = "medium"  # low | medium | high | critical
    acceptance_criteria: list[str] = field(default_factory=list)
    estimate_hours: float = 0.0
    assignee: str | None = None

    # Populated as the task moves through the pipeline.
    id: int = field(default_factory=lambda: next(_id_counter))
    phase: Phase = Phase.REQUIREMENTS
    status: TaskStatus = TaskStatus.TODO
    artifacts: dict[str, str] = field(default_factory=dict)
    test_pass_rate: float = 0.0  # 0.0 - 1.0, set during testing
    approvals: int = 0  # set during review
    history: list[str] = field(default_factory=list)
    blocked_reason: str | None = None

    def log(self, message: str) -> None:
        self.history.append(message)

    @property
    def is_done(self) -> bool:
        return self.phase is Phase.DONE

    def advance(self) -> bool:
        """Move to the next phase. Returns False if already DONE."""
        nxt = self.phase.next_phase
        if nxt is None:
            return False
        self.log(f"{self.phase.value} -> {nxt.value}")
        self.phase = nxt
        if nxt is Phase.DONE:
            self.status = TaskStatus.DONE
            self.blocked_reason = None
        return True


@dataclass
class Project:
    name: str
    description: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> Task:
        self.tasks.append(task)
        return task

    def create_task(self, title: str, **kwargs) -> Task:
        return self.add_task(Task(title=title, **kwargs))

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.is_done)

    @property
    def blocked_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status is TaskStatus.BLOCKED]

    @property
    def completion_percent(self) -> float:
        if not self.tasks:
            return 0.0
        return round(100.0 * self.completed_tasks / len(self.tasks), 1)

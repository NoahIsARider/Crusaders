"""The framework base class.

``HMCFramework`` is the abstract contract every framework author implements.
It is deliberately small: you tell the platform *who should be in control of
each step*, and the platform handles the choreography (running steps, recording
handover events, bookkeeping the session) and produces an ``TaskOutcome`` that
downstream evaluators consume.

The IV of the theoretical model -- *dynamic power handover* -- is exactly what
subclasses encode in :meth:`HMCFramework.decide_handover`.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable, Optional

from .adapters import AIModel, Expert
from .core.types import (
    AgentDecision,
    HandoverDirection,
    HandoverEvent,
    HandoverTrigger,
    Role,
    SessionSnapshot,
    StepContext,
    StepOutcome,
    StepSpec,
    TaskOutcome,
    TaskSpec,
)
from .metaknowledge import OrganizationalMetaknowledge
from .policies import HandoverPolicy, PolicyDecision, SessionState

StepEvaluator = Callable[[AgentDecision, StepSpec], bool]
Observer = Callable[[HandoverEvent, StepContext], None]


@dataclass
class HandoverDecision:
    """The framework's verdict for one step."""

    controller: Role
    trigger: HandoverTrigger = HandoverTrigger.POLICY
    reason: str = ""


class HMCFramework:
    """Subclass this to design your own collaboration framework.

    Parameters
    ----------
    name:
        Human-readable identifier, used in reports and traces.
    metaknowledge:
        The organisational meta-knowledge acting as moderator. If omitted a
        neutral default is used.
    policies:
        Optional list of policies. The base ``decide_handover`` consults them
        in order and uses the first that asks for a handover.
    handover_overhead:
        Cost in seconds of transferring control. Defaults to the organisation's
        meta-knowledge budget (or 0.5 s).
    step_evaluator:
        How to judge whether a single step succeeded. Defaults to a heuristic
        on ``quality_estimate``; supply your own to grade against golden data.
    """

    def __init__(
        self,
        name: str = "hmcf",
        metaknowledge: Optional[OrganizationalMetaknowledge] = None,
        policies: Optional[list[HandoverPolicy]] = None,
        handover_overhead: Optional[float] = None,
        step_evaluator: Optional[StepEvaluator] = None,
    ) -> None:
        self.name = name
        self.metaknowledge = metaknowledge or OrganizationalMetaknowledge()
        self.policies = policies or []
        for p in self.policies:
            p.bind(self.metaknowledge)
        self.handover_overhead = (
            self.metaknowledge.handover_overhead_budget()
            if handover_overhead is None
            else handover_overhead
        )
        self.step_evaluator = step_evaluator or _default_step_evaluator
        self._observers: list[Observer] = []

    # -- extension points ------------------------------------------------------

    def decide_handover(self, step: StepContext, session: SessionState) -> HandoverDecision:
        """Return which role should control the given step.

        This is *the* place where your framework's handover logic lives. The
        base implementation runs the configured policies in order and uses the
        first one that asks for a handover; subclasses may override it entirely
        for fully custom behaviour (see the built-in scenarios).
        """
        for policy in self.policies:
            decision: PolicyDecision = policy.decide(step, session)
            if decision.hand_over and decision.direction is not None:
                return HandoverDecision(decision.direction, decision.trigger, decision.reason)
        return HandoverDecision(session.current_controller, reason="keep current controller")

    def before_step(self, step: StepContext, session: SessionState) -> None:
        """Hook called before a step is processed. Override for instrumentation."""

    def after_step(self, outcome: StepOutcome, step: StepContext, session: SessionState) -> None:
        """Hook called after a step is processed. Override for instrumentation."""

    # -- observability ---------------------------------------------------------

    def add_observer(self, observer: Observer) -> "HMCFramework":
        self._observers.append(observer)
        return self

    def _notify(self, event: HandoverEvent, step: StepContext) -> None:
        for observer in self._observers:
            observer(event, step)

    # -- orchestration ---------------------------------------------------------

    def run(
        self,
        task: TaskSpec,
        ai: Optional[AIModel] = None,
        expert: Optional[Expert] = None,
        *,
        clock: Optional[Callable[[], float]] = None,
    ) -> TaskOutcome:
        """Execute a task through the framework.

        Parameters
        ----------
        task:
            The job to complete.
        ai:
            The machine-side actor. Defaults to a rule-based AI.
        expert:
            The human-side actor. Defaults to a simulated expert.
        clock:
            Injectable time source (defaults to ``perf_counter``) so tests and
            simulations are deterministic.
        """
        from .adapters import RuleBasedAI, SimulatedExpert

        ai = ai or RuleBasedAI()
        expert = expert or SimulatedExpert()
        now = clock or perf_counter
        session = SessionState()
        events: list[HandoverEvent] = []
        step_outcomes: list[StepOutcome] = []

        for index, spec in enumerate(task.steps):
            context = StepContext(
                task,
                spec,
                index,
                state={},
                current_controller=session.current_controller,
                expert_load=session.fatigue,
            )
            decision = self.decide_handover(context, session)

            step_events: list[HandoverEvent] = []
            if decision.controller is not session.current_controller:
                event = self._execute_handover(now(), decision, context)
                events.append(event)
                step_events.append(event)
                session.current_controller = decision.controller
                session.overhead_seconds += event.duration

            context.current_controller = session.current_controller
            context.expert_load = session.fatigue
            self.before_step(context, session)
            outcome = self._process_step(context, ai, expert, now, session)
            outcome.handovers = step_events
            self.after_step(outcome, context, session)
            step_outcomes.append(outcome)

        # elapsed is *simulated* time: decision latencies + handover overhead
        elapsed = (
            session.ai_active_seconds + session.expert_active_seconds + session.overhead_seconds
        )
        return TaskOutcome(
            task=task,
            step_outcomes=step_outcomes,
            events=events,
            elapsed=elapsed,
            expert_active_seconds=session.expert_active_seconds,
            ai_active_seconds=session.ai_active_seconds,
            successful=all(o.passed for o in step_outcomes),
            metadata={"overhead_seconds": session.overhead_seconds},
        )

    # -- internals -------------------------------------------------------------

    def _execute_handover(
        self, timestamp: float, decision: HandoverDecision, context: StepContext
    ) -> HandoverEvent:
        direction = (
            HandoverDirection.AI_TO_EXPERT
            if decision.controller is Role.EXPERT
            else HandoverDirection.EXPERT_TO_AI
        )
        event = HandoverEvent(
            timestamp=timestamp,
            direction=direction,
            trigger=decision.trigger,
            step_id=context.step_id,
            reason=decision.reason,
            duration=self.handover_overhead,
        )
        self._notify(event, context)
        return event

    def _process_step(
        self,
        context: StepContext,
        ai: AIModel,
        expert: Expert,
        now: Callable[[], float],
        session: SessionState,
    ) -> StepOutcome:
        spec = context.step
        if context.current_controller is Role.AI:
            decision: AgentDecision = ai.act(spec, session)
            session.ai_steps += 1
            session.consecutive_ai_steps += 1
            session.consecutive_expert_steps = 0
            session.ai_active_seconds += decision.latency
        else:
            decision = expert.act(spec, session)
            session.expert_steps += 1
            session.consecutive_expert_steps += 1
            session.consecutive_ai_steps = 0
            session.expert_active_seconds += decision.latency

        session.cognitive_load = _update_load(
            session.cognitive_load, decision.latency, spec.complexity, context.current_controller
        )
        session.fatigue = _update_fatigue(session.fatigue, session.cognitive_load)
        passed = self.step_evaluator(decision, spec)

        return StepOutcome(
            step=spec,
            decision=decision,
            controller=context.current_controller,
            passed=passed,
            note=f"processed by {context.current_controller.value}",
            session=SessionSnapshot(
                cognitive_load=session.cognitive_load,
                fatigue=session.fatigue,
                expert_steps=session.expert_steps,
                ai_steps=session.ai_steps,
                ai_active_seconds=session.ai_active_seconds,
                expert_active_seconds=session.expert_active_seconds,
                overhead_seconds=session.overhead_seconds,
            ),
        )


def _default_step_evaluator(decision: AgentDecision, spec: StepSpec) -> bool:
    """Heuristic: the decision must clear a bar that grows with step complexity.

    Supply your own ``step_evaluator`` to grade against golden labels instead.
    """
    bar = 0.5 + spec.complexity * 0.4
    return decision.quality_estimate >= bar


def _update_load(current: float, latency: float, complexity: float, controller: Role) -> float:
    step_load = min(1.0, latency / 12.0 + complexity * 0.5)
    if controller is Role.EXPERT:
        return min(1.0, current + step_load * 0.35)
    return max(0.0, current - 0.05)


def _update_fatigue(current: float, cognitive_load: float) -> float:
    return min(1.0, current * 0.96 + cognitive_load * 0.06)

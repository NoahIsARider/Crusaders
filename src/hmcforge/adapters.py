"""Actors: the AI and the human expert.

A framework choreographs *who* works on each step; the actors do the work.
``AIModel`` and ``Expert`` are protocols, so you can plug in anything:

* a rule-based bot (shipped here, great for simulations and tests),
* a real LLM (see :class:`OpenAIAdapter`),
* a Python object that calls your own internal model,
* a thin client that shows a task to a human operator and waits for input.

Both protocols receive the :class:`~hmcforge.policies.SessionState` so that
load-aware implementations are possible.
"""

from __future__ import annotations

import os
from typing import Optional, Protocol, runtime_checkable

from .core.types import AgentDecision, Role, StepSpec
from .policies import SessionState


@runtime_checkable
class AIModel(Protocol):
    """Anything that can act on a step as the machine side."""

    def act(self, step: StepSpec, session: SessionState) -> AgentDecision: ...


@runtime_checkable
class Expert(Protocol):
    """Anything that can act on a step as the human side."""

    def act(self, step: StepSpec, session: SessionState) -> AgentDecision: ...


class RuleBasedAI:
    """Deterministic AI for simulations and tests.

    Its competence degrades as step complexity rises, mirroring the classic
    "AI is great at easy/medium, shaky at hard" assumption. Confidence feeds
    ``ConfidencePolicy``; latency feeds the decision-time mediator.
    """

    def __init__(
        self,
        base_latency: float = 1.2,
        max_complexity_skill: float = 1.0,
    ) -> None:
        self.base_latency = base_latency
        self.max_complexity_skill = max_complexity_skill

    def act(self, step: StepSpec, session: SessionState) -> AgentDecision:
        overshoot = max(0.0, step.complexity - self.max_complexity_skill)
        quality = max(0.05, 0.92 - step.complexity * 0.55 - overshoot * 0.9)
        confidence = max(0.05, 0.95 - step.complexity * 0.6)
        latency = self.base_latency * (0.8 + step.complexity)
        return AgentDecision(
            role=Role.AI,
            step_id=step.id,
            action="ai_process",
            content=f"ai:{step.id}",
            confidence=confidence,
            quality_estimate=quality,
            latency=latency,
            metadata={"model": "rule-based", "complexity": step.complexity},
        )


class SimulatedExpert:
    """A configurable stand-in for the human.

    ``accuracy`` and ``latency`` define the person's baseline; ``fatigue_penalty``
    scales down performance as ``session.fatigue`` grows, and ``fatigue_growth``
    governs how quickly handling work tires them.
    """

    def __init__(
        self,
        accuracy: float = 0.9,
        latency: float = 6.0,
        fatigue_penalty: float = 0.3,
        fatigue_growth: float = 0.08,
        name: str = "sim-expert",
    ) -> None:
        if not 0.0 <= accuracy <= 1.0:
            raise ValueError("accuracy must be in [0, 1]")
        self.accuracy = accuracy
        self.latency = latency
        self.fatigue_penalty = fatigue_penalty
        self.fatigue_growth = fatigue_growth
        self.name = name

    def act(self, step: StepSpec, session: SessionState) -> AgentDecision:
        quality = self.accuracy - session.fatigue * self.fatigue_penalty
        quality = max(0.05, min(1.0, quality))
        latency = self.latency * (0.7 + step.complexity * 0.6 + session.fatigue * 0.4)
        return AgentDecision(
            role=Role.EXPERT,
            step_id=step.id,
            action="expert_review",
            content=f"expert:{step.id}",
            confidence=max(0.05, quality),
            quality_estimate=quality,
            latency=latency,
            metadata={"expert": self.name},
        )


class OpenAIAdapter:
    """Optional LLM-backed AI.

    Reads configuration from the *project's own* environment variables
    (``USER_LLM_API_KEY`` / ``USER_LLM_BASE_URL`` / ``USER_LLM_MODEL``) so no
    secrets are baked into code. The ``openai`` package must be installed
    (``pip install hmcforge[llm]``); if it is missing, a helpful error is
    raised at construction time.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        base_latency: float = 2.0,
        temperature: float = 0.0,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "OpenAIAdapter requires the 'openai' package. "
                "Install it with: pip install 'hmcforge[llm]'"
            ) from exc

        self._client = OpenAI(
            api_key=api_key or os.getenv("USER_LLM_API_KEY"),
            base_url=base_url or os.getenv("USER_LLM_BASE_URL"),
        )
        self._model = model or os.getenv("USER_LLM_MODEL", "deepseek-chat")
        self.base_latency = base_latency
        self.temperature = temperature
        if self._client.api_key is None or self._client.api_key == "":
            raise ValueError(
                "No API key found. Set USER_LLM_API_KEY (and optionally "
                "USER_LLM_BASE_URL / USER_LLM_MODEL) in your environment."
            )

    def act(self, step: StepSpec, session: SessionState) -> AgentDecision:
        prompt = (
            f"Task step: {step.description}\n"
            f"Complexity: {step.complexity:.2f}\n"
            f"Risk: {step.risk:.2f}\n"
            "Return a JSON object: "
            '{"action": str, "result": str, "confidence": 0..1, "quality": 0..1}'
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content or ""
        confidence = _extract_number(content, "confidence", 0.5)
        quality = _extract_number(content, "quality", 0.5)
        return AgentDecision(
            role=Role.AI,
            step_id=step.id,
            action="llm_process",
            content=content,
            confidence=confidence,
            quality_estimate=quality,
            latency=self.base_latency,
            metadata={"model": self._model},
        )


def _extract_number(text: str, key: str, default: float) -> float:
    import re

    for marker in (f'"{key}"', f"'{key}'", key):
        if marker in text:
            tail = text.split(marker, 1)[1]
            match = re.search(r"[:=]\s*([0-9]+(?:\.[0-9]+)?)", tail)
            if match:
                return max(0.0, min(1.0, float(match.group(1))))
    return default

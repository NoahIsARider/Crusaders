"""Built-in example scenarios.

Each scenario is a complete, runnable case study: an organisational
meta-knowledge (the moderator), a task corpus, and a reference framework
showing one philosophy of dynamic power handover. Use them as templates for
your own frameworks.

* :mod:`hmcforge.scenarios.healthcare_triage` -- risk-gated, human safety net.
* :mod:`hmcforge.scenarios.financial_underwriting` -- confidence-driven,
  experts own the judgement calls.
* :mod:`hmcforge.scenarios.code_review` -- efficiency-driven, load-aware.
"""

from . import code_review, financial_underwriting, healthcare_triage

__all__ = ["code_review", "financial_underwriting", "healthcare_triage"]

# Formal model: dynamic power handover

Crusaders makes a team decide *who controls each step* and hands control back and
forth between a machine and a human. The framework **measures** whether a handover
policy is good. This directory does the complementary thing: it **proves** what the
handover protocol must never do, by model-checking a TLA⁺ specification of it with
TLC.

## The protocol

`PowerHandover.tla` models the smallest thing that still deserves the name
"dynamic power handover". Every agent — human or machine — holds, at any instant:

- `exec[a]` — *execution* authority: how much work agent `a` may run itself;
- membership in `grant` — *authorisation* authority: the right to expand someone
  else's execution authority.

Five actions, one per thing a collaboration actually does:

| action | meaning |
| --- | --- |
| `Delegate(s, w)` | a grant holder authorises worker `w` to execute one more unit of work |
| `Return(w, s)` | a worker hands execution back — handover is reversible |
| `StepBack(h)` | a human leaves the authorising set |
| `Rejoin(h)` | a human re-joins the authorising set |
| `Ascend(a)` | an agent takes on authorisation |

## The three properties

```
SeparationOfPowers         no agent both executes and authorises
AuthorityBudget            total delegated execution authority stays <= CAP
HumanRetainsAuthorization  at least one human keeps the grant role
```

These are the same claims the empirical work argues for — use/authorisation
separation, structural prudence, and "high authorisation, zero" — except that here
they are *checked* rather than *measured*.

Two admission rules carry the first property: `Delegate` may not hand execution to
an agent that already authorises, and `Ascend`/`Rejoin` may not admit an agent that
still holds execution. Execution must be given up before authorisation is taken on.

## Running it

```bash
cd formal
./run.sh          # expects java 11+; downloads tla2tools.jar on first run
```

```
safe protocol (all guards in place)
  PASS  PowerHandover.cfg - no invariant violated
deliberately relaxed guards (each must produce its counterexample)
  PASS  PowerHandoverBuggy_separation.cfg - SeparationOfPowers violated, as designed
  PASS  PowerHandoverBuggy_human.cfg - HumanRetainsAuthorization violated, as designed
  PASS  PowerHandoverBuggy_budget.cfg - AuthorityBudget violated, as designed

4 passed, 0 failed
```

With `Agents = {h1, h2, m1, m2, m3}`, `CAP = 6`, `MaxAuth = 3`, TLC explores 7,450
states (843 distinct) and finds no violation of the safe protocol.

## Why the relaxed configurations exist

A model checker that reports "no error" on a spec that cannot fail has told you
nothing. Each `PowerHandoverBuggy_*.cfg` sets `DropGuard` so that exactly one guard
is removed, and each run must then produce a counterexample. That is what makes the
clean run meaningful.

Dropping the authorisation guard in `Delegate` breaks the first property after a
single step:

```
Error: Invariant SeparationOfPowers is violated.
State 1: <Initial predicate>
/\ exec = (h1 :> 0 @@ h2 :> 0 @@ m1 :> 0 @@ m2 :> 0 @@ m3 :> 0)
/\ grant = {h1, h2}
State 2: <Delegate>
/\ exec = (h1 :> 1 @@ h2 :> 0 @@ m1 :> 0 @@ m2 :> 0 @@ m3 :> 0)
/\ grant = {h1, h2}          \* h1 now executes and authorises at the same time
```

## Files

| file | what it is |
| --- | --- |
| `PowerHandover.tla` | the specification: state, actions, invariants, `DropGuard` |
| `PowerHandover.cfg` | safe configuration — every guard in place |
| `PowerHandoverBuggy_separation.cfg` | `Delegate` ignores the grant role |
| `PowerHandoverBuggy_human.cfg` | the last human may step back |
| `PowerHandoverBuggy_budget.cfg` | `Delegate` ignores `CAP` |
| `run.sh` | runs all four and asserts the documented outcome of each |

## Scope

TLC checks *safety* here: the invariants hold in every reachable state of every
execution the model allows. It does not prove liveness (that a handover eventually
completes), and it reasons about a finite abstraction of authority — integer levels
rather than the continuous load and fatigue signals the runtime policies actually
read. Extending the model with a fairness assumption and a liveness property is the
natural next step.

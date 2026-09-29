--------------------------- MODULE PowerHandover ---------------------------
(***************************************************************************)
(* Dynamic power handover, formalised.                                     *)
(*                                                                         *)
(* Crusaders lets a team decide *who controls a step* and hand control back *)
(* and forth between a machine and a human. The framework measures whether  *)
(* that works; this spec is the other half of the argument: it states the   *)
(* properties the handover protocol is supposed to preserve and lets TLC    *)
(* check them exhaustively.                                                 *)
(*                                                                         *)
(* Three safety properties, one per line of the design story:               *)
(*                                                                         *)
(*   SeparationOfPowers          nobody both executes and authorises        *)
(*   AuthorityBudget             the total delegated authority stays capped *)
(*   HumanRetainsAuthorization   at least one human keeps the grant role    *)
(*                                                                         *)
(* These are exactly the properties the empirical work argues for —         *)
(* use/authorisation separation, structural prudence, and "high            *)
(* authorisation, zero" — except that here they are checked, not measured.  *)
(*                                                                         *)
(* DropGuard relaxes one guard at a time so the checker can produce a       *)
(* counterexample for each property, demonstrating that the guard is what   *)
(* carries the property and that the check is not vacuous.                  *)
(*   0  every guard in place        -> no violation                         *)
(*   1  Delegate ignores grant      -> SeparationOfPowers violated          *)
(*   2  last human may step back    -> HumanRetainsAuthorization violated   *)
(*   3  Delegate ignores CAP        -> AuthorityBudget violated             *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets

CONSTANTS Agents,        \* every participant, machines and humans alike
          Humans,        \* the human principals; Humans \subseteq Agents
          CAP,           \* authority budget: how much execution authority may exist
          MaxAuth,       \* per-agent authority ceiling
          DropGuard      \* which guard to relax (0..3); see header

ASSUME Humans \subseteq Agents
ASSUME CAP \in Nat /\ MaxAuth \in Nat
ASSUME Cardinality(Humans) >= 1

VARIABLES
  exec,   \* exec[a]: execution authority held by agent a, in 0..MaxAuth
  grant   \* set of agents holding authorisation authority

vars == <<exec, grant>>

(***************************************************************************)
(* Total execution authority, folded over the finite agent set.             *)
(***************************************************************************)

RECURSIVE SumExec(_)
SumExec(S) ==
  IF S = {} THEN 0
  ELSE LET a == CHOOSE x \in S : TRUE
       IN exec[a] + SumExec(S \ {a})

TotalExec == SumExec(Agents)

(***************************************************************************)
(* The three properties.                                                    *)
(***************************************************************************)

SeparationOfPowers ==
  \A a \in Agents : ~(exec[a] > 0 /\ a \in grant)

AuthorityBudget ==
  TotalExec <= CAP

HumanRetainsAuthorization ==
  Cardinality(grant \cap Humans) >= 1

TypeOK ==
  /\ exec \in [Agents -> 0..MaxAuth]
  /\ grant \subseteq Agents

(***************************************************************************)
(* The protocol.                                                            *)
(***************************************************************************)

\* Initially nobody executes and every human authorises.
Init ==
  /\ exec = [a \in Agents |-> 0]
  /\ grant = Humans

\* A grant holder authorises a worker to execute one unit of work.
\* Guards: the worker must not already authorise, and the budget must have room.
Delegate(s, w) ==
  /\ s \in grant
  /\ w \in Agents
  /\ exec[w] < MaxAuth
  /\ (w \notin grant \/ DropGuard = 1)
  /\ (TotalExec < CAP \/ DropGuard = 3)
  /\ exec' = [exec EXCEPT ![w] = exec[w] + 1]
  /\ grant' = grant

\* A worker hands execution back: handover is reversible.
Return(w, s) ==
  /\ exec[w] > 0
  /\ s \in grant
  /\ exec' = [exec EXCEPT ![w] = exec[w] - 1]
  /\ grant' = grant

\* A human steps back from authorising, provided another human still holds it.
StepBack(h) ==
  /\ h \in Humans
  /\ h \in grant
  /\ (Cardinality(grant \cap Humans) > 1 \/ DropGuard = 2)
  /\ grant' = grant \ {h}
  /\ exec' = exec

\* A human who stepped back may re-join the authorising set, but only after
\* giving up any execution authority (same admission rule as Ascend).
Rejoin(h) ==
  /\ h \in Humans
  /\ h \notin grant
  /\ exec[h] = 0
  /\ grant' = grant \cup {h}
  /\ exec' = exec

\* An agent can take on authorisation, but only after giving up execution:
\* this is the separation of powers as an admission rule, not just an invariant.
Ascend(a) ==
  /\ a \in Agents
  /\ a \notin grant
  /\ exec[a] = 0
  /\ grant' = grant \cup {a}
  /\ exec' = exec

Next ==
  \/ \E s, w \in Agents : Delegate(s, w)
  \/ \E w, s \in Agents : Return(w, s)
  \/ \E h \in Humans : StepBack(h)
  \/ \E h \in Humans : Rejoin(h)
  \/ \E a \in Agents : Ascend(a)

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

=============================================================================

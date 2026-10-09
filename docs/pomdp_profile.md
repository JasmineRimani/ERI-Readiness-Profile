# POMDP with an ecosystem-readiness profile

The profile and the decision model have different roles. The profile records required capabilities, evidence, remaining work, dependencies and engineering figures of merit. A POMDP adds a joint belief about uncertain capability states and chooses the next admissible action using a separately specified objective. A scalar ERI is not required.

The methodological basis is [Kaelbling, Littman and Cassandra (1998), Artificial Intelligence 101, 99-134](https://doi.org/10.1016/S0004-3702(98)00023-X).

| Component | Possible ANALOGS interpretation | Evidence still needed |
|---|---|---|
| Hidden state | Selected-unit performance, interface suitability, delivery and test-access conditions | Configuration-specific assessments; dependency and correlation structure |
| Known decision state | Date, remaining money, completed tasks and observed structure availability | Current programme records |
| Action | Review supplier or interface evidence, perform a test, commission development or corrective work | Scope, cost, duration and effect of each action |
| Observation | Supplier response, verified milestone or measured test result | Observation likelihood, including false passes and false failures |
| Belief update | Revise joint uncertainty after an observation | Defensible prior and transition and observation models |
| Objective | Minimise expected additional development and testing cost subject to explicit completion and acceptance requirements | Agreed exact deadline, scope-matched budget and risk tolerance |

The structure-first procurement sequence and resource constraints belong in action admissibility and state transitions. A POMDP must not select equipment procurement before the structure prerequisite. Different action durations must advance the observed clock; an action count alone cannot represent the Q1 deadline.

Information gathering changes knowledge; it need not improve physical capability. Development or rework may change physical capability. Shared dependencies require a joint belief or another justified dependency model, rather than automatically multiplying independent confidence values.

The optimisation cost is a decision objective, not an aggregate readiness score. Mandatory acceptance remains an evidence requirement outside any arbitrary belief threshold. For a deadline-risk constraint, the target and tolerated risk must be supplied explicitly; neither has been numerically invented here.

## Implementation

`src/eri/profile_pomdp.py` implements Eq. (6) of the paper:

b_{k+1}(x') = eta O(o_{k+1} | x', u_k) sum_x T(x' | x, u_k) b_k(x)

`joint_conditions` enumerates joint conditions from named condition levels without assuming independence; `predict` applies the transition of the chosen action; `belief_update` applies the observation likelihood and normalises. Invalid distributions and observations that the declared models cannot explain raise an error. The module holds no priors, transition or observation probabilities and computes no policy. Those numbers must come from programme records, supplier information, test outcomes and comparable implementation histories before any numerical policy is calculated.

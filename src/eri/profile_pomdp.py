"""Belief update of the decision layer over the readiness profile.

The profile is the engineering record: requirements, evidence, remaining work
and dependencies. A partially observable Markov decision process (POMDP) would
use that record to choose the next action as evidence arrives. The joint
condition ``x`` collects the uncertain conditions of one architecture (supply,
configuration performance, interfaces, test access). After action ``u_k``
produces observation ``o_{k+1}`` the belief is updated as

    b_{k+1}(x') = eta * O(o_{k+1} | x', u_k) * sum_x T(x' | x, u_k) * b_k(x)

where ``T`` is the probability that the action changes the condition from
``x`` to ``x'``, ``O`` the probability of the observation under the resulting
condition and ``eta`` the normaliser (Kaelbling, Littman and Cassandra, 1998).

This module states the formulation only. It holds no priors, transition or
observation probabilities and computes no policy: those numbers must come from
programme records, supplier information and test outcomes. The qualitative
evidence states of the profile do not by themselves provide them, and the
belief is never collapsed into a readiness score.
"""
from itertools import product

import numpy as np

_TOL = 1e-9


def joint_conditions(conditions):
    """Enumerate joint conditions from named condition levels.

    ``conditions`` maps a condition name to its possible levels, e.g.
    ``{'supply': ('confirmed', 'unconfirmed'), 'interface': ('met', 'not_met')}``.
    Returns a list of dicts, one per joint condition, in a fixed order. Shared
    conditions are kept joint; no independence between them is assumed.
    """
    names = list(conditions)
    if not names or any(len(conditions[n]) == 0 for n in names):
        raise ValueError('Every condition needs at least one level')
    return [dict(zip(names, levels)) for levels in product(*(conditions[n] for n in names))]


def _distribution(values, name):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or (values < -_TOL).any() or abs(values.sum() - 1) > 1e-6:
        raise ValueError(f'{name} must be a probability vector')
    return values


def predict(belief, transition):
    """Prediction step: sum_x T(x' | x, u) b(x). ``transition[x, x']`` rows sum to one."""
    belief = _distribution(belief, 'belief')
    transition = np.asarray(transition, dtype=float)
    n = belief.size
    if transition.shape != (n, n) or (transition < -_TOL).any() or not np.allclose(transition.sum(axis=1), 1, atol=1e-6):
        raise ValueError('transition must be a row-stochastic (n, n) matrix for the chosen action')
    return belief @ transition


def belief_update(belief, transition, observation_likelihood):
    """Return b_{k+1} after one action (``transition``) and one observation.

    ``observation_likelihood[x']`` is O(o | x', u) of the observation actually
    received. An observation with zero predicted probability is an error: the
    declared models cannot explain it and must be revised.
    """
    predicted = predict(belief, transition)
    likelihood = np.asarray(observation_likelihood, dtype=float)
    if likelihood.shape != predicted.shape or (likelihood < -_TOL).any() or (likelihood > 1 + _TOL).any():
        raise ValueError('observation_likelihood must hold one probability per joint condition')
    unnormalised = likelihood * predicted
    total = unnormalised.sum()
    if total <= _TOL:
        raise ValueError('Observation has zero probability under the declared models')
    return unnormalised / total

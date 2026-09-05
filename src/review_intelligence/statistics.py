"""Small standard-library statistical helpers for transparent baselines."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BetaEstimate:
    alpha: float
    beta: float
    mean: float
    lower: float
    upper: float


def beta_posterior(
    observations: list[tuple[bool, float]],
    alpha_prior: float = 1.0,
    beta_prior: float = 1.0,
    credibility: float = 0.95,
) -> BetaEstimate:
    if alpha_prior <= 0 or beta_prior <= 0:
        raise ValueError("Beta prior parameters must be positive")
    if not 0 < credibility < 1:
        raise ValueError("credibility must be between zero and one")
    alpha = alpha_prior + sum(weight for success, weight in observations if success)
    beta = beta_prior + sum(weight for success, weight in observations if not success)
    tail = (1.0 - credibility) / 2.0
    return BetaEstimate(
        alpha=alpha,
        beta=beta,
        mean=alpha / (alpha + beta),
        lower=beta_quantile(tail, alpha, beta),
        upper=beta_quantile(1.0 - tail, alpha, beta),
    )


def effective_sample_size(weights: list[float]) -> float:
    if not weights:
        return 0.0
    denominator = sum(weight * weight for weight in weights)
    return 0.0 if denominator == 0 else sum(weights) ** 2 / denominator


def recency_weight(age_days: int, half_life_days: float | None) -> float:
    if age_days < 0:
        raise ValueError("observation date cannot be after the as-of date")
    if half_life_days is None:
        return 1.0
    if half_life_days <= 0:
        raise ValueError("half-life must be positive")
    return 0.5 ** (age_days / half_life_days)


def beta_quantile(probability: float, alpha: float, beta: float) -> float:
    if probability <= 0:
        return 0.0
    if probability >= 1:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(80):
        midpoint = (low + high) / 2.0
        if regularized_incomplete_beta(midpoint, alpha, beta) < probability:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def regularized_incomplete_beta(x: float, alpha: float, beta: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_front = (
        math.lgamma(alpha + beta)
        - math.lgamma(alpha)
        - math.lgamma(beta)
        + alpha * math.log(x)
        + beta * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (alpha + 1.0) / (alpha + beta + 2.0):
        return front * _beta_continued_fraction(x, alpha, beta) / alpha
    return 1.0 - front * _beta_continued_fraction(1.0 - x, beta, alpha) / beta


def _beta_continued_fraction(x: float, alpha: float, beta: float) -> float:
    max_iterations = 300
    epsilon = 3e-14
    tiny = 1e-300
    qab = alpha + beta
    qap = alpha + 1.0
    qam = alpha - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    result = d
    for iteration in range(1, max_iterations + 1):
        m2 = 2 * iteration
        term = iteration * (beta - iteration) * x / ((qam + m2) * (alpha + m2))
        d = 1.0 + term * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + term / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        result *= d * c
        term = -(alpha + iteration) * (qab + iteration) * x / ((alpha + m2) * (qap + m2))
        d = 1.0 + term * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + term / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < epsilon:
            break
    return result


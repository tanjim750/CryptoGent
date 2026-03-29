from __future__ import annotations

from abc import ABC, abstractmethod


class TokenEstimator(ABC):
    @abstractmethod
    def estimate(self, text: str) -> int:
        raise NotImplementedError


class HeuristicTokenEstimator(TokenEstimator):
    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / 4))


_DEFAULT = HeuristicTokenEstimator()
_REGISTRY: dict[str, TokenEstimator] = {}


def register_estimator(name: str, estimator: TokenEstimator) -> None:
    key = str(name).strip().lower()
    _REGISTRY[key] = estimator


def get_estimator(name: str | None = None) -> TokenEstimator:
    if not name:
        return _DEFAULT
    key = str(name).strip().lower()
    return _REGISTRY.get(key, _DEFAULT)


def estimate_tokens(text: str) -> int:
    return _DEFAULT.estimate(text)


def estimate_tokens_with(name: str | None, text: str) -> int:
    return get_estimator(name).estimate(text)

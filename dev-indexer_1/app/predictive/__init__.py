"""Predictive micro-model framework (lightweight embedded models).

Provides a central controller to host tiny calibration / selection models
that return fast numeric scores or label hints without external deps.
"""
from .controller import get_predictive_controller  # noqa: F401

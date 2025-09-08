"""
Causal Inference Module for ZenGlow

This module provides causal analysis capabilities to determine the effectiveness
of interventions (e.g., mindfulness exercises) on child wellness outcomes.

Uses DoWhy/CausalML for rigorous causal analysis beyond simple correlation.
"""

from .causal_inference import analyze_causal_effect

__all__ = ['analyze_causal_effect']
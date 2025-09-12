"""Deprecated top-level swarm package.

This module has moved to app.swarm2. Keeping a stub here to avoid import errors
in any older scripts; no routes are defined from this module.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/swarm", tags=["swarm-deprecated"])


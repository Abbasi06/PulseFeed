"""
Swarm intelligence layer for the PulseGen generator microservice.

Exports:
  SwarmCoordinator      — orchestrates each harvest cycle end-to-end
  DynamicQueryEngine    — generates adaptive, source-specific query sets
  MomentumTracker       — tracks per-tag velocity across cycles
  CrossSourceAmplifier  — detects cross-source hot signals for next cycle
"""

from src.swarm.coordinator import SwarmCoordinator
from src.swarm.momentum import MomentumTracker
from src.swarm.query_engine import CrossSourceAmplifier, DynamicQueryEngine

__all__ = [
    "SwarmCoordinator",
    "DynamicQueryEngine",
    "MomentumTracker",
    "CrossSourceAmplifier",
]

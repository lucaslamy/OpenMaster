"""Isolated external DSP plugin contracts for OpenMaster."""

from .isolated import IsolatedPluginProcessor, PluginExecutionError, PluginManifest

__all__ = ["IsolatedPluginProcessor", "PluginExecutionError", "PluginManifest"]

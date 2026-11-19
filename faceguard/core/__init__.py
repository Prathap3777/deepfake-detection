"""
FACEGUARD AI - Core Engine Package
Module: faceguard/core/__init__.py
"""
from faceguard.core.detector import DeepfakePredictor, get_predictor
from faceguard.core.gradcam import GradCAM
from faceguard.core.video import analyze_video

__all__ = ["DeepfakePredictor", "get_predictor", "GradCAM", "analyze_video"]

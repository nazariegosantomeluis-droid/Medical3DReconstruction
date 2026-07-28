"""Organ pipeline registry: the CLI's only coupling point to the organs."""

from __future__ import annotations

from medical3d.organs.base import OrganPipeline, PipelineResult
from medical3d.organs.brain import BrainPipeline
from medical3d.organs.heart import HeartPipeline
from medical3d.organs.kidneys import KidneysPipeline
from medical3d.organs.liver import LiverPipeline
from medical3d.organs.lungs import LungsPipeline

ORGAN_PIPELINES: dict[str, type[OrganPipeline]] = {
    "lungs": LungsPipeline,
    "heart": HeartPipeline,
    "liver": LiverPipeline,
    "kidneys": KidneysPipeline,
    "brain": BrainPipeline,
}

__all__ = ["ORGAN_PIPELINES", "OrganPipeline", "PipelineResult"]

"""Stage definition for the future automatic mastering pipeline."""


class AutoMasterPipeline:
    """Describe the ordered deterministic mastering stages."""

    stages = [
        "analysis",
        "eq",
        "compression",
        "limiter",
        "export",
    ]

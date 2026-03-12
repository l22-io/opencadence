from src.core.models import Sample
from src.processing.base import AnomalyFlag, BaseProcessor, ProcessingContext


class RangeValidator(BaseProcessor):
    """Flags samples outside the metric's valid range."""

    def process(self, sample: Sample, ctx: ProcessingContext) -> Sample:
        if not ctx.metric_def.is_in_range(sample.value):
            ctx.anomalies.append(
                AnomalyFlag(
                    reason="out_of_range",
                    severity="warning",
                    context={
                        "value": sample.value,
                        "min": ctx.metric_def.valid_range.min,
                        "max": ctx.metric_def.valid_range.max,
                    },
                )
            )
        return sample

from market.settled_output_batch import SettledOutputBatch


class SettledOutputBatchFactory:
    def build(
        self,
        outputs: list[dict[str, object]],
    ) -> SettledOutputBatch:
        return SettledOutputBatch(outputs=outputs)

class MinutePlan:
    def __init__(self, *, quote_notional: float, slice_quotes: list[float]):
        self.quote_notional = float(quote_notional)
        self.slice_quotes = [float(slice_quote) for slice_quote in slice_quotes]
        self.executed_slices = 0
        self.target_slice_count = len(self.slice_quotes)
        self.executed_quote_notional = 0.0

    def has_remaining_slices(self) -> bool:
        return self.executed_slices < len(self.slice_quotes)

    def remaining_slices(self) -> list[float]:
        return list(self.slice_quotes[self.executed_slices:])

    def remaining_quote_notional(self) -> float:
        return sum(self.remaining_slices())

    def remaining_slice_count(self) -> int:
        return len(self.slice_quotes) - self.executed_slices

    def pop_next_slice(self) -> float | None:
        if not self.has_remaining_slices():
            return None
        next_slice = self.slice_quotes[self.executed_slices]
        self.executed_slices += 1
        self.executed_quote_notional += next_slice
        return next_slice

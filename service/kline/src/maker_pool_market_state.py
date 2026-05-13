class PoolMarketState:
    def __init__(self, reserve_0: float, reserve_1: float):
        self.reserve_0 = float(reserve_0)
        self.reserve_1 = float(reserve_1)

        initial_price = 0.0
        if self.reserve_0 > 0 and self.reserve_1 > 0:
            initial_price = self.reserve_1 / self.reserve_0

        self.last_price = initial_price
        self.reference_price = initial_price
        self.anchor_price = initial_price

        self.regime = 'range'
        self.trend_direction = 0
        self.trend_strength = 0.0

    def update_reserves(self, reserve_0: float, reserve_1: float):
        self.reserve_0 = float(reserve_0)
        self.reserve_1 = float(reserve_1)

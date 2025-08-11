from typing import Optional

from pydantic import BaseModel


class Order(BaseModel):
    symbol: str
    orderId: int
    price: float
    origQty: float
    status: str
    type: str
    side: str
    updateTime: Optional[int] = None

    def was_sold(self):
        return self.side == "SELL" and self.status == "FILLED"

    def was_bought(self):
        return self.side == "BUY" and self.status == "FILLED"

    def is_sell(self):
        return self.side == "SELL" and self.status == "NEW"

    def is_buy(self):
        return self.side == "BUY" and self.status == "NEW"

from pydantic import BaseModel


class Fee(BaseModel):
    symbol: str
    makerCommission: float
    takerCommission: float

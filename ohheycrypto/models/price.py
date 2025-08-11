from pydantic import BaseModel


class Price(BaseModel):
    symbol: str
    priceChange: float
    priceChangePercent: float
    weightedAvgPrice: float
    prevClosePrice: float
    lastPrice: float
    lastQty: float
    bidPrice: float
    bidQty: float
    askPrice: float
    askQty: float
    openPrice: float
    highPrice: float
    lowPrice: float
    volume: float
    quoteVolume: float
    openTime: int
    closeTime: int
    firstId: int
    lastId: int
    count: int

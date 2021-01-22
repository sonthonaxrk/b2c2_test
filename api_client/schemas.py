from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List

from pydantic import BaseModel


class Instrument(BaseModel):
    name: str


class Instruments(BaseModel):
    __root__: List[Instrument]


class RequestForQuote(BaseModel):
    client_rfq_id: str
    quantity: str
    side: str
    instrument: str


class SideEnum(str, Enum):
    buy = 'buy'
    sell = 'sell'


class RequestForQuoteResponse(BaseModel):
    valid_until: datetime
    rfq_id: str
    client_rfq_id: str
    quantity: Decimal
    side: SideEnum
    instrument: str
    price: Decimal
    created: datetime


class Trade(BaseModel):
    rfq_id: str
    quantity: Decimal
    side: SideEnum
    instrument: str
    price: Decimal
    executing_unit: str


class TradeResponse(BaseModel):
    created: datetime
    price: Decimal
    instrument: str
    trade_id: str
    origin: str
    rfq_id: str
    side: SideEnum
    quantity: Decimal
    user: str
    executing_unit: str
    # Unknown field - not defined in documentation
    # Probably a dict?
    order: Any

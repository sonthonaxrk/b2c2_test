from pydantic import BaseModel
from decimal import Decimal
from typing import List, Tuple, Any, Optional, Dict
from b2c2.models import Instruments


class BaseRepsonseFrame(BaseModel):
    event: str
    success: bool


class TradableInstrumentsFrame(BaseRepsonseFrame):
    """
    Accepts both tradable_instruments
    and tradable_instruments_update
    """
    tradable_instruments: List[str]


class UsernameUpdateFrame(BaseRepsonseFrame):
    old_username: str
    new_username: str


class QuoteSubscribeFrame(BaseModel):
    event = 'subscribe'
    instrument: str
    # Levels apparently takes two numbers
    # However, I'm not entirely sure what the use
    # case for only two numbers is. So I'm going
    # to only allow one for the time being.

    # TODO: validate precision
    levels: Tuple[Decimal]
    # Technically not required - but it really is
    # if you're bulding anything useful
    tag: str


class QuoteUnsubscribeFrame(BaseModel):
    event = 'unsubscribe'
    instrument: str
    tag: Optional[str]


class QuoteUnsubscribeResponseFrame(QuoteUnsubscribeFrame):
    success: bool


class QuoteResponseFrame(BaseRepsonseFrame):

    class LevelItem(BaseModel):
        quantity: Decimal
        price: Decimal


    class LevelResponse(BaseModel):
        # Making an assumption these
        # are the two things that come with the
        # response
        buy: List['LevelItem']
        sell: List['LevelItem']

    instrument: str
    levels: LevelResponse
    timestamp: int


class ErrorResponseFrame(BaseRepsonseFrame):
    tag: Optional[str]
    error_code: int
    errors: Dict[str, List[Any]]
    tag: Optional[str]

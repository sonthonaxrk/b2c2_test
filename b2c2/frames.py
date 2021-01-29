import uuid
import string

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List, Any, Optional, Dict
from devtools import pformat


class BaseFrame(BaseModel):

    def __repr__(self):
        return pformat(self)


class BaseRepsonseFrame(BaseFrame):
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


class QuoteSubscribeFrame(BaseFrame):
    event = 'subscribe'
    instrument: str
    levels: List[Decimal]  # TODO: validate precision
    tag: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def _key(self):
        levels = tuple(sorted(self.levels))
        return (levels, self.instrument)


class QuoteSubscribeResponseFrame(BaseRepsonseFrame):
    event = 'subscribe'
    instrument: str
    levels: List[Decimal]  # TODO: validate precision
    success: bool = True
    # reset the default
    tag: Optional[str]


class QuoteUnsubscribeFrame(BaseFrame):
    event = 'unsubscribe'
    instrument: str
    tag: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


class QuoteUnsubscribeResponseFrame(QuoteUnsubscribeFrame):
    success: bool
    # reset the default
    tag: Optional[str]


class LevelItem(BaseFrame):
    quantity: Decimal
    price: Decimal


class LevelResponse(BaseFrame):
    # Making an assumption these
    # are the two things that come with the
    # response
    buy: List[LevelItem]
    sell: List[LevelItem]


class QuoteStreamFrame(BaseRepsonseFrame):
    instrument: str
    levels: LevelResponse
    timestamp: int

    @property
    def _key(self):
        levels = tuple(sorted(item.quantity for item in self.levels.buy))
        return (levels, self.instrument)


class ErrorResponseFrame(BaseRepsonseFrame):
    error_code: int
    error_message: str
    errors: Dict[str, List[Any]]
    tag: Optional[str]

    def to_exception(self):
        from b2c2.exceptions import quote_exceptions
        title = self.error_message.title().replace(' ', '')
        title = title.translate(str.maketrans('', '', string.punctuation))
        exc = getattr(quote_exceptions, title)
        return exc(self.error_message, self)

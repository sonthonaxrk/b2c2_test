import warnings
import ipywidgets
import functools

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional, Dict, TYPE_CHECKING

from devtools import pformat
from IPython.display import display
from pydantic import BaseModel as PydanticBaseModel, PrivateAttr

if TYPE_CHECKING:
    from b2c2.client import B2C2APIClient


def requires_bind(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_bound:
            raise RuntimeError(
                'Model must be bound to a client. '
                'Please bind to a client to call display\n\n\t'
                f'{self.__class__.__name}.bind_to_client(client)'
            )

        return func(self, *args, **kwargs)

    return wrapper


class BaseModel(PydanticBaseModel):
    _client = PrivateAttr(Optional['B2C2APIClient'])  # noqa
    _widgets_cache = PrivateAttr(None)

    def bind_to_client(self, client: 'B2C2APIClient') -> None:  # noqa
        self._client = client

    @property
    def _widgets(self):
        # Defered property: there's no point
        # creating widgets until they're accessed.
        # They will not be accessed until someone
        # deliberately uses the GUI.
        if not self._widgets_cache:
            self._widgets_cache = dict(self._get_data_widgets())

        return self._widgets_cache

    @property
    def is_bound(self) -> bool:
        return bool(getattr(self, '_client', None))

    def __repr__(self):
        return pformat(self)

    def _as_csv_row(self):
        return ','.join(
            str(v) for v in self.dict().values()
        )

    def _repr_pretty_(self, printer, cycle) -> None:
        """
        Display hook for the IPython repl.
        """
        printer.text(pformat(self))

    def _get_data_widgets(self):
        for field, field_value in self.dict().items():
            field_name_human_readable = field.replace('_', ' ').title()
            label = ipywidgets.Label(
                '{}:'.format(field_name_human_readable),
                layout={'width': '150px'}
            )

            data = ipywidgets.Label(str(field_value))

            yield (field, ipywidgets.HBox([label, data]))

    def _ipython_display_(self):
        """
        Display hook for Jupyter/QT notebooks
        """
        display(
            ipywidgets.VBox(list(self._widgets.values()))
        )


class SubscriptableSchema:
    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]


class SideEnum(str, Enum):
    buy = 'buy'
    sell = 'sell'


class Instrument(BaseModel):
    name: str

    def __str__(self):
        return self.name

    def safe_name(self):
        return self.name.replace('.', '_').lower()


class Instruments(BaseModel, SubscriptableSchema):
    __root__: List[Instrument]


class Balances(BaseModel, SubscriptableSchema):
    __root__: Dict[str, str]


class RequestForQuote(BaseModel):
    client_rfq_id: str
    quantity: str
    side: SideEnum
    instrument: str

    @requires_bind
    def get_quote(self):
        """
        :returns: the quote generated from the request for quote
        """
        return self._client.post_request_for_quote(self)


class Quote(BaseModel):
    valid_until: datetime
    rfq_id: str
    client_rfq_id: str
    quantity: Decimal
    side: SideEnum
    instrument: str
    price: Decimal
    created: datetime

    @property
    def expired(self):
        return self.time_left().total_seconds() <= 0

    def time_left(self, start_date: Optional[datetime] = None):
        if not start_date:
            start_date = datetime.now()

        return self.valid_until.replace(tzinfo=None) - start_date

    def _ipython_display_(self):
        """
        Display hook for Jupyter/QT notebooks
        """
        if self.is_bound:
            self._client.gui.quote_executor(self).display()
        else:
            warnings.warn(
                'The GUI needs the client to be active. To '
                'view interactive features on the model: bind '
                'the model by calling:\n\n\t'
                'quote.bind_to_client(client)'
            )

            super()._ipython_display_()

    def get_trade(self, executing_unit: Optional[str] = None) -> 'Trade':
        """
        Creates a trade from a quote. Is just a shortcut for
        users.

        :returns: Trade - unexecuted trade
        """
        return Trade(
            rfq_id=self.rfq_id,
            quantity=self.price,
            side=self.side,
            instrument=self.instrument,
            price=self.price,
            executing_unit=executing_unit
        )

    @requires_bind
    def execute_trade(
        self, executing_unit: Optional[str] = None
    ) -> 'TradeResponse':
        """
        This is a shortcut to execute a quote. For a user, there's no real
        difference between a quote and a trade except for the executing_unit
        parameter.

        :param executing_unit: for client side tracking

        :returns: TradeResponse - a completed trade.
        """
        trade = self.get_trade(executing_unit=executing_unit)
        return self._client.post_trade(trade)


class Trade(BaseModel):
    rfq_id: str
    quantity: Decimal
    side: SideEnum
    instrument: str
    price: Decimal
    executing_unit: Optional[str] = None


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
    # Unknown field - not defined in documentation
    # Probably a dict?
    order: Any
    executing_unit: Optional[str] = None

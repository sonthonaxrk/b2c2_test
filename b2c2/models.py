import warnings
import ipywidgets
import functools

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional, Dict, Generator

from devtools import pformat
from IPython.display import display
from ipywidgets.widgets.widget_core import CoreWidget

from pydantic import BaseModel as PydanticBaseModel, PrivateAttr


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
    _client = PrivateAttr()
    _widgets_cache = PrivateAttr(None)

    def bind_to_client(self, client: 'B2C2APIClient') -> None:
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
        return bool(self._client)

    def __repr__(self):
        return pformat(self)

    def _repr_pretty_(self, printer, cycle) -> None:
        """
        Display hook for the IPython repl.
        """
        printer.text(pformat(self))

    def _get_data_widgets(self):
        for field in self.fields:
            field_value = str(getattr(self, field, None))
            field_name_human_readable = field.replace('_', ' ').title()

            label = ipywidgets.Label(
                '{}:'.format(field_name_human_readable),
                layout={'width': '150px'}
            )

            data = ipywidgets.Label(field_value)

            yield (field, ipywidgets.HBox([label, data]))

    def _ipython_display_(self):
        """
        Display hook for Jupyter/QT notebooks
        """
        display(
            ipywidgets.VBox(self._widgets.values())
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
                f'quote.bind_to_client(client)'
            )

            super()._ipython_display_()

    @requires_bind
    def execute_trade(self, executing_unit: Optional[str] = None) -> 'Trade':
        trade = Trade(
            rfq_id=self.rfq_id,
            quantity=self.price,
            side=self.side,
            instrument=self.instrument,
            price=self.price,
            executing_unit=executing_unit
        )
        trade_response = self._client.post_trade(trade)
        self._client.history.completed_trades.append(trade_response)
        return trade_response


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

import pytest

from datetime import datetime
from decimal import Decimal
from b2c2.models import Balances, TradeResponse, SideEnum


def test_can_add_trade_to_balance():
    balance = Balances(__root__={'BTC': Decimal(0)})

    trade_resp = TradeResponse(
        created=datetime.now(),
        instrument='BTCUSD.SPOT',
        side=SideEnum.buy,
        quantity=1,
        price=1,
        trade_id='',
        origin='',
        rfq_id='',
        user='',
        order='',
        executing_unit=''
    )

    balance += trade_resp
    assert balance['BTC'] == 1

    trade_resp.side = SideEnum.sell
    balance += trade_resp
    assert balance['BTC'] == 0

    with pytest.raises(ValueError):
        trade_resp.instrument = 'unknown'
        balance += trade_resp

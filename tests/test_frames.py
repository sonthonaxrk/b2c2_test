from b2c2.frames import TradableInstrumentsFrame

def test_frame():

    frame = {
        'event': 'tradable_instruments',
        'success': True,
        'tradable_instruments': ['BTCUSD', 'BTCEUR', 'ETHEUR']
    }

    t_frame = TradableInstrumentsFrame(**frame)

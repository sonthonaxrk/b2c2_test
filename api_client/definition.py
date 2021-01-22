from api_client.schemas import (
    Instruments, RequestForQuote, RequestForQuoteResponse,
    Trade, TradeResponse
)

# This is a poor mans OpenAPI definition.
API_DEFINITION = {
    '/instruments/': {
        'GET': {
            'response': Instruments
        }
    },
    '/request_for_quote/': {
        'POST': {
            'body': RequestForQuote,
            'response': RequestForQuoteResponse
        }
    },
    '/trade/': {
        'POST': {
            'body': Trade,
            'TradeResponse': TradeResponse,
        }
    }
}

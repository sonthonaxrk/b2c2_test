from b2c2.exceptions import quote_exceptions


def test_quote_exception_object():
    exc = quote_exceptions.ExampleQuoteException('Hello', {})
    assert repr(exc) == "ExampleQuoteException('Hello')"

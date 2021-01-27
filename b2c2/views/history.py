import ipywidgets as widgets
from IPython.display import display
from tabulate import tabulate
from b2c2.models import TradeResponse, Quote
from b2c2.views import BaseView


class HistoryView(BaseView):

    def __init__(self):
        self._client.history.subscribe_trades(
            self.update_trade_view
        )

        self._client.history.subscribe_quotes(
            self.update_quote_view
        )

        self.trade_view = widgets.Box()
        self.quote_view = widgets.Box()
        self.root = widgets.Tab([
            self.trade_view, self.quote_view
        ])

        self.root.set_title(0, 'Trades')
        self.root.set_title(1, 'Quotes')

        self.update_trade_view()

    def _gen_format(self, history_list):
        for item in history_list:
            yield list(item.dict().values())

    def update_trade_view(self):
        headers = [f.name for f in TradeResponse.__fields__.values()]

        self.trade_view.children = [widgets.HTML(
            value=tabulate(
                self._gen_format(self._client.history.completed_trades),
                headers, tablefmt="html"
            )
        )]

    def update_quote_view(self):
        headers = [f.name for f in Quote.__fields__.values()]

        self.quote_view.children = [widgets.HTML(
            value=tabulate(
                self._gen_format(self._client.history.quotes),
                headers, tablefmt="html"
            )
        )]

    def display(self):
        display(self.root)

    def __del__(self):
        self._client.unsubscribe_trades(self.update_trade_view)
        self._client.unsubscribe_quotes(self.update_quote_view)

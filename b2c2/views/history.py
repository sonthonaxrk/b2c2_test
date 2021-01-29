import ipywidgets as widgets
from IPython.display import display
from tabulate import tabulate
from b2c2.models import TradeResponse, Quote
from b2c2.views import BaseView


class HistoryView(BaseView):

    def __init__(self):
        self.trade_view = widgets.Box()
        self.quote_view = widgets.Box()
        self.root = widgets.Tab([
            self.trade_view, self.quote_view
        ])

        self.root.set_title(0, 'Trades')
        self.root.set_title(1, 'Quotes')
        self._quote_task = self._client._loop.create_task(
            self.quote_watcher()
        )

        self._trade_task = self._client._loop.create_task(
            self.trade_watcher()
        )

    def _gen_format(self, history_list):
        for item in history_list:
            yield list(item.dict().values())

    def _update_quote_view(self):
        headers = [f.name for f in Quote.__fields__.values()]
        self.quote_view.children = [widgets.HTML(
            value=tabulate(
                self._gen_format(self._client.history.quotes),
                headers, tablefmt="html"
            )
        )]

    def _update_trade_view(self):
        headers = [f.name for f in TradeResponse.__fields__.values()]
        self.trade_view.children = [widgets.HTML(
            value=tabulate(
                self._gen_format(self._client.history.completed_trades),
                headers, tablefmt="html"
            )
        )]

    async def trade_watcher(self):
        self._update_trade_view()

        while True:
            async with self._client.history._trade_fanout.queue() as q:
                # New trade
                await q.get()
                self._update_trade_view()

    async def quote_watcher(self):
        self._update_quote_view()

        while True:
            async with self._client.history._quote_fanout.queue() as q:
                # New quote
                await q.get()
                self._update_quote_view()

    def display(self):
        display(self.root)

    def __del__(self):
        self._quote_task.cancel()
        self._trade_task.cancel()

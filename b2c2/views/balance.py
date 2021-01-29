import asyncio
import ipywidgets as widgets
from IPython.display import display
from b2c2.views import BaseView


class BalanceView(BaseView):

    async def _update(self, balance, trade_queue):
        while True:
            trade = await trade_queue.get()
            balance += trade
            self.root.children = [
                widgets.VBox(list(balance._widgets.values()))
            ]

    async def _watcher(self):
        while True:
            balance = self._client.get_balance()

            self.root.children = [
                widgets.VBox(list(balance._widgets.values()))
            ]

            try:
                async with self._client.history._trade_fanout.queue() as trade_queue:  # noqa
                    await asyncio.wait_for(
                        self._update(balance, trade_queue),
                        30
                    )

            except asyncio.TimeoutError:
                # no new trades in the last ten seconds
                pass

    def __init__(self):
        self.root = widgets.VBox()

    def display(self):
        self._watcher_task = self._client._loop.create_task(self._watcher())
        display(self.root)

    def __del__(self):
        self._watcher_task.cancel()

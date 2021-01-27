import asyncio
import ipywidgets as widgets

from IPython import get_ipython
from IPython.display import display

from b2c2.models import Quote
from b2c2.views import cell_creator, BaseView


class QuoteAdapter(BaseView):
    def __init__(self, quote):
        self.quote = quote

    def get_time_left_label(self):
        if self.quote.expired:
            return (
                'Quote has expired. Not able to execute trade. '
                'Try creating a new quote.'
            )
        else:
            time_left = self.quote.time_left().total_seconds()
            minutes, seconds = divmod(int(time_left), 60)
            return 'Time Left (minutes:seconds): {:02d}:{:02d}'.format(
                minutes, seconds
            )


class QuoteView:

    def __init__(self, quote: Quote):
        self._quote_adapter = QuoteAdapter(quote)

    async def _watcher(self):
        while True:
            self._countdown_label.value = (
                self._quote_adapter.get_time_left_label()
            )
            self._execute_trade_btn.disabled = self._quote_adapter.quote.expired  # noqa
            await asyncio.sleep(1)

    def display(self):
        self._execute_trade_btn = widgets.Button(
            description='Execute Trade', disabled=False,
            button_style='danger',
        )

        self._execute_trade_btn.on_click(self._execute_trade)

        self._executing_unit = widgets.Text(
            value='', placeholder='Optional (for user side tracking)',
            disabled=False,
        )

        self._countdown_label = widgets.Label()

        self._log_output = widgets.Output(
            layout={'border': '1px solid black'}
        )

        # Submit out state watcher to the gui loop
        # Sets the state of the button and runs the
        # count down.
        self._client._loop.create_task(self._watcher())

        display(
            widgets.VBox([
                # Basic data types
                *self._quote_adapter.quote._widgets.values(),
                # Our stuff
                self._executing_unit,
                self._execute_trade_btn,
                self._countdown_label,
                self._log_output,
            ])
        )

    def _execute_trade(self, event):
        # Coerce to none, rather than empty string
        executing_unit = (
            None if self._executing_unit.value == ''
            else self._executing_unit.value
        )

        quote = self._quote_adapter.quote
        trade_response = quote.execute_trade(executing_unit)

        self._log_output.append_stdout(
            'Trade completed. Details logged'
            ' in `client.history.completed_trades` \n'
        )

        get_ipython().user_ns['latest_trade'] = trade_response
        cell_creator.write(
            code='latest_trade',
            execute=True
        )

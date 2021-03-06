import ipywidgets as widgets
from IPython import get_ipython
from IPython.display import display

from b2c2.models import SideEnum, RequestForQuote, Instrument
from b2c2.views import cell_creator, BaseView


class InstrumentView(BaseView):
    def __init__(self):
        # Stateful widgets
        selector = self.selector = widgets.Select(
            options=[], value=None, disabled=False,
            layout=widgets.Layout(height='revert', width='100%')
        )

        quantity_slider = widgets.IntSlider(
            value=1, min=1, step=1,
            description='Quantity:',
            readout=True, layout=widgets.Layout(width='revert')
        )

        side = widgets.RadioButtons(
            options=[(s, s.value) for s in SideEnum],
            disabled=False, description='Side:'
        )

        client_request_for_quote = widgets.Text(
            value='', placeholder='Optional (for user side tracking)',
            description='Client RFQ ID:', disabled=False
        )

        self.stateful_widgets = {
            'instrument': selector,
            'quantity': quantity_slider,
            'side': side,
            'client_rfq_id': client_request_for_quote,
        }

        # Actions
        request_quote_btn = widgets.Button(
            description='Create Quote',
            disabled=False,
            button_style='',
            icon='check'
        )
        request_quote_btn.on_click(self._get_quote)

        create_monitor_btn = widgets.Button(
            description='Create Monitor',
            disabled=False,
            button_style='',
            icon='check'
        )

        # Layout stuff
        instrument_select = widgets.Box(
            [selector],
            layout=widgets.Layout(flex='0 1 100%')
        )

        rfq_create = widgets.VBox(
            [
                quantity_slider,
                side,
                client_request_for_quote,
                widgets.HBox([
                    request_quote_btn,
                    create_monitor_btn
                ])
            ],
            layout=widgets.Layout(flex='0 1 100%')
        )

        self.root = widgets.VBox(children=[
            widgets.HBox(children=[
                instrument_select, rfq_create
            ])
        ])

    def display(self):
        instruments_response = self._client.get_instruments().__root__
        self.selector.options = instruments_response
        display(self.root)

    def _get_state(self):
        client_rfq_id = self.stateful_widgets['client_rfq_id'].value
        client_rfq_id = None if client_rfq_id == '' else client_rfq_id

        return {
            'instrument': self.stateful_widgets['instrument'].value.name,
            'quantity': self.stateful_widgets['quantity'].value,
            'side': self.stateful_widgets['side'].value,
            'client_rfq_id': client_rfq_id,
        }

    def instrument(self) -> Instrument:
        """
        :return: The selected instrument
        """
        return self.stateful_widgets['instrument'].value

    def request_for_quote(self) -> RequestForQuote:
        """
        :return: The currently configured request for quote
        """
        state = self._get_state()

        rfq = RequestForQuote(
            **state,
        )

        rfq.bind_to_client(self._client)

        return rfq

    def _get_quote(self, event):
        quote = self._client.post_request_for_quote(
            self.request_for_quote(),
        )

        get_ipython().user_ns['quote'] = quote
        cell_creator.write(
            code='quote',
            execute=True
        )

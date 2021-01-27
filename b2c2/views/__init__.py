import asyncio
import warnings

from ipykernel.comm import Comm
from IPython import get_ipython
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from b2c2.client import B2C2APIClient


shell = get_ipython()


def _create_comm_with_confirm_resp(name):
    """
    Wait for the extension to send back
    it's heartbeat.
    """
    future = asyncio.Future()
    comm = Comm(name)

    @comm.on_msg
    def on_message(msg):
        if msg['content']['data'].get('setup'):
            future.set_result(comm)
            # Unset the callback
            comm.on_msg(None)

    return future


async def _create_comm(name):
    """
    Create a comm channel, but wait for
    the frontend comm to communicate back.
    """
    comm = None
    while not comm:
        try:
            comm = await asyncio.wait_for(
                _create_comm_with_confirm_resp(name),
                timeout=2
            )
            if comm:
                return comm
        except asyncio.TimeoutError:
            pass


async def _get_create_cell_comm():
    """
    Probably the most reliable way to establish
    communication between the Jupyter FE and the
    IPython kernel.

    NOTE: this blocks for a maximum of 5 seconds.
    """
    try:
        return await asyncio.wait_for(
            _create_comm('create_cell'), timeout=6
        )
    except asyncio.TimeoutError:
        return None


# I literally could not find a way to wait on this properly
#
# https://github.com/ipython/ipython/issues/12786
_comm_future = asyncio.ensure_future(_get_create_cell_comm())


class _CellCreator:
    """
    Creating a command line GUI was a real pain.

    I wanted to be able to create separate outputs and
    views automagically. The only way to do run the output
    immediately was to create an extension to Jupyter.

    The fallback methods do not run reliably (let alone
    automatically execute).

    I'm sorry if this was too much for a code test.
    """
    @property
    def comm(self):
        try:
            return _comm_future.result()
        except asyncio.InvalidStateError:
            return None

    @property
    def has_extension(self):
        return bool(self.comm)

    @property
    def has_ipython(self):
        return bool(shell)

    @property
    def has_gui(self):
        if shell:
            shell_cls_name = shell.__class__.__name__
            # Probably means a gui
            if shell_cls_name == 'ZMQInteractiveShell':
                return True   # Jupyter notebook

        return False

    def write_jupyter(self, code, execute):
        self.comm.send(dict(
            code=code,
            execute=execute
        ))

    def write_jupyter_no_extension(self, code, *args):
        shell.payload_manager.write_payload(
            dict(
                source='set_next_input',
                text=code,
                replace=False,
            ),
            single=False
        )

    def write_ipython(self, code, *args):
        warnings.warn(
            'Probable use of GUI in command line. '
            'Not supported, but falling back to set_next_input.',
            UserWarning
        )

        shell.set_next_input(code)

    def write_terminal(self, code, *args):
        raise NotImplementedError(
            'Attempt to write next output to next line in basic terminal.'
        )

    def _get_writer(self):
        if self.has_gui and self.has_extension:
            return self.write_jupyter
        elif self.has_gui:
            return self.write_jupyter_no_extension
        elif self.has_ipython:
            return self.write_ipython
        else:
            return self.write_terminal

    def write(self, code, execute=False):
        # Async because it depends on an
        # async resource
        writer = self._get_writer()
        writer(code, execute)


cell_creator = _CellCreator()


class BaseView:
    _client: 'B2C2APIClient'

    def _ipython_display_(self):
        self.display()

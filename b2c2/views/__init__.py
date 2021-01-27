import asyncio
import warnings
import threading
import time

from async_property import async_property
from IPython import get_ipython
from tornado.ioloop import IOLoop
from ipykernel.comm import Comm
import sys


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
        sys.stderr.write('here\n')
        sys.stderr.flush()
        msgs.append(('on_message', msg))
     #  if msg['content']['data'].get('setup'):
     #      future.set_result(comm)
     #      # Unset the callback
     #      comm.on_msg(None)

    return future


async def create_comm(name):
    """
    Create a comm channel, but wait for
    the frontend comm to communicate back.
    """
    comm = None

    while not comm:
        try:
            comm = await asyncio.wait_for(
                _create_comm_with_confirm_resp(name),
                timeout=10
            )
            if comm:
                 return comm
        except asyncio.TimeoutError:
            await asyncio.sleep(1)


async def get_create_cell_comm():
    """
    Probably the most reliable way to establish
    communication between the Jupyter FE and the
    IPython kernel.

    NOTE: this blocks for a maximum of 5 seconds.
    """
    try:
        return await asyncio.wait_for(
            create_comm('create_cell'), timeout=5
        )
    except asyncio.TimeoutError:
        return None


class CellCreator:
    """
    Creating a command line GUI was a real pain.

    I wanted to be able to create separate outputs and
    views automagically. The only way to do run the output
    immediately was to create an extension to Jupyter.

    The fallback methods do not run reliably (let alone
    automatically execute).

    I'm sorry if this was too much for a code test.
    """
    def __init__(self, comm):
        self._comm = comm
    
    @async_property
    async def comm(self):
        if self._comm is None:
            self._comm = await get_create_cell_comm()
        else:
            self._comm = False

        if self._comm:
            return self._comm

    @async_property
    async def has_extension(self):
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
                text=contents,
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
        raise NotImplemented(
            'Attempt to write next output to next line in basic terminal.'
        )

    async def _get_writer(self):
        if self.has_gui and await self.has_extension:
            return self.write_jupyter
        elif self.has_gui:
            return self.write_jupyter_no_extension
        elif self.has_ipython:
            return self.write_ipython
        else:
            return self.write_terminal

    async def write(self, code, execute=False):
        # Async because it depends on an
        # async resource
        writer = await self._get_writer()
        writer(code, execute)

    @classmethod
    async def create_async(cls):
        comm = await create_comm('create_cell')
        return CellCreator(comm)

import os
import subprocess

from distutils.util import strtobool
from setuptools import setup
from setuptools.command.install import install


current_dir = os.path.dirname(os.path.abspath(__file__))

class PostInstallCommand(install):
    """
    Automatically load the Jupyter extension on install
    """
    user_options = [
        (
            'no-install-jupyter-ext', None,
            'Should install jupyter extension.'
        ),
        *install.user_options
    ]

    def initialize_options(self):
        super().initialize_options()
        self.no_install_jupyter_ext = None

    def run(self):
        super().run()                                             

        if not self.no_install_jupyter_ext:
            jupyter_script = os.path.join(
                self.install_scripts, 'jupyter-nbextension'
            )   

            jupyter_extension = os.path.join(
                current_dir, 'b2c2/b2c2_jupyter_extension.js'
            )

            subprocess.call([
                jupyter_script,
                'install',
                jupyter_extension
            ])

            subprocess.call([
                jupyter_script,
                'enable',
                'b2c2_jupyter_extension'
            ])


# In a real production package I would do some snapshot
# testing of requirements where pretend to go back in
# time and test the oldest version of compatible packages.

# But that's too laborious for this and I can only
# guarantee that this will work in the same env as mine.

# So please run this in a clean virtualenv (otherwise you
# might find yourself debugging Jupyter and IPython).

setup(
    name='b2c2_client',
    version='0.0.0',
    install_requires=[
        'pydantic~=1.7.3',
        'devtools~=0.6.1',
        'requests~=2.25.1',
        'websockets~=8.1',
    ],
    extras_require={
        'gui': [
            'notebook~=6.2.0',
            'ipywidgets~=7.6.3',
        ],
        'dev': [
            'mypy==0.800',
            'flake8~=3.8.4',
            'pytest-mypy~=0.8.0',
            'pytest-flake8~=1.0.7',
        ]
    },
    cmdclass={
        'install': PostInstallCommand,
    },
)

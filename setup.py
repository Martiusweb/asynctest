# coding: utf-8
"""
asynctest setup script.

We rely on setuptools >= 30.3.0 to read setup.cfg, but provide a minimal
support with distutils.
"""

args = {
    "name": "asynctest",
    "packages": ["asynctest"],
}


def read_version():
    import configparser
    import os

    with open(os.path.join(os.path.dirname(__file__), "setup.cfg")) as cfg:
        config = configparser.ConfigParser()
        config.read_file(cfg, source="setup.cfg")
        return config['metadata']['version']


try:
    # We don't use this method, but it allows to detect if setuptools will read
    # the setup.cfg file or if we need to find the version by ourselves.
    from setuptools.config import read_configuration  # noqa
except ImportError:
        args['version'] = read_version()


if __name__ == "__main__":
    try:
        from setuptools import setup
    except ImportError:
        from distutils.core import setup

    setup(**args)

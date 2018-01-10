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

if __name__ == "__main__":
    from setuptools import setup
    setup(**args)

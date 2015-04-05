# coding: utf-8
"""
aiotest setup script.

Currently, only basic distribution features are required, hence distutils is
sufficient, and we won't use setuptools.
"""

from distutils.core import setup

setup(
    name="aiotest",
    version="0.1.0",
    description="Enhance the standard unittest package with features for "
                "testing asyncio libraries",
    author="Martin Richard",
    author_email="martius@martiusweb.net",
    url="https://github.com/Martiusweb/aiotest/",
    packages=["aiotest"]
)

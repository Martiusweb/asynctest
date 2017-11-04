# coding: utf-8
"""
asynctest setup script.

Currently, only basic distribution features are required, hence distutils is
sufficient, and we won't use setuptools.
"""

from setuptools import setup

args = {
    "name": "asynctest",
    "version": "0.11.1",
    "description": "Enhance the standard unittest package with features for "
                   "testing asyncio libraries",
    "author": "Martin Richard",
    "author_email": "martius@martiusweb.net",
    "url": "https://github.com/Martiusweb/asynctest/",
    "license": "Apache 2",
    "packages": ["asynctest"],
    "classifiers": [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    "keywords": 'unittest test testing asyncio tulip selectors async mock',
}

if __name__ == "__main__":
    setup(**args)

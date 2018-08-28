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

    try:
        from warnings import warn
        warn("CoroutineMock has been renamed to CoroutineFunctionMock, the alias "
             "will be removed in the future", DeprecationWarning)
    except DeprecationWarning as e:
        import sys
        print("DeprecationWarning:", str(e), file=sys.stderr)

.. automodule:: asynctest.mock

    .. toctree::
       :maxdepth: 2

    Mock classes
    ~~~~~~~~~~~~

    .. autoclass:: asynctest.Mock
        :members:
        :undoc-members:

    .. autoclass:: asynctest.NonCallableMock
        :members:
        :undoc-members:

    .. autoclass:: asynctest.MagicMock
        :members:
        :undoc-members:

    .. autoclass:: asynctest.CoroutineMock
        :members:
        :undoc-members:

    Patch
    ~~~~~

    .. autofunction:: asynctest.patch

    .. function:: asynctest.patch.object(target, attribute, new=DEFAULT, \
                    spec=None, create=False, spec_set=None, autospec=None, \
                    new_callable=None, **kwargs)

        Patch the named member (``attribute``) on an object (``target``) with
        a mock object, in the same fashion as :func:`~asynctest.patch`.

        See :func:`~asynctest.patch` and :func:`unittest.mock.patch.object`.

    .. function:: asynctest.patch.mutiple(target, spec=None, create=False, \
                    spec_set=None, autospec=None, new_callable=None, **kwargs)

        Perform multiple patches in a single call. It takes the object to be
        patched (either as an object or a string to fetch the object by
        importing) and keyword arguments for the patches.

        See :func:`~asynctest.patch` and :func:`unittest.mock.patch.multiple`.

    .. function:: asynctest.patch.dict(in_dict, values=(), clear=False, **kwargs)

        Patch a dictionary, or dictionary like object, and restore the
        dictionary to its original state after the test.

        :param in_dict: dictionary like object, or string referencing the
                        object to patch.
        :param values: a dictionary of values or an iterable of (key, value)
                       pairs to set in the dictionary.
        :param clear: if ``True``, in_dict will be cleared before the new
                      values are set.

        See :func:`unittest.mock.patch.dict`.

    Helpers
    ~~~~~~~

    .. autofunction:: asynctest.mock_open

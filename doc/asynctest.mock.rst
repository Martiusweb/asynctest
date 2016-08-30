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

    .. autodata:: asynctest.GLOBAL

    .. autodata:: asynctest.LIMITED

    .. autofunction:: asynctest.patch

    .. function:: asynctest.patch.object(target, attribute, new=DEFAULT, \
                    spec=None, create=False, spec_set=None, autospec=None, \
                    new_callable=None, scope=asynctest.GLOBAL, **kwargs)

        Patch the named member (``attribute``) on an object (``target``) with
        a mock object, in the same fashion as :func:`~asynctest.patch`.

        See :func:`~asynctest.patch` and :func:`unittest.mock.patch.object`.

    .. function:: asynctest.patch.mutiple(target, spec=None, create=False, \
                    spec_set=None, autospec=None, new_callable=None, \
                    scope=asynctest.global, **kwargs)

        Perform multiple patches in a single call. It takes the object to be
        patched (either as an object or a string to fetch the object by
        importing) and keyword arguments for the patches.

        See :func:`~asynctest.patch` and :func:`unittest.mock.patch.multiple`.

    .. function:: asynctest.patch.dict(in_dict, values=(), clear=False, \
                    scope=asynctest.GLOBAL, **kwargs)

        Patch a dictionary, or dictionary like object, and restore the
        dictionary to its original state after the test.

        Its behavior can be controlled on decorated generators and coroutines with
        ``scope``.

        .. versionadded:: 0.8 patch into generators and coroutines with
                        a decorator.

        :param in_dict: dictionary like object, or string referencing the
                        object to patch.
        :param values: a dictionary of values or an iterable of (key, value)
                       pairs to set in the dictionary.
        :param clear: if ``True``, in_dict will be cleared before the new
                      values are set.
        :param scope: :const:`asynctest.GLOBAL` or :const:`asynctest.LIMITED`,
            controls when the patch is activated on generators and coroutines

        :see: :func:`~asynctest.patch` (details about ``scope``) and
            :func:`unittest.mock.patch.dict`.

    Helpers
    ~~~~~~~

    .. autofunction:: asynctest.mock_open

    .. autofunction:: asynctest.return_once

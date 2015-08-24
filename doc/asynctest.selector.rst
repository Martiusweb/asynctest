.. automodule:: asynctest.selector

    .. toctree::
       :maxdepth: 2

    Mocking file-like objects
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    .. autoclass:: asynctest.FileMock
        :members:
        :undoc-members:

    .. autoclass:: asynctest.SocketMock
        :members:
        :undoc-members:
        :show-inheritance:

    .. autoclass:: asynctest.SSLSocketMock
        :members:
        :undoc-members:
        :show-inheritance:

    .. autoclass:: asynctest.FileDescriptor
        :members:
        :undoc-members:
        :show-inheritance:

    Helpers
    #######

    .. autofunction:: asynctest.fd

    .. autofunction:: asynctest.isfilemock

    Mocking the selector
    ~~~~~~~~~~~~~~~~~~~~

    .. autoclass:: asynctest.TestSelector
        :members:
        :undoc-members:

    Helpers
    #######

    .. autofunction:: asynctest.set_read_ready

    .. autofunction:: asynctest.set_write_ready

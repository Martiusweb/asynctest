"""Tests for the Hypothesis integration, which wraps async functions in a
sync shim for Hypothesis.
"""

import asynctest

from hypothesis import given, strategies as st


class TestHypothesisIntegration(asynctest.TestCase):

    @given(st.integers())
    async def test_mark_inner(self, n):
        assert isinstance(n, int)


import asyncio
from contextvars import copy_context
from queue import Queue
from threading import Thread
import unittest

import jag


class JagTestCase(unittest.TestCase):
    def tearDown(self):
        jag.__getattr__.cache_clear()

    def test_unset(self):
        with self.assertRaises(KeyError):
            jag.get_hey()

    def test_inside(self):
        with jag.define(hey=1):
            self.assertEqual(jag.get_hey(), 1)

    def test_nested(self):
        with jag.define(hey=1):
            with jag.define(hey=2):
                self.assertEqual(jag.get_hey(), 2)

    def test_after(self):
        with jag.define(hey=1):
            with jag.define(hey=2):
                pass
            self.assertEqual(jag.get_hey(), 1)

    def test_remember_doc_string(self):
        jag.get_hey.__doc__ = "Hey."
        self.assertEqual(jag.get_hey.__doc__, "Hey.")

    def test_only_getters(self):
        with self.assertRaises(AttributeError):
            jag.hey

    def test_threading_fresh(self):
        q = Queue()

        def run():
            try:
                q.put(jag.get_hey())
            except Exception:
                q.put(None)

        with jag.define(hey=1):
            t = Thread(target=run)
            t.start()
            t.join()
        self.assertEqual(q.get_nowait(), None)

    def test_threading_inherit(self):
        q = Queue()

        def run():
            q.put(jag.get_hey())

        with jag.define(hey=1):
            t = Thread(target=copy_context().run, args=(run,))
            t.start()
            t.join()
        self.assertEqual(q.get_nowait(), 1)

    def test_threading_set(self):
        q = Queue()

        def run():
            with jag.define(hey=2):
                q.put(jag.get_hey())

        with jag.define(hey=1):
            t = Thread(target=copy_context().run, args=(run,))
            t.start()
            t.join()
        self.assertEqual(q.get_nowait(), 2)

    def test_threading_no_leak(self):
        q1 = Queue()
        q2 = Queue()

        def run():
            with jag.define(hey=2):
                q1.put(None)
                q2.get(timeout=1)

        with jag.define(hey=1):
            t = Thread(target=copy_context().run, args=(run,))
            t.start()
            q1.get(timeout=1)
            hey = jag.get_hey()
        q2.put(None)
        t.join()
        self.assertEqual(hey, 1)

    def test_asyncio_inherit(self):
        async def coro():
            q = asyncio.Queue()

            async def run():
                await q.put(jag.get_hey())

            with jag.define(hey=1):
                await asyncio.create_task(run())
            self.assertEqual(q.get_nowait(), 1)

        asyncio.run(coro())

    def test_asyncio_set(self):
        async def coro():
            q = asyncio.Queue()

            async def run():
                with jag.define(hey=2):
                    await q.put(jag.get_hey())

            with jag.define(hey=1):
                await asyncio.create_task(run())
            self.assertEqual(q.get_nowait(), 2)

        asyncio.run(coro())

    def test_asyncio_no_leak(self):
        async def coro():
            q1 = asyncio.Queue()
            q2 = asyncio.Queue()

            async def run():
                with jag.define(hey=2):
                    await q1.put(None)
                    await q2.get()

            with jag.define(hey=1):
                t = asyncio.create_task(run())
                await q1.get()
                hey = jag.get_hey()
            await q2.put(None)
            await t
            self.assertEqual(hey, 1)

        asyncio.run(coro())

    def test_pkg(self):
        with jag.pkg.pkgname.define(hey=1):
            self.assertEqual(jag.pkg.pkgname.get_hey(), 1)

    def test_pkg_remember_doc_string(self):
        jag.pkg.pkgname.get_hey.__doc__ = "Hey."
        self.assertEqual(jag.pkg.pkgname.get_hey.__doc__, "Hey.")

    def test_pkg_only_getters(self):
        with self.assertRaises(AttributeError):
            jag.pkg.pkgname.hey

# -*- coding: utf-8 -*-
"""@@go/<suffix> redirects to the target url and counts the click."""

from BTrees.Length import Length
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser
from ZODB.FileStorage import FileStorage

import persistent.mapping
import tempfile
import transaction
import unittest
import ZODB


class GoViewTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        api.user.create(email="alice@example.org", username="alice", password="secret-alice")
        login(self.portal, "alice")
        self.shorturl = api.content.create(
            container=self.container,
            type="ShortUrl",
            title="AnorgChem",
            suffix="AnorgChem",
            target_url="https://www.plone.org/target?a=1",
        )
        transaction.commit()

    def browser(self, credentials=None):
        browser = Browser(self.layer["app"])
        browser.followRedirects = False
        browser.raiseHttpErrors = False
        if credentials:
            browser.addHeader("Authorization", "Basic {0}:{1}".format(*credentials))
        return browser

    def go(self, path, credentials=None):
        browser = self.browser(credentials)
        browser.open(self.portal.absolute_url() + "/@@go" + path)
        return browser

    def clicks(self):
        transaction.begin()
        return self.container["anorgchem"].clicks

    def assertRedirected(self, browser):
        self.assertEqual(browser.headers["status"], "302 Found")
        self.assertEqual(browser.headers["location"], "https://www.plone.org/target?a=1")

    def test_redirect_anonymous(self):
        browser = self.go("/AnorgChem")
        self.assertRedirected(browser)
        self.assertEqual(browser.headers["cache-control"], "no-store")
        self.assertEqual(self.clicks(), 1)

    def test_redirect_case_insensitive(self):
        for suffix in ("anorgchem", "ANORGCHEM", "aNoRgChEm"):
            self.assertRedirected(self.go("/" + suffix))
        self.assertEqual(self.clicks(), 3)

    def test_redirect_logged_in(self):
        # the click is a write during a GET request - plone.protect must not
        # turn it into a "confirm action" page for logged-in users
        for credentials in (("alice", "secret-alice"), ("admin", "secret")):
            self.assertRedirected(self.go("/AnorgChem", credentials))
        self.assertEqual(self.clicks(), 2)

    def test_not_found(self):
        for path in ("/unknown", "", "/", "/AnorgChem/more", "/a.b", "/%C3%A4"):
            browser = self.go(path)
            self.assertEqual(browser.headers["status"], "404 Not Found", path)
        self.assertEqual(self.clicks(), 0)

    def test_virtual_hosting(self):
        # the rewrite rule documented in the README (real Zope instances have
        # a VirtualHostMonster by default, the test fixture doesn't)
        from Products.SiteAccess.VirtualHostMonster import manage_addVirtualHostMonster

        manage_addVirtualHostMonster(self.layer["app"])
        transaction.commit()
        browser = self.browser()
        browser.open(
            "http://localhost/VirtualHostBase/https/go.example.org:443/plone"
            "/VirtualHostRoot/@@go/AnorgChem"
        )
        self.assertRedirected(browser)
        browser.open(
            "http://localhost/VirtualHostBase/https/go.example.org:443/plone"
            "/VirtualHostRoot/@@go/unknown"
        )
        self.assertEqual(browser.headers["status"], "404 Not Found")

    def test_view_shows_clicks(self):
        self.go("/AnorgChem")
        self.go("/AnorgChem")
        browser = self.browser(("alice", "secret-alice"))
        browser.open(self.container.absolute_url() + "/anorgchem")
        self.assertIn('<td id="clicks">2</td>', browser.contents)


class ClicksTest(unittest.TestCase):

    def test_set_clicks(self):
        # e.g. when migrating the clicks of the legacy system
        from mbarde.shorturls.content.short_url import ShortUrl

        obj = ShortUrl()
        self.assertEqual(obj.clicks, 0)
        obj.clicks = 41
        obj.countClick()
        self.assertEqual(obj.clicks, 42)
        self.assertIsInstance(obj._clicks, Length)

    def test_concurrent_clicks_dont_conflict(self):
        # two requests counting a click on the same short url at the same time
        with tempfile.TemporaryDirectory() as tmp:
            db = ZODB.DB(FileStorage(tmp + "/Data.fs"))
            try:
                tm1 = transaction.TransactionManager()
                tm2 = transaction.TransactionManager()
                conn1 = db.open(transaction_manager=tm1)
                root1 = conn1.root()
                root1["counter"] = persistent.mapping.PersistentMapping(clicks=Length(0))
                tm1.commit()

                conn2 = db.open(transaction_manager=tm2)
                conn2.root()["counter"]["clicks"].change(1)
                root1["counter"]["clicks"].change(1)
                tm2.commit()
                tm1.commit()  # would raise a ConflictError with a plain int

                tm1.begin()
                self.assertEqual(root1["counter"]["clicks"](), 2)
            finally:
                db.close()

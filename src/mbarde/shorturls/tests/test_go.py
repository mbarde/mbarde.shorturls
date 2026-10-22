# -*- coding: utf-8 -*-
"""@@go/<suffix> redirects to the target url and counts the click."""

from BTrees.Length import Length
from datetime import date
from mbarde.shorturls.content.short_url import ClickCounter
from mbarde.shorturls.content.short_url import ShortUrl
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser
from ZODB.FileStorage import FileStorage

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
        self.assertIsNone(self.shorturl.last_clicked)
        browser = self.go("/AnorgChem")
        self.assertRedirected(browser)
        self.assertEqual(browser.headers["cache-control"], "no-store")
        self.assertEqual(self.clicks(), 1)
        self.assertEqual(self.container["anorgchem"].last_clicked, date.today())

    def test_head_not_counted(self):
        browser = self.browser()
        response = browser.testapp.head(
            self.portal.absolute_url() + "/@@go/AnorgChem", expect_errors=True
        )
        self.assertEqual(response.status, "302 Found")
        self.assertEqual(response.headers["Location"], "https://www.plone.org/target?a=1")
        self.assertEqual(self.clicks(), 0)
        self.assertIsNone(self.container["anorgchem"].last_clicked)
        # a GET afterwards is counted
        self.assertRedirected(self.go("/AnorgChem"))
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

    NOT_FOUND = ("/unknown", "/AnorgChem/more", "/a.b", "/%C3%A4", "", "/")

    def test_not_found_redirects_to_fallback_target_url(self):
        api.portal.set_registry_record(
            "mbarde.shorturls.fallback_target_url", "https://www.example.org/not-found"
        )
        transaction.commit()
        for path in self.NOT_FOUND:
            browser = self.go(path)
            self.assertEqual(browser.headers["status"], "302 Found", path)
            self.assertEqual(browser.headers["location"], "https://www.example.org/not-found", path)
            self.assertEqual(browser.headers["cache-control"], "no-store", path)
        self.assertEqual(self.clicks(), 0)

    def test_not_found_without_fallback_target_url(self):
        # the base url is not used as fallback
        api.portal.set_registry_record("mbarde.shorturls.base_url", "https://go.example.org")
        transaction.commit()
        for path in self.NOT_FOUND:
            browser = self.go(path)
            self.assertEqual(browser.headers["status"], "404 Not Found", path)
        self.assertEqual(self.clicks(), 0)

    def test_disabled(self):
        api.portal.set_registry_record(
            "mbarde.shorturls.fallback_target_url", "https://www.example.org/not-found"
        )
        api.content.transition(obj=self.shorturl, transition="disable")
        transaction.commit()
        browser = self.go("/AnorgChem")
        self.assertEqual(browser.headers["location"], "https://www.example.org/not-found")
        self.assertEqual(self.clicks(), 0)

        api.content.transition(obj=self.container["anorgchem"], transition="enable")
        transaction.commit()
        self.assertRedirected(self.go("/AnorgChem"))
        self.assertEqual(self.clicks(), 1)

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
        self.assertIn(api.portal.get_localized_time(datetime=date.today()), browser.contents)


class ClicksTest(unittest.TestCase):

    def test_clicks_and_last_clicked(self):
        obj = ShortUrl()
        self.assertEqual(obj.clicks, 0)
        self.assertIsNone(obj.last_clicked)
        obj.countClick(today=date(2026, 10, 1))
        obj.countClick(today=date(2026, 10, 1))
        obj.countClick(today=date(2026, 10, 3))
        self.assertEqual(obj.clicks, 3)
        self.assertEqual(obj.last_clicked, date(2026, 10, 3))

    def test_set(self):
        # e.g. when migrating clicks / last click of the legacy system
        obj = ShortUrl()
        obj.clicks = 41
        obj.last_clicked = date(2020, 5, 17)
        self.assertEqual(obj.clicks, 41)
        self.assertEqual(obj.last_clicked, date(2020, 5, 17))
        obj.countClick(today=date(2026, 10, 1))
        self.assertEqual(obj.clicks, 42)
        self.assertEqual(obj.last_clicked, date(2026, 10, 1))
        obj.last_clicked = None
        self.assertIsNone(obj.last_clicked)

    def test_counter_of_older_versions(self):
        obj = ShortUrl()
        obj._clicks = Length(7)
        self.assertEqual(obj.clicks, 7)
        self.assertIsNone(obj.last_clicked)
        obj.countClick(today=date(2026, 10, 1))
        self.assertIsInstance(obj._clicks, ClickCounter)
        self.assertEqual(obj.clicks, 8)
        self.assertEqual(obj.last_clicked, date(2026, 10, 1))

    def withDB(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = ZODB.DB(FileStorage(tmp.name + "/Data.fs"))
        self.addCleanup(db.close)
        return db

    def test_click_only_writes_counter(self):
        # a click (also on a new day) doesn't write the short url itself
        db = self.withDB()
        tm = transaction.TransactionManager()
        root = db.open(transaction_manager=tm).root()
        root["shorturl"] = obj = ShortUrl()
        obj.countClick(today=date(2026, 10, 1))
        tm.commit()
        obj.countClick(today=date(2026, 10, 2))
        self.assertFalse(obj._p_changed)
        self.assertTrue(obj._clicks._p_changed)
        tm.commit()

    def test_concurrent_clicks_dont_conflict(self):
        # two requests counting a click on the same short url at the same time
        db = self.withDB()
        tm1 = transaction.TransactionManager()
        tm2 = transaction.TransactionManager()
        root1 = db.open(transaction_manager=tm1).root()
        root1["shorturl"] = ShortUrl()
        root1["shorturl"].countClick(today=date(2026, 10, 1))
        tm1.commit()

        root2 = db.open(transaction_manager=tm2).root()
        root2["shorturl"].countClick(today=date(2026, 10, 3))
        root1["shorturl"].countClick(today=date(2026, 10, 2))
        tm2.commit()
        tm1.commit()  # would raise a ConflictError without conflict resolution

        tm1.begin()
        self.assertEqual(root1["shorturl"].clicks, 3)
        self.assertEqual(root1["shorturl"].last_clicked, date(2026, 10, 3))

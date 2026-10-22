# -*- coding: utf-8 -*-
"""Default view of short url containers."""

from datetime import date
from DateTime import DateTime
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser

import re
import transaction
import unittest


class ShortUrlContainerViewTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(
            container=self.portal, type="ShortUrlContainer", id="s", title="Short URLs"
        )
        for username in ("alice", "bob", "moderator"):
            api.user.create(
                email=username + "@example.org", username=username, password="secret-" + username
            )
        api.user.grant_roles(username="moderator", obj=self.container, roles=["Editor"])
        self.createShortUrl("alice", "Alice1", day=1)
        self.createShortUrl("alice", "alice2", day=2)
        self.createShortUrl("bob", "bob1", day=3)
        logout()
        transaction.commit()

    def createShortUrl(self, username, suffix, day):
        login(self.portal, username)
        obj = api.content.create(
            container=self.container,
            type="ShortUrl",
            title=suffix,
            suffix=suffix,
            target_url="https://www.plone.org/" + suffix,
        )
        obj.creation_date = DateTime(2026, 10, day)
        obj.reindexObject()
        return obj

    def browser(self, username):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        browser.addHeader("Authorization", "Basic {0}:secret-{0}".format(username))
        return browser

    def listedSuffixes(self, browser):
        return re.findall(r'class="short-url-item"[^>]*>([^<]+)<', browser.contents)

    def test_default_view(self):
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        self.assertIn('id="short-urls"', browser.contents)

    def test_users_see_own_short_urls(self):
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        # newest first
        self.assertEqual(self.listedSuffixes(browser), ["alice2", "Alice1"])
        browser = self.browser("bob")
        browser.open(self.container.absolute_url())
        self.assertEqual(self.listedSuffixes(browser), ["bob1"])

    def test_moderator_sees_all(self):
        browser = self.browser("moderator")
        browser.open(self.container.absolute_url())
        self.assertEqual(self.listedSuffixes(browser), ["bob1", "alice2", "Alice1"])

    def test_columns(self):
        api.portal.set_registry_record("mbarde.shorturls.base_url", "https://go.example.org")
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        self.assertIn('href="https://go.example.org/Alice1"', browser.contents)
        self.assertIn('href="https://www.plone.org/Alice1"', browser.contents)
        self.assertIn('href="http://nohost/plone/s/alice1"', browser.contents)

    def test_last_clicked_column(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container["alice1"].last_clicked = date(2026, 10, 3)
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        self.assertEqual(
            re.findall(r'class="text-nowrap last-clicked">([^<]*)<', browser.contents),
            ["", "Oct 03, 2026"],
        )

    def test_no_short_url_column_without_base_url(self):
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        self.assertNotIn(">Short URL</th>", browser.contents)

    def test_add_button(self):
        browser = self.browser("bob")
        browser.open(self.container.absolute_url())
        browser.getLink(id="short-url-add").click()
        self.assertTrue(browser.url.endswith("/s/++add++ShortUrl"))

    def test_empty(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, "test-user")
        api.content.create(container=self.portal, type="ShortUrlContainer", id="empty")
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.portal.absolute_url() + "/empty")
        self.assertIn('id="short-urls-empty"', browser.contents)
        self.assertNotIn('id="short-urls"', browser.contents)

    def test_batching(self):
        for i in range(25):
            self.createShortUrl("alice", "batch{0:02d}".format(i), day=10 + i % 20)
        logout()
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        first_page = self.listedSuffixes(browser)
        self.assertEqual(len(first_page), 20)
        browser.open(self.container.absolute_url() + "?b_start:int=20")
        second_page = self.listedSuffixes(browser)
        self.assertEqual(len(second_page), 7)
        self.assertEqual(len(set(first_page + second_page)), 27)

    def disable(self, suffix):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, "test-user")
        api.content.transition(obj=self.container[suffix.lower()], transition="disable")
        logout()
        transaction.commit()

    def tabCount(self, browser, state):
        match = re.search(
            r'id="short-url-tab-{0}".*?<span class="badge[^>]*>(\d+)</span>'.format(state),
            browser.contents,
            re.S,
        )
        return int(match.group(1))

    def test_disabled_tab(self):
        self.disable("alice2")
        browser = self.browser("alice")
        browser.open(self.container.absolute_url())
        self.assertEqual(self.listedSuffixes(browser), ["Alice1"])
        self.assertEqual(self.tabCount(browser, "active"), 1)
        self.assertEqual(self.tabCount(browser, "disabled"), 1)
        self.assertNotIn('id="short-urls-disabled-info"', browser.contents)

        browser.getLink(id="short-url-tab-disabled").click()
        self.assertEqual(self.listedSuffixes(browser), ["alice2"])
        self.assertIn('id="short-urls-disabled-info"', browser.contents)

    def test_disabled_tab_only_own(self):
        self.disable("alice2")
        browser = self.browser("bob")
        browser.open(self.container.absolute_url() + "?state=disabled")
        self.assertEqual(self.listedSuffixes(browser), [])
        self.assertIn('id="short-urls-empty"', browser.contents)
        self.assertEqual(self.tabCount(browser, "disabled"), 0)
        browser = self.browser("moderator")
        browser.open(self.container.absolute_url() + "?state=disabled")
        self.assertEqual(self.listedSuffixes(browser), ["alice2"])

    def test_invalid_state_shows_active(self):
        self.disable("alice2")
        browser = self.browser("alice")
        browser.open(self.container.absolute_url() + "?state=nonsense")
        self.assertEqual(self.listedSuffixes(browser), ["Alice1"])

    def test_disabled_tab_batching(self):
        for i in range(22):
            self.createShortUrl("alice", "off{0:02d}".format(i), day=10 + i % 20)
            setRoles(self.portal, TEST_USER_ID, ["Manager"])
            login(self.portal, "test-user")
            api.content.transition(obj=self.container["off{0:02d}".format(i)], transition="disable")
        logout()
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.container.absolute_url() + "?state=disabled")
        self.assertEqual(len(self.listedSuffixes(browser)), 20)
        # the batch navigation keeps the tab
        browser.getLink(url="b_start:int=20").click()
        self.assertIn("state=disabled", browser.url)
        self.assertEqual(len(self.listedSuffixes(browser)), 2)

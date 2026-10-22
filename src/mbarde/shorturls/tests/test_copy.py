# -*- coding: utf-8 -*-
"""Short urls can't be copied (the copy would duplicate the suffix)."""

from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_RESTAPI_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser
from zExceptions import Unauthorized

import requests
import transaction
import unittest


def createShortUrl(container, suffix):
    return api.content.create(
        container=container,
        type="ShortUrl",
        title=suffix,
        suffix=suffix,
        target_url="https://www.plone.org",
    )


def countShortUrls():
    catalog = api.portal.get_tool("portal_catalog")
    return len(catalog.unrestrictedSearchResults(portal_type="ShortUrl"))


class ShortUrlCopyTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        self.other = api.content.create(container=self.portal, type="ShortUrlContainer", id="t")
        self.shorturl = createShortUrl(self.container, "abc")

    def test_copy_short_url_refused(self):
        for target in (self.container, self.other):
            with self.assertRaises(Unauthorized):
                api.content.copy(source=self.shorturl, target=target)
        self.assertEqual(list(self.other.objectIds()), [])
        self.assertEqual(countShortUrls(), 1)

    def test_copy_container_with_short_urls_refused(self):
        with self.assertRaises(Unauthorized):
            api.content.copy(source=self.container, target=self.portal, id="s-copy")
        self.assertNotIn("s-copy", self.portal)
        self.assertEqual(countShortUrls(), 1)

    def test_copy_folder_containing_container_refused(self):
        folder = api.content.create(container=self.portal, type="Folder", id="institution")
        api.content.move(source=self.container, target=folder)
        with self.assertRaises(Unauthorized):
            api.content.copy(source=folder, target=self.portal, id="institution-copy")
        self.assertNotIn("institution-copy", self.portal)
        self.assertEqual(countShortUrls(), 1)

    def test_copy_empty_container_allowed(self):
        api.content.copy(source=self.other, target=self.portal, id="t-copy")
        self.assertIn("t-copy", self.portal)

    def test_move_allowed(self):
        api.content.move(source=self.shorturl, target=self.other)
        self.assertEqual(list(self.other.objectIds()), ["abc"])
        self.assertEqual(findShortUrlBySuffix("abc").getPath(), "/plone/t/abc")


class ShortUrlCopyBrowserTest(unittest.TestCase):
    """Copy & paste of a short url through the web as its owner."""

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        api.user.create(email="alice@example.org", username="alice", password="secret-alice")
        login(self.portal, "alice")
        createShortUrl(self.container, "abc")
        transaction.commit()

    def browser(self, username, password):
        browser = Browser(self.layer["app"])
        browser.addHeader("Authorization", "Basic {0}:{1}".format(username, password))
        return browser

    def test_paste_refused(self):
        # regular users may copy (Plone grants "Copy or Move" to them), the
        # paste of a short url is refused
        browser = self.browser("alice", "secret-alice")
        # use the toolbar links, they carry the CSRF token
        browser.open(self.container.absolute_url() + "/abc")
        browser.getLink(url="/abc/object_copy").click()
        self.assertIn("abc copied.", browser.contents)
        browser.open(self.container.absolute_url())
        browser.getLink(url="/s/object_paste").click()
        # plone.app.content's object_paste shows "Item(s) pasted." even if
        # the paste was refused (missing return in its except Unauthorized)
        transaction.begin()
        self.assertEqual(list(self.container.objectIds()), ["abc"])
        self.assertEqual(countShortUrls(), 1)


class ShortUrlCopyRestApiTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_RESTAPI_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        createShortUrl(self.container, "abc")
        transaction.commit()

    def test_copy_refused(self):
        response = requests.post(
            self.container.absolute_url() + "/@copy",
            json={"source": self.container.absolute_url() + "/abc"},
            headers={"Accept": "application/json"},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
        )
        self.assertEqual(response.status_code, 401, response.text)
        transaction.begin()
        self.assertEqual(list(self.container.objectIds()), ["abc"])

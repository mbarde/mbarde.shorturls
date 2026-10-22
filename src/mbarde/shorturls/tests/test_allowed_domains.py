# -*- coding: utf-8 -*-
"""Target urls can be restricted to domains (see control panel)."""

from mbarde.shorturls.browser.controlpanel import IMbardeShorturlsControlPanel
from mbarde.shorturls.browser.controlpanel import InvalidDomain
from mbarde.shorturls.content.short_url import isAllowedDomain
from mbarde.shorturls.content.short_url import IShortUrl
from mbarde.shorturls.content.short_url import TargetUrlDomainNotAllowed
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_RESTAPI_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser

import requests
import transaction
import unittest

DOMAINS = ["example.org", "Uni-Example.DE"]


class IsAllowedDomainTest(unittest.TestCase):

    def test_no_restriction(self):
        self.assertTrue(isAllowedDomain("https://anything.com/", []))

    def test_allowed(self):
        for url in (
            "https://example.org",
            "https://example.org/path?q=1",
            "http://www.example.org/",
            "https://a.b.example.org/",
            "https://EXAMPLE.org/",
            "https://example.org:8443/",
            "https://example.org./",
            "https://www.uni-example.de/",
        ):
            self.assertTrue(isAllowedDomain(url, DOMAINS), url)

    def test_not_allowed(self):
        for url in (
            "https://notexample.org/",
            "https://example.org.evil.com/",
            "https://example.org@evil.com/",
            "https://evil.com/example.org",
            "https://evil.com/?u=https://example.org",
            "https://example.com/",
            "https:///nohost",
        ):
            self.assertFalse(isAllowedDomain(url, DOMAINS), url)


class AllowedDomainsIntegrationTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_default_no_restriction(self):
        self.assertEqual(api.portal.get_registry_record("mbarde.shorturls.allowed_domains"), [])
        IShortUrl["target_url"].validate("https://anything.com/")

    def test_blank_entries_ignored(self):
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", ["", " "])
        IShortUrl["target_url"].validate("https://anything.com/")
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", ["", "example.org"])
        IShortUrl["target_url"].validate("https://example.org/")
        with self.assertRaises(TargetUrlDomainNotAllowed):
            IShortUrl["target_url"].validate("https://anything.com/")

    def test_target_url_validation(self):
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", DOMAINS)
        field = IShortUrl["target_url"]
        field.validate("https://www.example.org/page")
        with self.assertRaises(TargetUrlDomainNotAllowed) as cm:
            field.validate("https://evil.com/")
        self.assertIn("example.org, Uni-Example.DE", api.portal.translate(cm.exception.doc()))

    def test_domain_entries_validated(self):
        field = IMbardeShorturlsControlPanel["allowed_domains"]
        field.validate(["example.org", "www.uni-example.de", "localhost"])
        for entry in ("https://example.org", "example.org/", "*.example.org", "exa mple.org"):
            with self.assertRaises(InvalidDomain, msg=entry):
                field.validate([entry])


class AllowedDomainsFormTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", DOMAINS)
        transaction.commit()
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )

    def add(self, suffix, target_url):
        self.browser.open(self.container.absolute_url() + "/++add++ShortUrl")
        self.browser.getControl(name="form.widgets.suffix").value = suffix
        self.browser.getControl(name="form.widgets.target_url").value = target_url
        self.browser.getControl(name="form.buttons.save").click()
        transaction.begin()

    def test_add_allowed(self):
        self.add("ok", "https://www.example.org/")
        self.assertIn("ok", self.container)

    def test_add_not_allowed(self):
        self.add("evil", "https://evil.com/")
        self.assertIn("The domain of this URL is not allowed.", self.browser.contents)
        self.assertNotIn("evil", self.container)

    def test_edit_existing_not_allowed(self):
        # created before the restriction - can't be saved without fixing it
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", [])
        obj = api.content.create(
            container=self.container,
            type="ShortUrl",
            title="old",
            suffix="old",
            target_url="https://evil.com/",
        )
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", DOMAINS)
        transaction.commit()
        self.browser.open(obj.absolute_url() + "/edit")
        self.browser.getControl(name="form.buttons.save").click()
        self.assertIn("The domain of this URL is not allowed.", self.browser.contents)

    def test_controlpanel(self):
        self.browser.open(self.portal.absolute_url() + "/@@mbarde-shorturls-controlpanel")
        self.browser.getControl(name="form.widgets.allowed_domains").value = (
            "example.org\n\nwww.uni-example.de\n"
        )
        self.browser.getControl(name="form.buttons.save").click()
        transaction.begin()
        domains = api.portal.get_registry_record("mbarde.shorturls.allowed_domains")
        self.assertEqual([d for d in domains if d], ["example.org", "www.uni-example.de"])

    def test_controlpanel_invalid_entry(self):
        self.browser.open(self.portal.absolute_url() + "/@@mbarde-shorturls-controlpanel")
        self.browser.getControl(name="form.widgets.allowed_domains").value = "https://example.org/"
        self.browser.getControl(name="form.buttons.save").click()
        self.assertIn(
            "https://example.org/ is not a valid domain. Enter domains only",
            self.browser.contents,
        )
        transaction.begin()
        self.assertEqual(
            api.portal.get_registry_record("mbarde.shorturls.allowed_domains"), DOMAINS
        )


class AllowedDomainsRestApiTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_RESTAPI_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        api.portal.set_registry_record("mbarde.shorturls.allowed_domains", DOMAINS)
        transaction.commit()

    def post(self, suffix, target_url):
        return requests.post(
            self.container.absolute_url(),
            json={"@type": "ShortUrl", "suffix": suffix, "target_url": target_url},
            headers={"Accept": "application/json"},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
        )

    def test_allowed(self):
        response = self.post("ok", "https://www.example.org/")
        self.assertEqual(response.status_code, 201, response.text)

    def test_not_allowed(self):
        response = self.post("evil", "https://evil.com/")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("The domain of this URL is not allowed.", response.text)
        self.assertIn("example.org", response.text)

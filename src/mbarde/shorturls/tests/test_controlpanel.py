# -*- coding: utf-8 -*-
"""Control panel tests for this package."""

from mbarde.shorturls.browser.controlpanel import BaseUrlEndsWithSlash
from mbarde.shorturls.browser.controlpanel import IMbardeShorturlsControlPanel
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser

import transaction
import unittest


class TestControlPanel(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_configlet_registered(self):
        controlpanel = api.portal.get_tool("portal_controlpanel")
        action_ids = [action.getId() for action in controlpanel.listActions()]
        self.assertIn("mbarde-shorturls-controlpanel", action_ids)

    def test_controlpanel_view(self):
        view = api.content.get_view(
            name="mbarde-shorturls-controlpanel",
            context=self.portal,
            request=self.request,
        )
        self.assertTrue(view())

    def test_base_url(self):
        api.portal.set_registry_record("mbarde.shorturls.base_url", "https://go.example.org")
        self.assertEqual(
            api.portal.get_registry_record("mbarde.shorturls.base_url"), "https://go.example.org"
        )

    def test_base_url_must_not_end_with_slash(self):
        field = IMbardeShorturlsControlPanel["base_url"]
        field.validate("https://go.example.org")
        field.validate("https://www.example.org/go")
        for value in ("https://go.example.org/", "https://www.example.org/go/"):
            with self.assertRaises(BaseUrlEndsWithSlash):
                field.validate(value)


class TestControlPanelForm(unittest.TestCase):

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )
        self.browser.open(self.portal.absolute_url() + "/@@mbarde-shorturls-controlpanel")

    def save(self, base_url):
        self.browser.getControl(name="form.widgets.base_url").value = base_url
        self.browser.getControl(name="form.buttons.save").click()
        transaction.begin()

    def test_trailing_slash_refused(self):
        self.save("https://go.example.org/")
        self.assertIn("The base URL must not end with a", self.browser.contents)
        self.assertIsNone(api.portal.get_registry_record("mbarde.shorturls.base_url"))

    def test_save(self):
        self.save("https://go.example.org")
        self.assertEqual(
            api.portal.get_registry_record("mbarde.shorturls.base_url"), "https://go.example.org"
        )

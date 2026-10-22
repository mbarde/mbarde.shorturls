# -*- coding: utf-8 -*-
"""Control panel tests for this package."""

from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

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

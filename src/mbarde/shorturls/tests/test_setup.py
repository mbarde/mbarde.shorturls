# -*- coding: utf-8 -*-
"""Setup tests for this package."""

from mbarde.shorturls.interfaces import IMbardeShorturlsLayer
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.base.utils import get_installer
from plone.browserlayer import utils

import unittest


class TestSetup(unittest.TestCase):
    """Test that mbarde.shorturls is properly installed."""

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        self.installer = get_installer(self.portal, self.layer["request"])

    def test_product_installed(self):
        """Test if mbarde.shorturls is installed."""
        self.assertTrue(self.installer.is_product_installed("mbarde.shorturls"))

    def test_browserlayer(self):
        """Test that IMbardeShorturlsLayer is registered."""

        self.assertIn(IMbardeShorturlsLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.installer = get_installer(self.portal, self.layer["request"])
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstall_product("mbarde.shorturls")
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if mbarde.shorturls is cleanly uninstalled."""
        self.assertFalse(self.installer.is_product_installed("mbarde.shorturls"))

    def test_browserlayer_removed(self):
        """Test that IMbardeShorturlsLayer is removed."""
        self.assertNotIn(IMbardeShorturlsLayer, utils.registered_layers())

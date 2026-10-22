# -*- coding: utf-8 -*-
from mbarde.shorturls.content.short_url_container import IShortUrlContainer
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.folder.unordered import UnorderedOrdering
from zope.component import createObject
from zope.component import queryUtility

import unittest


class ShortUrlContainerIntegrationTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_ct_short_url_container_schema(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrlContainer")
        schema = fti.lookupSchema()
        self.assertEqual(IShortUrlContainer, schema)

    def test_ct_short_url_container_fti(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrlContainer")
        self.assertTrue(fti)

    def test_ct_short_url_container_factory(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrlContainer")
        factory = fti.factory
        obj = createObject(factory)

        self.assertTrue(
            IShortUrlContainer.providedBy(obj),
            "IShortUrlContainer not provided by {0}!".format(
                obj,
            ),
        )

    def test_ct_short_url_container_adding(self):
        obj = api.content.create(
            container=self.portal, type="ShortUrlContainer", title="Short URLs"
        )
        self.assertEqual(obj.id, "short-urls")
        self.assertTrue(
            IShortUrlContainer.providedBy(obj),
            "IShortUrlContainer not provided by {0}!".format(
                obj.id,
            ),
        )
        self.assertEqual(api.content.get_state(obj), "open")

    def test_ct_short_url_container_globally_addable(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrlContainer")
        self.assertTrue(fti.global_allow, "{0} is not globally addable!".format(fti.id))

    def test_ct_short_url_container_only_admins_can_add(self):
        for role in ("Contributor", "Editor", "Owner"):
            setRoles(self.portal, TEST_USER_ID, [role])
            self.assertFalse(
                api.user.get_permissions(obj=self.portal)["mbarde.shorturls: Add ShortUrlContainer"]
            )
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])
        self.assertTrue(
            api.user.get_permissions(obj=self.portal)["mbarde.shorturls: Add ShortUrlContainer"]
        )

    def test_only_short_urls_allowed(self):
        container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        allowed = [fti.getId() for fti in container.allowedContentTypes()]
        self.assertEqual(allowed, ["ShortUrl"])
        # and short urls can't be added anywhere else
        folder = api.content.create(container=self.portal, type="Folder", id="f")
        self.assertNotIn("ShortUrl", [fti.getId() for fti in folder.allowedContentTypes()])

    def test_unordered(self):
        container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        self.assertIsInstance(container.getOrdering(), UnorderedOrdering)
        for suffix in ("b", "a", "c"):
            api.content.create(
                container=container,
                type="ShortUrl",
                title=suffix,
                suffix=suffix,
                target_url="https://www.plone.org",
            )
        self.assertEqual(sorted(container.objectIds()), ["a", "b", "c"])
        api.content.delete(obj=container["b"])
        self.assertEqual(sorted(container.objectIds()), ["a", "c"])

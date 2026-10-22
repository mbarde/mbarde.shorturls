# -*- coding: utf-8 -*-
from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.content.short_url import InvalidSuffix
from mbarde.shorturls.content.short_url import InvalidTargetUrlScheme
from mbarde.shorturls.content.short_url import IShortUrl
from mbarde.shorturls.content.short_url import SuffixInUse
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_RESTAPI_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.testing.zope import Browser
from z3c.form.interfaces import IValidator
from zope.component import createObject
from zope.component import getMultiAdapter
from zope.component import queryUtility

import requests
import transaction
import unittest


class ShortUrlIntegrationTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.folder = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")

    def createShortUrl(self, suffix, target_url="https://www.plone.org"):
        return api.content.create(
            container=self.folder,
            type="ShortUrl",
            # plone.api needs id or title - the title is ignored and the id
            # gets generated from the suffix
            title=suffix,
            suffix=suffix,
            target_url=target_url,
        )

    def validateSuffix(self, context, value):
        field = IShortUrl["suffix"]
        validator = getMultiAdapter((context, self.request, None, field, None), IValidator)
        validator.validate(value)

    def test_ct_short_url_schema(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrl")
        schema = fti.lookupSchema()
        self.assertEqual(IShortUrl, schema)

    def test_ct_short_url_fti(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrl")
        self.assertTrue(fti)

    def test_ct_short_url_factory(self):
        fti = queryUtility(IDexterityFTI, name="ShortUrl")
        factory = fti.factory
        obj = createObject(factory)

        self.assertTrue(
            IShortUrl.providedBy(obj),
            "IShortUrl not provided by {0}!".format(
                obj,
            ),
        )

    def test_ct_short_url_adding(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        obj = self.createShortUrl("00CLH")

        self.assertTrue(
            IShortUrl.providedBy(obj),
            "IShortUrl not provided by {0}!".format(
                obj.id,
            ),
        )
        # id and title are derived from the suffix
        self.assertEqual(obj.id, "00clh")
        self.assertEqual(obj.Title(), "00CLH")
        self.assertEqual(obj.clicks, 0)
        self.assertFalse(obj.is_api)

    def test_ct_short_url_globally_not_addable(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="ShortUrl")
        self.assertFalse(fti.global_allow, "{0} is globally addable!".format(fti.id))

    def test_reserved_suffix_gets_other_id(self):
        # "id" is no valid Plone id, but still a valid suffix
        obj = self.createShortUrl("id")
        self.assertNotEqual(obj.id, "id")
        self.assertEqual(obj.suffix, "id")
        self.assertEqual(findShortUrlBySuffix("id").UID, obj.UID())

    def test_find_by_suffix_case_insensitive(self):
        obj = self.createShortUrl("AnorgChem")
        for suffix in ("AnorgChem", "anorgchem", "ANORGCHEM"):
            self.assertEqual(findShortUrlBySuffix(suffix).UID, obj.UID())
        self.assertIsNone(findShortUrlBySuffix("Anorg"))

    def test_find_by_suffix_after_edit(self):
        obj = self.createShortUrl("old")
        obj.suffix = "New"
        obj.reindexObject()
        self.assertIsNone(findShortUrlBySuffix("old"))
        self.assertEqual(findShortUrlBySuffix("new").UID, obj.UID())

    def test_suffix_constraint(self):
        field = IShortUrl["suffix"]
        for value in ("abc", "00CLH", "bas_ss24", "zfl-faq", "id"):
            field.validate(value)
        for value in ("with space", "umlaut-ä", "a/b", "a.b", "a?b", "#x"):
            with self.assertRaises(InvalidSuffix):
                field.validate(value)

    def test_target_url_constraint(self):
        field = IShortUrl["target_url"]
        field.validate("https://www.plone.org/path?query=1")
        field.validate("http://www.plone.org")
        for value in ("javascript:alert(1)", "ftp://plone.org", "mailto:info@plone.org"):
            with self.assertRaises(InvalidTargetUrlScheme):
                field.validate(value)

    def test_suffix_unique_on_add(self):
        self.createShortUrl("Taken")
        # on add forms the context is the container
        for value in ("Taken", "taken", "TAKEN"):
            with self.assertRaises(SuffixInUse):
                self.validateSuffix(self.folder, value)
        self.validateSuffix(self.folder, "free")

    def test_suffix_unique_on_edit(self):
        obj = self.createShortUrl("mine")
        other = self.createShortUrl("other")
        # keeping (or re-casing) its own suffix is fine
        self.validateSuffix(obj, "mine")
        self.validateSuffix(obj, "MINE")
        with self.assertRaises(SuffixInUse):
            self.validateSuffix(other, "mine")

    def test_hidden_from_navigation_and_search(self):
        self.assertNotIn("ShortUrl", api.portal.get_registry_record("plone.displayed_types"))
        self.assertIn("ShortUrl", api.portal.get_registry_record("plone.types_not_searched"))


class ShortUrlRestApiTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_RESTAPI_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        transaction.commit()

        self.api_session = requests.Session()
        self.addCleanup(self.api_session.close)
        self.api_session.headers.update({"Accept": "application/json"})
        self.api_session.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

    def post(self, **data):
        return self.api_session.post(
            self.portal.absolute_url() + "/s", json={"@type": "ShortUrl", **data}
        )

    def test_created_via_api(self):
        response = self.post(suffix="ApiUrl", target_url="https://www.plone.org")
        self.assertEqual(response.status_code, 201, response.text)
        transaction.begin()
        obj = self.portal.s["apiurl"]
        self.assertTrue(obj.is_api)
        self.assertEqual(obj.clicks, 0)

    def test_readonly_fields_ignored(self):
        response = self.post(
            suffix="sneaky", target_url="https://www.plone.org", clicks=1000, is_api=False
        )
        self.assertEqual(response.status_code, 201, response.text)
        transaction.begin()
        obj = self.portal.s["sneaky"]
        self.assertEqual(obj.clicks, 0)
        self.assertTrue(obj.is_api)

    def test_duplicate_suffix_rejected(self):
        self.assertEqual(self.post(suffix="dup", target_url="https://a.org").status_code, 201)
        response = self.post(suffix="DUP", target_url="https://b.org")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("already in use", response.text)

    def test_invalid_target_url_rejected(self):
        response = self.post(suffix="evil", target_url="javascript:alert(1)")
        self.assertEqual(response.status_code, 400, response.text)


class ShortUrlAddFormTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        transaction.commit()

        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )

    def add(self, suffix, target_url="https://www.plone.org"):
        self.browser.open(self.portal.absolute_url() + "/s/++add++ShortUrl")
        self.browser.getControl(name="form.widgets.suffix").value = suffix
        self.browser.getControl(name="form.widgets.target_url").value = target_url
        self.browser.getControl(name="form.buttons.save").click()

    def test_add_form(self):
        self.add("FormUrl")
        self.assertEqual(self.browser.url, self.portal.absolute_url() + "/s/formurl/view")
        transaction.begin()
        obj = self.portal.s["formurl"]
        self.assertEqual(obj.suffix, "FormUrl")
        self.assertEqual(obj.clicks, 0)
        self.assertFalse(obj.is_api)

    def test_add_form_duplicate_suffix(self):
        self.add("taken")
        self.add("TAKEN")
        self.assertIn("This suffix is already in use.", self.browser.contents)
        transaction.begin()
        self.assertEqual(len(self.portal.s.objectIds()), 1)

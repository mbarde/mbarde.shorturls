# -*- coding: utf-8 -*-
from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.content.short_url import InvalidSuffix
from mbarde.shorturls.content.short_url import InvalidTargetUrlScheme
from mbarde.shorturls.content.short_url import IShortUrl
from mbarde.shorturls.content.short_url import SuffixInUse
from mbarde.shorturls.content.short_url import TargetUrlWithoutDomain
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
from urllib.parse import urlencode
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

    def test_find_by_target_url(self):
        obj = self.createShortUrl("one", target_url="https://www.plone.org/a")
        self.createShortUrl("two", target_url="https://www.plone.org/b")
        catalog = api.portal.get_tool("portal_catalog")

        def search(target_url):
            return [b.UID for b in catalog(shorturl_target_url=target_url)]

        self.assertEqual(search("https://www.plone.org/a"), [obj.UID()])
        self.assertEqual(search("https://www.plone.org/c"), [])
        obj.target_url = "https://www.plone.org/c"
        obj.reindexObject()
        self.assertEqual(search("https://www.plone.org/a"), [])
        self.assertEqual(search("https://www.plone.org/c"), [obj.UID()])

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

    def test_target_url_without_domain(self):
        field = IShortUrl["target_url"]
        for value in ("https://", "http://", "https:///path", "https://?x", "https://:443/"):
            with self.assertRaises(TargetUrlWithoutDomain, msg=value):
                field.validate(value)
        for value in ("https://localhost/", "http://127.0.0.1:8080/x", "https://[::1]/"):
            field.validate(value)

    def test_suffix_unique_on_add(self):
        self.createShortUrl("Taken")
        # on add forms the context is the container
        for value in ("Taken", "taken", "TAKEN"):
            with self.assertRaises(SuffixInUse):
                self.validateSuffix(self.folder, value)
        self.validateSuffix(self.folder, "free")

    def test_disabled_suffix_stays_reserved(self):
        obj = self.createShortUrl("Reserved")
        api.content.transition(obj=obj, transition="disable")
        for value in ("Reserved", "reserved"):
            with self.assertRaises(SuffixInUse):
                self.validateSuffix(self.folder, value)

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

    def test_search_by_target_url(self):
        url = "https://www.plone.org/news"
        response = self.post(suffix="news", target_url=url)
        self.assertEqual(response.status_code, 201, response.text)
        self.post(suffix="other", target_url=url + "/other")
        response = self.api_session.get(
            self.portal.absolute_url() + "/s/@search",
            params={"portal_type": "ShortUrl", "shorturl_target_url": url},
        )
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["items"]
        self.assertEqual([item["@id"] for item in items], [self.portal.absolute_url() + "/s/news"])

    def test_readonly_fields_ignored(self):
        response = self.post(
            suffix="sneaky",
            target_url="https://www.plone.org",
            clicks=1000,
            last_clicked="2099-01-01",
            is_api=False,
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()["last_clicked"])
        transaction.begin()
        obj = self.portal.s["sneaky"]
        self.assertEqual(obj.clicks, 0)
        self.assertIsNone(obj.last_clicked)
        self.assertTrue(obj.is_api)

    def test_duplicate_suffix_rejected(self):
        self.assertEqual(self.post(suffix="dup", target_url="https://a.org").status_code, 201)
        response = self.post(suffix="DUP", target_url="https://b.org")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("already in use", response.text)

    def test_owner_cannot_delete_but_disable(self):
        api.user.create(email="alice@example.org", username="alice", password="secret-alice")
        transaction.commit()
        alice = requests.Session()
        self.addCleanup(alice.close)
        alice.headers.update({"Accept": "application/json"})
        alice.auth = ("alice", "secret-alice")
        response = alice.post(
            self.portal.absolute_url() + "/s",
            json={"@type": "ShortUrl", "suffix": "alices", "target_url": "https://a.org"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        url = response.json()["@id"]

        response = alice.delete(url)
        self.assertIn(response.status_code, (401, 403), response.text)
        response = alice.post(url + "/@workflow/disable")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["review_state"], "disabled")
        response = alice.post(url + "/@workflow/enable")
        self.assertEqual(response.json()["review_state"], "active")

    def test_invalid_target_url_rejected(self):
        response = self.post(suffix="evil", target_url="javascript:alert(1)")
        self.assertEqual(response.status_code, 400, response.text)
        response = self.post(suffix="nohost", target_url="https:///path")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("The URL has to contain a domain", response.text)


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


class SuffixNotChangeableFormTest(unittest.TestCase):
    """Suffix can't be changed after creation."""

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        self.obj = api.content.create(
            container=container,
            type="ShortUrl",
            title="fixed",
            suffix="fixed",
            target_url="https://www.plone.org",
        )
        transaction.commit()
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )

    def test_add_form_suffix_editable(self):
        self.browser.open(self.portal.absolute_url() + "/s/++add++ShortUrl")
        self.assertTrue(self.browser.getControl(name="form.widgets.suffix"))

    def test_edit_form_suffix_displayed_only(self):
        self.browser.open(self.obj.absolute_url() + "/edit")
        with self.assertRaises(LookupError):
            self.browser.getControl(name="form.widgets.suffix")
        self.assertIn("fixed", self.browser.contents)
        self.browser.getControl(name="form.widgets.target_url").value = "https://plone.org/new"
        self.browser.getControl(name="form.buttons.save").click()
        transaction.begin()
        self.assertEqual(self.obj.target_url, "https://plone.org/new")
        self.assertEqual(self.obj.suffix, "fixed")

    def test_edit_form_forged_suffix_ignored(self):
        self.browser.open(self.obj.absolute_url() + "/edit")
        authenticator = self.browser.getControl(name="_authenticator").value
        self.browser.post(
            self.obj.absolute_url() + "/@@edit",
            urlencode(
                {
                    "form.widgets.suffix": "hijacked",
                    "form.widgets.target_url": "https://plone.org/new",
                    "form.buttons.save": "Save",
                    "_authenticator": authenticator,
                }
            ),
        )
        transaction.begin()
        self.assertEqual(self.obj.target_url, "https://plone.org/new")
        self.assertEqual(self.obj.suffix, "fixed")
        self.assertIsNone(findShortUrlBySuffix("hijacked"))


class SuffixNotChangeableRestApiTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_RESTAPI_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        self.obj = api.content.create(
            container=container,
            type="ShortUrl",
            title="fixed",
            suffix="fixed",
            target_url="https://www.plone.org",
        )
        transaction.commit()

    def patch(self, **data):
        return requests.patch(
            self.obj.absolute_url(),
            json=data,
            headers={"Accept": "application/json"},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
        )

    def test_change_refused(self):
        for suffix in ("other", "FIXED"):
            response = self.patch(suffix=suffix)
            self.assertEqual(response.status_code, 400, response.text)
            self.assertIn("can't be changed", response.text)
        transaction.begin()
        self.assertEqual(self.obj.suffix, "fixed")

    def test_unchanged_suffix_accepted(self):
        response = self.patch(suffix="fixed", target_url="https://plone.org/new")
        self.assertEqual(response.status_code, 204, response.text)
        transaction.begin()
        self.assertEqual(self.obj.target_url, "https://plone.org/new")

    def test_target_url_editable(self):
        response = self.patch(target_url="https://plone.org/new")
        self.assertEqual(response.status_code, 204, response.text)
        transaction.begin()
        self.assertEqual(self.obj.target_url, "https://plone.org/new")


class SuffixWidgetTest(unittest.TestCase):
    """The add form shows the base url in front of the suffix input."""

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

    def openAddForm(self):
        self.browser.open(self.portal.absolute_url() + "/s/++add++ShortUrl")

    def test_input_group(self):
        api.portal.set_registry_record("mbarde.shorturls.base_url", "https://go.example.org")
        transaction.commit()
        self.openAddForm()
        self.assertRegex(
            self.browser.contents,
            r'<div class="input-group">\s*'
            r'<span class="input-group-text" id="form-widgets-suffix-base-url">'
            r"https://go.example.org/</span>\s*"
            r'<input name="form.widgets.suffix"[^>]*class="text-widget form-control"'
            r'[^>]*aria-describedby="form-widgets-suffix-base-url"',
        )
        self.assertNotIn("Bootstrap input group", self.browser.contents)
        # still a normal input
        self.browser.getControl(name="form.widgets.suffix").value = "grouped"
        self.browser.getControl(name="form.widgets.target_url").value = "https://plone.org"
        self.browser.getControl(name="form.buttons.save").click()
        transaction.begin()
        self.assertEqual(self.portal.s["grouped"].suffix, "grouped")

    def test_without_base_url(self):
        self.openAddForm()
        self.assertNotIn('class="input-group"', self.browser.contents)
        self.assertNotIn("aria-describedby", self.browser.contents)
        self.assertTrue(self.browser.getControl(name="form.widgets.suffix"))

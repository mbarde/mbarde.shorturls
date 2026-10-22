# -*- coding: utf-8 -*-
"""Empty suffixes get generated (6 random lowercase characters without
look-alikes)."""

from mbarde.shorturls.content import short_url
from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.content.short_url import generateSuffix
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_RESTAPI_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.base.interfaces import INameFromTitle
from plone.dexterity.interfaces import IDexterityFTI
from plone.testing.zope import Browser
from unittest import mock
from zope.component import queryUtility

import re
import requests
import transaction
import unittest

GENERATED = re.compile(r"^[2-9a-hjkmnp-z]{6}$")


class SuffixGenerationTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")

    def test_format(self):
        suffixes = [generateSuffix() for i in range(2000)]
        for suffix in suffixes:
            self.assertRegex(suffix, GENERATED)
        # all 31 characters are used (12000 characters drawn)
        self.assertEqual(set("".join(suffixes)), set("23456789abcdefghjkmnpqrstuvwxyz"))

    def test_used_suffixes_skipped_case_insensitively(self):
        api.content.create(
            container=self.container,
            type="ShortUrl",
            title="AbCdE",
            suffix="AbCdE",
            target_url="https://www.plone.org",
        )
        with mock.patch.object(short_url, "randomSuffix", side_effect=["abcde", "Fresh"]):
            self.assertEqual(generateSuffix(), "Fresh")

    def test_disabled_suffixes_skipped(self):
        obj = api.content.create(
            container=self.container,
            type="ShortUrl",
            title="Taken",
            suffix="Taken",
            target_url="https://www.plone.org",
        )
        api.content.transition(obj=obj, transition="disable")
        with mock.patch.object(short_url, "randomSuffix", side_effect=["TAKEN", "Fresh"]):
            self.assertEqual(generateSuffix(), "Fresh")

    def test_gives_up_eventually(self):
        api.content.create(
            container=self.container,
            type="ShortUrl",
            title="taken",
            suffix="taken",
            target_url="https://www.plone.org",
        )
        with mock.patch.object(short_url, "randomSuffix", return_value="taken"):
            with self.assertRaises(RuntimeError):
                generateSuffix()

    def test_namefromtitle_behavior_removed(self):
        # it would make short urls provide INameFromTitle themselves, so the
        # NameFromSuffix adapter generating missing suffixes wouldn't be used
        fti = queryUtility(IDexterityFTI, name="ShortUrl")
        self.assertNotIn("plone.namefromtitle", fti.behaviors)
        obj = api.content.create(
            container=self.container,
            type="ShortUrl",
            title="abc",
            suffix="abc",
            target_url="https://www.plone.org",
        )
        self.assertFalse(INameFromTitle.providedBy(obj))

    def test_explicit_id_without_suffix(self):
        # plone.api with an explicit id skips the name chooser
        obj = api.content.create(
            container=self.container,
            type="ShortUrl",
            id="explicit",
            target_url="https://www.plone.org",
        )
        self.assertEqual(obj.getId(), "explicit")
        self.assertRegex(obj.suffix, GENERATED)
        self.assertEqual(findShortUrlBySuffix(obj.suffix).UID, obj.UID())

    def test_given_suffix_kept(self):
        obj = api.content.create(
            container=self.container,
            type="ShortUrl",
            title="Mine",
            suffix="Mine",
            target_url="https://www.plone.org",
        )
        self.assertEqual(obj.suffix, "Mine")


class SuffixGenerationFormTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        transaction.commit()

    def test_add_form_empty_suffix(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )
        browser.open(self.container.absolute_url() + "/++add++ShortUrl")
        browser.getControl(name="form.widgets.target_url").value = "https://www.plone.org"
        browser.getControl(name="form.buttons.save").click()
        transaction.begin()
        obj = self.container[list(self.container.objectIds())[0]]
        self.assertRegex(obj.suffix, GENERATED)
        # id derived from the generated suffix
        self.assertEqual(obj.getId(), obj.suffix)
        self.assertEqual(browser.url, obj.absolute_url() + "/view")


class SuffixGenerationRestApiTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_RESTAPI_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        transaction.commit()

    def post(self, **data):
        return requests.post(
            self.container.absolute_url(),
            json={"@type": "ShortUrl", "target_url": "https://www.plone.org", **data},
            headers={"Accept": "application/json"},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
        )

    def test_without_suffix(self):
        for data in ({}, {"suffix": ""}, {"suffix": None}):
            response = self.post(**data)
            self.assertEqual(response.status_code, 201, response.text)
            result = response.json()
            self.assertRegex(result["suffix"], GENERATED)
            self.assertEqual(result["id"], result["suffix"])
            self.assertTrue(result["is_api"])
        transaction.begin()
        self.assertEqual(len(self.container.objectIds()), 3)

    def test_suffix_not_removable(self):
        response = self.post(suffix="given")
        self.assertEqual(response.status_code, 201, response.text)
        response = requests.patch(
            response.json()["@id"],
            json={"suffix": ""},
            headers={"Accept": "application/json"},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
        )
        self.assertEqual(response.status_code, 400, response.text)
        transaction.begin()
        self.assertEqual(self.container["given"].suffix, "given")

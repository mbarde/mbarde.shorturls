# -*- coding: utf-8 -*-
"""All logged-in users may add short urls to a container and see / edit /
delete only their own ones."""

from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.testing import MBARDE_SHORTURLS_FUNCTIONAL_TESTING  # noqa
from mbarde.shorturls.testing import MBARDE_SHORTURLS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser
from zExceptions import Unauthorized

import transaction
import unittest


class ShortUrlPermissionsTest(unittest.TestCase):

    layer = MBARDE_SHORTURLS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        # no further setup needed, see shorturl_container_workflow
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")

        for username in ("alice", "bob", "moderator"):
            api.user.create(email=username + "@example.org", username=username)
        api.user.grant_roles(username="moderator", obj=self.container, roles=["Editor"])

        login(self.portal, "alice")
        self.alices = self.createShortUrl("alices")
        login(self.portal, "bob")
        self.bobs = self.createShortUrl("bobs")

    def createShortUrl(self, suffix):
        return api.content.create(
            container=self.container,
            type="ShortUrl",
            title=suffix,
            suffix=suffix,
            target_url="https://www.plone.org",
        )

    def can(self, permission, obj):
        return api.user.get_permissions(obj=obj).get(permission, False)

    def deleteActionOffered(self, obj):
        actions = api.portal.get_tool("portal_actions").listActionInfos(
            object=obj, categories=["object_buttons"]
        )
        return "delete" in [action["id"] for action in actions]

    def listedSuffixes(self):
        catalog = api.portal.get_tool("portal_catalog")
        return sorted(b.Title for b in catalog(portal_type="ShortUrl"))

    def test_workflow(self):
        self.assertEqual(api.content.get_state(self.alices), "active")

    def test_authenticated_can_add(self):
        login(self.portal, "alice")
        self.assertTrue(self.can("mbarde.shorturls: Add ShortUrl", self.container))
        self.assertTrue(self.can("List folder contents", self.container))

    def test_owner_can_view_edit_disable_enable_own(self):
        login(self.portal, "alice")
        self.assertTrue(self.can("View", self.alices))
        self.assertTrue(self.can("Modify portal content", self.alices))
        api.content.transition(obj=self.alices, transition="disable")
        self.assertEqual(api.content.get_state(self.alices), "disabled")
        # still visible (and editable) to re-enable it
        self.assertTrue(self.can("View", self.alices))
        self.assertTrue(self.can("Modify portal content", self.alices))
        api.content.transition(obj=self.alices, transition="enable")
        self.assertEqual(api.content.get_state(self.alices), "active")

    def test_owner_cannot_delete(self):
        # deleting would free the suffix - users disable instead
        login(self.portal, "alice")
        for state in ("active", "disabled"):
            api.content.transition(obj=self.alices, to_state=state)
            self.assertFalse(self.can("Delete objects", self.alices))
            self.assertFalse(self.deleteActionOffered(self.alices))
            with self.assertRaises(Unauthorized):
                self.container.manage_delObjects([self.alices.getId()])

    def test_cannot_disable_others(self):
        login(self.portal, "alice")
        with self.assertRaises(api.exc.InvalidParameterError):
            api.content.transition(obj=self.bobs, transition="disable")
        self.assertEqual(api.content.get_state(self.bobs), "active")

    def test_admins_can_delete(self):
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])
        login(self.portal, "test-user")
        for obj in (self.alices, self.bobs):
            self.assertTrue(self.can("Delete objects", obj))
        api.content.transition(obj=self.bobs, transition="disable")
        self.container.manage_delObjects([self.alices.getId(), self.bobs.getId()])
        self.assertEqual(list(self.container.objectIds()), [])

    def test_other_users_short_urls_invisible(self):
        login(self.portal, "alice")
        self.assertFalse(self.can("View", self.bobs))
        self.assertFalse(self.can("Modify portal content", self.bobs))
        self.assertEqual(self.listedSuffixes(), ["alices"])
        with self.assertRaises(Unauthorized):
            self.container.manage_delObjects([self.bobs.getId()])
        self.assertIn("bobs", self.container)

    def test_anonymous(self):
        logout()
        self.assertFalse(self.can("View", self.container))
        self.assertFalse(self.can("View", self.alices))
        self.assertEqual(self.listedSuffixes(), [])
        # redirecting does not depend on View
        self.assertEqual(findShortUrlBySuffix("alices").UID, self.alices.UID())

    def test_editor_on_container_sees_edits_and_disables_all(self):
        login(self.portal, "moderator")
        self.assertEqual(self.listedSuffixes(), ["alices", "bobs"])
        for obj in (self.alices, self.bobs):
            self.assertTrue(self.can("Modify portal content", obj))
            self.assertFalse(self.can("Delete objects", obj))
            api.content.transition(obj=obj, transition="disable")
            api.content.transition(obj=obj, transition="enable")

    def test_users_cannot_edit_container(self):
        login(self.portal, "alice")
        self.assertFalse(self.can("Modify portal content", self.container))

    def test_users_cannot_delete_container(self):
        # users have "Delete objects" on the container (to delete their own
        # short urls in it), which must not allow deleting the container itself
        login(self.portal, "alice")
        self.assertFalse(self.deleteActionOffered(self.container))
        with self.assertRaises(Unauthorized):
            api.content.delete(obj=self.container)
        self.assertIn("s", self.portal)
        login(self.portal, "moderator")
        with self.assertRaises(Unauthorized):
            api.content.delete(obj=self.container)
        self.assertIn("s", self.portal)

    def test_admins_can_delete_container(self):
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])
        login(self.portal, "test-user")
        api.content.delete(obj=self.container)
        self.assertNotIn("s", self.portal)

    def test_admins_can_delete_folder_containing_container(self):
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])
        login(self.portal, "test-user")
        folder = api.content.create(container=self.portal, type="Folder", id="institution")
        api.content.move(source=self.container, target=folder)
        api.content.delete(obj=folder)
        self.assertNotIn("institution", self.portal)


class ShortUrlViewBrowserTest(unittest.TestCase):
    """Edit / delete buttons of the short url view and deleting through the web."""

    layer = MBARDE_SHORTURLS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.container = api.content.create(container=self.portal, type="ShortUrlContainer", id="s")
        for username in ("alice", "bob", "reader"):
            api.user.create(
                email=username + "@example.org", username=username, password="secret-" + username
            )
        api.user.grant_roles(username="reader", obj=self.container, roles=["Reader"])
        for username in ("alice", "bob"):
            login(self.portal, username)
            api.content.create(
                container=self.container,
                type="ShortUrl",
                title=username,
                suffix=username,
                target_url="https://www.plone.org",
            )
        logout()
        transaction.commit()

    def browser(self, username, password=None):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        password = password or "secret-" + username
        browser.addHeader("Authorization", "Basic {0}:{1}".format(username, password))
        return browser

    def url(self, path):
        return self.portal.absolute_url() + "/s" + path

    def assertNoAccess(self, browser, path):
        # let Plone handle Unauthorized like for real users (handleErrors=False
        # breaks the request cleanup in this case)
        browser.handleErrors = True
        browser.open(self.url(path))
        self.assertEqual(browser.url, self.portal.absolute_url() + "/insufficient-privileges")

    def assertExists(self, path):
        browser = self.browser(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        browser.open(self.url(path))
        self.assertEqual(browser.headers["status"], "200 OK")

    def test_view(self):
        api.portal.set_registry_record("mbarde.shorturls.base_url", "https://go.example.org")
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.url("/alice"))
        self.assertIn('href="https://go.example.org/alice"', browser.contents)
        self.assertIn('href="https://www.plone.org"', browser.contents)

    def test_view_base_url_with_trailing_slash(self):
        # only the control panel form refuses a trailing slash
        api.portal.set_registry_record("mbarde.shorturls.base_url", "https://go.example.org/")
        transaction.commit()
        browser = self.browser("alice")
        browser.open(self.url("/alice"))
        self.assertIn('href="https://go.example.org/alice"', browser.contents)

    def test_view_without_base_url(self):
        browser = self.browser("alice")
        browser.open(self.url("/alice"))
        self.assertNotIn('id="short-url"', browser.contents)

    def test_owner_edits_via_button(self):
        browser = self.browser("alice")
        browser.open(self.url("/alice"))
        browser.getLink(id="short-url-edit").click()
        browser.getControl(name="form.widgets.target_url").value = "https://plone.org/new"
        browser.getControl(name="form.buttons.save").click()
        transaction.begin()
        self.assertEqual(self.container["alice"].target_url, "https://plone.org/new")

    def test_owner_disables_and_enables_via_buttons(self):
        browser = self.browser("alice")
        browser.open(self.url("/alice"))
        self.assertNotIn('id="short-url-delete"', browser.contents)
        self.assertNotIn('id="short-url-disabled"', browser.contents)
        browser.getLink(id="short-url-disable").click()
        transaction.begin()
        self.assertEqual(api.content.get_state(self.container["alice"]), "disabled")
        self.assertEqual(api.content.get_state(self.container["bob"]), "active")

        browser.open(self.url("/alice"))
        self.assertIn('id="short-url-disabled"', browser.contents)
        self.assertNotIn('id="short-url-disable"', browser.contents)
        browser.getLink(id="short-url-enable").click()
        transaction.begin()
        self.assertEqual(api.content.get_state(self.container["alice"]), "active")

    def test_admin_deletes_via_button(self):
        browser = self.browser(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        browser.open(self.url("/alice"))
        browser.getLink(id="short-url-delete").click()
        browser.getControl(name="form.buttons.Delete").click()
        transaction.begin()
        self.assertNotIn("alice", self.container)

    def test_user_cannot_delete(self):
        for path in ("/alice", "/bob"):
            self.assertNoAccess(self.browser("alice"), path + "/delete_confirmation")
            self.assertExists(path)

    def test_reader_sees_no_buttons(self):
        browser = self.browser("reader")
        browser.open(self.url("/alice"))
        for button in ("edit", "disable", "enable", "delete"):
            self.assertNotIn('id="short-url-{0}"'.format(button), browser.contents)

    def test_user_cannot_delete_container(self):
        self.assertNoAccess(self.browser("alice"), "/delete_confirmation")
        self.assertExists("")

    def test_admin_can_delete_container(self):
        browser = self.browser(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        browser.open(self.url("/delete_confirmation"))
        browser.getControl(name="form.buttons.Delete").click()
        transaction.begin()
        self.assertNotIn("s", self.portal)

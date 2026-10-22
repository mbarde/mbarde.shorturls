# -*- coding: utf-8 -*-
from plone import api
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.Five.browser import BrowserView


class ShortUrlView(BrowserView):
    """Default view of a short url, with edit / delete buttons.

    The delete button is needed because Plone only offers its own delete
    action if the user may delete in the container - which regular users must
    not (it would allow deleting the container itself). Deleting a short url
    via its delete_confirmation only needs "Delete objects" on the short url,
    which its owner has (see shorturl_workflow).
    """

    def shortUrl(self):
        """Full short url, or None if no base url is configured."""
        base_url = api.portal.get_registry_record("mbarde.shorturls.base_url", default=None)
        if not base_url:
            return None
        return base_url.rstrip("/") + "/" + self.context.suffix

    def canEdit(self):
        return api.user.has_permission(ModifyPortalContent, obj=self.context)

    def canDelete(self):
        return api.user.has_permission(DeleteObjects, obj=self.context)

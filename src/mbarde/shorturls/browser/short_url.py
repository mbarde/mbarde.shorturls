# -*- coding: utf-8 -*-
from plone import api
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.Five.browser import BrowserView


class ShortUrlView(BrowserView):

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

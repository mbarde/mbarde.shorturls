# -*- coding: utf-8 -*-
from plone import api
from plone.app.contenttypes.browser.folder import FolderView


class ShortUrlContainerView(FolderView):
    """Batched table of the short urls the current user is allowed to see.

    Reuses Plone's folder listing (catalog query, so only short urls the user
    may View - by default their own ones, see shorturl_workflow).
    """

    def results(self, **kwargs):
        kwargs.setdefault("portal_type", "ShortUrl")
        # the default sort (position in folder) is pointless for unordered
        # folders - and expensive with tens of thousands of short urls
        kwargs.setdefault("sort_on", "created")
        kwargs.setdefault("sort_order", "descending")
        return super().results(**kwargs)

    def baseUrl(self):
        base_url = api.portal.get_registry_record("mbarde.shorturls.base_url", default=None)
        return base_url.rstrip("/") if base_url else None

    def canAdd(self):
        return api.user.has_permission("mbarde.shorturls: Add ShortUrl", obj=self.context)

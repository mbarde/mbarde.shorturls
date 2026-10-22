# -*- coding: utf-8 -*-
from plone import api
from plone.app.contenttypes.browser.folder import FolderView

STATES = ("active", "disabled")


class ShortUrlContainerView(FolderView):
    """Batched table of the short urls the current user is allowed to see,
    active and disabled ones in separate tabs.

    Reuses Plone's folder listing (catalog query, so only short urls the user
    may View - by default their own ones, see shorturl_workflow).
    """

    @property
    def state(self):
        state = self.request.get("state")
        return state if state in STATES else "active"

    def results(self, **kwargs):
        kwargs.setdefault("portal_type", "ShortUrl")
        kwargs.setdefault("review_state", self.state)
        # the default sort (position in folder) is pointless for unordered
        # folders - and expensive with tens of thousands of short urls
        kwargs.setdefault("sort_on", "created")
        kwargs.setdefault("sort_order", "descending")
        return super().results(**kwargs)

    def tabs(self):
        catalog = api.portal.get_tool("portal_catalog")
        path = "/".join(self.context.getPhysicalPath())
        url = self.context.absolute_url()
        return [
            {
                "state": state,
                "url": url if state == "active" else url + "?state=" + state,
                "count": len(
                    catalog(
                        portal_type="ShortUrl",
                        path={"query": path, "depth": 1},
                        review_state=state,
                    )
                ),
                "selected": state == self.state,
            }
            for state in STATES
        ]

    def baseUrl(self):
        base_url = api.portal.get_registry_record("mbarde.shorturls.base_url", default=None)
        return base_url.rstrip("/") if base_url else None

    def canAdd(self):
        return api.user.has_permission("mbarde.shorturls: Add ShortUrl", obj=self.context)

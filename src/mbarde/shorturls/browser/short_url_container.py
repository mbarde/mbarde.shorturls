# -*- coding: utf-8 -*-
from mbarde.shorturls.content.short_url import normalizeSuffix
from mbarde.shorturls.content.short_url import SUFFIX_INDEX
from mbarde.shorturls.content.short_url import TARGET_URL_INDEX
from mbarde.shorturls.utils import getBaseUrl
from plone import api
from plone.app.contenttypes.browser.folder import FolderView
from urllib.parse import urlencode

STATES = ("active", "disabled")


def prefixQuery(value):
    """Catalog query for index values starting with `value`."""
    return {"query": (value, value + "\U0010ffff"), "range": "min:max"}


class ShortUrlContainerView(FolderView):
    """Batched table of the short urls the current user is allowed to see,
    active and disabled ones in separate tabs, optionally filtered by a search
    text (see searchCriteria).

    Reuses Plone's folder listing (catalog query, so only short urls the user
    may View - by default their own ones, see shorturl_workflow).
    """

    @property
    def state(self):
        state = self.request.get("state")
        return state if state in STATES else "active"

    @property
    def searchText(self):
        text = self.request.get("q")
        return text.strip() if isinstance(text, str) else ""

    def searchCriteria(self):
        """Catalog criteria for the search text - both indexes only allow
        exact and prefix matches:

        - a short url (base url + suffix): exactly that short url
        - an url: short urls whose target url starts with it
        - anything else: short urls whose suffix starts with it
        """
        text = self.searchText
        if not text:
            return {}
        baseUrl = getBaseUrl()
        if baseUrl and text.lower().startswith(baseUrl.lower() + "/"):
            return {SUFFIX_INDEX: normalizeSuffix(text[len(baseUrl) + 1 :])}
        if "://" in text:
            return {TARGET_URL_INDEX: prefixQuery(text)}
        return {SUFFIX_INDEX: prefixQuery(normalizeSuffix(text))}

    def results(self, **kwargs):
        kwargs.setdefault("portal_type", "ShortUrl")
        kwargs.setdefault("review_state", self.state)
        for key, value in self.searchCriteria().items():
            kwargs.setdefault(key, value)
        # the default sort (position in folder) is pointless for unordered
        # folders - and expensive with tens of thousands of short urls
        kwargs.setdefault("sort_on", "created")
        kwargs.setdefault("sort_order", "descending")
        return super().results(**kwargs)

    def tabs(self):
        catalog = api.portal.get_tool("portal_catalog")
        path = "/".join(self.context.getPhysicalPath())
        url = self.context.absolute_url()
        criteria = self.searchCriteria()
        tabs = []
        for state in STATES:
            # switching tabs keeps the search
            params = {}
            if state != "active":
                params["state"] = state
            if self.searchText:
                params["q"] = self.searchText
            tabs.append(
                {
                    "state": state,
                    "url": url + "?" + urlencode(params) if params else url,
                    "count": len(
                        catalog(
                            portal_type="ShortUrl",
                            path={"query": path, "depth": 1},
                            review_state=state,
                            **criteria,
                        )
                    ),
                    "selected": state == self.state,
                }
            )
        return tabs

    def baseUrl(self):
        return getBaseUrl()

    def localizedDate(self, value):
        return api.portal.get_localized_time(datetime=value) if value else ""

    def canAdd(self):
        return api.user.has_permission("mbarde.shorturls: Add ShortUrl", obj=self.context)

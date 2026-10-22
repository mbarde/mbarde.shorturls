# -*- coding: utf-8 -*-
from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.content.short_url import SUFFIX_PATTERN
from plone import api
from Products.Five.browser import BrowserView
from zExceptions import NotFound
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse


@implementer(IPublishTraverse)
class GoView(BrowserView):
    """Redirect `@@go/<suffix>` to the target url of the matching short url.

    Public: short urls themselves are not visible to anonymous users (see
    shorturl_workflow), so they are looked up regardless of permissions.

    Unknown suffixes and disabled short urls redirect to the "fallback target
    url" (see control panel).
    """

    suffix = None
    # @@go/<suffix>/<something>
    extra_path = False

    def publishTraverse(self, request, name):
        if self.suffix is not None:
            self.extra_path = True
        else:
            self.suffix = name
        return self

    def __call__(self):
        # no suffix: the base url itself (mapped to @@go by the web server)
        if not self.suffix or self.extra_path or not SUFFIX_PATTERN.match(self.suffix):
            return self.notFound()
        brain = findShortUrlBySuffix(self.suffix)
        # disabled short urls only keep their suffix reserved
        if brain is None or brain.review_state != "active":
            return self.notFound()
        shorturl = brain._unrestrictedGetObject()
        shorturl.countClick(self.request)
        return self.redirect(shorturl.target_url)

    def notFound(self):
        fallback_target_url = api.portal.get_registry_record(
            "mbarde.shorturls.fallback_target_url", default=None
        )
        if not fallback_target_url:
            raise NotFound(self.suffix)
        return self.redirect(fallback_target_url)

    def redirect(self, url):
        response = self.request.response
        # don't let browsers / proxies cache the redirect: the target url may
        # change, the suffix may get registered and clicks should be counted
        response.setHeader("Cache-Control", "no-store")
        response.redirect(url, status=302, lock=True)
        return ""

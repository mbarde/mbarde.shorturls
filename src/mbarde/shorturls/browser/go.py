# -*- coding: utf-8 -*-
from mbarde.shorturls.content.short_url import findShortUrlBySuffix
from mbarde.shorturls.content.short_url import SUFFIX_PATTERN
from Products.Five.browser import BrowserView
from zExceptions import NotFound
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse


@implementer(IPublishTraverse)
class GoView(BrowserView):
    """Redirect `@@go/<suffix>` to the target url of the matching short url.

    Public: short urls themselves are not visible to anonymous users (see
    shorturl_workflow), so they are looked up regardless of permissions.
    """

    suffix = None

    def publishTraverse(self, request, name):
        if self.suffix is not None:
            # @@go/<suffix>/<something>
            raise NotFound(name)
        self.suffix = name
        return self

    def __call__(self):
        if not self.suffix or not SUFFIX_PATTERN.match(self.suffix):
            raise NotFound(self.suffix)
        brain = findShortUrlBySuffix(self.suffix)
        if brain is None:
            raise NotFound(self.suffix)
        shorturl = brain._unrestrictedGetObject()
        shorturl.countClick(self.request)

        response = self.request.response
        # don't let browsers / proxies cache the redirect: the target url may
        # change and clicks should be counted
        response.setHeader("Cache-Control", "no-store")
        response.redirect(shorturl.target_url, status=302, lock=True)
        return ""

# -*- coding: utf-8 -*-
from mbarde.shorturls.utils import getBaseUrl
from plone import api
from plone.protect.utils import addTokenToUrl
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.Five.browser import BrowserView


class ShortUrlView(BrowserView):
    """Default view of a short url, with edit / disable / enable buttons.

    Users don't delete short urls but disable them, which keeps their suffix
    reserved (see shorturl_workflow). Only admins can delete them for real.
    """

    def shortUrl(self):
        """Full short url, or None if no base url is configured."""
        base_url = getBaseUrl()
        return base_url + "/" + self.context.suffix if base_url else None

    def lastClicked(self):
        last_clicked = self.context.last_clicked
        return api.portal.get_localized_time(datetime=last_clicked) if last_clicked else None

    def isDisabled(self):
        return api.content.get_state(self.context) == "disabled"

    def canEdit(self):
        return api.user.has_permission(ModifyPortalContent, obj=self.context)

    def canDelete(self):
        return api.user.has_permission(DeleteObjects, obj=self.context)

    def transitionUrl(self, transition):
        """URL performing the workflow transition, None if not available to
        the current user."""
        workflow = api.portal.get_tool("portal_workflow")
        available = [t["id"] for t in workflow.getTransitionsFor(self.context)]
        if transition not in available:
            return None
        return addTokenToUrl(
            "{0}/content_status_modify?workflow_action={1}".format(
                self.context.absolute_url(), transition
            ),
            self.request,
        )

# -*- coding: utf-8 -*-
from mbarde.shorturls import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from zope import schema
from zope.interface import Interface


class BaseUrlEndsWithSlash(schema.ValidationError):
    __doc__ = _("The base URL must not end with a '/'.")


def isValidBaseUrl(value):
    if value.endswith("/"):
        raise BaseUrlEndsWithSlash(value)
    return True


class IMbardeShorturlsControlPanel(Interface):
    """Settings stored in the registry under the "mbarde.shorturls" prefix."""

    base_url = schema.URI(
        title=_("Base URL"),
        description=_(
            "base_url_description",
            default="The URL short URLs start with, followed by their suffix "
            "(e.g. https://go.example.org).",
        ),
        required=False,
        constraint=isValidBaseUrl,
    )

    fallback_target_url = schema.URI(
        title=_("Fallback target URL"),
        description=_(
            "fallback_target_url_description",
            default="Visitors of unknown short URLs (and of the base URL itself) "
            "get redirected to this URL, e.g. your main website. Leave empty to "
            "show a 'Not found' page instead.",
        ),
        required=False,
    )


class MbardeShorturlsControlPanel(RegistryEditForm):
    schema = IMbardeShorturlsControlPanel
    schema_prefix = "mbarde.shorturls"
    label = _("mbarde.shorturls Settings")


MbardeShorturlsControlPanelView = layout.wrap_form(
    MbardeShorturlsControlPanel, ControlPanelFormWrapper
)

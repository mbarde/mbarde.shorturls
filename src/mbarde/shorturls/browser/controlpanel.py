# -*- coding: utf-8 -*-
from mbarde.shorturls import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from zope import schema
from zope.interface import Interface


class IMbardeShorturlsControlPanel(Interface):
    """Settings stored in the registry under the "mbarde.shorturls" prefix."""

    base_url = schema.URI(
        title=_("Base URL"),
        description=_(
            "base_url_description",
            default="The URL short URLs start with, followed by their suffix "
            "(e.g. https://go.example.org/).",
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

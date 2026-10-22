# -*- coding: utf-8 -*-
from mbarde.shorturls import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from zope import schema
from zope.interface import Interface

import re


class BaseUrlEndsWithSlash(schema.ValidationError):
    __doc__ = _("The base URL must not end with a '/'.")


def isValidBaseUrl(value):
    if value.endswith("/"):
        raise BaseUrlEndsWithSlash(value)
    return True


class InvalidDomain(schema.ValidationError):
    __doc__ = _("Enter domains only, without protocol or path (e.g. example.org).")

    def doc(self):
        return _(
            "invalid_domain",
            default="${domain} is not a valid domain. Enter domains only, "
            "without protocol or path (e.g. example.org).",
            mapping={"domain": self.args[0] if self.args else ""},
        )


DOMAIN_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$")


# validates the whole list (instead of its value_type): z3c.form only shows
# "Wrong contained type" for errors of single entries
def isValidDomainList(value):
    for domain in value:
        # blank lines are ignored when matching domains
        if domain.strip() and not DOMAIN_PATTERN.match(domain.strip().lower()):
            raise InvalidDomain(domain)
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

    allowed_domains = schema.List(
        title=_("Allowed domains"),
        description=_(
            "allowed_domains_description",
            default="Target URLs of short URLs have to be on one of these "
            "domains (one per line) - including their subdomains, e.g. "
            "example.org also allows www.example.org. Leave empty to allow "
            "all domains. Only checked when short URLs are added or edited.",
        ),
        value_type=schema.TextLine(),
        required=False,
        default=[],
        constraint=isValidDomainList,
    )


class MbardeShorturlsControlPanel(RegistryEditForm):
    schema = IMbardeShorturlsControlPanel
    schema_prefix = "mbarde.shorturls"
    label = _("mbarde.shorturls Settings")


MbardeShorturlsControlPanelView = layout.wrap_form(
    MbardeShorturlsControlPanel, ControlPanelFormWrapper
)

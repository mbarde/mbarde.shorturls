# -*- coding: utf-8 -*-
from mbarde.shorturls import _
from plone import api
from plone.dexterity.content import Item
from plone.indexer import indexer
from plone.rest.interfaces import IAPIRequest
from plone.restapi.deserializer.dxfields import TextLineFieldDeserializer
from plone.restapi.interfaces import IFieldDeserializer
from plone.supermodel import model
from plone.uuid.interfaces import IUUID
from z3c.form import validator
from zope import schema
from zope.component import adapter
from zope.globalrequest import getRequest
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserRequest

import re

SUFFIX_INDEX = "shorturl_suffix"

# same characters as used by the legacy short url system
SUFFIX_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class InvalidSuffix(schema.ValidationError):
    __doc__ = _("Only letters (a-z, A-Z), digits, '-' and '_' are allowed.")


class SuffixInUse(schema.ValidationError):
    __doc__ = _("This suffix is already in use.")


class InvalidTargetUrlScheme(schema.ValidationError):
    __doc__ = _("Only http:// and https:// URLs are allowed.")


def isValidSuffix(value):
    if not SUFFIX_PATTERN.match(value):
        raise InvalidSuffix(value)
    return True


def isValidTargetUrl(value):
    if not value.lower().startswith(("http://", "https://")):
        raise InvalidTargetUrlScheme(value)
    return True


class IShortUrl(model.Schema):

    suffix = schema.TextLine(
        title=_("Suffix"),
        description=_(
            "suffix_description",
            default="The part of the short URL after the base URL. Matched "
            "case-insensitively, so it has to be unique regardless of case.",
        ),
        required=True,
        max_length=100,
        constraint=isValidSuffix,
    )

    target_url = schema.URI(
        title=_("Target URL"),
        description=_("The URL the short URL redirects to."),
        required=True,
        constraint=isValidTargetUrl,
    )

    clicks = schema.Int(
        title=_("Clicks"),
        description=_("How often the short URL has been used."),
        required=False,
        readonly=True,
        default=0,
    )

    is_api = schema.Bool(
        title=_("Created via API"),
        required=False,
        readonly=True,
        default=False,
    )


class ISuffixField(Interface):
    """Marker for IShortUrl["suffix"], see SuffixDeserializer."""


alsoProvides(IShortUrl["suffix"], ISuffixField)


@implementer(IShortUrl)
class ShortUrl(Item):
    """Short URL redirecting to a target URL."""

    # the suffix doubles as title, so editors don't have to enter one and
    # the id gets generated from it (see plone.namefromtitle behavior)
    @property
    def title(self):
        return getattr(self, "suffix", None) or ""

    @title.setter
    def title(self, value):
        pass


def normalizeSuffix(suffix):
    return suffix.lower()


@indexer(IShortUrl)
def suffixIndexer(obj):
    return normalizeSuffix(obj.suffix or "")


def findShortUrlBySuffix(suffix):
    """Return the catalog brain of the short url with the given suffix
    (matched case-insensitively), regardless of permissions and state."""
    catalog = api.portal.get_tool("portal_catalog")
    brains = catalog.unrestrictedSearchResults(
        portal_type="ShortUrl", **{SUFFIX_INDEX: normalizeSuffix(suffix)}
    )
    return brains[0] if brains else None


def checkSuffixAvailable(context, suffix):
    """Raise SuffixInUse if another short url already uses the suffix.

    `context` is the short url itself when editing it (or when creating it via
    plone.restapi), and the container on add forms.
    """
    if not suffix:
        return
    brain = findShortUrlBySuffix(suffix)
    if brain is None:
        return
    own_uid = IUUID(context, None) if IShortUrl.providedBy(context) else None
    if own_uid is None or brain.UID != own_uid:
        raise SuffixInUse(suffix)


class SuffixValidator(validator.SimpleFieldValidator):
    """Unique suffix check for the add/edit forms."""

    def validate(self, value):
        super().validate(value)
        checkSuffixAvailable(self.context, value)


validator.WidgetValidatorDiscriminators(SuffixValidator, field=IShortUrl["suffix"])


@implementer(IFieldDeserializer)
@adapter(ISuffixField, IShortUrl, IBrowserRequest)
class SuffixDeserializer(TextLineFieldDeserializer):
    """Unique suffix check for plone.restapi, which doesn't run z3c.form
    validators (only field validation via deserializers and invariants)."""

    def __call__(self, value):
        value = super().__call__(value)
        checkSuffixAvailable(self.context, value)
        return value


def markCreatedViaApi(obj, event):
    """Remember whether a short url was added through plone.restapi."""
    if IAPIRequest.providedBy(getRequest()):
        obj.is_api = True

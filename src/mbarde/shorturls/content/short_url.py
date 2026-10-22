# -*- coding: utf-8 -*-
from AccessControl import Unauthorized
from BTrees.Length import Length
from datetime import date
from mbarde.shorturls import _
from persistent import Persistent
from plone import api
from plone.autoform import directives
from plone.dexterity.content import Item
from plone.indexer import indexer
from plone.protect.utils import safeWrite
from plone.registry.interfaces import IRegistry
from plone.rest.interfaces import IAPIRequest
from plone.restapi.deserializer.dxfields import TextLineFieldDeserializer
from plone.restapi.interfaces import IFieldDeserializer
from plone.supermodel import model
from plone.uuid.interfaces import IUUID
from urllib.parse import urlsplit
from z3c.form import validator
from z3c.form.interfaces import IEditForm
from zope import schema
from zope.component import adapter
from zope.component import queryUtility
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


class SuffixNotChangeable(schema.ValidationError):
    __doc__ = _("The suffix of a short URL can't be changed.")


class SuffixInUse(schema.ValidationError):
    __doc__ = _("This suffix is already in use.")


class InvalidTargetUrlScheme(schema.ValidationError):
    __doc__ = _("Only http:// and https:// URLs are allowed.")


class TargetUrlDomainNotAllowed(schema.ValidationError):
    __doc__ = _("The domain of this URL is not allowed.")

    def doc(self):
        return _(
            "target_url_domain_not_allowed",
            default="The domain of this URL is not allowed. Allowed domains "
            "(including their subdomains): ${domains}",
            mapping={"domains": ", ".join(getAllowedDomains())},
        )


def getAllowedDomains():
    """Domains target urls are restricted to (see control panel), empty if
    there is no restriction."""
    registry = queryUtility(IRegistry)
    if registry is None:
        return []
    domains = registry.get("mbarde.shorturls.allowed_domains") or []
    # the control panel's textarea may add blank entries
    return [domain for domain in domains if domain.strip()]


def normalizeDomain(domain):
    return domain.strip().lower().rstrip(".")


def isAllowedDomain(url, domains):
    """Whether the host of `url` is one of `domains` or a subdomain of one."""
    if not domains:
        return True
    # hostname: lowercased, without port and user info - so a url like
    # https://example.org@evil.com/ is matched against "evil.com"
    host = normalizeDomain(urlsplit(url).hostname or "")
    if not host:
        return False
    for domain in map(normalizeDomain, domains):
        if domain and (host == domain or host.endswith("." + domain)):
            return True
    return False


def isValidSuffix(value):
    if not SUFFIX_PATTERN.match(value):
        raise InvalidSuffix(value)
    return True


def isValidTargetUrl(value):
    if not value.lower().startswith(("http://", "https://")):
        raise InvalidTargetUrlScheme(value)
    if not isAllowedDomain(value, getAllowedDomains()):
        raise TargetUrlDomainNotAllowed(value)
    return True


class IShortUrl(model.Schema):

    suffix = schema.TextLine(
        title=_("Suffix"),
        description=_(
            "suffix_description",
            default="The part of the short URL after the base URL. Matched "
            "case-insensitively, so it has to be unique regardless of case. "
            "It can't be changed later.",
        ),
        required=True,
        max_length=100,
        constraint=isValidSuffix,
    )
    directives.mode(IEditForm, suffix="display")

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

    last_clicked = schema.Date(
        title=_("Last clicked"),
        description=_("The day the short URL has been used the last time."),
        required=False,
        readonly=True,
    )

    is_api = schema.Bool(
        title=_("Created via API"),
        required=False,
        readonly=True,
        default=False,
    )


class ClickCounter(Persistent):
    """Number of clicks and day of the last click of a short url.

    A separate persistent object, so a click only writes this tiny record
    (not the short url) - including the day costs no additional write. It
    resolves conflicts of concurrent clicks (instead of failing with a
    ConflictError when popular short urls get clicked simultaneously): clicks
    get added up, the later day wins.
    """

    clicks = 0
    # date.toordinal() of the day of the last click, 0 if never clicked
    last_clicked = 0

    def __init__(self, clicks=0, last_clicked=0):
        self.clicks = clicks
        self.last_clicked = last_clicked

    def __getstate__(self):
        return (self.clicks, self.last_clicked)

    def __setstate__(self, state):
        self.clicks, self.last_clicked = state

    def _p_resolveConflict(self, old, saved, new):
        return (saved[0] + new[0] - old[0], max(saved[1], new[1]))

    def click(self, day):
        self.clicks += 1
        if self.last_clicked != day.toordinal():
            self.last_clicked = day.toordinal()


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

    # clicks and the day of the last click are stored in a ClickCounter
    @property
    def clicks(self):
        return self._clickCounter().clicks

    @clicks.setter
    def clicks(self, value):
        self._writableClickCounter().clicks = value or 0

    @property
    def last_clicked(self):
        day = self._clickCounter().last_clicked
        return date.fromordinal(day) if day else None

    @last_clicked.setter
    def last_clicked(self, value):
        self._writableClickCounter().last_clicked = value.toordinal() if value else 0

    def _clickCounter(self):
        counter = getattr(self, "_clicks", None)
        if isinstance(counter, Length):
            # counter of older versions (clicks only)
            return ClickCounter(counter())
        return counter if counter is not None else ClickCounter()

    def _writableClickCounter(self, request=None):
        counter = getattr(self, "_clicks", None)
        if not isinstance(counter, ClickCounter):
            self._clicks = self._clickCounter()
            # the new counter has no oid yet, its creation modifies self
            safeWrite(self, request)
        return self._clicks

    def countClick(self, request=None, today=None):
        """Count a click, marked as safe write for plone.protect (the
        redirect is a GET request)."""
        counter = self._writableClickCounter(request)
        counter.click(today or date.today())
        safeWrite(counter, request)


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
    validators (only field validation via deserializers and invariants).

    Also refuses changing the suffix of an existing short url (the edit form
    only displays it). Sending the unchanged suffix is fine.
    """

    def __call__(self, value):
        value = super().__call__(value)
        current = self.context.suffix
        if current and value != current:
            raise SuffixNotChangeable(value)
        checkSuffixAvailable(self.context, value)
        return value


def markCreatedViaApi(obj, event):
    """Remember whether a short url was added through plone.restapi."""
    if IAPIRequest.providedBy(getRequest()):
        obj.is_api = True


def refuseCopy(obj, event):
    """Short urls can't be copied: the copy would have the same suffix.

    Also refuses copying a folder containing short urls, as copy events are
    dispatched to the contents of a copied folder. Raised before the copy is
    added. Unauthorized (instead of OFS' CopyError) gets turned into a proper
    message by Plone's paste views and into a 401 by plone.restapi.
    """
    raise Unauthorized("Short URLs can't be copied, their suffix has to be unique.")

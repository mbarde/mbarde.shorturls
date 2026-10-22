# -*- coding: utf-8 -*-
from plone import api
from plone.base.interfaces import INonInstallable
from zope.interface import implementer


@implementer(INonInstallable)
class HiddenProfiles(object):

    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return [
            "mbarde.shorturls:uninstall",
        ]


def post_install(context):
    setup_types_in_navigation()
    setup_types_searchable()


# there will be tens of thousands of short urls - keep them out of the
# navigation and the site search
HIDDEN_TYPES = ["ShortUrl"]


def setup_types_in_navigation():
    typesInNav = list(api.portal.get_registry_record("plone.displayed_types"))
    for typeName in HIDDEN_TYPES:
        if typeName in typesInNav:
            typesInNav.remove(typeName)
    api.portal.set_registry_record("plone.displayed_types", tuple(typesInNav))


def setup_types_searchable():
    blacklist = set(api.portal.get_registry_record("plone.types_not_searched"))
    blacklist.update(HIDDEN_TYPES)
    api.portal.set_registry_record("plone.types_not_searched", tuple(blacklist))


def uninstall(context):
    """Uninstall script"""
    # Do something at the end of the uninstallation of this package.

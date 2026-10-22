# -*- coding: utf-8 -*-
from plone import api


def getBaseUrl():
    """Base url of short urls (see control panel), None if not configured."""
    base_url = api.portal.get_registry_record("mbarde.shorturls.base_url", default=None)
    # rstrip: the trailing slash constraint is only enforced by the control
    # panel form (plone.registry's persistent fields drop constraints, so not
    # when set via registry API / registry.xml) and base urls saved before it
    # existed may still have one
    return base_url.rstrip("/") if base_url else None

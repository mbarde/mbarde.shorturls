# -*- coding: utf-8 -*-
from plone.dexterity.content import Container
from plone.supermodel import model
from zope.interface import implementer


class IShortUrlContainer(model.Schema):
    """Folder holding short urls."""


@implementer(IShortUrlContainer)
class ShortUrlContainer(Container):
    """Folder holding short urls."""

    # containers may hold tens of thousands of short urls: an ordered folder
    # stores the order of all items in one list, rewritten on every add /
    # delete, which makes adding slow and causes conflict errors
    _ordering = "unordered"

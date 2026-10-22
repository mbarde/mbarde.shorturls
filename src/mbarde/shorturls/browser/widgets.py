# -*- coding: utf-8 -*-
from mbarde.shorturls.utils import getBaseUrl
from plone.app.z3cform.interfaces import ITextWidget
from plone.app.z3cform.widgets.text import TextWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer


class ISuffixWidget(ITextWidget):
    """Text widget showing the base url in front of the input."""


@implementer(ISuffixWidget)
class SuffixWidget(TextWidget):

    def baseUrl(self):
        return getBaseUrl()


@implementer(IFieldWidget)
def SuffixFieldWidget(field, request):
    return FieldWidget(field, SuffixWidget(request))

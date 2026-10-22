# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing.zope import WSGI_SERVER_FIXTURE

import mbarde.shorturls


class MbardeShorturlsLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=mbarde.shorturls)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "mbarde.shorturls:default")


MBARDE_SHORTURLS_FIXTURE = MbardeShorturlsLayer()


MBARDE_SHORTURLS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(MBARDE_SHORTURLS_FIXTURE,),
    name="MbardeShorturlsLayer:IntegrationTesting",
)


MBARDE_SHORTURLS_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(MBARDE_SHORTURLS_FIXTURE,),
    name="MbardeShorturlsLayer:FunctionalTesting",
)


MBARDE_SHORTURLS_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        MBARDE_SHORTURLS_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        WSGI_SERVER_FIXTURE,
    ),
    name="MbardeShorturlsLayer:AcceptanceTesting",
)

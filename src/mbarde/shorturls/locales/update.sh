#!/bin/bash
# i18ndude should be available in current $PATH (eg by running
# ``export PATH=$PATH:$BUILDOUT_DIR/bin`` when i18ndude is located in your buildout's bin directory)
#
# For every language you want to translate into you need a
# locales/[language]/LC_MESSAGES/mbarde.shorturls.po
# (e.g. locales/de/LC_MESSAGES/mbarde.shorturls.po)

domain=mbarde.shorturls

i18ndude rebuild-pot --pot $domain.pot --create $domain ../
i18ndude sync --pot $domain.pot */LC_MESSAGES/$domain.po

# `sync` flags entries whose "#. Default:" comment changed as fuzzy, and
# msgfmt silently skips fuzzy entries - so their translations would never
# make it into the compiled .mo. This project doesn't use fuzzy translations
# on purpose, so drop the flag.
sed -i '/^#, fuzzy$/d' */LC_MESSAGES/$domain.po

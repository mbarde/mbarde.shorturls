Adding and updating locales
---------------------------

For every language you want to translate into you need a
locales/[language]/LC_MESSAGES/mbarde.shorturls.po
(e.g. locales/de/LC_MESSAGES/mbarde.shorturls.po)

For German

.. code-block:: console

    $ mkdir -p de/LC_MESSAGES
    $ touch de/LC_MESSAGES/mbarde.shorturls.po

For updating locales

.. code-block:: console

    $ ./update.sh

Note
----

The script uses i18ndude and the gettext package for internationalization.

Install them before running the script.

On macOS
--------

.. code-block:: console

    $ brew install gettext

On Windows
----------

see https://mlocati.github.io/articles/gettext-iconv-windows.html

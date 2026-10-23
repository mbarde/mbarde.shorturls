# mbarde.shorturls

Plone-Addon for managing short URLs.

## Installation

`uv pip install mbarde.shorturls`

## Setup

Short URLs live in _Short URL Folders_ (`ShortUrlContainer`), which only
Managers / Site Administrators can add. You can create as many as you like,
e.g. one per institution. In a Short URL Folder:

- every logged-in user can add short URLs - no sharing setup needed
- every short URL is only visible to and editable by its owner (the user who
  created it)
- users with the `Editor` role on the folder (_Sharing_ tab: _Can edit_) can
  see, edit, disable and enable all short URLs in it, users with the `Reader`
  role (_Can view_) can see all of them. Granting these roles on a regular
  folder containing several Short URL Folders applies to all of them.

Suffixes are unique across the whole site, not per folder. They can't be
changed after creation. Leave the suffix empty (in the add form or when
creating short URLs via REST API) to get a random one.

Short URLs are hidden from Plone's site search by default to avoid flooding it, but it possible to use the search in the `shorturls_listing` view or search by suffix (lowercased) or by exact target URL via `@search` endpoint: e.g. `@search?portal_type=ShortUrl&shorturl_suffix=abc` or
`@search?portal_type=ShortUrl&shorturl_target_url=https://example.org/page`.

### Disabling instead of deleting

Owners and Editors can't delete short URLs, they _disable_ them: a disabled
short URL doesn't redirect anymore (visitors get the same response as for an
unknown suffix), but keeps its suffix reserved - otherwise someone else could
register it, and old shared or printed links would lead to their target.
Owners and Editors can enable disabled short URLs again. Only Managers / Site
Administrators can delete short URLs, which frees their suffix.

Short URL Folders are unordered (no drag & drop sorting), as an ordered
folder would get slow with tens of thousands of short URLs.

### Allowed domains

_Allowed domains_ in the control panel restricts the target URLs of short URLs
to these domains (one per line) and their subdomains: `example.org` allows
`example.org`, `www.example.org` etc., but not `notexample.org`. Leave empty to
allow all domains. It's checked when short URLs are added or edited (forms and
REST API) - existing short URLs keep redirecting.

## Redirecting

`<portal-url>/@@go/<suffix>` redirects (`302`) to the target URL of the short
URL with that suffix (matched case-insensitively) and counts the click.
Unknown suffixes - and the base URL itself (`@@go` without a suffix) -
redirect (`302`) to the _Fallback target URL_ configured in the control panel
(e.g. your main website), or return a `404` if none is configured. Don't set
it to the base URL or an unknown short URL, that would redirect in a loop.

To serve short URLs from their own domain (e.g. `https://go.example.org/<suffix>`),
set _Base URL_ in the `mbarde.shorturls` control panel to that domain (used to
display the short URLs) and let the web server rewrite all requests to
`@@go`, e.g. for nginx and a Plone site with id `Plone`:

```
server {
    server_name go.example.org;
    ...
    location / {
        rewrite ^/(.*)$ /VirtualHostBase/https/go.example.org:443/Plone/VirtualHostRoot/@@go/$1 break;
        proxy_pass http://127.0.0.1:8080;
    }
}
```

## Contribute

- Issue Tracker: https://github.com/mbarde/mbarde.shorturls/issues
- Source Code: https://github.com/mbarde/mbarde.shorturls

## Development

### Setup

```
uv venv venv
source venv/bin/activate
uv pip install -e .
uv pip install -r requirements-dev.txt
```

### Test, lint & format

```
venv/bin/pytest
venv/bin/pytest -k name_of_a_test
venv/bin/black src/
venv/bin/flake8 src/
venv/bin/isort src/
```

### Run a local Plone instance

Create a Zope/Plone instance once (creates `instance/`, gitignored, with an
`admin` user):

```
venv/bin/mkwsgiinstance -d instance -u admin:admin
```

Start it:

```
venv/bin/runwsgi instance/etc/zope.ini
```

Then open http://localhost:8080 and use "Create a new Plone site" (log in as
`admin`), adding `mbarde.shorturls` as add-on during site creation, or
afterwards via _Site Setup > Add-ons_.

Set `debug-mode on` in `instance/etc/zope.conf` for template auto-reload
during development (Python changes still need a restart).

### Update translations

```
source venv/bin/activate
uv pip install i18ndude
cd src/mbarde/shorturls/locales
./update.sh
```

Zope only ever loads compiled `.mo` catalogs at startup, never the `.po`
source files directly (and `.mo` files are gitignored, since they're a build
artifact). Add this to the `<environment>` section of
`instance/etc/zope.conf` so a fresh `.po` is automatically compiled to `.mo`
on every restart - otherwise translations silently keep showing the English
text no matter which language is negotiated:

```
<environment>
  zope_i18n_compile_mo_files true
</environment>
```

### Publish to PyPI

1. Bump `version` in `pyproject.toml` (a version can never be uploaded twice), commit and push.
2. Run tests: `venv/bin/pytest`
3. Build fresh (clear `dist/` first, it may contain older versions):

```
rm -rf dist build src/*.egg-info
uv build
uvx twine check dist/*
```

4. Upload with an API token from pypi.org (_Account settings > API tokens_):

```
uv publish --token pypi-...
```

5. Tag the release: `git tag vX.Y.Z && git push --tags`
6. Verify in a clean environment: `uv pip install --pre mbarde.shorturls` (`--pre` is only needed for pre-releases like `1.0.0rc2`).

Optional dry run against TestPyPI (separate account and token):
`uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-...`

### VS Code setup

Plugins:

- `ms-python.black-formatter`: Python formatting
- `ms-python.flake8`: Python linting
- `ms-python.vscode-pylance`: Python language support
- `ms-python.isort`: Python imports sorting
- `esbenp.prettier-vscode`: .html/.pt/.md formatting
- `redhat.vscode-xml`: .xml formatting

Settings:

```json
{
  "[markdown]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "editor.formatOnSave": true,
  "files.associations": {
    "*.pt": "html",
    "*.zcml": "xml"
  },
  "editor.codeActionsOnSave": {
    "source.organizeImports": "always"
  }
}
```

## License

The project is licensed under the GPLv2, see [LICENSE.GPL](LICENSE.GPL).

## AI Usage

Parts of this addon were developed with assistance from Claude Code, Anthropic's agentic coding CLI. The tool was used interactively under human direction and review.

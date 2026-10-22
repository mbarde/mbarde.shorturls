# mbarde.shorturls

Plone-Addon for managing short URLs.

## Installation

`uv pip install mbarde.shorturls`

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

With `debug-mode on` and `Products.PrintingMailHost` installed (part of
`requirements-dev.txt`), outgoing mail is printed to the instance log
(`instance/var/log/event.log`) instead of actually being sent - no local
mail server needed.

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

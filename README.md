# notes2notion #

This script will import from Apple Notes directly into Notion.  Note that
data extraction from Apple Notes is very limited.  See Limitations below.

When working with your data, always make a backup and/or perform testing
in a safe area to ensure that your valuable data is protected!

# Requirements #

The script requires `python3` and `poetry`.  The easiest way to install on macOS is
using [Homebrew](https://brew.sh):

```bash
brew install python3 poetry
```

## Dependencies ##

This application uses `poetry` to manage dependencies.  This protects your local
environment and makes running the application more reliable.

To initialize the environment, simply run:

```bash
poetry install --sync
```

At any time, you may re-run he above command to get the latest supported version of all
dependencies.

# Usage #

You will need an integration for your Notion workspace.  This can be set either using
the command line or by setting the environment variable `NOTION_ACCESS_TOKEN`.  Be sure
that your target import page is shared with your integration.

For more information on setting up the workspace integration, visit the official
[Authorization Guide](https://developers.notion.com/docs/authorization).

Run the script to get a list of configuration options:

```bash
poetry run notes2notion --help
```

Simply run the script with the desired options when ready:

```bash
poetry run notes2notion --auth NOTION_ACCESS_TOKEN --page 2fac8b5571d04310bb2c695cf3d1422b
```

# Limitations #

Apple Notes only exports a limited set of the formatting from the original note.

- Many colors, font sizes, font styles, etc are not preserved.
- Underline is not preserved due to a limitation in Markdown.
- Hyperlinks are not preserved during Apple Notes export.

# Known Issues #

See [Issues](https://github.com/jheddings/notes2notion/issues) to review current bugs
or report new issues.

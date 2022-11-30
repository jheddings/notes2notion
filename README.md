# notes2notion

This is a basic script that will import from Apple Notes directly into Notion.  Note that
data extraction from Apple Notes is very limited.  See Limitations below.

When working with your data, always make a backup and/or perform testing in a safe area
to ensure that your valuable data is protected!

# Requirements

The script requires `python3` and `poetry`.  The easiest way to install on macOS is using
[Homebrew](https://brew.sh):

```bash
brew install python3 poetry
```

## Dependencies

This application uses `poetry` to manage dependencies.  This protects your local
environment and makes running the application more reliable.

To initialize the environment, simply run:

```bash
poetry install
```

At any time, you may re-run this command to get the latest supported version of all
dependencies.

# Usage

You will need to edit the default configuration file.  Specifically, you need to set
up an integration for your Notion workspace and set the `auth_token` property.  In
addtion, you will need to provide the ID or URL of the top-level archive page where
notes will be imported.  This page must be shared with your integration token.

For more information on setting up the workspace integration, visit the official
[Authorization Guide](https://developers.notion.com/docs/authorization).

There are several other configuration options that control how the script handles note
content.  Check the configuration document in the script for more details.

Run the script, as shown:

```bash
poetry run python main.py notes2notion.yaml
```

You will see the script print the name of each note as it is processed.

# Limitations

Apple Notes only exports a limited set of the formatting from the original note.

- Many colors, font sizes, font styles, etc are not preserved.
- Underline is not preserved due to a limitation in Markdown.
- Hyperlinks are not preserved, due to a limitation in Apple Notes.

# Known Issues

See [Issues](https://github.com/jheddings/notes2notion/issues) to review current bugs or
report new issues.

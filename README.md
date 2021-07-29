# notes2notion

> :warning: **Unofficial API**: This script uses the unofficial Notion API client.
Now that the official API client has been released, this script may not work until I
get the time to port to the official API.  Unfortunately, the new API does not have
all required features to import content from Notes.  If anyone would like to contribute,
feel free to submit a pull request or contact me directly.

This is a basic script that will import from Apple Notes directly into Notion.

When working with your data, always make a backup and/or perform testing in a safe area
to ensure that your valuable data is protected!

# Requirements

The script requires `python3`.  The easiest way to install on macOS is using
[Homebrew](https://brew.sh):

```bash
brew install python3
```

## Dependencies

You will also need to install the dependencies using `pip`:

```bash
python3 -m pip install -r requirements.txt
```

For advanced users, you may want to do this in a virtual environment to avoid
conflicts with your system modules.

# Usage

You will need to edit the default configuration file.  Specifically, you need to set
your `token_v2` cookie from an authenticated session, assign a top-level import page
and (optionally) provide an import log.

There are several other configuration options that control how the script handles note
content.  Check the configuration document in the script for more details.

Run the script, as shown:

```bash
python3 main.py --config notes2notion.yaml
```

You will see the script print the name of each note as it is processed.  If you
specified the Import Log, you can see the progress in real time.

# Limitations

Apple Notes only exports a limited set of the formatting from the original note.
Specifically, many colors, font sizes, font styles, etc are not preserved.

Underline is not preserved due to a limitation in Markdown.

Hyperlinks are not preserved, since they are not exported from Apple Notes.

Attachments (other than pictures) are not uploaded.  We can provide some metadata for
attachments to help track them down, but the note does not contain enough information
to add them in the export.

Tables are converted to Notion databases, which may alter the appearance or structure
for some types of tables.

# Known Issues

The script is VERY slow.  This is due to the way blocks are built using the
[notion-py](https://github.com/jamalex/notion-py) client.  Essentially, each "block"
in the source note is reconstructed on the server one-by-one.  I'm sure there are ways
to improve this, I just haven't taken the time to do so.

Some characters in title blocks (especially quotes) or styling can cause odd behavior
in the note body.

Please report any `yaml.parser.ParserError` errors.  These are caused by unexpected
characters in the note title or other metadata.

Some attachments (like scanned documents) are not captured properly, since they are
actually stored as multiple files in the account.

Network timeouts are common...  Using the Import Log will help resume from a failed
session.

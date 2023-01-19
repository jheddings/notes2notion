# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import re

import yaml

log = logging.getLogger(__name__)


def tell_app(app, *args):
    import applescript

    script = "\n".join(args)

    res = applescript.tell.app(app, script)

    if res.code != 0:
        print(f"!! ERROR - {res.err}")
        return None

    # do some basic string to type mapping...
    if res.out == "null":
        return None
    if res.out == "false":
        return False
    if res.out == "true":
        return True
    if len(res.out) == 0:
        return None

    return res.out


def tell_notes(*args):
    return tell_app("Notes", *args)


class Notes(object):
    def __init__(self):
        self.logger = log.getChild("Notes")

    def __iter__(self):
        note_ids = self.get_all_ids()
        self.logger.debug("starting iterator: %d notes", len(note_ids))
        return Notes.Iterator(self, note_ids)

    def __getitem__(self, note_id):
        return self.get(note_id)

    def get_all_ids(self):
        # the 'notes' object serializes as a list of Core Data URL's...
        notes_raw = tell_notes("return notes of default account")
        notes = re.split(r", *", notes_raw)
        self.logger.debug("parsing %d links", len(notes))

        # extract the full core data identifier; the strings from our list
        # contain extra identifiers at the beginning (note id x-coredata...)
        note_ids = [re.sub(r"^.*(x-coredata://.*/p[0-9]+)", r"\1", x) for x in notes]

        return note_ids

    def delete(self, note_id):
        self.logger.debug("deleting note: %s", note_id)

        # FIXME this isn't working...

        tell_notes(
            "repeat with theNote in notes of default account",
            "  set noteID to id of theNote as string",
            f'  if noteID is equal to "{note_id}" then',
            "    delete theNote",
            "  end if",
            "  end repeat",
        )

    def get(self, note_id):
        self.logger.debug("loading note: %s", note_id)

        # to get the data from Notes, we will get a dump from AppleScript
        # as YAML that we can turn back into a Python object

        text = tell_notes(
            # there is no direct way to get a note from AppleScript using the ID...
            # so we have to loop over all notes and look for the right one.
            # on large databases, this takes a VERY long time for some reason
            "repeat with theNote in notes of default account",
            "  set noteID to id of theNote as string",
            f'  if noteID is equal to "{note_id}" then',
            # determine the the Notes folder
            # TODO get the full folder path
            '    set folderName to ""',
            "    set theContainer to container of theNote",
            "    if theContainer is not missing value",
            '      set folderName to "/" & (name of theContainer)',
            "    end if",
            # "export" the note data when we find it...
            '    set noteMeta to "meta:" ¬',
            '      & "\n  id: " & quoted form of (id of theNote as string) ¬',
            '      & "\n  name: " & quoted form of (name of theNote as string) ¬',
            '      & "\n  folder: " & quoted form of folderName ¬',
            '      & "\n  creation_date: " & quoted form of (creation date of theNote as string) ¬',
            '      & "\n  modification_date: " & quoted form of (modification date of theNote as string) ¬',
            '      & "\n  locked: " & (password protected of theNote as boolean) ¬',
            '      & "\n  shared: " & (shared of theNote as boolean) ¬',
            '      & "\nattachments:"',
            "    repeat with theAttachment in attachments of theNote",
            '      set noteMeta to noteMeta & "\n  - id: " & (id of theAttachment as string) ¬',
            '      & "\n    name: " & quoted form of (name of theAttachment as string) ¬',
            '      & "\n    ref: " & quoted form of (content identifier of theAttachment as string) ¬',
            '      & "\n    creation_date: " & quoted form of (creation date of theAttachment as string) ¬',
            '      & "\n    modification_date: " & quoted form of (modification date of theAttachment as string) ¬',
            '      & "\n    url: " & (url of theAttachment)',
            "    end repeat",
            '    return noteMeta & "\n---\n" & (body of theNote as string)',
            "  end if",
            "end repeat",
        )

        # bail if nothing came out...
        if text is None:
            self.logger.debug("Note is empty: %s", note_id)
            return None

        self.logger.debug("parsing %d bytes from export", len(text))

        # parse the output from AppleScript into a Python object...
        (text_meta, text_body) = text.split("---", maxsplit=1)

        # adjust the metadata to account for `quoted form of`
        text_meta = text_meta.replace("'\\''", "''")

        note = yaml.full_load(text_meta)

        note["body"] = text_body.strip()
        self.logger.debug("loaded note - %s", note["meta"]["name"])

        return note

    class Iterator(object):
        outer = None
        iter_idx = None

        def __init__(self, outer, note_ids):
            self.note_ids = note_ids
            self.iter_idx = 0
            self.outer = outer
            self.logger = log.getChild("Notes.Iterator")

        def __next__(self):
            self.logger.debug("load next note - cursor: %d", self.iter_idx)

            # make sure we were properly initialized
            if self.iter_idx is None or self.note_ids is None:
                raise ValueError

            # make sure the next index is in bounds
            if self.iter_idx < 0 or self.iter_idx >= len(self.note_ids):
                raise StopIteration

            note_id = self.note_ids[self.iter_idx]
            self.logger.debug("next note ID: %s", note_id)

            # set up for next call...
            self.iter_idx += 1

            return self.outer.get(note_id)

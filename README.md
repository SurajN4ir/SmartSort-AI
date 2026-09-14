# SmartSort

SmartSort is a desktop app that looks at a messy folder, works out what's in
it, and proposes a clean structure to organize it into — without moving a
single file until you approve the plan.

```
Downloads/                      Downloads/
├── resume.pdf                  ├── Documents/
├── assignment.docx      --->   │   ├── resume.pdf
├── Messi.jpg                   │   └── assignment.docx
├── setup.exe                   ├── Images/
├── project.zip                 │   └── Messi.jpg
└── invoice.pdf                 ├── Applications/
                                │   └── setup.exe
                                ├── Archives/
                                │   └── project.zip
                                └── Documents/
                                    └── invoice.pdf
```

## How it works

1. **Scan** — reads the files in a folder (name, extension, size, modified date).
2. **Classify** — a rule-based engine maps each file's extension to a category
   (Documents, Images, Videos, Code, Archives, ...).
3. **Plan** — builds a full move plan (source → destination), resolving name
   collisions automatically. Nothing on disk changes at this point.
4. **Review** — every proposed move is shown before anything happens. Files
   can be excluded or reassigned to a different category.
5. **Apply** — only the moves you approved are executed, and every session is
   recorded so it can be undone later.

Nothing moves until you click *Apply*. That review step is the whole point:
running SmartSort on a folder full of files should never be a leap of faith.

## Project structure

```
smartsort/
├── scanner.py       # walks a directory, collects file metadata
├── categorizer.py   # extension -> category rules, plus AI-guess merging
├── semantic.py       # optional LLM-based classifier (Smart Organize)
├── planner.py       # turns classified files into a move plan
├── duplicates.py    # content-hash duplicate detection + cleanup plan
├── organizer.py     # executes a plan on disk, and undoes it later
├── database.py      # SQLite-backed scan/session history
├── local_config.py  # local-only settings (e.g. the API key)
├── models.py         # shared data structures
└── gui/              # CustomTkinter desktop UI
    ├── app.py
    ├── overview.py    # select -> scan -> propose -> review -> apply
    ├── duplicates.py  # select -> scan -> review -> clean up
    ├── history.py     # past sessions, drill-down, undo
    └── settings.py
main.py               # entry point
tests/                 # pytest suite for the core pipeline
```

The core pipeline (scanner, categorizer, planner, organizer, database) has no
GUI dependency and is fully unit tested. The GUI is a thin layer on top of it.

## Smart Organize (optional AI layer)

By default SmartSort classifies purely by file extension -- fast, free, and
fully offline. Turning on **Smart Organize** in the app adds an opt-in second
pass that asks an LLM (via the Anthropic API) to group files by what they
*mean* rather than just their type:

```
ML_Assignment_Final.pdf          ->  University/Machine Learning/Assignments
RealMadrid_vs_Barcelona_2026.mp4 ->  Football/Real Madrid/Matches
```

It's entirely additive: it needs your own Anthropic API key (set once in
Settings, stored locally on your machine, never in this repo), only runs
when you tick the checkbox, and any file it can't confidently place just
keeps its normal rule-based category. Every suggestion still goes through
the same review screen -- with a confidence score next to each AI-placed
file -- before anything moves.

Two extra signals feed into the same pass, both automatic once it's on:
- **Content previews**: for plain-text files (`.txt`, `.md`, `.py`, `.json`,
  ...) a short snippet from inside the file is sent along with the
  filename -- often a much stronger signal than the name alone.
- **Existing folder structure**: if the target folder already has
  subfolders from an earlier organize, their names are passed as a hint so
  repeated runs reuse "University" instead of drifting into "Uni" or
  "College" over time.

```bash
pip install -r requirements-ai.txt
```

## Finding and cleaning up duplicates

The **Duplicates** tab scans a folder and everything inside it, groups files
that have byte-identical content (compared by size first, then a content
hash -- never by filename), and shows every group before touching anything.

For each group you pick which copy to keep in place; the review screen
marks the rest "→ Duplicates/" so it's obvious what will move. Nothing is
ever deleted automatically -- extra copies are moved into a `Duplicates/`
folder at the scanned location, the same reviewable, undoable move used
everywhere else in the app, so a cleanup session shows up in History and
can be reversed just like an organize session.

## Running it

Requires Python 3.11+.

```bash
python -m venv venv
venv\Scripts\activate      # on Windows
pip install -r requirements.txt
python main.py
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Design notes

- **Extension-based classification** is deliberate for this version. It's the
  seam where a smarter, content-aware classifier could plug in later without
  touching the scanner, planner, or GUI.
- **SQLite history** means every organize session is remembered, not just
  performed and forgotten — which is what makes an undo feature possible.
- **Dry-run by default**: the planner only ever produces a proposal. The
  organizer is the one and only place that touches the filesystem, and it
  only runs on files you've explicitly approved in the review screen.

## License

MIT — see [LICENSE](LICENSE).

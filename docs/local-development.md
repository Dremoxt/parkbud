# Working on the site locally

Everything so far has been edited through GitHub. You can do the same work on
your own machine instead: keep the whole site and its data as files, see every
change in a real browser before anyone else does, and push only once it looks
right and the checks pass.

Nothing about the site changes. `main` is still what is published, GitHub still
runs the same checks on every push — you just stop being the first person to
find out something broke.

## What you need once

| | |
|---|---|
| **Git** | https://git-scm.com/downloads — macOS and most Linux have it already (`git --version`) |
| **Python 3** | `python3 --version`. Preinstalled on macOS and Linux; on Windows install from python.org and tick "Add python.exe to PATH" |
| **Node 22** | https://nodejs.org — only needed for the browser tests |
| **An editor** | VS Code (https://code.visualstudio.com) is a good default |

## Get the site onto your machine

```sh
git clone https://github.com/dremoxt/parkbud.git
cd parkbud
tools/dev.sh setup          # installs the test dependencies and Chromium
tools/dev.sh hooks          # optional: git push runs the checks first
```

That is the "data locally" part — `data/*.csv`, the seven language pages and
every image are now ordinary files in the `parkbud` folder. Open the CSVs in
Excel, Numbers or LibreOffice; open the HTML in your editor.

Windows: run the `tools/dev.sh` commands from Git Bash (installed with Git), or
use the raw commands each section lists.

## The loop

### 1. Start a branch

Never work on `main` — that is the published site.

```sh
git switch main
git pull                      # get whatever was merged since last time
git switch -c prices-october  # any short name for what you are doing
```

### 2. Edit

Parking facts, names, descriptions and UI labels live in `data/`. Read
[`data/README.md`](../data/README.md) for what each column means. Editing the
CSV is the supported way to change a lot — the HTML rows are generated from it,
and a hand-edit to a page will be overwritten and fails the checks.

### 3. Rebuild what is generated

```sh
tools/dev.sh build
# or: python3 tools/build-lots.py --write && python3 tools/build-llms-txt.py
```

This writes the parking rows into all seven language pages and regenerates
`llms.txt`. Skip it and the checks will tell you.

### 4. Look at it

```sh
tools/dev.sh serve            # or: python3 -m http.server 8000
```

Then open http://localhost:8000 — and http://localhost:8000/hu/, `/de/`, `/ro/`,
`/sr/`, `/hr/`, `/sk/` for the translations. Edit, save, reload; there is no
build step and no watcher to wait for.

Open the file directly (`file:///…/index.html`) and the language links and
consent banner behave differently than in production, so use the local server
rather than double-clicking `index.html`.

Check the phone layout too: in Chrome, F12 → the phone icon → pick iPhone SE.
Most of what has broken on this site broke at narrow widths.

### 5. Run the checks CI runs

```sh
tools/dev.sh test             # static checks + the two browser suites
tools/dev.sh check            # just the fast ones, no browser
```

`check` takes a couple of seconds and catches drift between the data and the
pages, broken references, a sitemap pointing at a missing file, and analytics
escaping the consent gate. `test` also drives a real Chromium over the filters,
the mobile menu and the consent banner. See
[`tests/README.md`](../tests/README.md) for what each suite covers.

Green here means green on GitHub — it is the same three commands the workflow
runs.

### 6. Commit

```sh
git add -A
git status                    # read this: it is your last look before it is history
git commit -m "October prices for the four shuttle lots"
```

Commit the CSV **and** the regenerated HTML together. They are one change.

### 7. Push when it is as expected

```sh
git push -u origin prices-october
```

If you installed the hook, this runs the checks first and refuses the push
while anything is failing. (`git push --no-verify` overrides it, for when you
want a red branch on GitHub on purpose.)

Then open a pull request on GitHub from the link the push prints, let CI
confirm, and merge. The live site updates from `main` a minute or so later.

## Undoing things

Working locally means mistakes are cheap and private:

```sh
git diff                      # what have I changed but not committed?
git restore index.html        # throw away my changes to one file
git restore .                 # throw away everything uncommitted
git switch main               # leave the branch alone and go back to safety
```

Nothing is on GitHub until you push, and nothing is live until a pull request
is merged into `main`.

## If something goes wrong

| Symptom | Cause |
|---|---|
| `tools/dev.sh: Permission denied` | `chmod +x tools/dev.sh` |
| `page has drifted from data/lots.csv` | You edited HTML by hand, or edited the CSV without running `tools/dev.sh build`. The build is the fix; the hand-edit belongs in the CSV. |
| `llms.txt is out of date` | You changed parking or service cards. Run `tools/dev.sh build`. |
| Browser suites skipped | `tools/dev.sh setup` was never run in this clone |
| `Address already in use` on serve | Something else has port 8000: `PORT=8080 tools/dev.sh serve` |
| Old content in the browser | Hard-reload: Cmd/Ctrl + Shift + R |

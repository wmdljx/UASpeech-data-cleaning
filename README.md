# UASpeech interactive project page

Buildless HTML/CSS/JavaScript for the `gh-pages` branch. The reconstruction code
and final tables remain on [main](https://github.com/wmdljx/UASpeech-data-cleaning).

## Publish

In repository **Settings → Pages**, choose **Deploy from a branch**, then
**gh-pages / (root)** and **Save**. The expected project URL is:

https://wmdljx.github.io/UASpeech-data-cleaning/

This branch alone does not turn on GitHub Pages. Wait for the Pages deployment
to finish, then check the URL before announcing it. No additional hosting account,
build dependencies, access tokens or server runtime are needed by the page.

## Preview and update

```bash
python -m http.server 8794 --bind 127.0.0.1
```

To update the browser metadata, provide a checkout of the reconstruction repository
with its archive tag available:

```bash
python tools/make_data.py /path/to/UASpeech-data-cleaning
```

`data.js` contains public speaker summaries, source mappings and sample identifiers,
text and frame intervals. The script records the source commit and four table
checksums. It does not read licensed audio or video. The lawyer figure and original
SVGs are copied from the approved main-branch assets. The two waveforms shown as
before/after are excerpts of that authorized image, not regenerated sound samples.

The site runs entirely in the browser. There are no uploads, command forms,
analytics scripts or third-party font requests. Hosting providers may keep their
own access logs. Reconstruction instructions remain on the main branch.

## Illustrated workflow

The Method section follows the original cleaning diagram with three selectable
routes: valid existing index, incorrect index, and missing index. Each stage has
an illustration; play/pause, previous/next and restart controls advance the
explanation, not an actual processing job. Playback pauses when the walkthrough
leaves the viewport or the browser tab is hidden. Reduced-motion preferences
disable decorative motion; timed stage changes start only on an explicit click.

`workflow.js` and `workflow.css` implement the walkthrough without dependencies.
The incorrect-index route uses the authorized lawyer waveform figure, real
source positions and a corrected-waveform comparison at verification. The valid-
and missing-index routes use only schematic signals and no real sample IDs.
Missing indices route both inputs directly to search. The constructed search
signals illustrate a fixed query, a moving window of equal duration, and the
current candidate comparison; they are not a historical search trace or computed
similarity scores. Candidates are labeled separately from verified intervals.
The pace defaults to 10 seconds per stage, with 6- and 15-second options. No
source video frames or editable approvals are presented.

The core overview and links are static HTML so they remain readable without
JavaScript and are available to search engines. A sitemap and canonical URL are
provided; neither guarantees Google indexing or search ranking. If adding a custom
domain, update the canonical/social URL and sitemap together.

## Checks

`tools/test_site.py` uses Playwright and an already-installed Chromium to check
the page at desktop and mobile sizes, all scenarios and case mappings, removed-form links,
source consistency, search-window behavior and playback controls. Install those test dependencies separately if
needed; visitors do not need them. Start the local server first, then run:

```bash
python tools/test_site.py http://127.0.0.1:8794 /path/to/screenshots
python tools/test_workflow.py http://127.0.0.1:8794 /path/to/workflow-screenshots
```

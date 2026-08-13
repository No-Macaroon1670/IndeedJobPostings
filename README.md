# Indeed Job Postings Index — US sector explorer

**Live: <https://no-macaroon1670.github.io/IndeedJobPostings/>**

A single-page explorer for Indeed Hiring Lab's **national, seasonally adjusted** US
job postings index: the national aggregate plus every occupational sector Indeed
still publishes (41 as of the last build), overlaid and compared.

The index is the percentage change in seasonally adjusted postings since
**Feb 1 2020 = 100**, on a seven-day trailing average. A reading of 112 means
postings are 12% above the pre-pandemic baseline.

## Running it locally

```bash
python -m http.server 4188
```

Then open <http://localhost:4188>. It has to be served over `http://` — opening
`index.html` from the filesystem fails because the page fetches `data.json`.

There are exactly three files: `index.html` (the whole app — no build step, no
dependencies, no CDN), `data.json` (the bundled data), and `build_data.py`.

## Updating the data

The live site keeps itself current: [`.github/workflows/update-data.yml`](.github/workflows/update-data.yml)
rebuilds `data.json` at 12:00 UTC daily and commits **only when the numbers actually
move**, which republishes the Pages site. Indeed refreshes weekly but not on a fixed
weekday, so a daily check catches it within a day without creating churn — `build_data.py`
compares against the existing file ignoring its `generated` stamp, so an unchanged day
rewrites nothing. You can also run it on demand from the Actions tab.

Note that GitHub suspends scheduled workflows on repos with no activity for 60 days;
if the data ever goes stale, re-enable the schedule from the Actions tab.

To update by hand instead:

- **In the page** — click *Refresh from source*. It fetches the two CSVs straight
  from GitHub and rebuilds in memory. Nothing is written to disk, so it lasts
  until you reload.
- **On disk** — re-run the build script, which rewrites `data.json`:

```bash
python build_data.py
```

Every path reads the live files, so **series Indeed discontinues disappear on the
next refresh** and newly added sectors show up automatically (unrecognised ones
land in an "Other" group — add them to `GROUPS` in `build_data.py` to file them
properly; the build prints a note when it sees one).

## What you can do with it

**Filter row** (scopes every view):

| Control | Notes |
|---|---|
| Date range | `All / 5Y / 3Y / 12M / 6M / YTD`, or type exact from/to dates |
| Postings | **Total** postings vs **New** postings (on Indeed ≤ 7 days) |
| Measure | index level · rebased to range start · % vs 1 / 3 / 12 months ago · cumulative % vs a flat 100 |
| Smoothing | as published (7-day) · 28 · 91 · 182-day trailing average |

The y-axis is always linear. A log scale was tried and dropped: an index anchored at
100 and living roughly between 50 and 250 has under a decade of range, so log buys no
readability and costs a reader who reasonably assumes linear.

There was also a "Change vs Feb 2020 (%)" measure, removed because it is just
`index − 100` — the identical curve with relabelled axis ticks. (It had been
marginally distinct only while the log scale existed, since a series crossing zero
can't be logged.) The table's *vs Feb 2020* column still gives that percentage view.

### Cumulative % vs a flat 100

**How far total postings ran above or below a counterfactual index held flat at 100
for the whole window.** National reads **+18.9%**: cumulatively, US postings since
Feb 2020 came in 18.9% above where a permanently-at-baseline market would have put
them. Where the curve crosses zero is the moment a sector finished paying back its
2020 deficit — nationally **5 September 2021**.

Mechanically it is the running trapezoid integral of `index − 100`, divided by the
days spanned. Because the counterfactual baseline is exactly 100, the percentage
and the mean index-point gap are the *same number*:

```
area / (100 × days) × 100  ≡  area / days
44,825.46 / (100 × 2372) × 100  =  18.8977 %
```

The table's **Cumulative %** column is that same figure for the current window,
always computed on the index level whatever measure is selected, so the column
means one thing.

Percent rather than raw index-point-days, because the raw area grows mechanically
with window length — a 6-month and a 6-year figure can't be compared. Normalised,
they can: national reads +18.9% / +10.6% / +2.6% over All / 3Y / 12M.

Three things to hold in mind, all of them real:

- **It nets the boom against the bust.** Software Development sits at 75.5 today but
  scores **+5.2%** over the full window, because 2021–22 more than paid for the
  crash — it was +42.8% at the end of 2022 and has been falling since. The measure
  is a cumulative history, not a health check on the present.
- **Every number depends on the visible window**, and drag-to-zoom changes it
  silently. Software Development is +5.2% from Feb 2020 but **−30.6%** over the
  trailing three years — same sector, same end date, opposite sign. The caption
  always names the date accumulation starts from.
- **Smoothing delays the start.** A 182-day average blanks the first 181 days, so
  accumulation begins on 31 Jul 2020 rather than 1 Feb 2020. The caption says so.

Integrating the raw index instead of its deviation from 100 would be useless: the
constant baseline dominates and all 42 sectors land within 1.69× of each other.

**Views:**

- **Overlay** — all selected sectors on one axis. Crosshair tooltip lists every
  series at the hovered date, sorted. Drag to zoom, double-click to reset. With
  the chart focused, ← / → move the crosshair (Shift = 30 days), Home/End jump to
  the ends, Esc dismisses.
- **Small multiples** — one panel per sector with the national index behind it in
  grey. Shared y-axis by default; uncheck to let each panel use its own range.
- **Table** — every value the charts show, sortable, plus 1/3/12-month changes.
  This is the accessible twin of the charts; nothing is reachable only by hover.

**Hover to highlight** (the way to find one sector in a crowded chart): pointing at
a sector — in the picker or in the legend — pulls its line to the front at full
strength, fades every other line back, and labels it. Keyboard focus does the same,
so it works without a mouse, and the picker row and legend entry highlight together
so you can see which sector you're on. Hovering a sector that *isn't* selected draws
it as a dashed preview without changing the y-scale, so you can scan the whole list
before committing to a selection. In small multiples the matching panel lifts
instead. Both charts pre-render their faded and full layers, so a hover is a blit
plus one line — scrubbing all 42 sectors holds 60 fps.

*Download CSV* exports exactly what's on screen — the selected sectors, over the
current window, with the current measure and smoothing applied.

## Design notes

- **Eight colours, assigned by entity.** A sector keeps its hue when you filter
  others out. Past eight selections the tail is drawn in grey and labelled
  "Other" rather than cycling hues that colourblind readers can't separate — use
  small multiples or the table to compare more than eight at once.
- Colours are the validated categorical palette from the `dataviz` skill, stepped
  separately for light and dark. The theme follows your OS; the *Theme* button
  overrides it.
- Sector names come from Indeed's CSVs and are inserted with `textContent`
  everywhere, never `innerHTML`.

## Caveats worth knowing

- Indeed adopted a new seasonal-adjustment method (the Bundesbank daily-series
  approach) in **November 2024** and revised all history. Numbers you saved from
  an older vintage won't match.
- Sectors are Indeed's own categorisation of normalised job titles, not NAICS or
  SOC — "Banking & Finance" is not the BLS financial-activities sector.
- The 1/3/12-month columns use 30/91/365-day lags, not calendar months.
- This is postings on Indeed, not total US labour demand; Indeed's market share
  varies by sector, so cross-sector *levels* are only comparable as changes from
  each sector's own Feb 2020 baseline.

Source: [hiring-lab/job_postings_tracker](https://github.com/hiring-lab/job_postings_tracker) ·
[methodology FAQ](https://www.hiringlab.org/indeed-data-faq/)

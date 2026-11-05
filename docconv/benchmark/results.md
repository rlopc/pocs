# Profile comparison (phase 3)

Snapshot of `benchmark/run.py` on 2026-11-05: Docling 2.147.0, docling-core 2.106.0,
docling-parse 7.24.2; model revisions as pinned in `src/docconv/profiles.toml`. The raw
results are in `data/outputs/<env>/benchmark.json` (not versioned).

## How to read this

- **What is measured:** Docling's Markdown export plus image renaming, *without* the
  post-processing rules (they come later). Normalised metrics are barely affected by
  post-processing; strict metrics, emphasis and structure are indicative only.
- **Cases:** 6 real documents (4 text PDFs, 1 scanned PDF, 1 PNG) and 11 synthetic
  ones, reported separately. Each metric is computed per document and averaged per
  type (macro). The scan and image rows rest on **one real document each**.
- **Thresholds** (fixed beforehand, `benchmark/cases.toml`): text WER ≤ 1 %, 0 invented
  words, heading F1 ≥ 0.9; scan/image WER ≤ 5 %, exact table shape, heading F1 ≥ 0.8.
  Veto: Mac warm ≤ 20 s/page and cold ≤ 60 s; Linux CPU warm ≤ 60 s/page and cold ≤ 120 s.
  In this phase "pass" is indicative; the thresholds bind in task 4.4.
- **Timing protocol:** one new process per profile and run, all cases in a fixed order;
  cold = process start to first document done; warm = median seconds per page of the
  following documents over 3 runs; memory = peak RSS. A first run above 3× a veto
  limit is stopped and marked vetoed.
- **Rates** are percentages; F1 values are 0–1; "Images" is references found / expected.

## Environments

- **Mac:** Apple M2 Max, 64 GB, macOS 26.6.2; device MPS (automatic).
- **Linux CPU:** Docker Desktop on the same Mac, native `linux/arm64` container
  (`docker run --network none`), 4 CPUs and 7.75 GiB assigned; device CPU. Linux x86_64 is
  checked for correctness in CI, not for speed.

## Known distortions (read them next to the numbers)

1. **No bold anywhere (Bold F1 = 0):** Docling's PDF pipeline does not fill text
   formatting (check V1). Bold has to be recovered from font names later.
2. **Text headings and lists:** exercise key words (`ORDER`) come out as `##` headings, so
   heading F1 is 0.80 with 32 % at the right level, and the exercise list is split into
   one-item lists (lists 0 %). Post-processing targets.
3. **Invented words in text PDFs (mean 0.2):** one word, `90days`: Docling drops a real
   hyphen at a line end in `90-days-in-180-days`.
4. **Images:** in text PDFs, 1 extra image is the ✈ bitmap of `03-02` (the expected file
   uses the emoji, see the transcription notes); in the scan, 1 extra image is the
   full-page scan itself.
5. **Scanned page (`01-01`):** the standard pipelines read the three columns out of order
   and the OCR duplicates fragments ("I'm glad to I'm glad to see you"), which drives
   WER to 60–90 %; WER is order-sensitive by definition.
6. **GLM-OCR (`vlm-glmocr`, C7):** reads in the right order and gets the text almost
   right, but returns plain text: no Markdown headings (heading F1 = 0), bullets inline
   as "•", circled numbers as LaTeX (`$\textcircled{1}$`), and in the PNG the table and
   the 10 images are lost.
7. **Vetoes:** `vlm-granite` (C4) was stopped early on both platforms (Mac: > 60 s for the
   second page; Linux: no page done in 360 s). `vlm-glmocr` (C7) was stopped on Linux
   (no page done in 360 s) and exceeds the Mac warm limit on the PNG (42.6 s/page).
8. **Metric fix before this snapshot:** ordered-list numbers are counted as text (they
   are document content); before the fix, numbers that Docling writes as plain text were
   counted as invented words. Applied to every profile alike.
9. **CPU vs MPS:** quality on Linux CPU matches the Mac within a few tenths, except
   small OCR differences on the scan.

## Decision (indicative)

C7 was activated because no portable profile (C1–C4) reached the normalised scan/image
thresholds. Per type, on real documents:

- **Text:** no profile passes. `standard-rapidocr` (C1) has the lowest WER (0.1 %); it fails
  on the single invented word and on headings, both expected to be fixed by
  post-processing. C1, C2 and C6 give identical text (all read the PDF text layer).
- **Scan:** only `vlm-glmocr` (C7) reaches the WER threshold (1.7 %), on the Mac only; it
  fails on headings. Best portable: `standard-fullocr` (C3), WER 62.6 %.
- **Image:** only `standard-ocrmac` (C6, macOS only) passes (WER 2.9 %). Best portable:
  `standard-fullocr` (C3), WER 14.5 %.
- **Synthetic** (informative): scans pass with C1 and C6; the PNG table loses its image
  column and merges two header cells in every standard profile.

## Mac (MPS)

Environment: date: 2026-11-05, host: macOS-26.6.2-arm64-arm-64bit-Mach-O, cpu: Apple M2 Max, ram_gib: 64

### Mac: Real — text

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 0.1 % | 3.5 % | 0.0 % | 0.2 | 0.5 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.5 | 0.1 | 3043.3 | fail: invented, headings | ok |
| standard-tesseract | 0.1 % | 3.5 % | 0.0 % | 0.2 | 0.5 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.2 | 0.1 | 1470.6 | fail: invented, headings | ok |
| standard-fullocr | 9.2 % | 13.6 % | 7.9 % | 12.8 | 42.8 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 7.6 | 1.6 | 3470.1 | fail: WER, invented, headings | ok |
| vlm-granite (0/4 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | 45.7 | N/A | 1607.1 | fail: missing outputs, WER, invented | vetoed: early cut |
| vlm-granite-mlx | 0.2 % | 3.7 % | 0.1 % | 0.5 | 1.0 | 0.92 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 0/0 | 13.4 | 3.1 | 1889.9 | fail: invented | ok |
| standard-ocrmac | 0.1 % | 3.5 % | 0.0 % | 0.2 | 0.5 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 7.3 | 0.1 | 1545.7 | fail: invented, headings | ok |
| vlm-glmocr | 0.4 % | 0.4 % | 0.7 % | 2.2 | 0.5 | 0.00 | N/A | 100 % | N/A | N/A | 0.04 | N/A | 0/0 | 21.4 | 10.1 | 3675.7 | fail: invented, headings | ok |

Decision: no profile passes (indicative). Lowest WER: **standard-rapidocr**; fails: invented, headings.

### Mac: Real — scan

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 84.7 % | 87.3 % | 64.6 % | 101.0 | 4.0 | 0.64 | 38 % | 22 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.5 | N/A | 3043.3 | fail: WER, headings | ok |
| standard-tesseract | 83.6 % | 89.9 % | 63.3 % | 122.0 | 50.0 | 0.43 | 20 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.2 | N/A | 1470.6 | fail: WER, headings | ok |
| standard-fullocr | 62.6 % | 64.4 % | 50.1 % | 2.0 | 5.0 | 0.80 | 30 % | 22 % | N/A | N/A | 0.00 | N/A | 1/0 | 7.6 | N/A | 3470.1 | fail: WER | ok |
| vlm-granite | 100.0 % | 100.0 % | 100.0 % | 0.0 | 752.0 | 0.00 | N/A | 0 % | N/A | N/A | 0.00 | N/A | 5/0 | 45.7 | N/A | 1607.1 | fail: WER, headings | vetoed: early cut |
| vlm-granite-mlx | 72.6 % | 80.3 % | 62.1 % | 45.0 | 195.0 | 0.64 | 38 % | 22 % | N/A | N/A | 0.00 | N/A | 5/0 | 13.4 | N/A | 1889.9 | fail: WER, headings | ok |
| standard-ocrmac | 89.2 % | 94.3 % | 70.5 % | 75.0 | 3.0 | 0.64 | 38 % | 11 % | N/A | N/A | 0.00 | N/A | 1/0 | 7.3 | N/A | 1545.7 | fail: WER, headings | ok |
| vlm-glmocr | 1.7 % | 11.7 % | 1.9 % | 13.0 | 0.0 | 0.00 | N/A | 0 % | N/A | N/A | 0.00 | N/A | 0/0 | 21.4 | N/A | 3675.7 | fail: headings | ok |

Decision: no profile passes (indicative). Lowest WER: **vlm-glmocr**; fails: headings.

### Mac: Real — image

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 17.9 % | 20.3 % | 15.1 % | 1.0 | 11.0 | 1.00 | 0 % | N/A | 100 % | 48 % | 0.00 | N/A | 9/10 | 9.5 | 4.8 | 3043.3 | fail: WER | ok |
| standard-tesseract | 30.4 % | 35.5 % | 17.3 % | 163.0 | 177.0 | 1.00 | 0 % | N/A | 100 % | 17 % | 0.00 | N/A | 9/10 | 9.2 | 7.1 | 1470.6 | fail: WER | ok |
| standard-fullocr | 14.5 % | 17.4 % | 11.8 % | 1.0 | 11.0 | 1.00 | 0 % | N/A | 100 % | 54 % | 0.00 | N/A | 9/10 | 7.6 | 4.7 | 3470.1 | fail: WER | ok |
| vlm-granite (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | 45.7 | N/A | 1607.1 | fail: missing outputs, WER | vetoed: early cut |
| vlm-granite-mlx | 15.8 % | 18.2 % | 16.1 % | 122.0 | 15.0 | 1.00 | 0 % | N/A | 100 % | 68 % | 0.00 | N/A | 5/10 | 13.4 | 7.6 | 1889.9 | fail: WER | ok |
| standard-ocrmac | 2.9 % | 5.4 % | 2.2 % | 1.0 | 10.0 | 1.00 | 0 % | N/A | 100 % | 67 % | 0.00 | N/A | 9/10 | 7.3 | 3.7 | 1545.7 | pass | ok |
| vlm-glmocr | 13.6 % | 15.8 % | 5.1 % | 109.0 | 10.0 | 0.00 | N/A | N/A | 0 % | 0 % | 0.00 | N/A | 0/10 | 21.4 | 42.6 | 3675.7 | fail: WER, headings, table shape | vetoed: warm |

Decision: **standard-ocrmac** passes and is the fastest warm.

### Mac: Synthetic — text

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 12.3 % | 18.2 % | 7.8 % | 1.2 | 0.0 | 0.86 | 49 % | 33 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 9.5 | 0.1 | 3043.3 | fail: WER, invented, headings | ok |
| standard-tesseract | 12.6 % | 18.7 % | 8.0 % | 1.8 | 0.0 | 0.86 | 49 % | 33 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 9.2 | 0.1 | 1470.6 | fail: WER, invented, headings | ok |
| standard-fullocr | 14.1 % | 18.6 % | 9.9 % | 3.0 | 4.4 | 0.86 | 49 % | 33 % | 100 % | 73 % | 0.00 | 0.00 | 8/8 | 7.6 | 1.3 | 3470.1 | fail: WER, invented, headings | ok |
| vlm-granite (0/5 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | 45.7 | N/A | 1607.1 | fail: missing outputs, WER, invented | vetoed: early cut |
| vlm-granite-mlx | 28.2 % | 35.9 % | 27.3 % | 0.0 | 34.0 | 0.98 | 44 % | 50 % | 0 % | 0 % | 0.00 | 0.00 | 8/8 | 13.4 | 2.3 | 1889.9 | fail: WER | ok |
| standard-ocrmac | 12.3 % | 18.2 % | 7.8 % | 1.2 | 0.0 | 0.86 | 49 % | 33 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 7.3 | 0.1 | 1545.7 | fail: WER, invented, headings | ok |
| vlm-glmocr | 2.4 % | 6.5 % | 1.5 % | 2.0 | 2.8 | 0.00 | N/A | 0 % | 0 % | 0 % | 0.34 | 0.00 | 0/8 | 21.4 | 9.5 | 3675.7 | fail: WER, invented, headings | ok |

### Mac: Synthetic — scan

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 3.1 % | 6.5 % | 1.7 % | 6.8 | 11.0 | 0.97 | 45 % | 50 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 9.5 | 1.2 | 3043.3 | pass | ok |
| standard-tesseract | 4.3 % | 8.8 % | 2.3 % | 4.0 | 4.2 | 0.97 | 45 % | 0 % | 100 % | 40 % | 0.00 | 0.00 | 8/8 | 9.2 | 1.4 | 1470.6 | pass | ok |
| standard-fullocr | 6.1 % | 9.5 % | 4.4 % | 0.4 | 0.4 | 0.97 | 45 % | 44 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 7.6 | 1.1 | 3470.1 | fail: WER | ok |
| vlm-granite (0/5 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | 45.7 | N/A | 1607.1 | fail: missing outputs, WER | vetoed: early cut |
| vlm-granite-mlx | 13.5 % | 20.6 % | 11.5 % | 4.0 | 8.2 | 0.97 | 45 % | 44 % | 100 % | 82 % | 0.00 | 0.00 | 8/8 | 13.4 | 3.0 | 1889.9 | fail: WER | ok |
| standard-ocrmac | 3.3 % | 6.4 % | 2.0 % | 0.0 | 0.4 | 0.97 | 45 % | 50 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 7.3 | 0.6 | 1545.7 | pass | ok |
| vlm-glmocr | 2.4 % | 6.5 % | 1.5 % | 2.0 | 2.8 | 0.00 | N/A | 0 % | 0 % | 0 % | 0.21 | 0.00 | 0/8 | 21.4 | 10.0 | 3675.7 | fail: headings, table shape | ok |

### Mac: Synthetic — image

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 5.7 % | 5.7 % | 2.3 % | 0.0 | 4.0 | 1.00 | 0 % | N/A | 0 % | 4 % | 0.00 | N/A | 8/8 | 9.5 | 2.1 | 3043.3 | fail: WER, table shape | ok |
| standard-tesseract | 9.2 % | 10.3 % | 3.4 % | 8.0 | 12.0 | 1.00 | 0 % | N/A | 0 % | 0 % | 0.00 | N/A | 8/8 | 9.2 | 2.9 | 1470.6 | fail: WER, table shape | ok |
| standard-fullocr | 5.2 % | 5.2 % | 2.1 % | 0.0 | 5.0 | 1.00 | 0 % | N/A | 0 % | 4 % | 0.00 | N/A | 8/8 | 7.6 | 1.9 | 3470.1 | fail: WER, table shape | ok |
| vlm-granite (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | 45.7 | N/A | 1607.1 | fail: missing outputs, WER | vetoed: early cut |
| vlm-granite-mlx | 100.0 % | 100.0 % | 100.0 % | 0.0 | 174.0 | 0.00 | N/A | N/A | 0 % | 0 % | 0.00 | N/A | 8/8 | 13.4 | 1.8 | 1889.9 | fail: WER, headings, table shape | ok |
| standard-ocrmac | 1.1 % | 1.1 % | 0.5 % | 0.0 | 0.0 | 1.00 | 0 % | N/A | 0 % | 4 % | 0.00 | N/A | 8/8 | 7.3 | 1.5 | 1545.7 | fail: table shape | ok |
| vlm-glmocr | 0.0 % | 0.0 % | 0.0 % | 0.0 | 0.0 | 0.00 | N/A | N/A | 100 % | 100 % | 0.00 | N/A | 0/8 | 21.4 | 31.7 | 3675.7 | fail: headings | vetoed: warm |

Early cuts:

- vlm-granite: warm > 60 s/page (3x veto) on b2-week_01-02_reading-source: 60 s for 1 page(s)

## Linux CPU (container)

Environment: date: 2026-11-05, host: macOS-26.6.2-arm64-arm-64bit-Mach-O, docker_cpus: 4, docker_mem_gib: 7.7, arch: aarch64

### Linux: Real — text

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 0.1 % | 3.5 % | 0.0 % | 0.2 | 0.5 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.0 | 0.7 | 2263.4 | fail: invented, headings | ok |
| standard-tesseract | 0.1 % | 3.5 % | 0.0 % | 0.2 | 0.5 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.2 | 0.7 | 1789.1 | fail: invented, headings | ok |
| standard-fullocr | 9.2 % | 13.6 % | 7.9 % | 12.8 | 42.8 | 0.80 | 32 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 7.7 | 2.2 | 2536.4 | fail: WER, invented, headings | ok |
| vlm-granite (0/4 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER, invented | vetoed: early cut |
| vlm-glmocr (0/4 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER, invented | vetoed: early cut |

Decision: no profile passes (indicative). Lowest WER: **standard-rapidocr**; fails: invented, headings.

### Linux: Real — scan

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 84.7 % | 87.3 % | 64.6 % | 101.0 | 4.0 | 0.64 | 38 % | 22 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.0 | N/A | 2263.4 | fail: WER, headings | ok |
| standard-tesseract | 83.9 % | 89.9 % | 63.3 % | 126.0 | 52.0 | 0.43 | 20 % | 0 % | N/A | N/A | 0.00 | N/A | 1/0 | 9.2 | N/A | 1789.1 | fail: WER, headings | ok |
| standard-fullocr | 62.6 % | 64.4 % | 50.1 % | 2.0 | 5.0 | 0.80 | 30 % | 22 % | N/A | N/A | 0.00 | N/A | 1/0 | 7.7 | N/A | 2536.4 | fail: WER | ok |
| vlm-granite (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |
| vlm-glmocr (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |

Decision: no profile passes (indicative). Lowest WER: **standard-fullocr**; fails: WER.

### Linux: Real — image

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 17.9 % | 20.3 % | 15.1 % | 1.0 | 11.0 | 1.00 | 0 % | N/A | 100 % | 48 % | 0.00 | N/A | 9/10 | 9.0 | 8.2 | 2263.4 | fail: WER | ok |
| standard-tesseract | 27.0 % | 31.8 % | 15.0 % | 133.0 | 147.0 | 1.00 | 0 % | N/A | 100 % | 20 % | 0.00 | N/A | 9/10 | 9.2 | 11.9 | 1789.1 | fail: WER | ok |
| standard-fullocr | 14.5 % | 17.4 % | 11.8 % | 1.0 | 11.0 | 1.00 | 0 % | N/A | 100 % | 54 % | 0.00 | N/A | 9/10 | 7.7 | 8.3 | 2536.4 | fail: WER | ok |
| vlm-granite (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |
| vlm-glmocr (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |

Decision: no profile passes (indicative). Lowest WER: **standard-fullocr**; fails: WER.

### Linux: Synthetic — text

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 12.3 % | 18.2 % | 7.8 % | 1.2 | 0.0 | 0.86 | 49 % | 33 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 9.0 | 0.6 | 2263.4 | fail: WER, invented, headings | ok |
| standard-tesseract | 12.5 % | 18.4 % | 8.0 % | 1.6 | 0.0 | 0.86 | 49 % | 33 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 9.2 | 0.7 | 1789.1 | fail: WER, invented, headings | ok |
| standard-fullocr | 14.1 % | 18.6 % | 9.9 % | 3.0 | 4.4 | 0.86 | 49 % | 33 % | 100 % | 73 % | 0.00 | 0.00 | 8/8 | 7.7 | 2.3 | 2536.4 | fail: WER, invented, headings | ok |
| vlm-granite (0/5 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER, invented | vetoed: early cut |
| vlm-glmocr (0/5 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER, invented | vetoed: early cut |

### Linux: Synthetic — scan

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 3.1 % | 6.5 % | 1.7 % | 6.8 | 11.0 | 0.97 | 45 % | 50 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 9.0 | 1.6 | 2263.4 | pass | ok |
| standard-tesseract | 5.3 % | 9.9 % | 2.4 % | 5.6 | 4.4 | 0.97 | 45 % | 0 % | 100 % | 40 % | 0.00 | 0.00 | 8/8 | 9.2 | 2.0 | 1789.1 | fail: WER | ok |
| standard-fullocr | 6.1 % | 9.5 % | 4.4 % | 0.4 | 0.4 | 0.97 | 45 % | 44 % | 100 % | 69 % | 0.00 | 0.00 | 8/8 | 7.7 | 1.7 | 2536.4 | fail: WER | ok |
| vlm-granite (0/5 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |
| vlm-glmocr (0/5 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |

### Linux: Synthetic — image

| Profile | WER n | WER s | CER | Inv | Omit | Head F1 | Head lvl | Lists | Tbl shape | Cells | Bold F1 | Under F1 | Images | Cold s | Warm s/p | Mem MiB | Thresholds | Veto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard-rapidocr | 5.7 % | 5.7 % | 2.3 % | 0.0 | 4.0 | 1.00 | 0 % | N/A | 0 % | 4 % | 0.00 | N/A | 8/8 | 9.0 | 4.0 | 2263.4 | fail: WER, table shape | ok |
| standard-tesseract | 9.8 % | 10.3 % | 3.6 % | 9.0 | 12.0 | 1.00 | 0 % | N/A | 0 % | 0 % | 0.00 | N/A | 8/8 | 9.2 | 5.0 | 1789.1 | fail: WER, table shape | ok |
| standard-fullocr | 5.2 % | 5.2 % | 2.1 % | 0.0 | 5.0 | 1.00 | 0 % | N/A | 0 % | 4 % | 0.00 | N/A | 8/8 | 7.7 | 3.9 | 2536.4 | fail: WER, table shape | ok |
| vlm-granite (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |
| vlm-glmocr (0/1 docs) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0/0 | N/A | N/A | N/A | fail: missing outputs, WER | vetoed: early cut |

Early cuts:

- vlm-granite: cold > 360 s (3x veto) at 361 s
- vlm-glmocr: cold > 360 s (3x veto) at 361 s

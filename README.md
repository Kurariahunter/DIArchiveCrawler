# Disney Infinity Archive Crawler

A resumable command-line inventory tool for Disney Infinity archives. It asks **QuickBMS to list archive members**, then saves searchable filenames, sizes, source paths, statuses, and logs without extracting member payloads.

Useful for locating character packages, comparing asset collections, and planning targeted extraction.

## Requirements

- Python 3 (tested with Python 3.11 on Windows). No Python packages required.
- A local QuickBMS executable and compatible Disney Infinity BMS script, supplied separately.
- Local game assets. No game content, mappings, QuickBMS executable, or BMS script is included.

Obtain QuickBMS and format scripts from their author: [aluigi.altervista.org/quickbms.htm](https://aluigi.altervista.org/quickbms.htm). This wrapper expects a DI script containing `get FILE_NAME basename`; script variants may require adaptation. Only use scripts you trust: the wrapper invokes them as external programs.

## Run

```powershell
py -3 crawl_archives.py "D:\Game\assets" --output "D:\Research\inventory" --quickbms "C:\Tools\quickbms.exe" --bms "C:\Tools\disney_infinity.bms"
```

The output folder must be **outside the source tree**. Use a separate output folder per game/platform/root. The public copy requires explicit tool paths and does not use the original developer's workstation defaults.

Optional switches:

| Option | Purpose |
|---|---|
| `--limit 10` | Process up to ten new/changed archive candidates |
| `--timeout 300` | Allow up to 300 seconds per QuickBMS invocation |
| `--retry-failed` | Revisit failed, opaque, or timed-out results |
| `--mapping paths.csv` | Supply optional logical-name mappings |

Candidates are `.zip` files and eight-hex-digit filenames under an `assets` path. Inputs are processed smallest first. Nested archives are listed as members, not recursively opened.

## Saved results and resume

- `inventory.sqlite`: checkpoint database, committed after each archive.
- `members.jsonl`: member inventory exported at normal completion/interruption.
- `summary.json`: status counts and run scope.
- `logs/`: QuickBMS output for each processed input.

Repeat the command to resume. Completed unchanged inputs are skipped using size/mtime, script fingerprint, and logical-name selection; files are not all rehashed. SQLite saves progress as the scan runs; JSON exports refresh when the run exits through its normal cleanup path. Ctrl+C retains completed checkpoints.

Run only one crawler against a given output database. If files are removed or you change source roots, use a fresh output folder to avoid historical records in results. Initial candidate discovery can take time before per-archive progress appears; ETA is approximate.

## Optional name mapping

CSV columns are `source_path` and `path`. `source_path` identifies the hashed relative route, normally starting with `assets/`; `path` supplies a candidate readable logical path. Ambiguous mappings are not selected.

Mapped basenames help the external BMS script choose its filename-dependent encryption profile. They do not recover unknown keys or prove asset identity.

## Interpretation and limits

`listed` means QuickBMS returned a consistent nonempty file listing. It does **not** verify payload decompression, CRCs, playable characters, or cross-platform compatibility. `opaque_fallback` detects a common single-file `.dat` fallback; a `.dat` result is not automatically a successfully unpacked archive.

Archive/key/compression support depends on the supplied BMS. Ordinary ZIPs may also be rejected or returned as opaque by that script. This tool inventories; it does not repair archives, repack them, or modify the original source files.

## Examples and verification

`examples/` contains results from an invented DI-format archive holding only `demo/note.txt`. Real QuickBMS listing and checkpoint/resume were verified against that synthetic input. Python syntax and CLI help were also checked. These are not exhaustive platform-library tests.

## Contributing

Useful improvements include format-independent listing adapters, additional mapping formats, clearer progress during discovery, and bounded parallel processing with safe checkpoint ownership.

Report the revision, platform, BMS version, exact command, status, and relevant log. Do not post proprietary archives, keys, or personal paths. Preserve applicable credits and licenses for external tools. No repository-wide license is assigned by this README.

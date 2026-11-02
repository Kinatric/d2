# Repository Language

Use English for all file and directory names, file contents, documentation, code comments, annotations, and commit messages. Do not introduce Chinese text into repository files or metadata.

Preserve part identifiers, technical specifications, and source data when translating existing content. Check filenames and readable content for Chinese characters before committing.

## Mandatory Pre-Push Check

Before every push, run `python scripts/check_language.py HEAD` and require a successful result. Keep the versioned pre-push hook enabled with `git config core.hooksPath .githooks`. Never bypass this check with `--no-verify`.

The hook checks every outgoing commit, including filenames, text files, STEP strings, Office XML, extractable PDF text and metadata, and commit messages. Install `scripts/requirements-language.txt` in the Python environment used by the hook. A custom interpreter can be selected with `git config languageCheck.python /path/to/python`.

Images, scanned PDFs, video frames, audio, and unsupported binary formats also require manual language review before pushing. Automated text extraction cannot prove that these assets contain no Chinese. Translate any Chinese content before publishing. Keep all new rules and tooling in English.

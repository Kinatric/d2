"""Reject Chinese characters in commit snapshots and outgoing commit messages."""

import argparse
import io
import re
import subprocess
import sys
import zipfile
from pathlib import PurePosixPath

HAN = re.compile("[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]")
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".mp3", ".wav"}


def git(*args):
    return subprocess.check_output(["git", *args])


def check_text(text, label):
    if HAN.search(text):
        raise ValueError(f"Chinese characters detected: {label}")


def check_blob(data, name):
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in MEDIA:
        return "manual"
    if suffix in {".xlsx", ".docx", ".pptx"}:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.namelist():
                check_text(member, name + " archive entry")
                if member.endswith((".xml", ".rels")):
                    check_text(archive.read(member).decode("utf-8-sig"), name + ":" + member)
        return
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        check_text(str(reader.metadata), name + " metadata")
        for page in reader.pages:
            check_text(page.extract_text() or "", name)
            for annotation in page.get("/Annots", []):
                check_text(str(annotation.get_object()), name + " annotation")
        return "manual"
    if b"\x00" in data and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "manual"
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        text = data.decode("gb18030")
    check_text(text, name)
    if suffix in {".step", ".stp"}:
        for match in re.finditer(r"\\X([24])\\([0-9A-Fa-f]+)\\X0\\", text):
            encoding = "utf-16-be" if match[1] == "2" else "utf-32-be"
            check_text(bytes.fromhex(match[2]).decode(encoding), name + " encoded string")


def commits_to_push(lines):
    commits = set()
    for line in lines:
        _, local, _, remote = line.split()
        if set(local) == {"0"}:
            continue
        revision = local if set(remote) == {"0"} else remote + ".." + local
        commits.update(git("rev-list", revision).decode().splitlines())
    return sorted(commits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision", nargs="?", default="HEAD")
    parser.add_argument("--pre-push", action="store_true")
    args = parser.parse_args()
    commits = commits_to_push(sys.stdin) if args.pre_push else [args.revision]
    seen = set()
    manual = set()
    for commit in commits:
        check_text(git("show", "-s", "--format=%B", commit).decode("utf-8"), "commit message")
        for entry in git("ls-tree", "-rz", commit).split(b"\0"):
            if not entry:
                continue
            metadata, raw_name = entry.split(b"\t", 1)
            name = raw_name.decode("utf-8")
            check_text(name, "filename")
            _, kind, oid = metadata.split()
            if kind != b"blob":
                raise ValueError(f"Manual review required for submodule: {name}")
            if oid in seen:
                continue
            seen.add(oid)
            if check_blob(git("cat-file", "blob", oid.decode()), name) == "manual":
                manual.add(name)
    print(f"Language check passed: {len(commits)} commits, {len(seen)} unique files.")
    if manual:
        print(f"All submitted content must use English. Review the text and audio in {len(manual)} media or binary files before pushing; see AGENTS.md.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Language check failed: {error}", file=sys.stderr)
        sys.exit(1)

# Upload steps — Zenodo new version (owner's five minutes)

1. Go to `zenodo.org`, log in, navigate to the existing record for DOI `10.5281/zenodo.21399411`
   (the E5 registered-run snapshot, tag `e5-verdict-2026-07-16`).
2. Click **New version** on that record.
3. In the file list, remove nothing from the original deposit unless you choose to; **add**
   `E5-CORRECTION.md` from this folder as a new file in the deposit (upload the copy in this
   `publication-prep/zenodo-e5-correction/` folder, not a fresh export — it's already the reviewed
   text).
4. Update the metadata fields using `METADATA.md` in this folder: title, description, version string,
   related identifiers. Copy-paste the description paragraph directly; it's written for the field.
5. Confirm authorship, license, and keywords match (or intentionally extend) the original record's
   values — `METADATA.md` flags the two fields (resource type, license) worth double-checking against
   the existing record before submitting, since Zenodo constrains new versions to match some of the
   original record's settings.
6. Click **Publish**. Zenodo mints the same concept DOI with an incremented version DOI; the old
   version stays permanently accessible and citable, now marked as superseded by this one.

That's the whole act. No file renames, no reformatting — the correction note is ready to upload as-is.

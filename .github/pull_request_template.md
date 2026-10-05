<!-- One extension per pull request: add or change extensions/<id>.toml, nothing else. -->

**Extension:** <!-- its id, and what it does in a sentence -->

**Source code:** <!-- where the code the archive is built from can be read -->

The check (the `index` workflow) has made sure that:

- the entry has every field (`id`, `kind`, `name`, `description`, `author`, `license`, `homepage`, `url`, `sha256`) and no other, and its file is named after its `id`;
- the archive downloads over https://, and its sha256 is the entry's;
- the archive is a tar (plain, gzip or xz) or a zip holding one `module.toml` or `source.toml`, at its root or in its one folder;
- that manifest's `id` and kind are the entry's, it names a `version` and an `api`, and a source's names its `exe`;
- no module or source that ships with Universe has that id.

What the review checks, since no check can:

- [ ] the archive holds what the source code builds, and does what the description says;
- [ ] nothing in it reaches further than it needs: an extension runs as the user, with their files and accounts;
- [ ] the license lets anyone install it.

Merging the pull request is the review. The index is rebuilt once it merges.

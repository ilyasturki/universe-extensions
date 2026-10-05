# universe-extensions

The add-ons [Universe](https://github.com/ilyasturki/universe) lists under "Get more…" and installs with
`universe extension install <id>`. Each one is a module or a source that doesn't ship with Universe: a folder with a
`module.toml` or a `source.toml` and the programs it names, as
[docs/extensions.md](https://github.com/ilyasturki/universe/blob/main/docs/extensions.md) describes. Nothing sandboxes
an extension. It runs as you, with your files and your accounts.

This repo holds one entry per extension. On every merge, CI checks each entry against its archive and publishes the
index Universe reads to the `index` branch:

```
https://raw.githubusercontent.com/ilyasturki/universe-extensions/index/index.json
```

## Listing an extension

1. Publish a release archive of your extension: a tar (plain, gzip or xz) or a zip holding its folder, at the root or
   in one folder. Upload it as a release asset. GitHub's "Source code" archives are generated on demand and their bytes
   can change, which breaks the sha256.
2. Add `extensions/<id>.toml`, named after the manifest's `id`:

   ```toml
   id = "now-playing"
   kind = "module"
   name = "Now Playing"
   description = "Shares the game you play as your chat status."
   author = "Jane Doe"
   license = "MIT"
   homepage = "https://github.com/jane/now-playing"
   url = "https://github.com/jane/now-playing/releases/download/v1.2.0/now-playing-1.2.0.tar.gz"
   sha256 = "…"
   ```

   `sha256sum now-playing-1.2.0.tar.gz` gives the digest. The version and the `api` come from the manifest inside the
   archive, so the entry doesn't repeat them.
3. Open a pull request. Its template lists what the check covers and what the review looks at.

A new version is a pull request changing `url` and `sha256`. Merging is the review, and an entry that goes bad is
removed by another pull request.

## The check

`tools/index` reads every entry, downloads its archive and refuses the run when an entry:

- lacks one of the nine fields, has another, or sits in a file named after another id;
- has a `url` or `homepage` that isn't https://;
- names an archive that doesn't download, or whose sha256 isn't the entry's;
- names an archive holding no `module.toml` or `source.toml` at its root or in its one folder, or holding both;
- has a manifest whose `id` or kind isn't the entry's, that lacks a `version` or an `api`, or, for a source, an `exe`;
- takes an id a module or a source shipping with Universe holds.

Then it writes `index.json`: schema 1, each entry with the manifest's version and api and the archive's size. Author and
license stay here, for the review.

To run it as CI does, against a Universe checkout:

```
python3 -m unittest discover -s tests
tools/index --universe ../universe --out index.json
```

Both need Python 3.11 or later and no package.

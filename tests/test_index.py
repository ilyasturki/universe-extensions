import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "index"

MODULE = 'api = 2\nid = "now-playing"\nname = "Now Playing"\nversion = "1.2.0"\n\n[hooks]\ngame_start = "bin/hook"\n'
SOURCE = 'api = 2\nid = "shop"\nname = "Shop"\nversion = "0.3.1"\nexe = "bin/source"\n'


def tar_gz(files: dict[str, str]) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as t:
        for name, text in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(text.encode()), 0o755
            t.addfile(info, io.BytesIO(text.encode()))
    return out.getvalue()


def zipped(files: dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return out.getvalue()


class Index(unittest.TestCase):
    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.entries = self.dir / "extensions"
        self.entries.mkdir()
        universe = self.dir / "universe"
        for kind, id in (("module", "screenshot"), ("source", "steam")):
            (universe / f"{kind}s" / id).mkdir(parents=True)
            (universe / f"{kind}s" / id / f"{kind}.toml").write_text(f'api = 2\nid = "{id}"\nversion = "0.0.10"\n')
        self.archives = {
            "now-playing": self.archive("now-playing.tar.gz", tar_gz({"module.toml": MODULE, "bin/hook": "#!/bin/sh\n"})),
            "shop": self.archive("shop.zip", zipped({"shop-0.3.1/source.toml": SOURCE, "shop-0.3.1/bin/source": "#!/bin/sh\n"})),
        }

    def archive(self, name: str, body: bytes) -> Path:
        path = self.dir / name
        path.write_bytes(body)
        return path

    def entry(self, id: str, kind: str, archive: Path, **over: str):
        fields = {
            "id": id,
            "kind": kind,
            "name": id.title(),
            "description": f"The {id} {kind}.",
            "author": "Jane Doe",
            "license": "MIT",
            "homepage": f"https://example.org/{id}",
            "url": archive.as_uri(),
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        } | over
        (self.entries / f"{id}.toml").write_text("".join(f"{k} = {json.dumps(v)}\n" for k, v in fields.items()))

    def samples(self):
        self.entry("now-playing", "module", self.archives["now-playing"])
        self.entry("shop", "source", self.archives["shop"])

    def run_index(self, *extra: str) -> subprocess.CompletedProcess:
        command = [sys.executable, str(TOOL), "--universe", str(self.dir / "universe"), "--entries", str(self.entries), *extra]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def index(self) -> dict:
        done = self.run_index("--allow-local")
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def assert_fails(self, entry: str, *extra: str):
        done = self.run_index("--allow-local", *extra)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn(f"failed: {entry}", done.stderr)
        self.assertEqual(done.stdout, "")

    def test_two_samples_make_the_index(self):
        self.samples()
        index = self.index()
        self.assertEqual(index["schema"], 1)
        by_id = {e["id"]: e for e in index["extensions"]}
        self.assertEqual([e["id"] for e in index["extensions"]], ["now-playing", "shop"])
        for id, kind, version in (("now-playing", "module", "1.2.0"), ("shop", "source", "0.3.1")):
            archive = self.archives[id]
            self.assertEqual(by_id[id]["kind"], kind)
            self.assertEqual(by_id[id]["version"], version)
            self.assertEqual(by_id[id]["api"], 2)
            self.assertEqual(by_id[id]["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(by_id[id]["size"], archive.stat().st_size)
            self.assertNotIn("author", by_id[id])

    def test_no_entries_is_an_empty_index(self):
        self.assertEqual(self.index(), {"schema": 1, "extensions": []})

    def test_out_writes_the_file(self):
        self.samples()
        out = self.dir / "index.json"
        done = self.run_index("--allow-local", "--out", str(out))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(json.loads(out.read_text())["extensions"]), 2)

    def test_a_digest_that_differs(self):
        self.samples()
        self.entry("shop", "source", self.archives["shop"], sha256="0" * 64)
        self.assert_fails("shop.toml")

    def test_an_archive_that_does_not_download(self):
        self.entry("shop", "source", self.archives["shop"], url=(self.dir / "gone.zip").as_uri())
        self.assert_fails("shop.toml")

    def test_a_kind_the_archive_does_not_hold(self):
        self.entry("shop", "module", self.archives["shop"])
        self.assert_fails("shop.toml")

    def test_an_id_the_archive_does_not_hold(self):
        self.entry("playing", "module", self.archives["now-playing"])
        self.assert_fails("playing.toml")

    def test_an_id_that_ships(self):
        steam = self.archive("steam.zip", zipped({"source.toml": SOURCE.replace('"shop"', '"steam"')}))
        self.entry("steam", "source", steam)
        self.assert_fails("steam.toml")

    def test_an_id_the_other_kind_ships(self):
        archive = self.archive("steam.tgz", tar_gz({"module.toml": MODULE.replace('"now-playing"', '"steam"')}))
        self.entry("steam", "module", archive)
        self.assert_fails("steam.toml")

    def test_a_file_named_after_another_id(self):
        self.entry("shop", "source", self.archives["shop"])
        (self.entries / "shop.toml").rename(self.entries / "store.toml")
        self.assert_fails("store.toml")

    def test_a_missing_or_unknown_field(self):
        self.entry("shop", "source", self.archives["shop"], license="")
        self.assert_fails("shop.toml")
        self.entry("shop", "source", self.archives["shop"], version="1.0")
        self.assert_fails("shop.toml")

    def test_a_local_url_without_allow_local(self):
        self.entry("shop", "source", self.archives["shop"])
        done = self.run_index()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("failed: shop.toml", done.stderr)

    def test_an_archive_holding_both_kinds(self):
        both = self.archive("both.zip", zipped({"module.toml": MODULE.replace('"now-playing"', '"shop"'), "source.toml": SOURCE}))
        self.entry("shop", "source", both)
        self.assert_fails("shop.toml")

    def test_a_source_with_no_exe(self):
        bare = self.archive("bare.zip", zipped({"source.toml": SOURCE.replace('exe = "bin/source"\n', "")}))
        self.entry("shop", "source", bare)
        self.assert_fails("shop.toml")

    def test_a_manifest_with_no_version_or_api(self):
        bare = self.archive("bare.tar.gz", tar_gz({"pkg/module.toml": 'id = "now-playing"\n', "pkg/bin/hook": ""}))
        self.entry("now-playing", "module", bare)
        self.assert_fails("now-playing.toml")

    def test_not_an_archive(self):
        self.entry("shop", "source", self.archive("shop.bin", b"\x00" * 600))
        self.assert_fails("shop.toml")


if __name__ == "__main__":
    unittest.main()

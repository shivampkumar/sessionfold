from __future__ import annotations

import importlib.util
import io
import json
import os
import random
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).parents[1] / "sessionfold" / "cli.py"
SPEC = importlib.util.spec_from_file_location("sessionfold_cli", SCRIPT)
assert SPEC and SPEC.loader
sessionfold = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sessionfold
SPEC.loader.exec_module(sessionfold)


class SessionfoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / "store"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_session(self) -> tuple[Path, bytes]:
        image_a = b"data:image/png;base64," + (b"QUJD" * 2000)
        image_b = b"data:image/jpeg;base64," + (b"REVG" * 1600)
        content = (
            b"\n".join(
                [
                    b'{"type":"message","image_url":"' + image_a + b'"}',
                    b'{"type":"compacted","replacement_history":[{"image_url":"'
                    + image_a
                    + b'"}]}',
                    b'{"type":"tool","image_url":"' + image_b + b'"}',
                    b'{"type":"compacted","replacement_history":[{"image_url":"'
                    + image_a
                    + b'"}]}',
                    b'{"type":"message","text":"asd:v1:sha256:' + (b"a" * 64) + b'"}',
                ]
            )
            + b"\n"
        )
        path = self.root / "rollout-test.jsonl"
        path.write_bytes(content)
        return path, content

    def make_titled_codex_session(
        self, title: str = "Plan storage cleanup"
    ) -> tuple[Path, bytes, Path]:
        codex_home = self.root / ".codex"
        session_dir = codex_home / "sessions" / "2026" / "09" / "07"
        session_dir.mkdir(parents=True)
        path, content = self.make_session()
        path = path.rename(
            session_dir
            / "rollout-2026-09-07T01-02-03-01a00000-0000-7000-8000-000000000001.jsonl"
        )
        database = sqlite3.connect(codex_home / "state_5.sqlite")
        database.execute("CREATE TABLE threads (id TEXT, rollout_path TEXT, name TEXT)")
        database.execute(
            "INSERT INTO threads VALUES (?, ?, ?)",
            ("01a00000-0000-7000-8000-000000000001", str(path), title),
        )
        database.commit()
        database.close()
        return path, content, codex_home

    def test_codex_title_index_is_read_only_and_path_based(self) -> None:
        path, _, codex_home = self.make_titled_codex_session()
        metadata = sessionfold.load_codex_session_metadata(codex_home)
        found = metadata[sessionfold._metadata_path_key(path)]
        self.assertEqual(found.title, "Plan storage cleanup")
        self.assertEqual(found.thread_id, "01a00000-0000-7000-8000-000000000001")

    def test_codex_picker_title_is_joined_from_local_catalog(self) -> None:
        path, _, codex_home = self.make_titled_codex_session(title="Legacy name")
        state = sqlite3.connect(codex_home / "state_5.sqlite")
        state.execute("UPDATE threads SET name = NULL")
        state.commit()
        state.close()
        catalog_path = codex_home / "sqlite" / "codex-dev.db"
        catalog_path.parent.mkdir()
        catalog = sqlite3.connect(catalog_path)
        catalog.execute(
            "CREATE TABLE local_thread_catalog ("
            "thread_id TEXT, display_title TEXT, observation_sequence INTEGER)"
        )
        catalog.execute(
            "INSERT INTO local_thread_catalog VALUES (?, ?, ?)",
            (
                "01a00000-0000-7000-8000-000000000001",
                "Picker display title",
                1,
            ),
        )
        catalog.commit()
        catalog.close()
        metadata = sessionfold.load_codex_session_metadata(codex_home)
        self.assertEqual(
            metadata[sessionfold._metadata_path_key(path)].title,
            "Picker display title",
        )

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_archive_records_codex_title_and_resolves_it(
        self, _open: mock.Mock
    ) -> None:
        path, _, codex_home = self.make_titled_codex_session()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
            manifest = sessionfold.archive_file(path, self.store, 0, False)
            self.assertEqual(manifest["source"]["title"], "Plan storage cleanup")
            by_title = sessionfold.manifest_path_from_reference(
                "Plan storage cleanup", self.store
            )
            by_id = sessionfold.manifest_path_from_reference(
                manifest["archive_id"], self.store
            )
        self.assertEqual(by_title, Path(manifest["archive_path"]))
        self.assertEqual(by_id, Path(manifest["archive_path"]))

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_scan_and_list_show_codex_title(self, _open: mock.Mock) -> None:
        path, _, codex_home = self.make_titled_codex_session()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
            scan_output = io.StringIO()
            with redirect_stdout(scan_output):
                self.assertEqual(sessionfold.main(["scan", str(path), "--top", "1"]), 0)
            sessionfold.archive_file(path, self.store, 0, False)
            list_output = io.StringIO()
            with redirect_stdout(list_output):
                self.assertEqual(
                    sessionfold.main(
                        [
                            "list",
                            "--store",
                            str(self.store),
                            "--search",
                            "storage cleanup",
                        ]
                    ),
                    0,
                )
            private_output = io.StringIO()
            with redirect_stdout(private_output):
                self.assertEqual(
                    sessionfold.main(
                        ["list", "--store", str(self.store), "--no-titles"]
                    ),
                    0,
                )
        self.assertIn("Plan storage cleanup", scan_output.getvalue())
        self.assertIn("Plan storage cleanup", list_output.getvalue())
        self.assertNotIn("Plan storage cleanup", private_output.getvalue())

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_manual_archive_title_and_relabel(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(
            path, self.store, 0, False, title="Storage archive"
        )
        self.assertEqual(manifest["source"]["title"], "Storage archive")
        self.assertEqual(manifest["source"]["title_source"], "user")
        output = io.StringIO()
        with redirect_stdout(output):
            result = sessionfold.main(
                [
                    "label",
                    manifest["archive_id"],
                    "--store",
                    str(self.store),
                    "--title",
                    "Storage archive updated",
                ]
            )
        self.assertEqual(result, 0)
        updated = json.loads(Path(manifest["archive_path"]).read_text())
        self.assertEqual(updated["source"]["title"], "Storage archive updated")
        self.assertIn("Verified archive", output.getvalue())

    @mock.patch.object(sessionfold, "available_bytes", return_value=1)
    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_archive_refuses_insufficient_headroom(
        self, _open: mock.Mock, _available: mock.Mock
    ) -> None:
        path, _ = self.make_session()
        with self.assertRaisesRegex(RuntimeError, "Insufficient archive headroom"):
            sessionfold.archive_file(path, self.store, 0, False)
        self.assertFalse(self.store.exists())

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_restore_to_original_path(self, _open: mock.Mock) -> None:
        path, original = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, True)
        self.assertFalse(path.exists())
        output = io.StringIO()
        with redirect_stdout(output):
            result = sessionfold.main(
                [
                    "restore",
                    manifest["archive_id"],
                    "--store",
                    str(self.store),
                    "--original",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(path.read_bytes(), original)

    def test_parse_byte_size(self) -> None:
        self.assertEqual(sessionfold.parse_byte_size("2 GiB"), 2 * 1024**3)
        self.assertEqual(sessionfold.parse_byte_size("512M"), 512 * 1024**2)
        with self.assertRaisesRegex(
            sessionfold.argparse.ArgumentTypeError, "Invalid byte size"
        ):
            sessionfold.parse_byte_size("many")

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_deep_scan_counts_duplicate_images(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        report, digests = sessionfold.analyze_file(path, deep=True, recent_minutes=30)
        self.assertEqual(report.image_occurrences, 4)
        self.assertEqual(len(digests), 2)
        self.assertGreater(report.duplicate_image_bytes or 0, 0)
        self.assertEqual(report.replacement_history_records, 2)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_archive_and_restore_are_byte_exact(self, _open: mock.Mock) -> None:
        path, original = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        self.assertTrue(manifest["verified"])
        self.assertTrue(path.exists())
        self.assertEqual(manifest["images"]["unique_blobs"], 2)
        restored = self.root / "restored.jsonl"
        sessionfold.restore_stream(Path(manifest["archive_path"]), restored)
        self.assertEqual(restored.read_bytes(), original)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_second_archive_reuses_global_blobs(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        first = sessionfold.archive_file(path, self.store, 0, False)
        second = sessionfold.archive_file(path, self.store, 0, False)
        self.assertGreater(first["images"]["new_blob_bytes"], 0)
        self.assertEqual(second["images"]["new_blob_bytes"], 0)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_relocated_store_can_be_overridden(self, _open: mock.Mock) -> None:
        path, original = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        archive_id = manifest["archive_id"]
        relocated = self.root / "relocated-store"
        self.store.rename(relocated)
        relocated_manifest = relocated / "archives" / archive_id / "manifest.json"
        verified = sessionfold.verify_archive(relocated_manifest, store=relocated)
        self.assertEqual(verified["source"]["size"], len(original))

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_remove_source_requires_explicit_flag_and_verification(
        self, _open: mock.Mock
    ) -> None:
        path, original = self.make_session()
        original_verify = sessionfold.verify_archive
        with mock.patch.object(
            sessionfold, "verify_archive", wraps=original_verify
        ) as verify:
            manifest = sessionfold.archive_file(path, self.store, 0, True)
        self.assertEqual(verify.call_count, 2)
        self.assertFalse(path.exists())
        self.assertTrue(manifest["source_removed"])
        restored = self.root / "restored.jsonl"
        sessionfold.restore_stream(Path(manifest["archive_path"]), restored)
        self.assertEqual(restored.read_bytes(), original)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_reclaim_after_review_is_byte_exact(self, _open: mock.Mock) -> None:
        path, original = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        reclaimed = sessionfold.reclaim_source(
            Path(manifest["archive_path"]), min_age_minutes=0
        )
        self.assertFalse(path.exists())
        self.assertTrue(reclaimed["source_removed"])
        self.assertFalse(reclaimed["source_removal_pending"])
        restored = self.root / "reclaimed-restore.jsonl"
        sessionfold.restore_stream(Path(manifest["archive_path"]), restored)
        self.assertEqual(restored.read_bytes(), original)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_reclaim_refuses_same_size_source_with_changed_hash(
        self, _open: mock.Mock
    ) -> None:
        path, original = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        recorded_mtime = path.stat().st_mtime_ns
        changed = bytearray(original)
        changed[0] = ord("X")
        path.write_bytes(changed)
        os.utime(path, ns=(recorded_mtime, recorded_mtime))
        with self.assertRaisesRegex(RuntimeError, "SHA-256 has changed"):
            sessionfold.reclaim_source(
                Path(manifest["archive_path"]), min_age_minutes=0
            )
        self.assertTrue(path.exists())

    def test_reclaim_refuses_open_source(self) -> None:
        path, _ = self.make_session()
        with mock.patch.object(sessionfold, "open_by_process", return_value=False):
            manifest = sessionfold.archive_file(path, self.store, 0, False)
        with (
            mock.patch.object(sessionfold, "open_by_process", return_value=True),
            self.assertRaisesRegex(RuntimeError, "may be open"),
        ):
            sessionfold.reclaim_source(
                Path(manifest["archive_path"]), min_age_minutes=0
            )
        self.assertTrue(path.exists())

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_reclaim_cli_requires_yes(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        result = sessionfold.main(["reclaim", manifest["archive_path"]])
        self.assertEqual(result, 2)
        self.assertTrue(path.exists())

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_recent_file_is_refused(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        with self.assertRaisesRegex(RuntimeError, "Refusing recent file"):
            sessionfold.archive_file(path, self.store, 60, False)

    @mock.patch.object(sessionfold, "open_by_process", return_value=True)
    def test_open_file_is_refused(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        old = path.stat().st_mtime - 7200
        os.utime(path, (old, old))
        with self.assertRaisesRegex(RuntimeError, "open by another process"):
            sessionfold.archive_file(path, self.store, 60, False)

    def test_parser_handles_markers_across_tiny_chunks(self) -> None:
        image = b"data:image/png;base64," + (b"QUJD" * 8)
        raw = b'prefix:"' + image + b'":suffix'
        with mock.patch.object(sessionfold, "CHUNK_SIZE", 7):
            parts = list(
                sessionfold.iter_session_parts(
                    io.BytesIO(raw), min_image_bytes=1, max_image_bytes=1024
                )
            )
        self.assertEqual(b"".join(part.data for part in parts), raw)
        self.assertEqual(sum(part.is_image for part in parts), 1)

    def test_parser_roundtrips_randomized_chunk_boundaries(self) -> None:
        rng = random.Random(20260906)
        for case in range(100):
            pieces: list[bytes] = []
            expected_images = 0
            for index in range(rng.randint(1, 12)):
                pieces.append(f'{{"case":{case},"part":{index},"value":"'.encode())
                if rng.choice((True, False)):
                    pieces.append(
                        b"data:image/png;base64," + b"QUJD" * rng.randint(1, 40)
                    )
                    expected_images += 1
                else:
                    pieces.append(
                        b"data:image/png;base64," + b"QUJD%" * rng.randint(1, 12)
                    )
                pieces.append(b'"}\n')
            raw = b"".join(pieces)
            with mock.patch.object(sessionfold, "CHUNK_SIZE", rng.randint(1, 37)):
                parts = list(
                    sessionfold.iter_session_parts(
                        io.BytesIO(raw), min_image_bytes=1, max_image_bytes=4096
                    )
                )
            self.assertEqual(b"".join(part.data for part in parts), raw)
            self.assertEqual(sum(part.is_image for part in parts), expected_images)

    def test_marker_counter_handles_chunk_boundaries(self) -> None:
        counter = sessionfold.StreamingMarkerCounter(b"replacement_history")
        counter.update(b"xxreplace")
        counter.update(b"ment_historyyyreplacement_")
        counter.update(b"historyzz")
        self.assertEqual(counter.finish(), 2)

    def test_oversized_image_candidate_is_refused(self) -> None:
        raw = b"data:image/png;base64," + (b"A" * 100) + b'"'
        with self.assertRaisesRegex(RuntimeError, "exceeds safety limit"):
            list(
                sessionfold.iter_session_parts(
                    io.BytesIO(raw), min_image_bytes=1, max_image_bytes=32
                )
            )

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_corrupt_blob_prevents_restore(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        digest = manifest["images"]["sequence"][0]["sha256"]
        blob = self.store / "blobs" / digest[:2] / digest
        blob.write_bytes(b"corrupt")
        restored = self.root / "corrupt-restore.jsonl"
        with self.assertRaisesRegex(RuntimeError, "Blob size mismatch"):
            sessionfold.restore_stream(Path(manifest["archive_path"]), restored)
        self.assertFalse(restored.exists())
        self.assertEqual(list(self.root.glob(f".{restored.name}.*.tmp")), [])

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_session_without_images_roundtrips(self, _open: mock.Mock) -> None:
        original = b'{"type":"message","text":"plain text only"}\n'
        path = self.root / "plain.jsonl"
        path.write_bytes(original)
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        self.assertEqual(manifest["images"]["occurrences"], 0)
        restored = self.root / "plain-restored.jsonl"
        sessionfold.restore_stream(Path(manifest["archive_path"]), restored)
        self.assertEqual(restored.read_bytes(), original)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_pending_removal_marker_recovers_after_unlink(
        self, _open: mock.Mock
    ) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        manifest_path = Path(manifest["archive_path"])
        payload = json.loads(manifest_path.read_text())
        payload["source_removal_pending"] = True
        sessionfold.write_json_atomic(manifest_path, payload)
        path.unlink()
        recovered = sessionfold.reclaim_source(manifest_path, min_age_minutes=0)
        self.assertTrue(recovered["source_removed"])
        self.assertFalse(recovered["source_removal_pending"])

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_verify_does_not_materialize_restored_file(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        verified = sessionfold.verify_archive(Path(manifest["archive_path"]))
        self.assertEqual(verified["source"]["sha256"], sessionfold.hash_file(path))
        self.assertEqual(list(self.store.rglob("restored.jsonl")), [])

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_nonmonotonic_manifest_is_refused(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        manifest_path = Path(manifest["archive_path"])
        payload = json.loads(manifest_path.read_text())
        payload["images"]["sequence"][1]["offset"] = -1
        manifest_path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(RuntimeError, "non-monotonic"):
            sessionfold.verify_archive(manifest_path)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_manifest_path_traversal_is_refused(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        manifest_path = Path(manifest["archive_path"])
        payload = json.loads(manifest_path.read_text())
        payload["thin"]["path"] = "../transcript.thin.jsonl.gz"
        manifest_path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(RuntimeError, "Invalid thin transcript path"):
            sessionfold.verify_archive(manifest_path)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_failed_verification_removes_incomplete_archive(
        self, _open: mock.Mock
    ) -> None:
        path, _ = self.make_session()
        with (
            mock.patch.object(
                sessionfold,
                "verify_archive",
                side_effect=RuntimeError("injected failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "injected failure"),
        ):
            sessionfold.archive_file(path, self.store, 0, False)
        self.assertEqual(list((self.store / "archives").glob("*/manifest.json")), [])

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_source_mutation_during_archive_is_refused(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        original_iterator = sessionfold.iter_session_parts

        def mutating_iterator(source: object, **kwargs: object):
            for index, part in enumerate(original_iterator(source, **kwargs)):
                yield part
                if index == 0:
                    with path.open("ab") as changed:
                        changed.write(b"mutation")

        with (
            mock.patch.object(sessionfold, "iter_session_parts", mutating_iterator),
            self.assertRaisesRegex(RuntimeError, "Source changed while archiving"),
        ):
            sessionfold.archive_file(path, self.store, 0, False)
        self.assertEqual(list((self.store / "archives").glob("*/manifest.json")), [])

    def test_archive_refuses_symlink_source(self) -> None:
        path, _ = self.make_session()
        link = self.root / "linked.jsonl"
        link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            sessionfold.archive_file(link, self.store, 0, False)

    def test_archive_refuses_claude_code_transcript(self) -> None:
        path = self.root / ".claude" / "projects" / "session.jsonl"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"{}\n")
        with self.assertRaisesRegex(RuntimeError, "Claude Code transcripts"):
            sessionfold.archive_file(path, self.store, 0, False)

    @mock.patch.object(sessionfold, "open_by_process", return_value=False)
    def test_restore_refuses_existing_target(self, _open: mock.Mock) -> None:
        path, _ = self.make_session()
        manifest = sessionfold.archive_file(path, self.store, 0, False)
        restored = self.root / "existing.jsonl"
        restored.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            sessionfold.restore_stream(Path(manifest["archive_path"]), restored)
        self.assertEqual(restored.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()

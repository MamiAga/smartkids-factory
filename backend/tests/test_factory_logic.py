"""Unit tests for the factory decision logic (no network, no ffmpeg).

Run:  python -m unittest discover -s backend/tests -v
"""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine.longform import PACKS as CATALOG, build_timeline, youtube_metadata as lf_meta  # noqa: E402
from backend.engine.factory_orchestrator import plan_cycle, pick_next_episode  # noqa: E402
from backend.engine.production_runner import ProductionEngine, make_job_id  # noqa: E402

CTRL = {"enabled": True, "daily_master_episodes": 1, "schedule_time": "04:00",
        "timezone": "Europe/Istanbul", "active_languages": ["EN"]}
# 2026-09-26 00:30 UTC = 03:30 Istanbul (before slot); 02:30 UTC = 05:30 Istanbul (after slot)
BEFORE = datetime(2026, 9, 26, 0, 30, tzinfo=timezone.utc)
AFTER = datetime(2026, 9, 26, 2, 30, tzinfo=timezone.utc)


class PlanCycleTests(unittest.TestCase):
    def test_disabled_is_standby(self):
        p = plan_cycle(dict(CTRL, enabled=False), [], AFTER)
        self.assertFalse(p["should_run"])
        self.assertTrue(p["reason"].startswith("STANDBY"))

    def test_waits_for_schedule_slot(self):
        p = plan_cycle(CTRL, [], BEFORE)
        self.assertFalse(p["should_run"])
        self.assertEqual(p["per_language"]["EN"]["status"], "WAITING_FOR_SLOT")

    def test_android_start_runs_now(self):
        self.assertTrue(plan_cycle(CTRL, [], BEFORE, run_now=True)["should_run"])

    def test_runs_after_slot(self):
        p = plan_cycle(CTRL, [], AFTER)
        self.assertEqual(p["languages"], ["EN"])

    def test_hourly_cron_does_not_duplicate_after_daily_target(self):
        jobs = [{"language": "EN", "state": "PROCESSED_PRIVATE"}]
        p = plan_cycle(CTRL, jobs, AFTER)
        self.assertFalse(p["should_run"])
        self.assertEqual(p["per_language"]["EN"]["status"], "DONE_TODAY")
        self.assertFalse(plan_cycle(CTRL, jobs, AFTER, run_now=True)["should_run"])

    def test_quota_pause_waits_until_tomorrow(self):
        p = plan_cycle(CTRL, [{"language": "EN", "state": "QUOTA_PAUSED"}], AFTER)
        self.assertEqual(p["per_language"]["EN"]["status"], "QUOTA_PAUSED_TODAY")

    def test_language_isolation(self):
        ctrl = dict(CTRL, active_languages=["EN", "ES"])
        jobs = [{"language": "ES", "state": "FAILED_UPLOAD"}] * 3
        p = plan_cycle(ctrl, jobs, AFTER)
        self.assertEqual(p["languages"], ["EN"])
        self.assertEqual(p["per_language"]["ES"]["status"], "LANGUAGE_PAUSED_TODAY")

    def test_daily_target_multiplies(self):
        p = plan_cycle(dict(CTRL, daily_master_episodes=2), [{"language": "EN", "state": "PROCESSED_PRIVATE"}], AFTER)
        self.assertEqual(p["per_language"]["EN"]["remaining"], 1)


class EpisodeSelectionTests(unittest.TestCase):
    def test_existing_video_is_never_picked_again(self):
        self.assertEqual(pick_next_episode("EN", []), "EP-COLORS-MEGA-V1")
        jobs = [{"episode_id": "EP-COLORS-MEGA-V1", "state": "PROCESSED_PRIVATE"}]
        self.assertEqual(pick_next_episode("EN", jobs), CATALOG[1]["episode_id"])

    def test_failed_upload_is_retried(self):
        jobs = [{"episode_id": "EP-COLORS-MEGA-V1", "state": "FAILED_UPLOAD"}]
        self.assertEqual(pick_next_episode("EN", jobs), "EP-COLORS-MEGA-V1")

    def test_exhausted(self):
        jobs = [{"episode_id": e["episode_id"], "state": "COMPLETED"} for e in CATALOG]
        self.assertIsNone(pick_next_episode("EN", jobs))

    def test_new_template_does_not_reuse_v0_job_id(self):
        # v0.1 video (JOB-EN-eea4cd1f) predates the quality standard and must never be auto-published
        self.assertNotEqual(make_job_id("EP-COLORS-MEGA-V1", "EN")[0], "JOB-EN-eea4cd1f")


class CurriculumQaTests(unittest.TestCase):
    def test_every_pack_passes_script_gate(self):
        for ep in CATALOG:
            with self.subTest(ep=ep["episode_id"]):
                self.assertTrue(ProductionEngine.run_linguistic_and_pedagogical_qa("EN", ep)["passed"])

    def test_every_item_has_countdown_and_quiz(self):
        for ep in CATALOG:
            segs = build_timeline(ep)
            self.assertGreaterEqual(sum(1 for s in segs if s["kind"] == "countdown"), 2 * len(ep["items"]))

    def test_metadata(self):
        for ep in CATALOG:
            m = lf_meta(ep, [{"t": 0, "title": "Hello"}, {"t": 30, "title": "Red"}])
            self.assertLessEqual(len(m["title"]), 100)
            self.assertIn("0:00", m["description"])
            self.assertLess(sum(len(t) for t in m["tags"]), 450)


class FakeDB:
    connected = True

    def __init__(self, existing=None):
        self.existing = existing
        self.upserts = []

    def get_job(self, job_id):
        return self.existing

    def upsert_job(self, rec, strict=False):
        self.upserts.append(dict(rec))

    def heartbeat(self, **kw):
        pass

    def upsert_episode(self, row):
        pass


class IdempotencyTests(unittest.TestCase):
    def test_already_uploaded_job_is_not_uploaded_again(self):
        db = FakeDB({"job_id": make_job_id("EP-COLORS-MEGA-V1", "EN")[0], "state": "PROCESSED_PRIVATE",
                     "youtube_video_id": "3JTsS1ZW_zw"})
        eng = ProductionEngine(db=db)
        r = eng.run_production("EP-COLORS-MEGA-V1", "EN")
        self.assertEqual(r["status"], "SKIPPED_DUPLICATE")
        self.assertEqual(r["youtube_video_id"], "3JTsS1ZW_zw")
        self.assertEqual(db.upserts, [])

    def test_unlocalized_language_is_isolated_not_crashing(self):
        from backend.engine.production_runner import LanguageNotReady
        with self.assertRaises(LanguageNotReady):
            ProductionEngine(db=FakeDB()).run_production("EP-COLORS-MEGA-V1", "ES")


if __name__ == "__main__":
    unittest.main()


class QualityStandardTests(unittest.TestCase):
    GOOD = {"width": 1920, "height": 1080, "fps": 60.0, "video_codec": "h264", "video_profile": "High",
            "pix_fmt": "yuv420p", "audio_codec": "aac", "audio_rate": 48000, "audio_channels": 2,
            "duration": 560.0, "loudness_lufs": -16.2, "true_peak_dbtp": -2.0, "silences": [],
            "black_segments": [], "max_luma_step": 6.0, "max_flashes_per_sec": 1}
    DESIGN = {"items": 8, "text_checks": [{"text": "RED", "px": 170, "contrast": 4.7}], "pictures": [True] * 5,
              "character_every_scene": True, "decorations": True, "music_bed": True, "countdowns": 24,
              "wpm": 128, "voice": "af_heart", "interjection_ratio": 1.0, "tagged_ratio": 1.0,
              "whisper_lines": 20, "countdown_sfx": True}

    def meta(self):
        m = lf_meta(CATALOG[0], [{"t": 0, "title": "Hello"}])
        m["made_for_kids"] = True
        return m

    def test_good_video_passes(self):
        from backend.engine.quality import evaluate
        r = evaluate(self.GOOD, self.DESIGN, self.meta())
        self.assertTrue(r["passed"], r["failures"])

    def test_below_standard_is_rejected(self):
        from backend.engine.quality import evaluate
        for bad in ({"loudness_lufs": -23.0}, {"fps": 30.0}, {"max_flashes_per_sec": 5}, {"silences": [1.4]},
                    {"true_peak_dbtp": 0.2}, {"duration": 300.0}, {"duration": 700.0}):
            with self.subTest(bad=bad):
                self.assertFalse(evaluate(dict(self.GOOD, **bad), self.DESIGN, self.meta())["passed"])
        for bad in ({"wpm": 175}, {"voice": "piper_robot"}, {"interjection_ratio": 0.3}, {"whisper_lines": 0},
                    {"countdown_sfx": False}, {"music_bed": False}, {"countdowns": 2},
                    {"text_checks": [{"text": "X", "px": 40, "contrast": 3.0}]}):
            with self.subTest(bad=bad):
                self.assertFalse(evaluate(self.GOOD, dict(self.DESIGN, **bad), self.meta())["passed"])
        m = self.meta()
        m["made_for_kids"] = False
        self.assertFalse(evaluate(self.GOOD, self.DESIGN, m)["passed"])

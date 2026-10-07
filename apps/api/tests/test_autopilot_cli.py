import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from autopost_api.config import settings
from autopost_api.services import autopilot
from autopost_api.workers import enqueue


class AutopilotScheduleTests(unittest.TestCase):
    def setUp(self):
        self._saved = (settings.autopilot_hours, settings.autopilot_hour, settings.autopilot_minute, settings.timezone)

    def tearDown(self):
        settings.autopilot_hours, settings.autopilot_hour, settings.autopilot_minute, settings.timezone = self._saved

    def test_four_daily_slots(self):
        settings.autopilot_hours = "9,12,15,18"
        settings.autopilot_minute = 0
        settings.timezone = "Asia/Seoul"
        self.assertEqual(settings.autopilot_clock_times(), [(9, 0), (12, 0), (15, 0), (18, 0)])
        self.assertEqual(settings.autopilot_time_label(), "09:00,12:00,15:00,18:00 Asia/Seoul")

    def test_empty_hours_fall_back_to_single_hour(self):
        settings.autopilot_hours = ""
        settings.autopilot_hour = 9
        settings.autopilot_minute = 0
        self.assertEqual(settings.autopilot_clock_times(), [(9, 0)])

    def test_invalid_hours_are_skipped(self):
        settings.autopilot_hours = "9,noon,15,18,9"
        settings.autopilot_minute = 0
        self.assertEqual(settings.autopilot_clock_times(), [(9, 0), (15, 0), (18, 0)])


class RecentPostTests(unittest.TestCase):
    def test_post_inside_the_slot_counts_as_recent(self):
        now = datetime(2026, 10, 7, 3, 38, tzinfo=timezone.utc)
        published = now - timedelta(minutes=30)
        self.assertTrue(autopilot.published_recently(published, now=now, within=timedelta(hours=2)))

    def test_post_from_the_previous_slot_does_not_block(self):
        now = datetime(2026, 10, 7, 6, 8, tzinfo=timezone.utc)
        published = now - timedelta(hours=3)
        self.assertFalse(autopilot.published_recently(published, now=now, within=timedelta(hours=2)))


class AutopilotCliTests(unittest.TestCase):
    def setUp(self):
        self._scheduler_backend = settings.scheduler_backend
        settings.scheduler_backend = "apscheduler"
        self._recent = patch.object(autopilot, "blogger_posted_recently", return_value=False)
        self._recent.start()

    def tearDown(self):
        self._recent.stop()
        settings.scheduler_backend = self._scheduler_backend

    def test_wait_inline_finishes_submitted_work(self):
        done: list[str] = []
        enqueue._pool.submit(done.append, "ok")
        enqueue.wait_inline()
        self.assertEqual(done, ["ok"])

    def test_main_exits_when_autopilot_skips(self):
        with (
            patch("autopost_api.db.models.Base") as base,
            patch("autopost_api.db.seed.seed_if_empty"),
            patch("autopost_api.db.session.SessionLocal", return_value=MagicMock()),
            patch("autopost_api.db.session.engine"),
            patch.object(autopilot, "run_autopilot", return_value="no-key"),
            patch("autopost_api.workers.enqueue.wait_inline") as wait_inline,
            patch("autopost_api.workers.scheduler.dispatch_due_jobs") as dispatch,
        ):
            with self.assertRaises(SystemExit) as raised:
                autopilot.main([])
        self.assertEqual(raised.exception.code, 1)
        base.metadata.create_all.assert_called_once()
        wait_inline.assert_not_called()
        dispatch.assert_not_called()

    def test_main_publishes_due_jobs_before_exit(self):
        job = MagicMock(channel_code="blogger", status="succeeded")
        item = MagicMock(post_id="post-1")
        batch = MagicMock(status="ready", items=[item])
        db = MagicMock()
        db.get.return_value = batch
        db.scalars.return_value.all.return_value = [job]

        with (
            patch("autopost_api.db.models.Base"),
            patch("autopost_api.db.seed.seed_if_empty"),
            patch("autopost_api.db.session.SessionLocal", return_value=db),
            patch("autopost_api.db.session.engine"),
            patch.object(autopilot, "run_autopilot", return_value="batch-1"),
            patch("autopost_api.workers.enqueue.wait_inline") as wait_inline,
            patch("autopost_api.workers.scheduler.dispatch_due_jobs", return_value=1) as dispatch,
        ):
            autopilot.main([])

        wait_inline.assert_called_once()
        dispatch.assert_called_once()

    def test_main_exits_when_publish_job_failed(self):
        job = MagicMock(channel_code="blogger", status="failed")
        item = MagicMock(post_id="post-1")
        batch = MagicMock(status="ready", items=[item])
        db = MagicMock()
        db.get.return_value = batch
        db.scalars.return_value.all.return_value = [job]

        with (
            patch("autopost_api.db.models.Base"),
            patch("autopost_api.db.seed.seed_if_empty"),
            patch("autopost_api.db.session.SessionLocal", return_value=db),
            patch("autopost_api.db.session.engine"),
            patch.object(autopilot, "run_autopilot", return_value="batch-1"),
            patch("autopost_api.workers.enqueue.wait_inline"),
            patch("autopost_api.workers.scheduler.dispatch_due_jobs", return_value=0),
        ):
            with self.assertRaises(SystemExit) as raised:
                autopilot.main([])
        self.assertEqual(raised.exception.code, 1)

    def test_main_skips_when_this_slot_already_has_a_post(self):
        self._recent.stop()
        with (
            patch("autopost_api.db.models.Base"),
            patch("autopost_api.db.seed.seed_if_empty"),
            patch("autopost_api.db.session.SessionLocal", return_value=MagicMock()),
            patch("autopost_api.db.session.engine"),
            patch.object(autopilot, "blogger_posted_recently", return_value=True),
            patch.object(autopilot, "run_autopilot") as run_autopilot,
        ):
            autopilot.main([])
        run_autopilot.assert_not_called()
        self._recent.start()


if __name__ == "__main__":
    unittest.main()

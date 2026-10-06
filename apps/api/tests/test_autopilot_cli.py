import unittest
from unittest.mock import MagicMock, patch

from autopost_api.config import settings
from autopost_api.services import autopilot
from autopost_api.workers import enqueue


class AutopilotCliTests(unittest.TestCase):
    def setUp(self):
        self._scheduler_backend = settings.scheduler_backend
        settings.scheduler_backend = "apscheduler"

    def tearDown(self):
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
                autopilot.main()
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
            autopilot.main()

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
                autopilot.main()
        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()

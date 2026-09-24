"""Unit tests for YouTubeUploadStateMachine."""
import unittest
from backend.workers.youtube_worker import (
    VideoUploadState,
    YouTubeUploadStateMachine,
    InvalidStateTransitionError
)

class TestYouTubeUploadStateMachine(unittest.TestCase):

    def setUp(self):
        self.sm = YouTubeUploadStateMachine(job_id="test_job_001")

    def test_initial_state(self):
        self.assertEqual(self.sm.current_state, VideoUploadState.RENDERED)
        self.assertFalse(self.sm.is_failed())
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

    def test_happy_path_transitions(self):
        # RENDERED -> UPLOADING
        self.sm.start_upload()
        self.assertEqual(self.sm.current_state, VideoUploadState.UPLOADING)
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

        # UPLOADING -> UPLOADED
        self.sm.mark_uploaded("yt_vid_12345")
        self.assertEqual(self.sm.current_state, VideoUploadState.UPLOADED)
        self.assertEqual(self.sm.youtube_video_id, "yt_vid_12345")
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

        # UPLOADED -> PROCESSING
        self.sm.start_processing()
        self.assertEqual(self.sm.current_state, VideoUploadState.PROCESSING)
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

        # PROCESSING -> PROCESSED
        self.sm.mark_processed()
        self.assertEqual(self.sm.current_state, VideoUploadState.PROCESSED)
        self.assertTrue(self.sm.is_safe_for_local_cleanup())

        # PROCESSED -> PUBLISHED
        self.sm.mark_published()
        self.assertEqual(self.sm.current_state, VideoUploadState.PUBLISHED)
        self.assertTrue(self.sm.is_safe_for_local_cleanup())

        # PUBLISHED -> LOCAL_DELETE_PENDING -> COMPLETED
        self.sm.transition_to(VideoUploadState.LOCAL_DELETE_PENDING)
        self.assertEqual(self.sm.current_state, VideoUploadState.LOCAL_DELETE_PENDING)
        self.assertTrue(self.sm.is_safe_for_local_cleanup())

        self.sm.complete_lifecycle()
        self.assertEqual(self.sm.current_state, VideoUploadState.COMPLETED)
        self.assertTrue(self.sm.is_terminal())

    def test_illegal_transition_rejection(self):
        # Cannot jump from RENDERED directly to PROCESSED
        with self.assertRaises(InvalidStateTransitionError):
            self.sm.mark_processed()

        # Cannot jump from RENDERED directly to COMPLETED
        with self.assertRaises(InvalidStateTransitionError):
            self.sm.complete_lifecycle()

    def test_auth_failure_handling(self):
        self.sm.handle_auth_failure("OAuth refresh token revoked by user")
        self.assertEqual(self.sm.current_state, VideoUploadState.AUTH_FAILED)
        self.assertTrue(self.sm.is_failed())
        self.assertFalse(self.sm.is_safe_for_local_cleanup())
        self.assertEqual(self.sm.error_message, "OAuth refresh token revoked by user")

    def test_quota_paused_handling(self):
        self.sm.handle_quota_exceeded("Daily channel upload limit (100) reached")
        self.assertEqual(self.sm.current_state, VideoUploadState.QUOTA_PAUSED)
        self.assertTrue(self.sm.is_failed())
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

    def test_upload_failure_handling(self):
        self.sm.start_upload()
        self.sm.handle_upload_failure("TCP connection reset during chunk transfer")
        self.assertEqual(self.sm.current_state, VideoUploadState.UPLOAD_FAILED)
        self.assertTrue(self.sm.is_failed())
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

    def test_processing_failure_handling(self):
        self.sm.start_upload()
        self.sm.mark_uploaded("yt_vid_999")
        self.sm.start_processing()
        self.sm.handle_processing_failure("Transcoding rejected: unsupported container")
        self.assertEqual(self.sm.current_state, VideoUploadState.PROCESSING_FAILED)
        self.assertTrue(self.sm.is_failed())
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

    def test_quarantine_handling(self):
        self.sm.start_upload()
        self.sm.quarantine("Content policy automated red flag")
        self.assertEqual(self.sm.current_state, VideoUploadState.QUARANTINED)
        self.assertTrue(self.sm.is_failed())
        self.assertTrue(self.sm.is_terminal())
        self.assertFalse(self.sm.is_safe_for_local_cleanup())

    def test_transition_history(self):
        self.sm.start_upload()
        self.sm.mark_uploaded("yt_abc")
        # History: Initialized + UPLOADING + UPLOADED = 3 records
        self.assertEqual(len(self.sm.history), 3)
        self.assertEqual(self.sm.history[1]["to_state"], "UPLOADING")
        self.assertEqual(self.sm.history[2]["to_state"], "UPLOADED")

if __name__ == "__main__":
    unittest.main()

"""Local unit tests: run from the repository root with python -B -m unittest discover -s demo."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import Lab, Snapshot, DEFAULT_RUN, STATES, online_config


class WebDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab = Lab()

    @classmethod
    def tearDownClass(cls):
        cls.lab.close()

    def test_snapshot_is_verified_and_has_all_three_states(self):
        snapshot = self.lab.snapshot
        self.assertEqual([snapshot.states[s]['count'] for s in STATES], [24, 20, 24])
        self.assertEqual([snapshot.states[s]['quality']['success'] for s in STATES], [True, False, True])
        self.assertGreaterEqual(snapshot.verified_checks, 99)

    def test_dropped_doi_and_stale_date_are_real_differences(self):
        data = self.lab.snapshot.states
        dropped = '10.1145/3637528.3671812'
        stale = '10.1145/3637528.3671806'
        self.assertNotIn(dropped, {r['paper_id'] for r in data['corrupted']['rows']})
        dates = [next(r['published'] for r in data[s]['rows'] if r['paper_id'] == stale) for s in STATES]
        self.assertEqual(dates, ['2026-05-02', '2025-05-02', '2026-05-02'])

    def test_public_dashboard_does_not_expose_credentials(self):
        data = self.lab.status()
        key, _ = online_config()
        if key:
            self.assertNotIn(key, json.dumps(data))
        self.assertNotIn('api_key', data)
        self.assertEqual(data['saved_online']['summary']['corrupted']['correct_against_raw'], 2)

    def test_chat_rejects_unknown_and_duplicate_states(self):
        for states in [['outside'], ['baseline', 'baseline'], [], '../raw']:
            with self.assertRaises(ValueError):
                self.lab.submit('chat', {'question': 'test', 'states': states, 'mode': 'local'})

    def test_chat_rejects_unbounded_or_empty_question(self):
        for question in ['', ' ', 'x' * 2001, 123]:
            with self.assertRaises(ValueError):
                self.lab.submit('chat', {'question': question, 'states': ['baseline'], 'mode': 'local'})

    def test_busy_worker_rejects_overlapping_mutation(self):
        self.lab.active = 'test_busy'
        try:
            with self.assertRaises(RuntimeError):
                self.lab.submit('pipeline', {})
        finally:
            self.lab.active = None

    def test_missing_online_key_does_not_fall_back_to_mock(self):
        with patch('app.online_config', return_value=('', 'test')):
            with self.assertRaisesRegex(ValueError, 'KEY'):
                self.lab.submit('chat', {'question': 'test', 'states': ['baseline'], 'mode': 'gemini'})


if __name__ == '__main__':
    unittest.main()

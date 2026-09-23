import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

SPEC = importlib.util.spec_from_file_location('limit', Path(__file__).parents[1] / 'skills/limit/scripts/limit.py')
limit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(limit)
NOW = 1_800_000_000


def iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat().replace('+00:00', 'Z')


def event(stamp, used=30, limit_id='codex', empty=False):
    return {'timestamp': iso(stamp), 'type': 'event_msg', 'payload': {'type': 'token_count', 'rate_limits': {
        'limit_id': limit_id, 'primary': None if empty else {'used_percent': used, 'window_minutes': 300, 'resets_at': NOW + 600}}}}


def model_limit(name='Fable', percent=87, resets_at=None, **extra):
    return {
        'kind': 'weekly_scoped', 'group': 'weekly', 'percent': percent,
        'resets_at': iso(NOW + 7 * 86400) if resets_at is None else resets_at,
        'scope': {'model': {'id': None, 'display_name': name}, 'surface': None},
        **extra,
    }


class LimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.snapshot = self.root / 'snapshots.json'
        self.now = patch.object(limit, '_now', return_value=NOW)
        self.now.start()
        self.addCleanup(self.now.stop)
        self.paths = patch.object(limit, '_codexbar_snapshot_paths', return_value=[str(self.snapshot)])
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.env = patch.dict(os.environ, {'CODEX_HOME': str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def write_snapshot(self, records):
        self.snapshot.write_text(json.dumps({'snapshots': records}), encoding='utf-8')

    def record(self, used=15, age=60, **extra):
        return {'updatedAt': iso(NOW - age), 'primaryWindow': {'usedPercent': used, 'resetAt': iso(NOW + 600), 'limitWindowSeconds': 18000}, **extra}

    def rollout(self, name, records):
        path = self.root / 'sessions' / name
        path.parent.mkdir(exist_ok=True)
        path.write_text('\n'.join(json.dumps(x) for x in records) + '\n', encoding='utf-8')
        return path

    def test_python310_z_dates_and_invalid_dates(self):
        self.assertEqual(limit._parse_iso(iso(NOW)), NOW)
        for value in (None, 42, {}, 'bad', '2026-01-01T00:00:00'):
            self.assertIsNone(limit._parse_iso(value))

    def test_observation_requires_finite_epoch_and_both_windows(self):
        for data in ({'epoch': float('nan'), 'five': 10, 'seven': 20},
                     {'epoch': NOW, 'five': 10}, {'epoch': NOW, 'five': 0, 'seven': 0},
                     {'epoch': NOW + 60, 'five': 10, 'seven': 20}):
            self.snapshot.write_text(json.dumps(data), encoding='utf-8')
            self.assertIsNone(limit.read_claude_observation(str(self.snapshot)))
        self.snapshot.write_text(json.dumps({'epoch': NOW, 'five': 0, 'seven': 20}), encoding='utf-8')
        self.assertEqual(limit.read_claude_observation(str(self.snapshot))['five'], 0)

    def test_multiple_accounts_are_not_combined(self):
        self.write_snapshot({'one': self.record(), 'two': self.record(90)})
        self.assertEqual(limit.read_codex()['windows'], [])
        self.assertEqual(limit.read_codex(account='one')['windows'][0]['used_percent'], 15)

    def test_sentinel_does_not_borrow_another_accounts_week(self):
        self.write_snapshot({'one': self.record(100, limitReached=True), 'two': self.record(1)})
        result = limit.read_codex(account='one')
        self.assertEqual(result['windows'], [])
        self.assertIn('sentinel', result['warnings'][0])

    def test_selected_missing_account_never_uses_unscoped_rollout(self):
        self.rollout('one.jsonl', [event(NOW)])
        self.assertEqual(limit.read_codex(account='missing')['windows'], [])

    def test_swift_cache_reference_dates(self):
        self.snapshot.write_text(json.dumps({'version': 1, 'records': [{
            'id': 'one', 'snapshot': {'updatedAt': NOW - 60 - 978307200,
            'secondary': {'usedPercent': 12, 'windowMinutes': 10080, 'resetsAt': NOW + 600 - 978307200}}}]}), encoding='utf-8')
        result = limit.read_codex()
        self.assertEqual(result['age_minutes'], 1)
        self.assertEqual(result['windows'][0]['resets_in'], '10m')
        self.assertEqual(result['windows'][0]['name'], 'weekly (7-day)')

    def test_old_measurement_with_recent_file_mtime_is_stale(self):
        self.rollout('one.jsonl', [event(NOW - 3600)])
        result = limit.read_codex()
        self.assertEqual(result['age_minutes'], 60)
        self.assertTrue(result['stale'])
        self.assertTrue(any('stale' in w for w in result['warnings']))

    def test_newest_event_wins_not_newest_file(self):
        a = self.rollout('new-event.jsonl', [event(NOW - 30, 25)])
        b = self.rollout('new-file.jsonl', [event(NOW - 3000, 90)])
        os.utime(a, (NOW - 60, NOW - 60))
        os.utime(b, (NOW, NOW))
        self.assertEqual(limit.read_codex()['windows'][0]['used_percent'], 25)

    def test_null_and_partial_lines_do_not_hide_measurement(self):
        path = self.rollout('one.jsonl', [event(NOW - 30), {'type': 'event_msg', 'payload': {'type': 'token_count', 'rate_limits': None}}])
        with path.open('a', encoding='utf-8') as f:
            f.write('{"rate_limits":')
        self.assertEqual(limit.read_codex()['windows'][0]['used_percent'], 30)

    def test_empty_latest_measurement_does_not_resurrect_old_window(self):
        self.rollout('one.jsonl', [event(NOW - 60), event(NOW, empty=True)])
        self.assertEqual(limit.read_codex()['windows'], [])

    def test_other_bucket_and_embedded_tool_text_are_ignored(self):
        self.rollout('one.jsonl', [event(NOW - 60, 22), event(NOW, 100, 'spark'),
            {'type': 'response_item', 'rate_limits': {'primary': {'used_percent': 99}}, 'timestamp': iso(NOW)}])
        self.assertEqual(limit.read_codex()['windows'][0]['used_percent'], 22)

    def test_missing_timestamp_is_unknown_not_fresh(self):
        data = event(NOW)
        del data['timestamp']
        self.rollout('one.jsonl', [data])
        result = limit.read_codex()
        self.assertTrue(result['stale'])
        self.assertIsNone(result['age_minutes'])

    def test_bad_percentages_render_unknown(self):
        for value in (float('nan'), float('inf'), True, '30', -1, 101):
            self.write_snapshot({'one': self.record(value)})
            result = limit.read_codex()
            self.assertIsNone(result['windows'][0]['used_percent'])
            self.assertIn('?', limit.render({'windows': [], 'warnings': []}, result))

    def test_invalid_cache_shapes_do_not_crash(self):
        for value in ([], 1, 'bad', {'snapshots': []}, {'snapshots': {'one': []}}):
            self.snapshot.write_text(json.dumps(value), encoding='utf-8')
            self.assertEqual(limit.read_codex()['windows'], [])

    def test_expired_and_future_cache_are_unknown(self):
        record = self.record(age=-60)
        record['primaryWindow']['resetAt'] = iso(NOW - 10)
        self.write_snapshot({'one': record})
        result = limit.read_codex()
        self.assertTrue(result['stale'])
        self.assertTrue(result['windows'][0]['expired'])
        self.assertIn('WINDOW EXPIRED', limit.render({'windows': [], 'warnings': []}, result))

    def test_claude_redirect_handler_does_not_forward_bearer(self):
        import urllib.error
        with patch.object(limit, '_claude_token', return_value='synthetic-token'), \
             patch.object(limit.urllib.request, 'build_opener') as build:
            build.return_value.open.side_effect = urllib.error.HTTPError(
                limit.CLAUDE_USAGE_URL, 302, 'redirect', {}, None)
            live, reason = limit._fetch_claude_live_detailed()
            self.assertIsNone(live)
            self.assertIn('302', reason)
            handler = build.call_args.args[0]
            self.assertIsNone(handler.redirect_request(None, None, 302, '', {}, 'https://example.invalid/'))
            self.assertNotIn('synthetic-token', reason)

    def test_claude_rate_limit_is_unknown_not_full(self):
        import urllib.error
        with patch.object(limit, '_claude_token', return_value='synthetic-token'), \
             patch.object(limit.urllib.request, 'build_opener') as build:
            build.return_value.open.side_effect = urllib.error.HTTPError(
                limit.CLAUDE_USAGE_URL, 429, 'limited', {}, None)
            live, reason = limit._fetch_claude_live_detailed()
            self.assertIsNone(live)
            self.assertIn('NOT a quota reading', reason)

    def test_claude_invalid_credentials_shape_is_unavailable(self):
        from unittest.mock import mock_open
        for data in ('[]', '{"claudeAiOauth": []}', '{"claudeAiOauth": 7}'):
            with patch('builtins.open', mock_open(read_data=data)):
                self.assertEqual(limit._claude_oauth(), {})

    def test_claude_bad_usage_values_do_not_crash(self):
        out = {'windows': [], 'warnings': []}
        limit._append_windows(out, {'five_hour': {'utilization': 'bad', 'resets_at': 3}})
        self.assertIsNone(out['windows'][0]['used_percent'])

    def test_model_windows_extracts_scoped_week(self):
        windows = limit.model_windows({'limits': [model_limit()]})
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]['name'], 'Fable 7-day')
        self.assertEqual(windows[0]['model'], 'Fable')
        self.assertEqual(windows[0]['used_percent'], 87.0)
        self.assertFalse(windows[0]['expired'])
        self.assertIsNotNone(windows[0]['resets_in'])

    def test_model_windows_ignores_unscoped_entries(self):
        limits = [
            {'kind': 'session', 'group': 'session', 'percent': 15, 'scope': None},
            {'kind': 'weekly_all', 'group': 'weekly', 'percent': 61, 'scope': None},
        ]
        self.assertEqual(limit.model_windows({'limits': limits}), [])

    def test_model_windows_skips_malformed_limits(self):
        scoped = {'scope': {'model': {'display_name': 'Fable'}}}
        bad = [
            None,
            'not a dict',
            {'scope': {'model': {}}, 'percent': 87},
            {**scoped, 'scope': {'model': {'display_name': '  '}}},
            {**scoped, 'percent': True},
            {**scoped, 'percent': '87'},
            {**scoped, 'percent': float('nan')},
            {**scoped},
        ]
        for usage in ({}, {'limits': None}, {'limits': {}}, {'limits': 'bad'}):
            self.assertEqual(limit.model_windows(usage), [])
        self.assertEqual(limit.model_windows({'limits': bad}), [])
        # A valid percentage with an unreadable reset is still shown, just without a reset time.
        for reset in (NOW + 60, 'garbage'):
            windows = limit.model_windows({'limits': [{**scoped, 'percent': 87, 'resets_at': reset}]})
            self.assertEqual([(w['used_percent'], w['resets_at'], w['resets_in']) for w in windows],
                             [(87.0, None, None)])

    def test_model_windows_marks_past_reset_expired(self):
        windows = limit.model_windows({'limits': [model_limit(resets_at=iso(NOW - 60))]})
        self.assertTrue(windows[0]['expired'])
        self.assertIsNone(windows[0]['resets_in'])

    def test_read_claude_keeps_model_windows_out_of_pool(self):
        live = {
            'five_hour': {'utilization': 15, 'resets_at': iso(NOW + 3600)},
            'seven_day': {'utilization': 61, 'resets_at': iso(NOW + 7 * 86400)},
            'limits': [model_limit()],
        }
        with patch.object(limit, '_fetch_claude_live_detailed', return_value=(live, None)), \
             patch.object(limit, '_claude_plan', return_value='max'), \
             patch.object(limit, '_now', return_value=NOW):
            result = limit.read_claude()
        self.assertEqual([window['name'] for window in result['windows']], ['5-hour', '7-day'])
        self.assertEqual([window['name'] for window in result['model_windows']], ['Fable 7-day'])
        self.assertEqual(result['warnings'], [])

        pro = dict(live)
        del pro['limits']
        with patch.object(limit, '_fetch_claude_live_detailed', return_value=(pro, None)), \
             patch.object(limit, '_claude_plan', return_value='pro'), \
             patch.object(limit, '_now', return_value=NOW):
            pro_result = limit.read_claude()
        self.assertEqual(pro_result['model_windows'], [])
        self.assertEqual(pro_result['warnings'], [])

    def test_render_model_window_and_legacy_codex_block(self):
        model_window = limit.model_windows({'limits': [model_limit()]})[0]
        output = limit.render(
            {'windows': [], 'model_windows': [model_window], 'warnings': []},
            {'windows': [], 'warnings': []},
        )
        self.assertIn('Fable 7-day', output)
        self.assertIn('87%', output)


if __name__ == '__main__':
    unittest.main()

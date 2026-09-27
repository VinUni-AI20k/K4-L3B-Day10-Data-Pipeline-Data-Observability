"""Exercise a running demo via HTTP; all evidence stays in demo/evidence/."""
import argparse
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--online', action='store_true')
    parser.add_argument('--pipeline', action='store_true')
    args = parser.parse_args()
    base = f'http://127.0.0.1:{args.port}'
    result = {'checks': {}, 'jobs': []}

    def request(path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        req = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read()
            return json.loads(body) if response.headers.get_content_type() == 'application/json' else body

    def job(kind, payload):
        started = request('/api/' + kind, payload)
        print('Running', kind, payload.get('mode', ''), payload.get('states', ''), flush=True)
        deadline = time.monotonic() + 360
        while time.monotonic() < deadline:
            response = request('/api/jobs/' + started['job_id'])
            if response['status'] in {'complete', 'failed'}:
                result['jobs'].append(response)
                print('Finished', response['status'], flush=True)
                return response
            time.sleep(1)
        raise TimeoutError('Job did not finish within six minutes')

    try:
        dashboard = request('/api/dashboard')
        result['checks']['dashboard_counts'] = [dashboard['states'][s]['count'] for s in ('baseline', 'corrupted', 'repaired')] == [24, 20, 24]
        for path in ['/', '/app.js', '/styles.css', '/favicon.svg']:
            result['checks']['static:' + path] = bool(request(path))
        try:
            request('/.env')
            result['checks']['env_not_served'] = False
        except urllib.error.HTTPError as exc:
            result['checks']['env_not_served'] = exc.code == 404
        try:
            request('/api/chat', {'question': 'test', 'states': ['baseline'], 'mode': 'local'}, origin='https://untrusted.example')
            result['checks']['cross_origin_rejected'] = False
        except urllib.error.HTTPError as exc:
            result['checks']['cross_origin_rejected'] = exc.code == 403
        states = ['baseline', 'corrupted', 'repaired']
        stale = "When was the paper '10.1145/3637528.3671806' published? Return only YYYY-MM-DD."
        response = job('chat', {'question': stale, 'states': states, 'mode': 'local'})
        result['checks']['local_stale_three_states'] = response['status'] == 'complete' and [a['answer'] for a in response['answers']] == ['2026-05-02', '2025-05-02', '2026-05-02']
        response = job('chat', {'question': "When was the paper '10.1145/3637528.3671812' published?", 'states': states, 'mode': 'local'})
        result['checks']['local_dropped_three_states'] = response['status'] == 'complete' and [a['answer'] for a in response['answers']] == ['2026-07-22', "I don't know from the indexed corpus.", '2026-07-22']
        if args.online:
            response = job('chat', {'question': stale, 'states': states, 'mode': 'gemini'})
            result['checks']['gemini_stale_three_states'] = response['status'] == 'complete' and [a['answer'].strip('`\" \n') for a in response['answers']] == ['2026-05-02', '2025-05-02', '2026-05-02']
            result['checks']['gemini_real_tools'] = response['status'] == 'complete' and all(a['tool_calls'] and a['tokens'] > 0 for a in response['answers'])
            response = job('chat', {'question': "Who authored the paper '10.9999/cp6-not-in-corpus'? If unavailable, reply exactly: I don't know from the indexed corpus.", 'states': ['corrupted'], 'mode': 'gemini'})
            result['checks']['gemini_absent_abstains'] = response['status'] == 'complete' and "don't know" in response['answers'][0]['answer'].lower() and not response['answers'][0]['sources']
        if args.pipeline:
            before = request('/api/dashboard')['run_id']
            response = job('pipeline', {})
            after = request('/api/dashboard')
            result['checks']['new_pipeline_completed'] = response['status'] == 'complete' and after['run_id'] != before
            result['checks']['new_pipeline_verified'] = after['verified_checks'] >= 99
            response = job('chat', {'question': stale, 'states': states, 'mode': 'local'})
            result['checks']['chat_uses_new_run'] = response.get('run_id') == after['run_id'] and [a['answer'] for a in response['answers']] == ['2026-05-02', '2025-05-02', '2026-05-02']
    finally:
        result['passed'] = bool(result['checks']) and all(result['checks'].values())
        (ROOT / 'evidence').mkdir(exist_ok=True)
        (ROOT / 'evidence/http_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': result['passed'], 'checks': result['checks']}, indent=2), flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()

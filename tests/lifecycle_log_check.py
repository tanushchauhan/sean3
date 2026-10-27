"""Summarize lifecycle diagnostics after the owned processes have stopped."""

import argparse
import json
from pathlib import Path


def summarize(player, endpoint):
    counts = {
        'duplicate_hud_headers': player.count('HUDPanel already contains a header'),
        'queue_overflows': player.count('Queue full!'),
        'connection_failures': player.count(' failed - System.'),
        'reset_by_peer_writes': player.count('failed - System.IO.IOException: Unable to write data to the transport connection: Connection reset by peer.'),
        'reader_exceptions': player.count(' exception!'),
        'missing_references': player.count('MissingReferenceException'),
        'unregistered_topics': player.count('Not registered to publish topic'),
        'endpoint_tracebacks': endpoint.count('Traceback (most recent call last)'),
        'endpoint_other_errors': sum('[ERROR]' in line for line in endpoint.splitlines()),
        'endpoint_connections': endpoint.count('Connection from '),
        'endpoint_logger_warnings': endpoint.count('Publisher already registered for provided node name'),
        'endpoint_closed_socket_writes': endpoint.count('Exception [Errno 9] Bad file descriptor'),
        'endpoint_graceful_disconnects': endpoint.count('Graceful Unity disconnect from '),
        'endpoint_disconnects': endpoint.count('Disconnected from '),
        'endpoint_unannounced_disconnects': endpoint.count('Unannounced Unity disconnect'),
        'endpoint_replacements': endpoint.count('Replacing a still-active Unity connection'),
        'worker_cleanup_errors': player.count('ROS graceful disconnect') + player.count('ROS connection worker did not stop'),
        'native_crashes': player.count('Native Crash Reporting') + player.count('Got a SIGSEGV'),
        'display_errors': player.count('XIO:') + player.count('X connection to '),
        'endpoint_disconnect_eof': endpoint.count('Exception: No more data available'),
    }
    failures = ('duplicate_hud_headers', 'queue_overflows', 'connection_failures',
                'reader_exceptions', 'missing_references', 'unregistered_topics',
                'endpoint_tracebacks', 'endpoint_other_errors', 'endpoint_logger_warnings',
                'endpoint_closed_socket_writes', 'endpoint_disconnect_eof',
                'endpoint_unannounced_disconnects', 'endpoint_replacements',
                'worker_cleanup_errors', 'native_crashes', 'display_errors')
    counts['transport_clean'] = not any(counts[key] for key in failures)
    counts['passed'] = counts['transport_clean']
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    player = (args.results / 'player.log').read_text(errors='replace')
    console = args.results / 'player-console.log'
    if console.exists():
        player += '\n' + console.read_text(errors='replace')
    report = summarize(player,
                       (args.results / 'endpoint.log').read_text(errors='replace'))
    expected = 1
    for filename, stages in [('lifecycle.json', 'stages'), ('navigation.json', 'resets'),
                             ('placements.json', 'placements')]:
        path = args.results / filename
        if path.exists():
            lifecycle = json.loads(path.read_text())
            expected = 1 + sum(stage['kind'] == 'scene' for stage in lifecycle[stages])
            report['passed'] = report['passed'] and lifecycle['passed']
            break
    report['expected_connections'] = expected
    report['passed'] = (report['passed'] and report['endpoint_connections'] == expected
                        and report['endpoint_graceful_disconnects'] == expected
                        and report['endpoint_disconnects'] == expected)
    try:
        endpoint_exit = json.loads((args.results / 'endpoint-exit.json').read_text())
        wrapper_exit = int((args.results / 'player-wrapper-exit.txt').read_text())
        forced = (args.results / 'player-forced-pids.txt').read_text().strip()
        report['processes_stopped_cleanly'] = (not endpoint_exit['Running'] and not endpoint_exit['OOMKilled']
            and endpoint_exit['ExitCode'] == 0 and wrapper_exit == 0 and not forced)
    except (OSError, ValueError, KeyError):
        report['processes_stopped_cleanly'] = False
    report['passed'] = report['passed'] and report['processes_stopped_cleanly']
    (args.results / 'lifecycle-logs.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()

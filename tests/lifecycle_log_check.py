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
        'endpoint_other_errors': sum('[ERROR]' in line and 'Exception: No more data available' not in line
                                     and 'Exception [Errno 9] Bad file descriptor' not in line
                                     for line in endpoint.splitlines()),
        'endpoint_connections': endpoint.count('Connection from '),
        'endpoint_logger_warnings': endpoint.count('Publisher already registered for provided node name'),
        'endpoint_closed_socket_writes': endpoint.count('Exception [Errno 9] Bad file descriptor'),
        'endpoint_disconnect_eof': endpoint.count('Exception: No more data available'),
    }
    # The pinned endpoint can log EOF and a sender write racing socket closure.
    # Preserve those diagnostics; live graph checks detect duplicate registrations.
    failures = ('duplicate_hud_headers', 'queue_overflows',
                'reader_exceptions', 'missing_references', 'unregistered_topics',
                'endpoint_tracebacks', 'endpoint_other_errors')
    counts['passed'] = (not any(counts[key] for key in failures)
                        and counts['connection_failures'] == counts['reset_by_peer_writes'])
    counts['transport_clean'] = not (counts['connection_failures'] or counts['endpoint_closed_socket_writes'])
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    report = summarize((args.results / 'player.log').read_text(errors='replace'),
                       (args.results / 'endpoint.log').read_text(errors='replace'))
    lifecycle = json.loads((args.results / 'lifecycle.json').read_text())
    report['expected_connections'] = 1 + sum(stage['kind'] == 'scene' for stage in lifecycle['stages'])
    report['passed'] = (report['passed'] and lifecycle['passed']
                        and report['endpoint_connections'] == report['expected_connections']
                        and report['reset_by_peer_writes'] <= report['expected_connections'] - 1)
    (args.results / 'lifecycle-logs.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()

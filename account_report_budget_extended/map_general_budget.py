#!/usr/bin/env python3
"""Copy Odoo 17 budget-line general budget mapping to Odoo 18.

Dry run: python3 map_general_budget.py
Apply:   python3 map_general_budget.py --apply

A general_budget_id may be shared by any number of budget lines. This script
never enforces uniqueness of the budget-line -> general-budget relationship.
It does, however, refuse to guess between different account_report_budget
records having the same name unless another verified identifier distinguishes them.
"""
import argparse
import configparser
import csv
import os
from collections import Counter, defaultdict

import psycopg2

CONFIG_FILE = '/opt/odoo18/ekara_18_test_5.conf'
SOURCE_DB = 'ekara_17_test_12'
TARGET_DB = 'ekara_18_test_10'

SOURCE_SQL = '''
SELECT cbl.id, cb.name, cbl.name, abp.id, abp.name
FROM crossovered_budget_lines cbl
JOIN crossovered_budget cb ON cb.id = cbl.crossovered_budget_id
LEFT JOIN account_budget_post abp ON abp.id = cbl.general_budget_id
'''
TARGET_SQL = '''
SELECT bl.id, ba.name, bl.name, bl.general_budget_id
FROM budget_line bl
JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
'''
POSITION_SQL = 'SELECT id, name FROM account_report_budget'


def settings(path, dbname):
    cfg = configparser.ConfigParser(interpolation=None)
    if not cfg.read(path):
        raise FileNotFoundError(path)
    if not cfg.has_section('options'):
        raise ValueError('Missing [options] section in config')
    opts = cfg['options']
    result = {'dbname': dbname, 'connect_timeout': 15}
    for key, pgkey in [('db_host', 'host'), ('db_port', 'port'),
                       ('db_user', 'user'), ('db_password', 'password')]:
        value = opts.get(key, '').strip()
        if value and value.lower() not in ('false', 'none'):
            result[pgkey] = value
    return result


def norm(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise TypeError(f'Unexpected name type {type(value).__name__}: {value!r}')
    return ' '.join(value.split()).casefold()


def indexed(rows, key):
    output = defaultdict(list)
    for row in rows:
        output[key(row)].append(row)
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--overwrite', action='store_true', help='With --apply, replace incorrect non-NULL mappings too')
    ap.add_argument('--source-db', default=SOURCE_DB)
    ap.add_argument('--target-db', default=TARGET_DB)
    ap.add_argument('--config', default=CONFIG_FILE)
    ap.add_argument('--report', default='budget_mapping_report.csv')
    args = ap.parse_args()
    if args.source_db == args.target_db:
        ap.error('Source and target databases must differ')
    if args.overwrite and not args.apply:
        ap.error('--overwrite requires --apply')

    with psycopg2.connect(**settings(args.config, args.source_db)) as source, \
         psycopg2.connect(**settings(args.config, args.target_db)) as target:
        source.set_session(readonly=True)
        with source.cursor() as cur:
            cur.execute(SOURCE_SQL)
            source_lines = cur.fetchall()
        with target.cursor() as cur:
            cur.execute(TARGET_SQL)
            target_lines = cur.fetchall()
            cur.execute(POSITION_SQL)
            positions = cur.fetchall()

        source_by_line = indexed(source_lines, lambda r: (norm(r[1]), norm(r[2])))
        target_by_line = indexed(target_lines, lambda r: (norm(r[1]), norm(r[2])))
        positions_by_name = indexed(positions, lambda r: norm(r[1]))
        position_by_id = {r[0]: r for r in positions}
        report = []
        updates = []

        for key, target_matches in target_by_line.items():
            old_matches = source_by_line.get(key, [])
            for line_id, budget, line, current_id in target_matches:
                status = ''
                source_position_id = None
                source_position_name = None
                proposed_id = None
                candidates = []
                if not all(key):
                    status = 'missing_line_or_budget_name'
                elif len(target_matches) != 1:
                    status = 'ambiguous_target_budget_line'
                elif len(old_matches) != 1:
                    status = 'source_line_not_found' if not old_matches else 'ambiguous_source_budget_line'
                else:
                    _, _, _, source_position_id, source_position_name = old_matches[0]
                    if source_position_id is None:
                        status = 'source_position_empty'
                    else:
                        candidates = positions_by_name.get(norm(source_position_name), [])
                        if not candidates:
                            status = 'target_position_not_found'
                        elif len(candidates) == 1:
                            proposed_id = candidates[0][0]
                        else:
                            # A same-name position may be shared by many lines; that is
                            # fine. The ambiguity here is *multiple position records*.
                            # Reuse existing mapping if its name matches the source.
                            if current_id in {p[0] for p in candidates}:
                                proposed_id = current_id
                            # If migrated IDs happened to survive, only trust an ID
                            # when it ALSO has the matching position name.
                            elif source_position_id in {p[0] for p in candidates}:
                                proposed_id = source_position_id
                            else:
                                status = 'ambiguous_target_position_records'
                        if proposed_id is not None:
                            if current_id == proposed_id:
                                status = 'already_correct'
                            elif current_id is None:
                                status = 'ready_to_update'
                                updates.append((line_id, current_id, proposed_id))
                            else:
                                status = 'ready_to_replace' if args.overwrite else 'existing_mapping_differs'
                                if args.overwrite:
                                    updates.append((line_id, current_id, proposed_id))
                report.append([line_id, budget, line, source_position_id,
                               source_position_name, current_id, proposed_id,
                               ';'.join(str(p[0]) for p in candidates), status])

        for key, rows in source_by_line.items():
            if key not in target_by_line:
                for old_id, budget, line, pos_id, pos_name in rows:
                    report.append(['', budget, line, pos_id, pos_name, '', '', '',
                                   f'source_only_line_{old_id}'])

        with open(args.report, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['odoo18_line_id', 'budget_name', 'budget_line_name',
                             'odoo17_position_id', 'odoo17_position_name',
                             'current_odoo18_position_id', 'proposed_odoo18_position_id',
                             'candidate_odoo18_position_ids', 'status'])
            writer.writerows(report)

        if args.apply:
            with target.cursor() as cur:
                for line_id, old_id, new_id in updates:
                    cur.execute('''
                        UPDATE budget_line
                           SET general_budget_id = %s
                         WHERE id = %s
                           AND general_budget_id IS NOT DISTINCT FROM %s
                    ''', (new_id, line_id, old_id))
                    if cur.rowcount != 1:
                        raise RuntimeError(f'Concurrent modification on budget_line {line_id}; transaction rolled back')
            target.commit()
            print(f'COMMITTED: {len(updates)} budget lines updated in {args.target_db}')
        else:
            target.rollback()
            print(f'DRY RUN: {len(updates)} eligible changes; database untouched')
        print('Source:', args.source_db, '| Target:', args.target_db)
        print('Report:', os.path.abspath(args.report))
        for status, count in sorted(Counter(r[-1] for r in report).items()):
            print(f'  {status}: {count}')
        if any(r[-1] == 'ambiguous_target_position_records' for r in report):
            print('WARNING: Same-name target position records remain ambiguous. Review candidate IDs in CSV; no arbitrary assignment was made.')


if __name__ == '__main__':
    main()

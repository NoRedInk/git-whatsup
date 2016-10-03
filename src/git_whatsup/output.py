import sys
from typing import Dict, List
from enum import Enum
import operator
import itertools
import json
import textwrap

from .datastructures import BranchStatus, MergeStatus, ConflictType


def print_json(branch_statuses: [BranchStatus]) -> None:
    '''Print all branches as a JSON array.
    '''
    json.dump(jsonify(branch_statuses), sys.stdout)
    print('')


def print_plain(
        branch_statuses: [BranchStatus],
        output_diffs: bool = False) -> None:
    '''Print branches grouped by merge status in human-readable format.
    '''
    uninteresting_statuses = (
        MergeStatus.no_common_ancestor,
        MergeStatus.no_conflicts,
        MergeStatus.conflicts_with_master,
    )

    grouped_statuses = _group_branch_statuses(branch_statuses)
    for merge_status in sorted(grouped_statuses.keys()):
        group_branches = grouped_statuses[merge_status]
        if not group_branches:
            continue
        print(merge_status.value)
        print('-' * 60)
        if merge_status in uninteresting_statuses:
            for branch_status in group_branches:
                print(branch_status.shorthand)
            continue

        for branch_status in group_branches:
            master_status = '(M!)' if branch_status.master_conflicts else ''
            print(branch_status.shorthand, master_status)
            grouped_conflicts = itertools.groupby(
                sorted(
                    branch_status.our_conflicts,
                    key=operator.attrgetter('path')),
                key=operator.attrgetter('path'))
            for path, group in grouped_conflicts:
                conflicts = list(group)
                print('  ',
                      path,
                      ''.join(map(_conflict_type_shorthand, conflicts)))

                if not output_diffs:
                    continue

                for conflict in conflicts:
                    if conflict.conflict_type == ConflictType.edit_conflict:
                        print(textwrap.indent(conflict.diff, '\t'))
        print('')


def jsonify(o):
    '''
    >>> from .datastructures import MergeResult, MergeStatus, ConflictType
    >>> jsonify('hello')
    'hello'
    >>> jsonify(0.1)
    0.1
    >>> jsonify(21)
    21
    >>> jsonify(ConflictType.edit_conflict)
    'edit_conflict'
    >>> jsonify(MergeResult(MergeStatus.no_conflicts)) == \
        {'status': 'no_conflicts', 'conflicts': []}
    True
    >>> jsonify((MergeStatus.no_common_ancestor,))
    ['no_common_ancestor']
    >>> jsonify(set([ConflictType.deleted_by_them]))
    ['deleted_by_them']
    >>> jsonify( \
            {MergeStatus.conflicts_with_me: [ConflictType.deleted_by_us]}) \
        == {'conflicts_with_me': ['deleted_by_us']}
    True
    '''
    if isinstance(o, (str, int, float)):
        return o
    if isinstance(o, Enum):
        return o.name
    if hasattr(o, '_asdict'):
        return {jsonify(k): jsonify(v) for k, v in o._asdict().items()}
    if isinstance(o, (list, tuple, set)):
        return list(map(jsonify, o))
    if isinstance(o, dict):
        return {jsonify(k): jsonify(v) for k, v in o.items()}
    return o


def _group_branch_statuses(
        branch_statuses: [BranchStatus]) \
        -> Dict[MergeStatus, List[BranchStatus]]:
    '''
    >>> set(_group_branch_statuses([]).keys()) == set(MergeStatus)
    True
    '''
    grouped_branches = itertools.groupby(
        sorted(branch_statuses, key=operator.attrgetter('merge_status')),
        key=operator.attrgetter('merge_status'))

    rv = {merge_status: [] for merge_status in MergeStatus}
    for merge_status, branch_statuses in grouped_branches:
        rv[merge_status] = sorted(branch_statuses,
                                  key=operator.attrgetter('head_commit_time'))
    return rv


def _conflict_type_shorthand(conflict_type: ConflictType) -> str:
    '''
    >>> _conflict_type_shorthand(ConflictType.deleted_by_us)
    'deleted by us'
    >>> _conflict_type_shorthand(ConflictType.deleted_by_them)
    'deleted by them'
    >>> _conflict_type_shorthand(ConflictType.edit_conflict)
    'C'
    '''
    as_is_statuses = (ConflictType.deleted_by_us, ConflictType.deleted_by_them)
    if conflict_type in as_is_statuses:
        return conflict_type.value
    else:
        return 'C'

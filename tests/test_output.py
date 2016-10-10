import json

import pytest

from git_whatsup.datastructures import (
    BranchStatus, MergeStatus, Conflict, ConflictType, OutputFormat)
from git_whatsup import output


@pytest.fixture(scope='module')
def all_branch_statuses():
    return [
        BranchStatus(
            shorthand=MergeStatus.no_common_ancestor.value,
            head_commit_time=0,
            merge_status=MergeStatus.no_common_ancestor,
            our_conflicts=set(),
            master_conflicts=set(),
        ),
        BranchStatus(
            shorthand=MergeStatus.no_conflicts.value,
            head_commit_time=0,
            merge_status=MergeStatus.no_conflicts,
            our_conflicts=set(),
            master_conflicts=set(),
        ),
        BranchStatus(
            shorthand=MergeStatus.conflicts_with_master.value,
            head_commit_time=0,
            merge_status=MergeStatus.conflicts_with_master,
            our_conflicts=set(),
            master_conflicts=set([
                Conflict(
                    path='their.py',
                    conflict_type=ConflictType.deleted_by_us)]),
        ),
        BranchStatus(
            shorthand=MergeStatus.conflicts_with_me.value,
            head_commit_time=0,
            merge_status=MergeStatus.conflicts_with_me,
            our_conflicts=set([
                Conflict(
                    path='mine.py',
                    conflict_type=ConflictType.edit_conflict,
                    start=0,
                    diff='this is the diff')]),
            master_conflicts=set(),
        ),
    ]


def test_print_branches_prints_conflicts_in_json(capsys, all_branch_statuses):
    output.print_branches(
        all_branch_statuses, OutputFormat.json, include_all=False)
    out, err = capsys.readouterr()
    expected = [
        {
            'shorthand': 'conflicts with me',
            'head_commit_time': 0,
            'merge_status': 'conflicts_with_me',
            'our_conflicts': [{
                'conflict_type': 'edit_conflict',
                'path': 'mine.py',
                'start': 0,
                'diff': 'this is the diff',
            }],
            'master_conflicts': [],
        }
    ]
    assert json.loads(out) == expected


def test_print_branches_prints_all_in_json(capsys, all_branch_statuses):
    output.print_branches(
        all_branch_statuses, OutputFormat.json, include_all=True)
    out, err = capsys.readouterr()
    expected = [
        {
            'shorthand': 'no common ancestor',
            'head_commit_time': 0,
            'merge_status': 'no_common_ancestor',
            'our_conflicts': [],
            'master_conflicts': [],
        },
        {
            'shorthand': 'no conflicts',
            'head_commit_time': 0,
            'merge_status': 'no_conflicts',
            'our_conflicts': [],
            'master_conflicts': [],
        },
        {
            'shorthand': 'conflicts with master',
            'head_commit_time': 0,
            'merge_status': 'conflicts_with_master',
            'our_conflicts': [],
            'master_conflicts': [{
                'path': 'their.py',
                'start': None,
                'conflict_type': 'deleted_by_us',
                'diff': None,
            }],
        },
        {
            'shorthand': 'conflicts with me',
            'head_commit_time': 0,
            'merge_status': 'conflicts_with_me',
            'our_conflicts': [{
                'conflict_type': 'edit_conflict',
                'path': 'mine.py',
                'start': 0,
                'diff': 'this is the diff',
            }],
            'master_conflicts': [],
        },
    ]
    assert json.loads(out) == expected


def test_print_branches_prints_all_in_plain(capsys, all_branch_statuses):
    output.print_branches(
        all_branch_statuses, OutputFormat.plain, include_all=True)
    out, err = capsys.readouterr()
    for merge_status in MergeStatus:
        assert merge_status.value in out


def test_print_branches_prints_conflicts_in_plain(capsys, all_branch_statuses):
    output.print_branches(
        all_branch_statuses, OutputFormat.plain,
        include_all=False, output_diffs=True)
    out, err = capsys.readouterr()
    assert MergeStatus.conflicts_with_me.value in out
    assert 'this is the diff' in out


def test_print_branches_can_hide_diffs_in_plain(capsys, all_branch_statuses):
    output.print_branches(
        all_branch_statuses, OutputFormat.plain,
        include_all=False, output_diffs=False)
    out, err = capsys.readouterr()
    assert MergeStatus.conflicts_with_me.value in out
    assert 'this is the diff' not in out

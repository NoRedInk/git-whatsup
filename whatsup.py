'''
List up remote branches that conflict with the current working copy.
'''
import sys
from typing import Set, Dict, List, NamedTuple, Optional, Iterator
from enum import Enum
from functools import total_ordering
from collections import namedtuple
import operator
import itertools
import re
import json
import textwrap
import argparse

import pygit2


WORKING_COPY_TAG_NAME = 'whatsup-with-me'
WORKING_COPY_TAG_REF = 'refs/tags/' + WORKING_COPY_TAG_NAME
CONFLICTING_DIFF_RE = re.compile(
    r'<<<<<<< .*?(>>>>>>>) (?P<path>.*?).$', re.DOTALL|re.MULTILINE)


@total_ordering
class OrderedEnum(Enum):
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            all_members = list(self.__class__)
            return all_members.index(self) < all_members.index(other)
        return NotImplemented


class MergeStatus(OrderedEnum):
    no_common_ancestor = 'no common ancestor'
    no_conflicts = 'no conflicts'
    conflicts_with_master = 'conflicts with master'
    conflicts_with_me = 'conflicts with me'


class ConflictType(OrderedEnum):
    edit_conflict = 'edit conflict'
    deleted_by_us = 'deleted by us'
    deleted_by_them = 'deleted by them'


Conflict = NamedTuple(
    'Conflict', [
        ('path', str),
        ('conflict_type', ConflictType),
        ('start', Optional[int]),
        ('diff', Optional[str]),
    ]
)
Conflict.__new__.__defaults__ = (None, None)


MergeResult = NamedTuple(
    'MergeResult', [
        ('status', MergeStatus),
        ('conflicts', Set[Conflict]),
    ]
)
MergeResult.__new__.__defaults__ = (set(),)


BranchStatus = NamedTuple(
    'BranchStatus', [
        ('shorthand', str),
        ('head_commit_time', int),
        ('merge_status', MergeStatus),
        ('our_conflicts', Set[Conflict]),
        ('master_conflicts', Set[Conflict]),
    ]
)
BranchStatus.__new__.__defaults__ = (set(), set())


class OutputFormat(Enum):
    plain = 'plain'
    json = 'json'


# branch status


def preview_merge(
        repo: pygit2.Repository,
        us: pygit2.Oid,
        them: pygit2.Oid) -> MergeResult:
    base = repo.merge_base(us, them)
    if base is None:
        return MergeResult(MergeStatus.no_common_ancestor)

    merged_index = repo.merge_trees(base, us, them)
    if merged_index.conflicts is None:
        return MergeResult(MergeStatus.no_conflicts)

    conflicts = set(parse_conflicts(repo, merged_index.conflicts))
    return MergeResult(MergeStatus.conflicts_with_me, conflicts)


def parse_conflicts(
        repo: pygit2.Repository,
        conflicts: pygit2.index.ConflictCollection) -> Iterator[Conflict]:
    for conflict in conflicts:
        ancestor, ours, theirs = conflict
        if ours is None:
            yield Conflict(ancestor.path, ConflictType.deleted_by_us)
        elif theirs is None:
            yield Conflict(ancestor.path, ConflictType.deleted_by_them)
        else:
            file_diff = repo.merge_file_from_index(*conflict)
            for part in CONFLICTING_DIFF_RE.finditer(file_diff):
                yield Conflict(
                    next(entry for entry in conflict if entry).path,
                    ConflictType.edit_conflict,
                    part.start(),
                    part.group(0))


def get_branch_status(
        repo: pygit2.Repository,
        us: pygit2.Oid,
        them: pygit2.Branch,
        master: pygit2.Branch) -> BranchStatus:
    no_conflict_statuses = (MergeStatus.no_common_ancestor, MergeStatus.no_conflicts)

    us_and_them = preview_merge(repo, us, them.target)
    if us_and_them.status in no_conflict_statuses:
        return branch_status_from(them, us_and_them.status)

    # investigate which side(s) the conflicts lie
    master_and_them = preview_merge(repo, master.target, them.target)
    if master_and_them.status in no_conflict_statuses:
        return branch_status_from(
            them,
            MergeStatus.conflicts_with_me,
            our_conflicts=us_and_them.conflicts)
    elif master_and_them.status == MergeStatus.conflicts_with_me:
        just_our_conflicts = us_and_them.conflicts - master_and_them.conflicts
        if just_our_conflicts:
            status = MergeStatus.conflicts_with_me
        else:
            status = MergeStatus.conflicts_with_master
        return branch_status_from(
            them,
            status,
            our_conflicts=just_our_conflicts,
            master_conflicts=master_and_them.conflicts)
    else:
        raise Exception(
            "Don't know what to do with this master_and_them: {}".format(master_and_them))


def branch_status_from(branch, status, **kwargs):
    target_object = branch.get_object()
    return BranchStatus(
        branch.shorthand,
        target_object.commit_time + target_object.commit_time_offset,
        status,
        **kwargs)


def get_branch_statuses(
        repo: pygit2.Repository,
        master: pygit2.Branch,
        branches: [pygit2.Branch]) -> [BranchStatus]:
    working_copy_oid = commit_to_working_copy_tag(repo)
    return [
        get_branch_status(
            repo,
            working_copy_oid,
            branch,
            master) for branch in branches]


# working copy management


def commit_to_working_copy_tag(repo: pygit2.Repository) -> pygit2.Oid:
    repo.index.read()
    repo.index.add_all()  # TODO: add a binding for update_all to pygit2 and use it.
    tree = repo.index.write_tree()
    signature = repo.default_signature
    message = 'whats up with me'
    commit_oid = repo.create_commit(
        None,
        signature,
        signature,
        message,
        tree,
        [repo.head.get_object().hex])
    try:
        tag = get_working_copy_tag(repo)
        tag.set_target(commit_oid)
    except KeyError:
        repo.create_tag(
            WORKING_COPY_TAG_NAME,
            commit_oid,
            pygit2.GIT_OBJ_COMMIT,
            signature,
            message)

    return commit_oid


def get_working_copy_tag(repo: pygit2.Repository) -> pygit2.Reference:
    return repo.lookup_reference(WORKING_COPY_TAG_REF)


# printing


def group_branch_statuses(branch_statuses: [BranchStatus]) -> Dict[MergeStatus, List[BranchStatus]]:
    '''
    >>> set(group_branch_statuses([]).keys()) == set(MergeStatus)
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


def conflict_type_shorthand(conflict_type: ConflictType) -> str:
    '''
    >>> conflict_type_shorthand(ConflictType.deleted_by_us)
    'deleted by us'
    >>> conflict_type_shorthand(ConflictType.deleted_by_them)
    'deleted by them'
    >>> conflict_type_shorthand(ConflictType.edit_conflict)
    'C'
    '''
    if conflict_type in (ConflictType.deleted_by_us, ConflictType.deleted_by_them):
        return conflict_type.value
    else:
        return 'C'


def print_plain(
        branch_statuses: [BranchStatus],
        output_diffs: bool = False) -> None:
    uninteresting_statuses = (
        MergeStatus.no_common_ancestor,
        MergeStatus.no_conflicts,
        MergeStatus.conflicts_with_master,
    )

    grouped_statuses = group_branch_statuses(branch_statuses)
    for merge_status in sorted(grouped_statuses.keys()):
        group_branches = grouped_statuses[merge_status]
        if not group_branches:
            continue
        print(merge_status.value)
        print('=' * 60)
        if merge_status in uninteresting_statuses:
            for branch_status in group_branches:
                print(branch_status.shorthand)
        else:
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
                    print('  ', path, ''.join(map(conflict_type_shorthand, conflicts)))

                    if output_diffs:
                        for conflict in conflicts:
                            if conflict.conflict_type == ConflictType.edit_conflict:
                                print(textwrap.indent(conflict.diff, '\t'))
        print('')


def jsonify(o):
    '''
    >>> jsonify('hello')
    'hello'
    >>> jsonify(0.1)
    0.1
    >>> jsonify(21)
    21
    >>> jsonify(ConflictType.edit_conflict)
    'edit_conflict'
    >>> jsonify(MergeResult(MergeStatus.no_conflicts)) == {'status': 'no_conflicts', 'conflicts': []}
    True
    >>> jsonify((MergeStatus.no_common_ancestor,))
    ['no_common_ancestor']
    >>> jsonify(set([ConflictType.deleted_by_them]))
    ['deleted_by_them']
    >>> jsonify({MergeStatus.conflicts_with_me: [ConflictType.deleted_by_us]}) == {'conflicts_with_me': ['deleted_by_us']}
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


def print_json(branch_statuses: [BranchStatus]) -> None:
    json.dump(jsonify(branch_statuses), sys.stdout)
    print('')


# main / helpers


def list_remote_branches(
        repo: pygit2.Repository,
        remote: str = 'origin',
        exclude_remote_of_head: bool = True) -> Iterator[pygit2.Branch]:
    remote_prefix = remote + '/'
    remote_head = remote + '/HEAD'
    remote_of_local_head = remote + '/' + repo.head.shorthand
    for branch_name in repo.listall_branches(pygit2.GIT_BRANCH_REMOTE):
        if not branch_name.startswith(remote_prefix):
            continue
        if branch_name == remote_head:
            continue
        if exclude_remote_of_head and branch_name == remote_of_local_head:
            continue
        yield repo.lookup_branch(branch_name, pygit2.GIT_BRANCH_REMOTE)


def prune_branch_statuses(
        branch_statuses: [BranchStatus],
        all_statuses: bool = False) -> Iterator[BranchStatus]:
    for branch_status in branch_statuses:
        if not all_statuses and branch_status.merge_status != MergeStatus.conflicts_with_me:
            continue

        yield branch_status


def main(
        repo_path: str = '.',
        remote: str = 'origin',
        master: str = 'master',
        includes: [str] = [],
        all_statuses: bool = False,
        output_diffs: bool = False,
        output_format: OutputFormat = OutputFormat.plain) -> None:
    repo = pygit2.Repository(repo_path)
    master = repo.lookup_branch('{}/{}'.format(remote, master), pygit2.GIT_BRANCH_REMOTE)

    if includes:
        branches = [repo.lookup_branch(branch_name, pygit2.GIT_BRANCH_REMOTE)
                    for branch_name in includes]
    else:
        branches = list_remote_branches(repo, remote)

    branch_statuses = get_branch_statuses(repo, master, branches)
    pruned_output = prune_branch_statuses(branch_statuses, all_statuses)

    if output_format == OutputFormat.plain:
        print_plain(pruned_output, output_diffs)
    elif output_format == OutputFormat.json:
        print_json(pruned_output)

    has_conflicts_with_me = any(
        branch.merge_status == MergeStatus.conflicts_with_me
        for branch in branch_statuses)
    exit_status = 1 if has_conflicts_with_me else 0
    sys.exit(exit_status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo_path', default='.', nargs='?',
                        help='target Git repository')
    parser.add_argument('--remote', metavar='REMOTE_NAME', default='origin',
                        help='compare against branches in this remote')
    parser.add_argument('--master', metavar='BRANCH_NAME', default='master',
                        help='master branch name')
    parser.add_argument('--include', '-i', metavar='BRANCH_NAME',
                        dest='includes', action='append',
                        help='branches to check')
    parser.add_argument('--all', '-a', default=False,
                        dest='all_statuses', action='store_true',
                        help='output all branch statuses')
    parser.add_argument('--diff', '-d', default=False,
                        dest='output_diffs', action='store_true',
                        help='output diffs if output format is plain')
    parser.add_argument('--format', '-f', default=OutputFormat.plain,
                        dest='output_format',
                        choices=[m.name for m in OutputFormat], type=lambda v: OutputFormat[v],
                        help='json always includes diffs')

    args = parser.parse_args()
    main(
        args.repo_path,
        args.remote,
        args.master,
        args.includes,
        args.all_statuses,
        args.output_diffs,
        args.output_format)

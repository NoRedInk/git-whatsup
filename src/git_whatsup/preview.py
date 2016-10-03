from typing import Iterator
import re

import pygit2

from .datastructures import (
    BranchStatus,
    MergeStatus, MergeResult,
    Conflict, ConflictType)
from . import working_copy


CONFLICTING_DIFF_RE = re.compile(
    r'<{7} .*?(>{7}) (?P<path>.*?).$', re.DOTALL | re.MULTILINE)


def get_branch_statuses(
        repo: pygit2.Repository,
        master: pygit2.Branch,
        branches: [pygit2.Branch]) -> [BranchStatus]:
    working_copy_oid = working_copy.commit_to_working_copy_tag(repo)
    return [
        get_branch_status(
            repo,
            working_copy_oid,
            branch,
            master) for branch in branches]


def get_branch_status(
        repo: pygit2.Repository,
        us: pygit2.Oid,
        them: pygit2.Branch,
        master: pygit2.Branch) -> BranchStatus:
    no_conflict_statuses = (MergeStatus.no_common_ancestor,
                            MergeStatus.no_conflicts)

    us_and_them = preview_merge(repo, us, them.target)
    if us_and_them.status in no_conflict_statuses:
        return _branch_status_from(them, us_and_them.status)

    # investigate which side(s) the conflicts lie
    master_and_them = preview_merge(repo, master.target, them.target)
    if master_and_them.status in no_conflict_statuses:
        return _branch_status_from(
            them,
            MergeStatus.conflicts_with_me,
            our_conflicts=us_and_them.conflicts)
    elif master_and_them.status == MergeStatus.conflicts_with_me:
        just_our_conflicts = us_and_them.conflicts - master_and_them.conflicts
        if just_our_conflicts:
            status = MergeStatus.conflicts_with_me
        else:
            status = MergeStatus.conflicts_with_master
        return _branch_status_from(
            them,
            status,
            our_conflicts=just_our_conflicts,
            master_conflicts=master_and_them.conflicts)
    else:
        message = "Don't know what to do with this master_and_them: {}".format(
            master_and_them)
        raise Exception(message)


def _branch_status_from(branch, status, **kwargs):
    target_object = branch.get_object()
    return BranchStatus(
        branch.shorthand,
        target_object.commit_time + target_object.commit_time_offset,
        status,
        **kwargs)


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

    conflicts = set(_parse_conflicts(repo, merged_index.conflicts))
    return MergeResult(MergeStatus.conflicts_with_me, conflicts)


def _parse_conflicts(
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

'''
List up remote branches that conflict with the current working copy.
'''
import sys
from typing import Optional, Iterator, List
import argparse

import pygit2

from .datastructures import BranchStatus, MergeStatus, OutputFormat
from . import output
from . import preview


def _list_remote_branches(
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


def _prune_branch_statuses(
        branch_statuses: [BranchStatus],
        all_statuses: bool = False) -> Iterator[BranchStatus]:
    for branch_status in branch_statuses:
        if not all_statuses and \
           branch_status.merge_status != MergeStatus.conflicts_with_me:
            continue

        yield branch_status


def main(argv: Optional[List[str]] = None) -> None:
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
                        help='output all statuses if output format is `plain`')
    parser.add_argument('--diff', '-d', default=False,
                        dest='output_diffs', action='store_true',
                        help='output diffs if output format is `plain`')
    parser.add_argument('--format', '-f', default=OutputFormat.plain,
                        dest='output_format',
                        choices=[m.name for m in OutputFormat],
                        type=lambda v: OutputFormat[v],
                        help='json always includes diffs')
    args = parser.parse_args(args=argv)

    repo = pygit2.Repository(args.repo_path)
    master = repo.lookup_branch(
        '{}/{}'.format(args.remote, args.master),
        pygit2.GIT_BRANCH_REMOTE)

    if args.includes:
        branches = [repo.lookup_branch(branch_name, pygit2.GIT_BRANCH_REMOTE)
                    for branch_name in args.includes]
    else:
        branches = _list_remote_branches(repo, args.remote)

    branch_statuses = preview.get_branch_statuses(repo, master, branches)
    pruned_output = _prune_branch_statuses(branch_statuses, args.all_statuses)

    if args.output_format == OutputFormat.plain:
        output.print_plain(pruned_output, args.output_diffs)
    elif args.output_format == OutputFormat.json:
        output.print_json(pruned_output)

    has_conflicts_with_me = any(
        branch.merge_status == MergeStatus.conflicts_with_me
        for branch in branch_statuses)
    exit_status = 1 if has_conflicts_with_me else 0
    sys.exit(exit_status)

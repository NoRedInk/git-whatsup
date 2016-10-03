from typing import Set, NamedTuple, Optional
from enum import Enum
from functools import total_ordering


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

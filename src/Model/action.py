from enum import Enum


class Action(Enum):
    add = "add"
    remove = "remove"
    transfer = "transfer"
    revert = "revert"

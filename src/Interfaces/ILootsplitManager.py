from abc import ABC, abstractmethod

class ILootsplitManager(ABC):

    @abstractmethod
    def create_lootsplit()
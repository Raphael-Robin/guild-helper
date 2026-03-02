from src.Interfaces import IEconomyManager, ILogManager, IConfigurationManager
from src.Model import Player, Log, Lootsplit, Action

class EconomyManager(IEconomyManager):

    def __init__(self, config: IConfigurationManager, logger: ILogManager | None = None) -> None:
        self.logger = logger
    

    def get_balance(self, player: Player):
        return player.balance
    
    def add_balance(self, player: Player, amount: int) -> None:
        if not amount > 0:
            return
    
        if self.logger:
            log = Log(player=player, action= Action.add, amount=amount)
            self.logger.log_economy(log=log)

        player.balance += amount
    
    def remove_balance(self, player: Player,amount: int) -> None:
        if not amount < 0:
            return
    
        if self.logger:
            log = Log(player=player, action= Action.add, amount=amount)
            self.logger.log_economy(log=log)

        player.balance -= amount


from juicethirstyfruitwarriors.Server.OrangeLogic import OrangeLogic
from juicethirstyfruitwarriors.Server.PlayerAILogic import PlayerAILogic


class OrangeAI(PlayerAILogic, OrangeLogic):
    def __init__(self, player_id, terrain):
        super(OrangeAI, self).__init__(player_id, terrain)
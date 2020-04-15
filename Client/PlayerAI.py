import Player


class PlayerAI(Player.Player):
    def __init__(self, player_id, pic_file):
        super(PlayerAI, self).__init__(player_id, pic_file)

    def update(self, events):  # override player's update
        self.pos_update()

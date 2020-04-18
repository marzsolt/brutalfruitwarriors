import Player
import pygame as pg
import Vector2D
from BaseMessage import BaseMessage
from Client import Client
import client_message_constants as climess


class ApplePlayer(Player.Player):
    def __init__(self, player_id):
        super(ApplePlayer, self).__init__(player_id, Player.PicFile.APPLE)

    def update(self, pressed_keys):
        super().update(pressed_keys)
        ev = pg.event.get()
        for event in ev:
            print("eve")
            if event.type == pg.MOUSEBUTTONUP:
                print("fggfds")
                x, y = pg.mouse.get_pos()
                print(x, y)
                mes = BaseMessage(climess.MessageType.APPLE_ATTACK, climess.Target.PLAYER_LOGIC + str(self._id))
                mes.x = x
                mes.y = y
                Client.get_instance().send_message(mes)




import pygame as pg
import pygameMenu as pgM
import logging
import functools

import src.Client.Screen.screen_state_constants as sstatecons

# networking
from src.Client.Network_communication.Client import Client

# messaging
from src.Client.Player.PlayerManager import PlayerManager
import src.Client.Network_communication.client_message_constants as climess
import src.Server.Network_communication.server_message_constants as sermess
from src.utils.BaseMessage import BaseMessage

# constants
from src.utils.general_constants import *


class Screen:
    """ Screen - responsible for the main tasks on client side, such as drawing to display, etc. """
    def __init__(self, screen_height=SCREEN_HEIGHT, screen_width=SCREEN_WIDTH, port=None, \
                 ip=None, name=None):
        self.logger = logging.getLogger('Domi.Screen')
        self.__screen = pg.display.set_mode([screen_width, screen_height])
        self.__h, self.__w = [pg.display.Info().current_h, pg.display.Info().current_w]  # get screen h and w

        # argparsed args
        self.__port = port  # get port number for server setup
        self.__def_ip = ip  # ip number for (default) ip setup
        self.__def_name = name  # name for (default) name setup

        self.__screenState = sstatecons.ScreenState.MAIN_MENU

        # initializing the menus, the order is important! (i.e. the sub menus of main menu - about & play menus first)
        self.__playMenu = self._init_play_menu()
        self.__aboutMenu = self._init_about_menu()
        self.__mainMenu = self._init_main_menu()
        self.__connectionMenu, self.__connectionMenuState = self._init_connection_menu()

        self.__is_first_player = None  # so that the first can modify in connectionMenu the player count

        self.__running = True  # so that a member function can trigger exiting
        self.__game_over_state = None  # trace game over status
        self.__t_to_exit = None  # on game over, trace time before automated exiting

        self.__show_cannot_attack_text = False

    def update(self, events, pressed_keys):
        """" Responsible for updating the screen, and returning its running state to the main function. """
        self._draw_adequate_screen(events, pressed_keys)
        pg.display.flip()  # flip the display
        self._check_exit_criteria(events)  # this should be the last, as closes connection on running = False
        return self.__running

    def _draw_adequate_screen(self, events, pressed_keys):
        """" Draw the adequate screen (according to the state). """
        if self.__screenState == sstatecons.ScreenState.MAIN_MENU:
            self.__mainMenu.mainloop(events)  # triggering the main menu structure
        elif self.__screenState == sstatecons.ScreenState.CONNECTION_MENU:
            self.__connectionMenu.mainloop(events)  # triggering the connectionMenu structure
        elif self.__screenState == sstatecons.ScreenState.GAME:
            self._game_screen(pressed_keys, events)  # showing the game screen

    def _game_screen(self, pressed_keys, events):
        """ Responsible for showing the game screen. """
        msgs = Client.get_instance().get_targets_messages(sermess.Target.SCREEN)
        self._check_game_over(msgs)  # check if same so called 'game over' related activity happend or not
        self._draw_background_and_terrain()
        self.__check_draw_if_cannot_attack_text(msgs)  # check if its player can not attack --> show text
        PlayerManager.get_instance().update(pressed_keys, events)  # update player manager
        PlayerManager.get_instance().draw_players(screen=self.__screen)  # draw players by player manager

    def _check_game_over(self, msgs):
        """" Checks if 'game over' related activity happened or not. """
        for msg in msgs:
            if msg.type == sermess.MessageType.DIED:  # a player's dead was announced by the Game (server side)
                self.logger.info(f"ID: {msg.player_id} Death of player acknowledged.")
                PlayerManager.get_instance().remove_player(msg.player_id)  # remove from player manager
                self.logger.info(f"ID: {msg.player_id} Player removed from player manager.")
                if Client.get_instance().id == msg.player_id:  # if it was our player, set screen's game over state
                    self.__game_over_state = sstatecons.GameOverState.LOST
                    self.logger.info("It is our player that died!")
                    self.__show_cannot_attack_text = False
            elif msg.type == sermess.MessageType.NO_ALIVE_HUMAN:  # if Game announced that all human player is dead
                self.__game_over_state = sstatecons.GameOverState.ALL_HUMAN_DIED  # set game over state of Screen
                self.__t_to_exit = FPS * 10 - 1  # trigger delayed exit
            elif msg.type == sermess.MessageType.WON:  # if Game announced that a player won
                if msg.player_id == Client.get_instance().id:  # check if it's ours'
                    self.__game_over_state = sstatecons.GameOverState.WON  # then set it's go. state accordingly
                self.__t_to_exit = FPS * 10 - 1  # trigger delayed exit for regardless

    def _check_exit_criteria(self, events):
        """" Checks if an exit criteria is met or not. """
        for event in events:  # event handling - look at every event in the queue
            if event.type == pg.KEYDOWN:  # did the user hit a key?

                if event.key == pg.K_ESCAPE:  # Was it the Escape key? If so, stop the loop.
                    self.__running = False

            # Did the user click the window close button? If so, stop the loop. w/o. doesn't work
            if event.type == pg.QUIT:
                self.__running = False

        # close connection (if there is any - see fun implementation) on running = False (Screen kill)
        if not self.__running:
            Client.get_instance().close_connection()

    def _init_main_menu(self):
        """ Initializes the main menu.
            First needs it's sub menus to be initialized! """
        main_menu = pgM.Menu(
            self.__screen,
            self.__w,
            self.__h,
            pgM.font.FONT_OPEN_SANS,
            'Main Menu',
            bgfun=self._default_bgfun,
            menu_color=BLACK,
            menu_color_title=BLACK,
            menu_alpha=100,
            back_box=False
        )

        main_menu.add_option('Play', self.__playMenu)
        main_menu.add_option('About', self.__aboutMenu)
        main_menu.add_option('Exit', pgM.events.EXIT)

        return main_menu

    def _init_play_menu(self):
        """" Initializes playMenu. """
        play_menu = pgM.TextMenu(
            self.__screen,
            self.__w,
            self.__h,
            pgM.font.FONT_OPEN_SANS,
            'Play Menu',
            bgfun=self._default_bgfun,
            menu_color=BLACK,
            menu_color_title=BLACK,
            menu_alpha=100
        )

        play_menu_lines = [  # lines to display in main menu -- play menu
            'In order to connect to a server, please enter',
            'its IP address below, followed by enter:',
            ''
        ]
        for txt in play_menu_lines:
            play_menu.add_line(txt)

        play_menu.add_text_input(  # text input for IP
            title='IP: ',
            textinput_id='playMenu_input_IP',
            maxchar=4 * 3 + 3,
            default=self.__def_ip,
            onchange=self._onchange_play_menu_input_ip,
            onreturn=self._onreturn_play_menu_input_ip
        )
        play_menu.add_text_input(  # text input for name
            title='Name: ',
            textinput_id='playMenu_input_name',
            maxchar=8,
            default=self.__def_name
        )
        play_menu.add_option('Back', pgM.events.BACK)

        return play_menu

    def _init_about_menu(self):
        """" Initializes aboutMenu. """
        about_menu = pgM.TextMenu(
            self.__screen,
            self.__w,
            self.__h,
            pgM.font.FONT_OPEN_SANS,
            'About Menu',
            bgfun=self._default_bgfun,
            menu_color=BLACK,
            menu_color_title=BLACK,
            menu_alpha=100
        )

        about_menu_lines = [
            'This is a game developed in pygame,',
            'proudly delivered to you by:',
            '',
            'Farkas Domonkos László',
            'Molnár Petra',
            'Márkos Zsolt'
        ]
        for txt in about_menu_lines:
            about_menu.add_line(txt)

        about_menu.add_option('Back', pgM.events.BACK)

        return about_menu

    def _init_connection_menu(self):
        """" Initializes connectionMenu. """
        connection_menu = pgM.TextMenu(
            self.__screen,
            self.__w,
            self.__h,
            pgM.font.FONT_OPEN_SANS,
            'Connection Menu',
            bgfun=self._connection_menu_bgfun,
            menu_color=BLACK,
            menu_color_title=BLACK,
            menu_alpha=100,
            back_box=False
        )

        return connection_menu, sstatecons.ConnectionMenuState.INITIAL

    def _default_bgfun(self):
        """" Default bg function for menus that need just a black screen. """
        self.__screen.fill(BLACK)

    def _onchange_play_menu_input_ip(self, val):
        """" Checks onchange of playMenu IP input field. """
        inp_widget = self.__playMenu.get_widget('playMenu_input_IP')

        # do not let to write anything but numbers and dots
        if len(val) > 0 and not (val[-1].isnumeric() or val[-1] == '.'):
            inp_widget.set_value(val[:-1])

    def _onreturn_play_menu_input_ip(self, val):
        """" Checks onreturn of playMenu IP input field. """
        is_okay = True  # assume that entry is valid, then gradually check.

        if val.count('.') != 3:  # IP has exactly 3 dots.
            is_okay = False
        else:
            for field in val.split('.'):
                if len(field) == 0 or int(field) > 255:  # digits in it have > 0 length and max val of 255
                    is_okay = False

        if not is_okay:  # if not ok, delete input field content
            self.__playMenu.get_widget('playMenu_input_IP').set_value('')
        else:  # if IP entry valid, trigger connectionMenu and attempt to connect via Client
            self.__connectionMenu.add_line('Connecting to ' + val + ', please wait.')
            Client.get_instance().setup_connection(val, self.__port)
            self.__screenState = sstatecons.ScreenState.CONNECTION_MENU
            self.__mainMenu.disable()
            self.__connectionMenu.enable()

    def _connection_menu_bgfun(self):
        """" Background function of connectionMenu, manages actions in its states. """
        # when in INITIAL state and client connection got a status
        if self.__connectionMenuState == sstatecons.ConnectionMenuState.INITIAL and\
                Client.get_instance().connection_alive is not None:

            self.__connectionMenu.add_line('')

            if Client.get_instance().connection_alive:  # if connection got alive
                self.__connectionMenu.disable()
                self.__connectionMenu, _ = self._init_connection_menu()
                self.__connectionMenu.enable()
                self.__connectionMenu.add_line('Successfully connected.')

                # also, send the player name
                while Client.get_instance().id is None:
                    pass
                msg = BaseMessage(climess.MessageType.NAME, climess.Target.GAME)
                msg.player_id = Client.get_instance().id
                msg.name = self.__playMenu.get_widget('playMenu_input_name').get_value()
                Client.get_instance().send_important_message(msg)
                self.logger.info(f"Sent name: {msg.name}")
            else:  # else
                self.__connectionMenu.add_line('Connection error, please try again!')

            # change state to show connection status message
            self.__connectionMenuState = sstatecons.ConnectionMenuState.CONN_MSG_SHOWN

        # when in CONN_MSG_SHOWN state
        elif self.__connectionMenuState == sstatecons.ConnectionMenuState.CONN_MSG_SHOWN:
            if Client.get_instance().connection_alive:
                msgs = Client.get_instance().get_targets_messages(sermess.Target.SCREEN)

                for msg in msgs:
                    # if this is the first time got FIRST PLAYER msg, then set it accordingly to true
                    if self.__is_first_player is None and msg.type == sermess.MessageType.FIRST_PLAYER:
                        self.logger.info("I am the host.")
                        self.__is_first_player = True

                        self.__connectionMenu.add_selector(
                            title='Player count: ',
                            values=[('2', 2), ('3', 3), ('4', 4), ('5', 5)],
                            default=0,
                            onchange=self._connection_menu_player_count_selector_onchange
                        )

                        self.__connectionMenu.add_option('Play', self._connection_menu_start_pressed)
                    elif msg.type == sermess.MessageType.INITIAL_DATA:  # if initial data sent, start game
                        self.logger.info("Game started, terrain loaded")
                        self.__terrain_points = msg.terrain_points
                        self.__terrain_points_levels = msg.terrain_points_levels
                        self.__screenState = sstatecons.ScreenState.GAME
                        self.__connectionMenu.disable()
                        PlayerManager.get_instance().create_players(
                            msg.apple_human_ids,
                            msg.orange_human_ids,
                            msg.apple_ai_ids,
                            msg.orange_ai_ids
                        )

            else:  # if conn msg was shown and connection isn't alive, go back to playMenu (sub menu of mainMenu)
                self.__screenState = sstatecons.ScreenState.MAIN_MENU
                self.__connectionMenu.disable()
                self.__mainMenu.enable()

                # reinitialize. connectionMenu so that it flushes msgs
                self.__connectionMenu, self.__connectionMenuState = self._init_connection_menu()

                # acknowledged the connection error status, and now set back the flag to None
                Client.get_instance().connection_alive = None

                # some delays, so that the connection msg can be read
                pg.time.wait(2500)

    @staticmethod
    def _connection_menu_player_count_selector_onchange(_, value):
        """" Manages onChange of the connectionMenu's player count selector. """
        msg = BaseMessage(mess_type=climess.MessageType.CHANGE_PLAYER_NUMBER, target=climess.Target.GAME)
        msg.new_number = value  # send Game (server side) the new player count.
        Client.get_instance().send_message(msg)

    @staticmethod
    def _connection_menu_start_pressed():
        """" Manages press of start on connectionMenu (forcibly trigger game without meeting count). """
        msg = BaseMessage(mess_type=climess.MessageType.START_GAME_MANUALLY, target=climess.Target.GAME)
        Client.get_instance().send_important_message(msg)

    def bck_bg_decorator(fun):
        """" Decorator for black bg. """
        @functools.wraps(fun)
        def wrapper(self):
            self.__screen.fill(BLACK)  # black bg
            # before fun ^^^
            fun(self)  # PyCharm - liar

        return wrapper

    @bck_bg_decorator  # PyCharm - liar
    def _draw_background_and_terrain(self):
        self.__draw_terrain()

        # draw game over text
        if self.__game_over_state is not None:
            self.__draw_game_over_text()

        # draw t to exit below game over text
        if self.__t_to_exit is not None:
            self.__draw_t_to_exit_text()

    def __draw_terrain(self):
        """" Responsible for drawing terrain. """
        for i in range(1, len(self.__terrain_points)):  # draw the terrain lines

            pg.draw.line(
                self.__screen,
                WHITE,
                (self.__terrain_points[i - 1], self.__h - self.__terrain_points_levels[i - 1]),
                (self.__terrain_points[i], self.__h - self.__terrain_points_levels[i])
            )

    def __draw_game_over_text(self):
        """" Responsible for drawing game over text corresponding to game over state. """
        font = pg.font.Font('freesansbold.ttf', 32)

        game_over_text = None
        if self.__game_over_state == sstatecons.GameOverState.LOST:
            game_over_text = font.render("You've been squeezed!", True, RED, BLACK)
        elif self.__game_over_state == sstatecons.GameOverState.WON:
            game_over_text = font.render("You've sliced everyone!", True, GREEN, BLACK)
        elif self.__game_over_state == sstatecons.GameOverState.ALL_HUMAN_DIED:
            game_over_text = font.render("All humanoid fruits've been squeezed!", True, RED, BLACK)

        game_over_text_rect = game_over_text.get_rect()
        game_over_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.__screen.blit(game_over_text, game_over_text_rect)

    def __draw_t_to_exit_text(self):
        """" Responsible for drawing time to exit text when triggered and signaling Screen kill. """
        font = pg.font.Font('freesansbold.ttf', 32)
        t_to_exit_text = font.render(
            "Exit in " + str(self.__t_to_exit // FPS + 1) + " s",
            True,
            WHITE,
            BLACK
        )
        t_to_exit_text_rect = t_to_exit_text.get_rect()
        t_to_exit_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
        self.__screen.blit(t_to_exit_text, t_to_exit_text_rect)

        self.__t_to_exit -= 1  # decrease every frame by 1
        if self.__t_to_exit == 0:
            self.__running = False

    def __check_draw_if_cannot_attack_text(self, msgs):
        # msgs = Client.get_instance().get_targets_messages(sermess.Target.SCREEN)
        for msg in msgs:
            if msg.type == sermess.MessageType.ATTACK_ABILITY:
                if not msg.value:
                    self.__show_cannot_attack_text = True
                elif msg.value:
                    self.__show_cannot_attack_text = False
        if self.__show_cannot_attack_text:
            font = pg.font.Font('freesansbold.ttf', 24)

            game_over_text = font.render("You need some rest", True, RED, BLACK)
            game_over_text_rect = game_over_text.get_rect()
            game_over_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 8)
            self.__screen.blit(game_over_text, game_over_text_rect)

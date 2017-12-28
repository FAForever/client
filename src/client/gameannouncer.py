from chat.friendtracker import build_friends_tracker, FriendEvents
import time


class GameAnnouncer:

    def __init__(self, playerset, me, colors, client):
        self._me = me
        self._colors = colors
        self._client = client

        self._friends_event_tracker = build_friends_tracker(me, playerset)
        self._friends_event_tracker.friendEvent.connect(self._friend_event)

        self.announce_games = True
        self.announce_replays = True
        self._delayed_event_list = []
        self.delay_friend_events = True

    def _friend_event(self, player, event):
        if self.delay_friend_events:
            self._delayed_event_list.append((player, event))
        else:
            self._friend_announce(player, event)

    def delayed_friend_events(self, player):
        if not self.delay_friend_events:
            return
        if len(self._delayed_event_list) == 0:
            self.delay_friend_events = False
            return
        i = 0
        for event in self._delayed_event_list:
            if player in event:
                player, event = self._delayed_event_list.pop(i)
                self._friend_announce(player, event)
            i += 1

    def _friend_announce(self, player, event):
        if player.currentGame is None:
            return
        game = player.currentGame
        if event == FriendEvents.HOSTING_GAME:
            if not self.announce_games:  # Menu Option Chat
                return
            if game.featured_mod == "ladder1v1":
                activity = "started"
            else:
                activity = "is <font color='GoldenRod'>hosting</font>"
        elif event == FriendEvents.JOINED_GAME:
            if not self.announce_games:  # Menu Option Chat
                return
            if game.featured_mod == "ladder1v1":
                activity = "started"
            else:
                activity = "joined"
        elif event == FriendEvents.REPLAY_AVAILABLE:
            if not self.announce_replays:  # Menu Option Chat
                return
            activity = "is playing live"
        else:  # that shouldn't happen
            return

        if game.featured_mod == "faf":
            modname = ""
        else:
            modname = game.featured_mod + " "
        if game.featured_mod != "ladder1v1":
            player_info = " [{}/{}]".format(game.num_players, game.max_players)
        else:
            player_info = ""
        time_info = ""
        if game.has_live_replay:
            time_running = time.time() - game.launched_at
            if time_running > 6 * 60:  # already running games on client start
                time_format = '%M:%S' if time_running < 60 * 60 else '%H:%M:%S'
                time_info = " runs {}"\
                    .format(time.strftime(time_format, time.gmtime(time_running)))
        url_color = self._colors.getColor("url")
        url = game.url(player.id).toString()

        fmt = '{} {}<a style="color:{}" href="{}">{}</a> ' \
              '(on <font color="GoldenRod">{}</font> {}{})'
        msg = fmt.format(activity, modname, url_color, url, game.title,
                         game.mapdisplayname, player_info, time_info)
        self._client.forwardLocalBroadcast(player.login, msg)

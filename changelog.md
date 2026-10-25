0.x.x
=====

0.28.0
* Fix compatibility with server
* Update dependencies and GitHub actions
* Infer mapgen size from its name

0.27.4
* Fix compatibility with server

0.27.3
* Hotfix semantic versioning of map generators

0.27.2
* Allow multiple choices in some of mapgen options
* Allow switching mapgen versions
* Show clan tags in game panel
* Add 'Copy Link' action to online replays
* Update dependencies

0.27.1
* Fix displaying live replays prematurely
* Host widget: fix inconsistent filtering and mapgen names
* Update dependencies

0.27.0
* Make one Settings dialog instead of having them in context menus
* Implement map and mod upload
* Add managing installed maps and mods
* Highlight new maps in map list on generating many for hosting
* Add favourite maps for hosting functionality
* Enrich live replay tab
* Show max rating line in rating plots
* Fix not handling 'enemies' in replay's chat

0.26.3
* Add more filter options to vaults
* Fix broken notification sound playback
* Add ETFreeman unit database link
* Limit game title length to 128
* Improve QThreads handling
* Update dependencies

0.26.2
* [Windows] Workaround `Premature EOF` in live replays with an option to disable it
* Fix advanced search in replay vault
* Fix mod search not working in game host widget
* Chat:
  - Search chat content with Ctrl+F
  - Elide sender name so it fits in its column width
  - Hide empty chat topic
* Themes:
  - Read all colors from CSS
  - Add Dark Blue builtin theme
* Show map size in game panel if map is available
* Allow to open host game dialog while in game

0.26.1
* Fix breaking `game.prefs` file with no mods selected
* Fix parsing `[[]]` empty strings in lua files

0.26.0
* Highlight only mentioned nicknames instead of entire chat lines
* Display more detailed information in the status bar during
  game launch
* Fix inability to play replays from the live replays tab
* Allow users to configure how many pages of rating history are
  initially loaded in Playercard
* Improve network performance by reusing a single
  QNetworkAccessManager for API requests
* Improve application launch performance
  - Implement lazy loading for heavy modules
  - Load coop and vault widgets on demand
    + Fix slow initial opening of replay tab by configuring
      QTreeWidgetItem appearances on demand instead of all at once
  - Reuse QSoundEffect instances and defer their loading
* Reduce RAM usage
  - Refactor Playercard to use a common CachedImageDownloader
    for all league formatters
  - Load only requested images into memory in CachedImageDownloader

0.25.3
* Fix starting ladder games with 'unlisted' league score
* Reduce installation size
* Update JRE's Java from 21 to 25

0.25.2
* Fix joining custom games

0.25.1
* Require 3.14+
* Update pyqtgraph to 0.14.0
* Fix passing `/subdivision` when it is empty

0.25.0
* Features
  - Add matchmaker veto support
  - Allow watching replay alongside normal game
  - Mark watched replays
  - Add Game panel widget
  - Replaycard:
    + Add Events tab
    + Add search and basic recipient filters to chat tab
  - Allow to set custom maps/mods folder

* Improvements
  - Compress local replays with zstd
  - Connect to replay server with websocket
  - Create settings dialogs for cache and game settings
  - Show file size in map/mod details
  - Write game version and client version to `fa_path.lua`
  - Add visual indication of modded games in game list

* Updates
  - Migrate to Hydra2 Oauth2 client id
  - Update Zig to 0.15.2 and PyQt to 6.10.0

* Fixes
  - Fix matchmaker keyboard shortcuts
  - Fix ignoring cache settings

0.24.6
* Force connecting with IPv4 protocol when IPv6 is available, because IPv6 does not work
* Add ICE Adapter option to always force relay
* Load only 10 pages of rating history by default in player profile

0.24.5
* Adjust rating history plots to new API restrictions (see https://github.com/FAForever/faf-java-api/pull/1004):
  - avoid unhandled exceptions on closing profile dialog with unfinished API requests
  - load recent games first
  - show pagination progress
  - update graph on every page of data
  - add button to try more
* Pass `force-relay` option to ICE adapter based on API value (see https://github.com/FAForever/faf-icebreaker/pull/121)
   - add a client option to disable `force-relay` even if it is enabled in API
* Replaycard: deflate APM count by calculating it more accurately

0.24.4
* Fix exceptions in modvault when modname and modfolder differ

0.24.3
* Add `UNKNOWN_RESULT` to replay validity search options
* Fix not displaying installed maps in host widget

0.24.2
* Handle multline strings in lua files
* Fix displaying generated map icon in notifications and vaults

0.24.1
* Add separate 'Game Launched' notification for ladder
* Handle null clan descriptions
* Send `division` and `subdivision` as game arguments to ladder games
* Fix connecting game session's signals multiple times
* Fix 4v4 faction selection not working properly

0.24.0
* Support [faf-pioneer](https://github.com/faforever/faf-pioneer)].
  Add feature switch between `java-ice-adapter` nad `faf-pioneer`
  and allow to select specific tool versions.
  Also, don't include java ICE adapter into installer and download
  it separately as it is done with new `faf-pioneer`
* Don't duplicate chat history on reconnect
* Fix downloading avatars in chat
* Fix chatter tooltip
* Don't crash on non-existent map foder when trying to parse maps metadata
* Correctly handle map generator version on options extraction
* Remember selected environment (main, test) on login
* Log irc into a dediciated file

0.23.2
* Adapt client updater to .exe installer
* Temporary add dummy .msi file to trigger update notification in older client version

0.23.1
* Fix error on shutdown
* Fix active ladder search tab color
* Add "Game Launched" notification
* Show chat chennel's message history on join

0.23.0
* Features:
  - Rework HostGameWidget (maps/mods filters, add game rating enforcement option)
  - Add map count option to MapGenerator
  - Allow adding, editing, and removing map/mod comments
  - Add map foreground, command filters, and player selection to heatmap
  - Display clan information in player profiles
  - Add splash screen
  - Add log level controls with configurable file size and backup count
  - Add "Details" action to local replays

* Fixes:
  - Fix heatmap's math and debounce setting
  - Fix "friends only" host option
  - Fix UI mod manager's uselessness -- remember selected mods
  - Fix possible memory leak caused by playercard

* Other:
  - Upgrade to python3.13 and migrate installer to Inno Setup
  - Bump ICE Adapter to version 3.3.12 with proper GPG port handling
  - Unify checkbox stylesheets, remove gradients, update some icons
  - Mask userprofile in logs
  - Improve replay details tab performance and remove unnecessary OpenGL context sharing
  - Switch to scipy's gaussian filter for faster processing
  - Cache installed maps metadata

0.22.5
* Fix crash on choosing heatmap colormap

0.22.4
* Add replayparser to the client based on [LiveReplayServer](https://github.com/fafafaf/livereplayserver)
* Add zig library to parse replays faster
* Add age info to game items
* Add context menu to game items with ability to joing game/see large map preview
* Get mapgen options from generator itself (so they don't break/outdate with every mapgen update)
* Modernize vaults

0.22.3
* Allow user to create custom game filters
* Improve broken reconnection (hopefully fix)
* Fix broken QActions
* Fix crashes on player card early closing

0.22.2
* Freeze application for linux and ship it as tar.gz archive
* Fix dragging window near screen edges
* Download sim mods for replays
* Fix some notifications not being shown

0.22.1
* Hotfix OAuth

0.22.0
* Add player profile card
* Add access to player's context menu via replay scoreboard
* Allow to individually override notifications' "show ingame" rules
* Allow generating maps by name
* Fix incompatibility with new map generator options
* Fix NEW_GAME notification
* Fix alias viewer
* Update ice adapter to 3.3.9

0.21.0
=====
### Make it operational again
* Port the client to PyQt6 and python3.12

  Qt stopped providing 32-bit packages several years ago,
  therefore we have to move to 64-bit too.

  The previous port added QtWebEngine with the hope to eliminate
  it in the future, and the future has come. This port removes
  QtWebEngine and allows real web browsers to do their job.
  But unfortunately this change hasn't slimmed down the client,
  as previous maintainers had hoped, because java-ice-adapter
  has become about **11  times larger**, not to mention jre and Qt itself

* Fixes:
  - Fix constant reconnect while in game
  - Fix parsing Game.prefs file
  - Fix sim mod downloads for coop games
  - Fix updater not being able to download game files (#1133)
  - Fix notifications being shown over taskbar
  - Fix replay decompression
  - Fix ice adapter usage
  - Fix movies and sounds unpacking
  - Fix maximizing/resizing window
  - Fix updating MapGenerator
* Other:
  - Connect to lobby and chat with websockets
  - Move updater's work into its own thread and don't block UI
  - Finally use the UpdaterProgressDialog and give the user more
    information about what's going on
  - Restore coop leaderboards
  - Move from jsonschema to pydantic (also speeds up loading the replay tab)
  - Log in with browser
  - Add option to change application style
  - Fetch coop missions from API and don't rely on lobby server
  - Patch FA version by ourselves if the one in the downloaded file
    is incorrect

0.20.2
=====
* Fix updater

0.20.1
=====
* Fixes
   * Connect to chat faster
   * Fix throwing an exception in chat when someone renames
   * Fix map generator not being able to generate some maps
   * Fix pre-release being recognised as stable release
* Features
   * Add ability to set generator map size in 1.25km increments
   * Display technical names of matchmaker queues
* Other
   * Add support for game options in matchmaker queues
   * Update ICE adapter to v3.1.2

0.20.0
=====
 * Features:
    * Add advanced login parameters (#1096)
    * Add full game title to the game tooltip
    * Add leaderboards from API
    * Add map generator support
    * Add option to force switching to vault fallback location
    * Add teammatchmaking, basic party system
    * Allow to foe moderators
    * Disable ICE adapter info window by default
    * Exclude observers from game player count
    * Separate 'ignore' from 'add fore' option
 * Technical
    * Login with OAuth tokens
    * Use new server protocol
    * Replace hardcoded irclib with external library
    * Migrate to GitHub Actions
 * Fixes:
    * Fix broken map downloader
    * Fix diplaying news
    * Fix download cancellation in vaults
    * Fix icon sizes in vaults
    * Fix window flags (#867)
    * Remove some deprecations
    * Support zstandard compression in replay files

Contributors:
 - Askaholic
 - Strogo
 - Gatsik

0.19.0
=====
 * Fix broken compatibility with server
 * Fix basic searching in vaults
 * Implement somewhat of a cache system like in the Java client
 * Online replay vault: fix downloading replays

Contributors:
 - Gatsik

0.18.9
=====
 * Online vault: display player name as "No data" instead of throwing an error

Contributors:
 - Strogo

0.18.8
=====
 * News tab: disable automatic urls
 * News tab: add filtering

Contributors:
 - Strogo

0.18.7
=====
 * Fix units database
 * Add Spooky database as an alternative

Contributors:
 - Brutus5000
 - Strogo
 - Dragonite

0.18.6
=====
 * Show "unofficial client" message via notifications and only once per day.
 * Fetch featured mod info from API instead of lobby server

Contributors:
 - Askaholic
 - Strogo

0.18.5
=====
 * map vault fixes
 * fix featured_mod_versions server problem

Contributors:
 - Strogo

0.18.4
=====
 * Replay vault update for JSONAPI

Contributors:
 - Strogo
 - muellni

0.18.3
=====
 * ICE adapter debug window fixes

Contributors:
 - Geosearchef
 - muellni

0.18.2
=====
 * ICE adapter integration
 * Don't disable autorelogin after sending credentials
 * Fix 'connect'/'disconnect' naming

Contributors:
 - Wesmania
 - muellni

0.18.1
=====
 * Fix repeated opening of 'host game' widget filling mod selection with
   duplicate entries
 * Fix 'open config file' button opening the wrong directory on Windows
 * Update ladder map pool forum link

Contributors:
 - Wesmania
 - EvanGalea

0.18.0
=====
 * Refactor updater code. Although tested to work, let's still pray that it
   doesn't break everything!
 * Pick the right SupCom directory even if the user picked some subdirectory of
   it like 'bin'

 Contributors:
 - Wesmania

0.18.0-rc.5
=====
 * Prevent being able to foe or igore aeolus mods
 * Fix game names being accidentally HTML-escaped
 * Fix communication with nickserv sometimes breaking

 Contributors:
 - Wesmania

0.18.0-rc.4
=====
 * Fix wrong chat line colors in some rare cases
 * Fix client crash at some points during live game when connection to
   lobbyserver was lost

 Contributors:
 - Wesmania
 - muellni

0.18.0-rc.3
=====
 * Fix an uncaught exception when handling unknown IRC chatter mode
 * Log fatal errors like segmentation faults to crash.log

 Contributors:
 - Wesmania

0.18.0-rc.2
=====
 * Fix an issue with login dialog not starting
 * Add a caveat about themes to the exception dialog

 Contributors:
 - Wesmania

0.17.4
=====
 * Integrate client with new Rackover's database
 * Implement autojoining language channels
   - Currently supports #german, #french and #russian.
   - At first run, checks system UI language on Windows and LANG on unix. If no
     matching channel is found, uses user's geoIP.
   - Language channels to join configurable through settings.
 * Log qt messages to FAF client log, silence some noisier messages.
 * Re-add chat disconnect notifications.
 * Temporarily hide Tutorials and Tournaments tabs. We'll re-add them once
   they're in working state.
 * Add icons to chat tabs to indicate activity in the channel.
 * Restore private chat channels after reconnecting to chat.
 * Fix a bunch of chat and mod tool bugs.

 Contributors:
 - Wesmania
 - Giebmasse

0.17.3
=====
 * Fix all players being displayed as clannies if user is not in a clan (#1011)
 * Fix player count in chat ignoring leaving players
 * Restore copying text in chat area with Ctrl-C
 * Restore joining game / replay when doubleclicking player status
 * Fix several bugs in mod tools
 * Add a "copy username" entry to chatter menu
 * Allow to hide parts of chatter list interface:
   - Options -> chat -> hide chatter controls the hiding of UI items.

 Contributors:
 - Wesmania

0.17.2
=====
 * Rewrite chat from the ground up. No changes in functionality, but should fix
   plenty of chat mubs and make it easier to add new features.
 * Ctrl-C now quits the client when ran from console (#1001, #1008)
 * Add config file location entry to client menu.

 Contributors:
 - Wesmania

0.17.1
=====
 * Fix missing audio plugin causing sounds not to be played on Windows (#995)

 Contributors:
 - Wesmania

0.17.0
=====
 * Fix the error message "failed to get uid" which has bad spacing
 * Fix replay search map - automatic replacement of blanks with * (#955, #599)
 * Redirect some larger game messages to a separate logfile (#952)
 * Send logs from every game to a separate log file (#875, #975)
 * Refactor downloading previews to fix issues with broken previews (#852)
 * User's own messages can no longer ping him (#906)
 * Update "run from source" instructions for Linux (#980)
 * Standarize client data model classes (#981)

Contributors:
 - MathieuB8
 - Grothe
 - Wesmania

0.16.1
====

 * Fix rare race condition between avatar download and user leaving (#969, #970)

Contributors:
 - Wesmania

0.16.1-rc.3
====
 * Fix game sorting sometimes not matching saved settings at startup (#918, #919)
 * Fix players in chat sometimes not displayed with their clan tags (#922, #923)
 * Fix channel autojoin settings not loading properly
 * Don't show checked user's name among other alias users
 * Fix host and link in announcements in chat (#930, #934)
 * Fix '/me' message formatting for senders with no avatars (#936, #940)
 * Restore the 'quit' server message when a chatter quits chat (#937, #939)
 * Fix exception in the mod kick dialog (#941)
 * Fix race condition causing autojoining #newbie at random (#949, #950)
 * Hotfix race condition between downloading avatars and removing chatters (#957)
 * Don't proceed with game launch if FA path is invalid (#933, #959)
 * Hotfix an irclib exception popping up in some cases (#958)
 * Delay displaying of user's ladder game info until launch (#360, #912)
 * Use the more compatible ANGLE renderer by default (#963)

Contributors:
 - Wesmania
 - Grothe

0.16.1-rc.2
====
 * Introduce new object model:
   - Game, Player and IrcUser classes track corresponding info from the server,
     giving the client singular representations of online users, games and
     chatters
   - Most of the client using the above data converted to utilize new classes
   - Game and chat tabs converted from QListWidgets to QListViews based on a
     single model, ensuring proper game tracking, filtering and sorting
   - Many small refactors necessary to introduce the model
 * Pressing spacebar on games tab will no longer start ladder search (#860, #861)
 * Notification when a game is full
 * Added map preview icon in chat. Toggle in the chat settings. (#870, #891)
 * Add menu Link to ladder map pool in forum (#882)
 * Add host & live-game-delay to user status + nicer tooltip in Chat (#892)
 * Add a button to see the ladder maps pool from play tab (#882)
 * Add 'view in leaderboard' to chat user context menu (#893)
 * Add autojoin #newbie channel and the possibility to autojoin other channels (#899)
 * Restore 'view aliases' functionality as a quick fix (#883)
 * Gracefully handle invalid game sort option settings (#863, #915)

Contributors:
 - Wesmania
 - Grothe
 - Surtsan
 - IceDreamer
 - Mathieu

0.16.0
====

* Fix map names being displayed wrong in host window for a modded game (#786, #787)
* Fix and add observer in tooltip for hosted games (#711)
* Fix "in game" icons next to chatters not showing at client launch (#791, #792)
* Fix join hosted game from chat user (#796)
* Leftover Qt5 fixes
* Fix fa updater not cancelling download (#802, #803)
* Fix regression - map and mod previews not downloading correctly (#804, #805)
* Fix maps with spaces in them sometimes failing to download in vault (#771, #772)
* Rework client updater (#671, #672)
* Fixup rehosting throwing an exception (#828, #829)
* Fix mods selected in game host window not remembered properly (#840, #841)
* Add menu option: Show paths for themes (#844)

Contributors:
 - Wesmania
 - Grothe
 - Duke

0.15.1
====

* Slightly decrease dependency of tabs on client class (#644)
* Clean up theme-specific util code (#663, #664)
* Cleanup receiving game info (#708, #709)
* Add Friend/Foe feature for IRC users (#609, #657)
* Replace game quality in the play tab (NOT in the lobby) by average rating (#687, #688)
* Split replay widget to separate classes (#698, #699)
* Cleanup and unify map & mod download behaviour (#718, #719)
* Decouple update connection from updater (#701, #702)
* Check for null datagrams in TURN relay \_ready\_read (#769, #770)
* Fix showing file in explorer throwing an exception (#773, #779)
* Fix games not sorting immediately after adding a friend (#784, #785)

Contributors:
 - Wesmania

0.15.0
====

* Port the client to python3 and qt5 (#412, #474, #479, #509)

  Qt4 has not been supported for the last 2.5 years, so it was high time for
  us to move to Qt5. As PyQt5 only works with python3, this also prompted a
  move from python2 to python3.

  This port involved running the code through automated tools first, then
  fixing whatever errors were left. Because of that, even though we tested the
  client thoroughly, some leftovers might have slipped through and remain to be
  caught and fixed.

  Apart from the conversion work, the port makes some additional changes,
  mostly needed for the port to work correctly:

  * Add a setting to log to console (default true for development environment)
  * Remove the SSL disable workaround for the test server
  * Use QtWebEngine instead of QtWebkit
  * Switch from miniconda back to python
  * Move to cx\_freeze 5
  * Move travis build to Trusty

  Of these the switch to QtWebEngine is the most significant, as it adds around
  20 megabytes to the installer. We hope to eventually eliminate the need to
  use a web browser in the client in the future, as well as get rid of some
  unneeded Qt libraries to further slim down the client.

Contributors:
  - Wesmania
  - muellni
  - Grothe

0.13.2
====

* Actually merge the versioning code

Contributers:
  - Wesmania

0.13.1
====

* Remove dependency on faftools (#756, #757)
* Remove many unused client dependencies (#566, 759)
* Clean up usage of directory paths (#571)
* Rework versioning code (#615, #753, #765)
* Check if game connection is null before using it (#764, #765)

Contributors:
  - Wesmania

0.13.0
=====

* Update uid to 4.0.4
* (Admin Menu) Check for valid user before kicking

Contributors:
  - Duke

0.12.6
=====

* Single-Line Mod-Vault toolbar (#730)
* Pin UID version in appveyor
* Log errors from faf-uid executable (#741, #742)
* Add menu option: Show paths for maps, mods & replays (#735)
* Slightly clean up client resize logic (#747, #748)
* Don't autoreconnect when sent invalid command to server (#743, #744)
* Don't modify env in order to launch faf-uid.exe (#736, #750)

Contributors:
  - Grothe
  - Wesmania

0.12.5
=====

* Significantly refactor connection to lobby server (#620, #621)
* Remove redundant APPDATA_DIR loading in util (#665, #666)
* Fix theme breakage caused by a promoted widget (#669, #670)
* Fix random/nomads faction shown in replay info (#676)
* Fix lobby name change not showing in Play (#690)
* Add sorting games By Map, Host and Age to Play (#686)
* Fix set mod to 'All' from chat user 'View Replays in Vault' (#695)
* Mod dropdown-list in Replays show all mods (no scrolling) (#696)
* Recognise `nosuchnick` irc server message
* Purge last remains of (long removed) mumble integration (#681, #682)
* Don't use eval in legacy updater (#715, #716)
* Fix crash on opening files in explorer on non-Windows (#654, #655)
* Clean up layout of login widget (#652, #653)
* Use "foo" instead of user password in develop mode (#712, #653)
* Remove unused label from GamesWidget (#717)
* Fix for user in chat shown in long gone games (#705)
* Fix some unicode handling problems (#689,  #721)
* Rework autologin logic to fix loops at login error (#720, #722)
* Allow the user to stay offline instead of logging in (#727, #728)
* Improve administrator menu (#726)

Contributors:
  - Wesmania
  - Grothe
  - Duke

0.12.4
=====

* Fix irc/notification recursion loop (#638, 641)
* Fix movie file crc calculations (#640, #642)
* Make Github updater see prereleases (#643, #645)
* Fix null byte being logged by replay code (#648, #649)
* Fix IRC nick renames (#625, #650)

Contributors:
  - Duke
  - Wesmania

0.12.3
=====

* Add feature to disable / delay client notifications while ingame (#627 / #628
* Point other links to the new website (#636)
* Point account-related links to the new website (#631/#633)
* Replace account creation wizard with link to FAF 'create account' page (#577 / #635)
* Fix typo preventing rehost feature from working (#630 / #632)
* Remove needless abstract base class for client (#629)
* Fall back to APPDATA if Documents folder cannot be created (#619, #626)
* Make all (themed) stylesheets reloadable (#584)
* Add option to always load outdated themes in given version of FA (#583 / #634)

Contributors:
  - Duke
  - speed2
  - Wesmania
  - yorick

0.12.2
======

* Make sure client updater progress is shown (#605)
* Check for updates on Github (#578)
* fix usability of 'Live Games' in Replays (#615)
* Fix live replay sorting (#616)
* Unpack movies from mod packages (#610)
* Render "what's new" directly in client from WP-API (#533, #603)
* Fix updater displaying update dialog twice (#612)

Contributors:
 - Duke
 - Grothe
 - Wesmania

0.12.1
======

* Verson bump for updater

0.12.0
=======

* Make it possible to choose subset of factions in ladder
* Re-enable notification of game events
* Update UI in the Replayvault
    - Split generateInfoPlayersHtml into different methods
    - Moved HTML as much as possible to the top and in constants
    - Added free-for-all in the extra information of the replay
    - Removed observers from the extra information of the replay
    - Removed after rating from extra information of the replay (in code)
* Added option to sort nicknames with friends on top.
* Multiple mods are now downloaded if required
* Fixed sorting bug with the player list
* Add linux support (thanks @muellni and @wesmania)
* Add new uid implementation (thanks @muellni)
* Leaderboard display performance improvement (#438, thanks @grotheFAF)
* Save game logs as default
* Fix a bug with preview generation (#481)
* Remove unused map downloader class (#483)
* Fix error in PERSONAL_DIR selection (#428)
* Make map preview download asynchronous (#507)
* Fix duration for live games in Replays (#497, thank @grotheFAF)
* Fix file permissions (#521, thanks @muellni)
* Check for WMI service needed by uid (#523, thanks @muellni)
* Build improvements (#531)
* Fix What's New Tab displaying correct page (thanks @downlord)
* replace Tab Livestreams with (old) Unit Database (#539)
* Add logging to game updater and disable cert verification on test server (#558)
* Clean up 'res' directory finding (#552)
* Improve ladder race selection (#554)
* Make selected mods persistent (#560)
* Disable modvault feedback (#568)
* Fix local replays being shown as broken when offline (#564)
* Update 'Search Options' in Replays (#498)
    - Load recent replays list only on first entry
    - Add Button 'Refresh Recent List'/'Reset Search to Recent'
    - Add Checkbox to enable Automatic Refresh (old behavior)
    - Add Label 'Searching...' while waiting for server
    - Change 'Min rating' steps to 100
* Fix 'View Replays in Vault' change to 'Online Vault' Tab (#495)
* Make announcements less annoying (#575, thanks @HardlySoftly!)

Contributors:
 - Downlord
 - Softly
 - Sheeo
 - Duke
 - Grothe
 - Muellni
 - Wesmania

0.11.64
=======

Hotfix release

0.11.60
=======

- Uncheck 'remember me' if sign in failed
- Fix autodownload of sim mods
- Add options to skip dialogs for autodownload of maps/mods
- Fix crash when rightclicking in the replayvault
- Fix 'spoiler free' option in replay vault not working
- Fix hosting of coop missions (Requires server updates, TBA)
- Fix chatlist sometimes not getting populated with additional player information
- Add support for 'rehost' functionality (Will be enabled by upcoming gamepatch)

Contributors:
 - HaraldWeber
 - TimWolters
 - Yorick
 - Downlord
 - Softly
 - Sheeo

0.11.58
=======

- Show a warning if the required C++ 2010 runtime is missing
- Default IRC to port 6667 without the use of TLS (Standard IRC behavior)


0.11.57
=======

- Fix another problem that would cause IRC to disconnect randomly (And show an error popup)

0.11.55
=======

- Fix a problem that would cause IRC to disconnect randomly
  - Fix an automated bug report popping up if above happened

0.11.54
=======

- Fix an issue that could block connections in certain circumstances
- Remove "connecting to statistics server popup" that would block normal operation of the client
- Make chat a whole lot faster
- Persist the 'Hide private games' checkbox

Contributors:

 - TimWolters


0.11.53
=======

- Sword icons now disappear again as players leave games and lobbies
- Added /msg <target> command for chat
- Fix an issue with registering on IRC
- Fix map previews not downloading properly
- Fix unicode characters in chatmessage URL's causing an exception
- Make logs not grow out of proportion

0.11.52
=======

- Mitigate an issue for certain players that could cause disconnects during longer teamgames

0.11.51
=======

- Add 'view aliases' option to chat user list
- Fix updating of featured mods
- Fix resetting of game file permissions on non-windows systems


Contributors
------------

- Softly
- Sheeo

0.11.50
=======

- Fix an issue with users who have ' in their game path
- Renamed "Find Games" to "Play"
- Fix links to forum and unit database
- Fix map vault when using the client in development mode
- Allow replays to be launched from anywhere again (Make sure the client executable is associated with .fafreplay)
- Fix an issue that causes the client to never quit when searching the mod vault / connecting to statistics server

Contributors
------------

- Blackclaws
- Speed2
- Sheeo
- Yorick

0.11.0
======

Enhancements
------------

- The client will automatically reconnect when it loses connection to the server
- Connection status popups have been replaced with a status logo (top left).
  Right click the logo to disconnect / reconnect from the server manually.
- The featured mods list has received a visual facelift (Icons thanks to Exotic_Retard)

Bugfixes
--------

- Fixed colouring problem with certain names
- Automatic login will now get disabled if login fails
- Fixed exceptions popping up related to corrupted replays
- Logs will no longer fill to unreasonable sizes
- Many other small issues fixed


Contributors
------------

- Ckitching
- Downlord
- DragonFire
- Eximius
- IceDreamer
- Sheeo
- Softly
- Thygrr

0.10.123 (July 27, 2015)
========

Bugfixes
--------

- Map previews for undownloaded maps work again

Enhancements
------------

- Ability to sort active games by number of players / game quality and average rating
- Ability to hide private games
- Games will launch slightly faster

Contributors
------------

- HaraldWeber
- Dragonfire
- Sheeo

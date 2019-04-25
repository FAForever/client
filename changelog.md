0.x.x
=====

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

0.11.54
=======

- Fix an issue that could block connections in certain circumstances
- Remove "connecting to statistics server popup" that would block normal operation of the client


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

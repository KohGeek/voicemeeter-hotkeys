# Voicemeeter Hotkeys App

A simple app made in Python to control Voicemeeter with hotkeys via the [Voicemeeter Remote API](https://download.vb-audio.com/Download_CABLE/VoicemeeterRemoteAPI.pdf).

Attribution to [Fajar Annaba](https://www.behance.net/fajarannaba28/projects) for his logos. I can't find your contacts but if you want me to pull it down or discuss usage, let me know.

This app only works with **Voicemeeter Potato**! Other versions may be supported in the future.

## Usage

### Recommended

Download the latest release and just run the .exe file in adminstrator mode.

### Through .py file

1. Clone this repository.
2. Install the dependencies with `pip install -r requirements.txt`.
3. Run the app with `python .\hotkeys.py`.

## Features

- Mute/Unmute B1 Channel: `Win` + `Shift` + `Num 0`
- Restart audio engine: `Win` + `Shift` + `Pause`
- Unintrusive overlay to show current status
- Tray icon for easier management

## FAQ

### Why not VB Macro Buttons?

Macro Buttons does not support custom keybind beyond the list that is provided. If you play ARMA or use Blender, you'll know why this is a problem.

### Where can I submit feedback/feature requests/bug reports?

Submit them through the issues tab, or contact me directly via Discord.

## Issues

### Hotkeys no longer works after locking computer

> Reported bug under the [keyboard modules #595](https://github.com/boppreh/keyboard/issues/595)

Assign to task scheduler to restart every time unlock happens.

### Hotkeys does not work in some games/apps

> Some apps maybe blocking the hotkeys due to running at higher privileges

Run the app as administrator, and make sure task scheduler is set to `Run with highest privileges`. If there is security concern, then try to make sure the app is not in admin mode.

### Hotkey does not differentiate between normal 0 and numpad 0

> Known problem with the keyboard module

No solution currently. If this is an issue, please report them through the issues tab.

## Developers

### Building

Make sure you are in the correct python environment, then run `pyinstaller.ps1` with the following command:

```powershell
& .\pyinstaller.ps1
```

The output of the build will be in the `dist` folder.

### Todo

#### Feature Wishlist

- [ ] Add a way to change the hotkeys, preferably through settings file
- [ ] Allow changing the mute target
- [ ] Allow specifying which corner the overlay shows up
- [ ] Allow media control
- [ ] Allow controlling individual apps/channels
- [ ] Allow the app to work with other versions of Voicemeeter (Banana, etc.)

#### Improvements

- [ ] Document the code better
- [ ] Refactor classes into different files
- [ ] Remove Pillow from the dependencies

#### Bugs

- [ ] Fix the issue with numpad differentiation
- [x] Fix the issue with hotkeys breaking after locking and unlocking the computer

# CS2 stretched on a 24" screen (black bars on a bigger monitor)

Play CS2 stretched (4:3, 1280x960) on a **24 inch** sized area of your **27", 32" or ultrawide** monitor, with black bars around it. Like having a 24" esports monitor again.

![screenshot](docs/gui.png)

## Download

**[Download the latest version](https://github.com/gogasaldadze/monitor-internal-resize/releases/latest)** and unzip it anywhere.

You also need [Python](https://www.python.org/downloads/) (free). When installing it, tick **"Add Python to PATH"**.

## How to use

1. Double click **`CS2 24-inch.bat`**
2. Check the settings in the window (see below)
3. Click **START**

The screen shrinks to 24" and CS2 opens. When you quit CS2, your screen goes back to normal by itself.

### Settings

| Setting | What to put |
|---|---|
| Play size | The screen size you want to play on. `24` or `24.5` |
| Stretched resolution | The resolution you use in CS2. `1280x960` for most people |
| Your monitor | Your real monitor size in inches, like `27` or `26.5` |

### CS2 video settings

* Aspect ratio: **4:3**
* Resolution: **same as in the app** (1280x960)
* Display mode: **Fullscreen Windowed** (works best)

Using normal Fullscreen? It works too, but set the refresh rate to your monitor's exact value (for example 239.97 Hz, not 240 Hz).

## Turning it off

It turns off by itself when you close CS2. You can also:

* Click **STOP**
* Close the window
* Screen stuck? Click **"Restore normal screen"** in the app, or double click `normal-screen.bat`, or restart your PC

## FAQ

**Does it work on my monitor?**
Any size and resolution should work. Tested on an RTX 5080 with a 26.5" 1440p monitor.

**Is it safe with VAC?**
It doesn't touch the game. It only changes Windows display settings, like changing your resolution.

**Input lag?**
The scaling is done by your graphics card, the same as GPU scaling in NVIDIA or AMD settings.

**Other games?**
Uncheck "Launch CS2 on START". Works in games running in borderless or windowed fullscreen. Click STOP when done.

<details>
<summary>How it works / command line</summary>

It uses the Windows display API (`SetDisplayConfig`) to scale the desktop into a smaller rectangle in the middle of the screen. The monitor keeps its native resolution and refresh rate. Nothing is saved permanently.

```
python cs2_24inch.py run --panel 26.5    turn on, start CS2, turn off when it closes
python cs2_24inch.py on --panel 26.5     turn on
python cs2_24inch.py off                 turn off
python cs2_24inch.py info                show monitor info
```

Options: `--size`, `--res`, `--panel`, `--monitor`. Log is saved to `cs2_24inch.log`.

| Monitor | 24" area |
|---|---|
| 27" 2560x1440 | 2274x1280 |
| 27" 1920x1080 | 1706x960 |
| 32" 3840x2160 | 2878x1618 |
| 34" 3440x1440 ultrawide | 2294x1290 |

</details>

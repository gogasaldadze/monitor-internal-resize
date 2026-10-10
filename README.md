# cs2-24inch

Play CS2 stretched (1280x960 or whatever you use) on a 24" sized area of a bigger monitor, with black bars around it. Click START, it shrinks the screen and opens CS2. Quit CS2 and your normal desktop comes back.

![screenshot](docs/gui.png)

I made this because I moved to a 26.5" monitor and missed playing on 24". NVIDIA's desktop resize can do something similar but it applies to everything and you have to switch it on and off by hand.

## How it works

It uses the Windows display API (`SetDisplayConfig`) to scale the desktop into a smaller rectangle in the middle of the screen. The monitor stays at its native resolution and refresh rate. Nothing gets saved, so if anything goes wrong a reboot puts everything back.

## Setup

1. Install [Python](https://www.python.org/downloads/) (3.8 or newer, nothing else needed)
2. Download this repo
3. Double click `CS2 24-inch.bat`

In the window:

* **Play size** is the screen size you want to play on (24, 24.5, 25...)
* **Stretched resolution** should match what you use in CS2
* **Your monitor** is read from the monitor automatically, but it's rounded to whole cm so type in the real size if it's off

## CS2 settings

Aspect ratio 4:3 and the same resolution as in the app.

Fullscreen Windowed works best. Normal Fullscreen works too. CS2 resets the layout when it goes fullscreen and the app turns it back on right after. If you use Fullscreen, pick your monitor's exact refresh rate (for example 239.97 instead of 240), otherwise CS2 might switch the monitor to a lower resolution.

## Other monitors

Should work on any size. The area is always 16:9, so it looks like a real 24" monitor even on an ultrawide.

| Monitor | 24" area |
|---|---|
| 26.5" 2560x1440 | 2318x1304 |
| 27" 2560x1440 | 2274x1280 |
| 27" 1920x1080 | 1706x960 |
| 32" 3840x2160 | 2878x1618 |
| 32" 2560x1440 | 1920x1080 |
| 34" 3440x1440 | 2294x1290 |

Tested on an RTX 5080 with an ASUS XG27AQDMES. Let me know if it works on AMD/Intel.

## Command line

```
python cs2_24inch.py run --panel 26.5
python cs2_24inch.py test --panel 26.5
python cs2_24inch.py on --panel 26.5
python cs2_24inch.py off
python cs2_24inch.py info
```

Options: `--size`, `--res`, `--panel`, `--monitor`. Log goes to `cs2_24inch.log`.

## Screen stuck?

Click "Restore normal screen" in the app, run `normal-screen.bat`, or reboot.

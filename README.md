# CS2 stretched on a 24" screen (black bars on a bigger monitor)

Play CS2 stretched (1280x960, 1280x1024, 1440x1080...) on a 24 inch sized area of a bigger monitor, with black bars around it. Made for people who moved to a 27", 32" or ultrawide monitor but still want the 24" feel they're used to in Counter-Strike.

Click START, the screen shrinks to 24" and CS2 opens. Quit CS2 and your normal desktop comes back.

![screenshot](docs/gui.png)

**[Download](https://github.com/gogasaldadze/monitor-internal-resize/releases/latest)**

I made this because I moved to a 26.5" monitor and missed playing on 24". NVIDIA's desktop resize can do something similar but it applies to everything and you have to switch it on and off by hand.

## How it works

It uses the Windows display API (`SetDisplayConfig`) to scale the desktop into a smaller rectangle in the middle of the screen. The monitor stays at its native resolution and refresh rate. Nothing gets saved, so if anything goes wrong a reboot puts everything back. No driver hacks, no registry edits, no NVIDIA Control Panel.

## Setup

1. Install [Python](https://www.python.org/downloads/) (3.8 or newer, nothing else needed)
2. [Download](https://github.com/gogasaldadze/monitor-internal-resize/releases/latest) and unzip
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

## FAQ

**Can I play CS2 on a 24 inch size on my 27 inch monitor?**
Yes, that's what this does. Set play size to 24 (or 24.5 like most tournament monitors) and your monitor size to 27.

**Does it work with 4:3 stretched?**
Yes. The 4:3 image is stretched to fill the 16:9 24" area, same as stretched on a real 24" monitor.

**Can I use it without stretching, like 4:3 black bars or native 16:9?**
Set the resolution to a 16:9 one like 1920x1080 for a smaller native looking screen. The picture is always scaled to fill the area.

**Does it add input lag?**
The GPU does the scaling, same as GPU scaling in the NVIDIA or AMD control panel.

**Is it safe with VAC?**
It doesn't touch the game files or memory. It only changes Windows display settings, the same kind of thing as changing your resolution in Windows.

**Does it work for other games?**
Uncheck "Launch CS2 on START" and it works in other games too (Valorant, Apex, Fortnite...) as long as they run in borderless or windowed fullscreen. Press STOP when you're done.

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

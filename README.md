# Cursor Ninja

*[Українською](README.uk.md)*

Fruit Ninja on your desktop — the mouse cursor is the blade. Swipe the mouse
quickly through a fruit to slice it. Better leave the bombs alone.

![Windows](https://img.shields.io/badge/Windows-10%2F11-0078d4)
![Python](https://img.shields.io/badge/Python-3-3776ab)
![Dependencies](https://img.shields.io/badge/dependencies-none-2ecc71)

## Two versions

| File | What it is | When to use it |
|---|---|---|
| `cursor_ninja.py` | a transparent overlay on top of **all** windows on screen | to play yourself: slice fruit anywhere on the desktop |
| `cursor_ninja_bg.py` | a regular window with a drawn night-sky background | for building an `.exe` to send to a friend — this is the one built into the release |

The game logic is identical in both — the only difference is whether the
game occupies the whole screen as a transparent layer, or lives in a
regular window.

## How to play

- **Swipe the mouse** quickly through the fruit — that's the slice.
- **Leave the bomb 💣 alone** — it costs you a life, same as a missed fruit.
- Several slices in a row make a **combo**, worth more points.
- `R` or `Enter` — restart after losing.
- `Esc` — quit.

## Running it

A ready-made `.exe` is on the [Releases](../../releases) page. Nothing to
install, just run it.

> Windows may show "Windows protected your PC" — the file isn't signed
> with a paid certificate. "More info" → "Run anyway".

From source:

```
python cursor_ninja_bg.py      # windowed
python cursor_ninja.py         # overlay on top of all windows
```

Needs only Python 3 on Windows. No third-party libraries — `tkinter`,
`ctypes`, `random`, `math`, `time` are all in the standard library.

## Building it yourself

```
pyinstaller CursorNinja.spec
```

## Why Windows

`ctypes.windll.user32` (reading cursor position and keys) is WinAPI,
Windows-only. The game itself, built on `tkinter`, is cross-platform.

# tetris-microbit

A Tetris game in MicroPython for micro:bit V2, featuring all 7 Tetromino types,
the classic Korobeiniki theme, gyro controls, and row-clear animations.

## Requirements

- micro:bit V2
- Python 3 with [uflash](https://github.com/ntoll/uflash) installed

```
pip install uflash
```

## Installation

Flash `tetris.py` directly to the micro:bit:

```
uflash tetris.py
```

The game starts automatically after flashing.

## Controls

| Input | Action |
|-------|--------|
| Tilt left / right | Move piece left / right |
| Tilt forward (toward you) | Fast-drop (piece falls faster) |
| Button A | Rotate piece counterclockwise |
| Button B | Rotate piece clockwise |

## Gameplay

- All 7 Tetromino types: I, O, T, S, Z, J, L
- Pieces spawn mostly off the top of the 5×5 screen and fall into view
- Completing a row flashes the display and plays a sound effect
- The Korobeiniki melody (Tetris theme) plays continuously in the background
- When the board fills up: game-over sound, bricks animate up from the bottom,
  then the game restarts automatically

## Running Tests

Tests run on standard Python 3 (no micro:bit hardware needed — hardware APIs
are stubbed out):

```
python3 test_tetris.py
```

All 55 tests should pass.

## Files

| File | Description |
|------|-------------|
| `tetris.py` | Complete game — the only file needed on the micro:bit |
| `test_tetris.py` | Host-side unit tests with micro:bit stubs |

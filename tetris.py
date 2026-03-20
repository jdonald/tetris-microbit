# tetris.py - Tetris for micro:bit V2
# Single file for uflash upload.
# Controls:
#   Tilt left/right -> move piece left/right
#   Tilt forward -> move piece down faster
#   Button A -> rotate counterclockwise
#   Button B -> rotate clockwise
# When a row is completed: flash effect + sound.
# Game over: sound + brick animation, then restart.

import microbit
import music
import utime
import random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLS = 5
ROWS = 5

# Speeds (ms per gravity tick)
SPEED_NORMAL = 800
SPEED_FAST = 150

# Gyro thresholds (milli-g)
TILT_THRESHOLD = 200

# ---------------------------------------------------------------------------
# Tetromino definitions
# Each piece: list of (row, col) offsets from pivot (0,0), for rotation 0.
# We store all 4 rotations pre-computed.
# ---------------------------------------------------------------------------

def _rotate_cw(cells):
    """Rotate list of (r,c) offsets 90 degrees clockwise."""
    return [(c, -r) for r, c in cells]

def _rotate_ccw(cells):
    """Rotate list of (r,c) offsets 90 degrees counterclockwise."""
    return [(-c, r) for r, c in cells]

def _all_rotations(cells):
    rots = [cells]
    for _ in range(3):
        cells = _rotate_cw(cells)
        rots.append(cells)
    return rots

# Canonical cell offsets (row, col) for each piece at rotation 0
_PIECES_BASE = {
    'I': [(-1, 0), (0, 0), (1, 0), (2, 0)],
    'O': [(0, 0), (0, 1), (1, 0), (1, 1)],
    'T': [(0, -1), (0, 0), (0, 1), (1, 0)],
    'S': [(0, 0), (0, 1), (1, -1), (1, 0)],
    'Z': [(0, -1), (0, 0), (1, 0), (1, 1)],
    'J': [(0, -1), (1, -1), (1, 0), (1, 1)],
    'L': [(0, 1), (1, -1), (1, 0), (1, 1)],
}

PIECES = {name: _all_rotations(cells) for name, cells in _PIECES_BASE.items()}
PIECE_NAMES = list(PIECES.keys())

# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

class Board:
    """5x5 playing field. Row 0 = top, Row 4 = bottom."""
    def __init__(self):
        self.grid = [[0] * COLS for _ in range(ROWS)]

    def is_valid(self, cells):
        """Return True if all cells are in bounds and unoccupied."""
        for r, c in cells:
            if c < 0 or c >= COLS or r >= ROWS:
                return False
            if r >= 0 and self.grid[r][c]:
                return False
        return True

    def lock(self, cells):
        """Write cells to the grid."""
        for r, c in cells:
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.grid[r][c] = 1

    def clear_rows(self):
        """Remove full rows, return count cleared."""
        new_grid = [row for row in self.grid if not all(row)]
        cleared = ROWS - len(new_grid)
        for _ in range(cleared):
            new_grid.insert(0, [0] * COLS)
        self.grid = new_grid
        return cleared

    def is_full_row(self, r):
        return all(self.grid[r])

    def full_rows(self):
        return [r for r in range(ROWS) if self.is_full_row(r)]

# ---------------------------------------------------------------------------
# Piece
# ---------------------------------------------------------------------------

class Piece:
    """Active falling piece."""
    def __init__(self, name):
        self.name = name
        self.rot = 0
        # Start mostly off-screen: pivot row = -1 so piece enters from top
        self.row = -2
        self.col = COLS // 2

    def cells(self):
        offsets = PIECES[self.name][self.rot]
        return [(self.row + dr, self.col + dc) for dr, dc in offsets]

    def rotated(self, direction):
        """Return cells for next rotation. direction: +1 cw, -1 ccw."""
        rot = (self.rot + direction) % 4
        offsets = PIECES[self.name][rot]
        return [(self.row + dr, self.col + dc) for dr, dc in offsets]

# ---------------------------------------------------------------------------
# Korobeiniki (Tetris Theme) - simplified melody
# Each tuple: (note_string, duration_ticks)
# music.play uses note strings like 'C4:4'
# ---------------------------------------------------------------------------

THEME = [
    'E5:4', 'B4:2', 'C5:2', 'D5:4', 'C5:2', 'B4:2',
    'A4:4', 'A4:2', 'C5:2', 'E5:4', 'D5:2', 'C5:2',
    'B4:6', 'C5:2', 'D5:4', 'E5:4',
    'C5:4', 'A4:4', 'A4:8',
    'R:2', 'D5:4', 'F5:2', 'A5:4', 'G5:2', 'F5:2',
    'E5:6', 'C5:2', 'E5:4', 'D5:2', 'C5:2',
    'B4:4', 'B4:2', 'C5:2', 'D5:4', 'E5:4',
    'C5:4', 'A4:4', 'A4:8',
]

# ---------------------------------------------------------------------------
# Sound effects
# ---------------------------------------------------------------------------

def sfx_clear():
    """Play a short ascending arpeggio for row clear."""
    music.play(['C5:1', 'E5:1', 'G5:1', 'C6:2'], wait=True)

def sfx_game_over():
    """Descending tones for game over."""
    music.play(['G4:2', 'E4:2', 'C4:4'], wait=True)

def sfx_lock():
    """Soft click when piece locks."""
    music.pitch(200, 30)

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def render(board, piece):
    """Render board + active piece to micro:bit display."""
    img = microbit.Image(5, 5)
    # Draw board
    for r in range(ROWS):
        for c in range(COLS):
            if board.grid[r][c]:
                img.set_pixel(c, r, 9)
    # Draw piece
    for r, c in piece.cells():
        if 0 <= r < ROWS and 0 <= c < COLS:
            img.set_pixel(c, r, 9)
    microbit.display.show(img)

def flash_rows(board, rows):
    """Flash completed rows three times."""
    for _ in range(3):
        img_on = microbit.Image(5, 5)
        img_off = microbit.Image(5, 5)
        for r in range(ROWS):
            for c in range(COLS):
                if board.grid[r][c]:
                    img_off.set_pixel(c, r, 9)
                if r in rows:
                    img_on.set_pixel(c, r, 9)
                elif board.grid[r][c]:
                    img_on.set_pixel(c, r, 9)
        microbit.display.show(img_on)
        utime.sleep_ms(100)
        microbit.display.show(img_off)
        utime.sleep_ms(100)

def game_over_animation():
    """Animate bricks filling from bottom, then clear."""
    for r in range(ROWS - 1, -1, -1):
        img = microbit.Image(5, 5)
        for rr in range(r, ROWS):
            for c in range(COLS):
                img.set_pixel(c, rr, 9)
        microbit.display.show(img)
        utime.sleep_ms(80)
    utime.sleep_ms(400)
    microbit.display.clear()

# ---------------------------------------------------------------------------
# Music player (non-blocking tick)
# ---------------------------------------------------------------------------

class MusicPlayer:
    """Plays a looping melody one note at a time via tick()."""
    # ticks_per_beat: how many game ticks per music beat unit
    # We'll call tick() ~every 100ms from main loop
    MS_PER_BEAT = 200  # 1 beat unit = 200ms

    def __init__(self, melody):
        self.melody = melody
        self.idx = 0
        self._next_ms = 0

    def tick(self):
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._next_ms) < 0:
            return
        note_str = self.melody[self.idx]
        self.idx = (self.idx + 1) % len(self.melody)
        # Parse 'NOTE:DUR' or 'R:DUR'
        parts = note_str.split(':')
        note = parts[0]
        dur = int(parts[1]) if len(parts) > 1 else 4
        duration_ms = dur * self.MS_PER_BEAT
        if note == 'R':
            pass  # rest
        else:
            # Extract frequency from note name
            freq = _note_to_freq(note)
            if freq:
                music.pitch(freq, int(duration_ms * 0.85), wait=False)
        self._next_ms = utime.ticks_add(now, duration_ms)

# Note -> frequency mapping (A4 = 440 Hz, equal temperament)
_NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def _note_to_freq(note_str):
    """Convert note string like 'E5' to frequency in Hz."""
    try:
        if len(note_str) == 2:
            name, octave = note_str[0], int(note_str[1])
            semitone_offset = 0
        elif len(note_str) == 3:
            name, sharp, octave = note_str[0], note_str[1], int(note_str[2])
            semitone_offset = 1 if sharp == '#' else -1
            name = name  # flat not used here
        else:
            return None
        idx = _NOTE_NAMES.index(name) + semitone_offset
        # MIDI note: C4 = 60
        midi = (octave + 1) * 12 + idx
        freq = int(440 * (2 ** ((midi - 69) / 12.0)))
        return freq
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class Input:
    """Debounced gyro and button input."""
    MOVE_COOLDOWN_MS = 200
    ROT_COOLDOWN_MS = 300

    def __init__(self):
        self._last_move = 0
        self._last_rot = 0

    def get_move(self):
        """Return -1 (left), +1 (right), 0 (none) based on tilt."""
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_move) < self.MOVE_COOLDOWN_MS:
            return 0
        x = microbit.accelerometer.get_x()
        if x < -TILT_THRESHOLD:
            self._last_move = now
            return -1
        if x > TILT_THRESHOLD:
            self._last_move = now
            return 1
        return 0

    def is_fast(self):
        """Return True if tilted forward (piece drops faster)."""
        y = microbit.accelerometer.get_y()
        return y < -TILT_THRESHOLD

    def get_rotation(self):
        """Return -1 (ccw, button A), +1 (cw, button B), 0 (none)."""
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_rot) < self.ROT_COOLDOWN_MS:
            return 0
        if microbit.button_a.was_pressed():
            self._last_rot = now
            return -1
        if microbit.button_b.was_pressed():
            self._last_rot = now
            return 1
        return 0

# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        self.board = Board()
        self.piece = self._new_piece()
        self.player = MusicPlayer(THEME)
        self.inp = Input()
        self._last_gravity = utime.ticks_ms()

    def _new_piece(self):
        return Piece(random.choice(PIECE_NAMES))

    def _try_move(self, dr, dc):
        """Attempt to move piece by (dr, dc). Return True if success."""
        p = self.piece
        new_cells = [(r + dr, c + dc) for r, c in p.cells()]
        if self.board.is_valid(new_cells):
            p.row += dr
            p.col += dc
            return True
        return False

    def _try_rotate(self, direction):
        """Attempt rotation with simple wall kick."""
        new_cells = self.piece.rotated(direction)
        if self.board.is_valid(new_cells):
            self.piece.rot = (self.piece.rot + direction) % 4
            return
        # Try wall kicks: shift left/right by 1
        for dc in (-1, 1):
            kicked = [(r, c + dc) for r, c in new_cells]
            if self.board.is_valid(kicked):
                self.piece.rot = (self.piece.rot + direction) % 4
                self.piece.col += dc
                return

    def _lock_piece(self):
        """Lock piece, handle row clears, spawn new piece. Return False if game over."""
        self.board.lock(self.piece.cells())
        sfx_lock()
        rows = self.board.full_rows()
        if rows:
            flash_rows(self.board, rows)
            sfx_clear()
            self.board.clear_rows()
        self.piece = self._new_piece()
        # Check if new piece already collides (game over)
        if not self.board.is_valid(self.piece.cells()):
            return False
        return True

    def tick(self):
        """One game loop iteration. Return False if game over."""
        # Music
        self.player.tick()

        # Input
        move = self.inp.get_move()
        if move:
            self._try_move(0, move)

        rot = self.inp.get_rotation()
        if rot:
            self._try_rotate(rot)

        # Gravity
        speed = SPEED_FAST if self.inp.is_fast() else SPEED_NORMAL
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_gravity) >= speed:
            self._last_gravity = now
            if not self._try_move(1, 0):
                # Piece landed
                if not self._lock_piece():
                    return False

        # Render
        render(self.board, self.piece)
        return True

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    while True:
        game = Game()
        running = True
        while running:
            running = game.tick()
            utime.sleep_ms(50)
        # Game over
        sfx_game_over()
        game_over_animation()
        utime.sleep_ms(500)

main()

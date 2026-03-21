# test_tetris.py - Unit tests for tetris.py (runs on host Python 3)
# Mocks the micro:bit hardware APIs so tests run without physical device.

import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Micro:bit stubs
# ---------------------------------------------------------------------------

# --- microbit stub ---
microbit_mod = types.ModuleType('microbit')

class _Display:
    def __init__(self):
        self._pixels = [[0]*5 for _ in range(5)]
    def show(self, img):
        for r in range(5):
            for c in range(5):
                self._pixels[r][c] = img.get_pixel(c, r)
    def clear(self):
        self._pixels = [[0]*5 for _ in range(5)]
    def get_pixel(self, c, r):
        return self._pixels[r][c]

class _Image:
    def __init__(self, w=5, h=5):
        self._data = [[0]*w for _ in range(h)]
        self._w = w
        self._h = h
    def set_pixel(self, x, y, v):
        if 0 <= x < self._w and 0 <= y < self._h:
            self._data[y][x] = v
    def get_pixel(self, x, y):
        if 0 <= x < self._w and 0 <= y < self._h:
            return self._data[y][x]
        return 0

class _Accelerometer:
    def __init__(self):
        self.x = 0
        self.y = 0
    def get_x(self): return self.x
    def get_y(self): return self.y

class _Button:
    def __init__(self):
        self._pressed = False
    def press(self):
        self._pressed = True
    def was_pressed(self):
        v = self._pressed
        self._pressed = False
        return v

microbit_mod.display = _Display()
microbit_mod.Image = _Image
microbit_mod.accelerometer = _Accelerometer()
microbit_mod.button_a = _Button()
microbit_mod.button_b = _Button()
sys.modules['microbit'] = microbit_mod

# --- music stub ---
music_mod = types.ModuleType('music')
music_mod._last_pitch = None
music_mod._played = []

def _pitch(freq, dur=None, wait=True):
    music_mod._last_pitch = freq

def _play(notes, wait=True):
    music_mod._played.extend(notes if isinstance(notes, list) else [notes])

music_mod.pitch = _pitch
music_mod.play = _play
sys.modules['music'] = music_mod

# --- utime stub ---
utime_mod = types.ModuleType('utime')
_fake_time = [0]

def _ticks_ms():
    return _fake_time[0]

def _ticks_diff(a, b):
    return a - b

def _ticks_add(a, b):
    return a + b

def _sleep_ms(ms):
    _fake_time[0] += ms

utime_mod.ticks_ms = _ticks_ms
utime_mod.ticks_diff = _ticks_diff
utime_mod.ticks_add = _ticks_add
utime_mod.sleep_ms = _sleep_ms
sys.modules['utime'] = utime_mod

# --- random stub (use real random) ---
import random  # noqa: E402 - already available

# ---------------------------------------------------------------------------
# Now import the game module (without running main())
# We do this by reading tetris.py and exec-ing everything except the
# final `main()` call.
# ---------------------------------------------------------------------------

import importlib

# Patch: remove `main()` call at module level so import doesn't block
with open('tetris.py', 'r') as f:
    src = f.read()

# Strip the bare `main()` call at end of file
src_no_main = src.replace('\nmain()\n', '\n').rstrip()
if src_no_main.endswith('main()'):
    src_no_main = src_no_main[:-len('main()')]

_ns = {}
exec(compile(src_no_main, 'tetris.py', 'exec'), _ns)

# Pull names into local scope for convenience
Board = _ns['Board']
Piece = _ns['Piece']
PIECES = _ns['PIECES']
PIECE_NAMES = _ns['PIECE_NAMES']
COLS = _ns['COLS']
ROWS = _ns['ROWS']
_note_to_freq = _ns['_note_to_freq']
_rotate_cw = _ns['_rotate_cw']
_rotate_ccw = _ns['_rotate_ccw']
_all_rotations = _ns['_all_rotations']
MusicPlayer = _ns['MusicPlayer']
THEME = _ns['THEME']
Input = _ns['Input']
Game = _ns['Game']

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _normalize_shape(cells):
    """Shift cells so min row and min col are both 0, then sort."""
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return sorted((r - min_r, c - min_c) for r, c in cells)


class TestRotation(unittest.TestCase):
    def test_rotate_cw_identity_4x(self):
        cells = [(0, 0), (1, 0), (0, 1)]
        result = cells
        for _ in range(4):
            result = _rotate_cw(result)
        self.assertEqual(sorted(result), sorted(cells))

    def test_rotate_ccw_identity_4x(self):
        cells = [(0, 0), (1, 0), (0, 1)]
        result = cells
        for _ in range(4):
            result = _rotate_ccw(result)
        self.assertEqual(sorted(result), sorted(cells))

    def test_all_pieces_have_4_rotations(self):
        for name, rots in PIECES.items():
            self.assertEqual(len(rots), 4, f"{name} missing rotations")

    def test_all_rotations_have_4_cells(self):
        for name, rots in PIECES.items():
            for i, rot in enumerate(rots):
                self.assertEqual(len(rot), 4, f"{name} rot {i} wrong cell count")

    def test_O_piece_all_rotations_equal(self):
        # O piece looks the same in all rotations when normalized (2x2 square).
        rots = PIECES['O']
        shape0 = _normalize_shape(rots[0])
        for rot in rots[1:]:
            self.assertEqual(shape0, _normalize_shape(rot))

    def test_I_piece_has_two_distinct_shapes(self):
        # I piece alternates between vertical (4 tall) and horizontal (4 wide).
        rots = PIECES['I']
        shape0 = _normalize_shape(rots[0])
        shape1 = _normalize_shape(rots[1])
        shape2 = _normalize_shape(rots[2])
        # Rot 0 and rot 2 should be the same normalized shape
        self.assertEqual(shape0, shape2)
        # Rot 0 and rot 1 should differ
        self.assertNotEqual(shape0, shape1)

    def test_I_piece_vertical_shape(self):
        # At least one rotation of I is 4 cells in a single column
        rots = PIECES['I']
        found_vertical = False
        for rot in rots:
            cols = [c for r, c in rot]
            if len(set(cols)) == 1:
                found_vertical = True
        self.assertTrue(found_vertical)

    def test_I_piece_horizontal_shape(self):
        # At least one rotation of I is 4 cells in a single row
        rots = PIECES['I']
        found_horizontal = False
        for rot in rots:
            rows = [r for r, c in rot]
            if len(set(rows)) == 1:
                found_horizontal = True
        self.assertTrue(found_horizontal)


class TestBoard(unittest.TestCase):
    def _make_board(self):
        return Board()

    def test_initial_board_empty(self):
        b = self._make_board()
        for r in range(ROWS):
            self.assertEqual(b.grid[r], [0]*COLS)

    def test_is_valid_within_bounds(self):
        b = self._make_board()
        self.assertTrue(b.is_valid([(0, 0), (1, 1)]))

    def test_is_valid_out_of_bounds_col(self):
        b = self._make_board()
        self.assertFalse(b.is_valid([(0, COLS)]))

    def test_is_valid_out_of_bounds_col_neg(self):
        b = self._make_board()
        self.assertFalse(b.is_valid([(0, -1)]))

    def test_is_valid_below_bottom(self):
        b = self._make_board()
        self.assertFalse(b.is_valid([(ROWS, 0)]))

    def test_is_valid_above_top_ok(self):
        # Cells with r < 0 are allowed (off screen above)
        b = self._make_board()
        self.assertTrue(b.is_valid([(-1, 0)]))

    def test_is_valid_occupied(self):
        b = self._make_board()
        b.grid[0][0] = 1
        self.assertFalse(b.is_valid([(0, 0)]))

    def test_lock_sets_cells(self):
        b = self._make_board()
        b.lock([(0, 0), (0, 1)])
        self.assertEqual(b.grid[0][0], 1)
        self.assertEqual(b.grid[0][1], 1)

    def test_lock_ignores_out_of_bounds(self):
        b = self._make_board()
        b.lock([(-1, 0), (ROWS, 0)])
        # No exception; board still clean
        for r in range(ROWS):
            self.assertEqual(b.grid[r], [0]*COLS)

    def test_clear_rows_single_full_row(self):
        b = self._make_board()
        b.grid[ROWS-1] = [1]*COLS
        cleared = b.clear_rows()
        self.assertEqual(cleared, 1)
        # Last row should be empty now (shifted down)
        self.assertEqual(b.grid[ROWS-1], [0]*COLS)

    def test_clear_rows_none_full(self):
        b = self._make_board()
        b.grid[0][0] = 1
        cleared = b.clear_rows()
        self.assertEqual(cleared, 0)
        self.assertEqual(b.grid[0][0], 1)

    def test_clear_rows_multiple(self):
        b = self._make_board()
        b.grid[ROWS-1] = [1]*COLS
        b.grid[ROWS-2] = [1]*COLS
        cleared = b.clear_rows()
        self.assertEqual(cleared, 2)
        for r in range(ROWS):
            self.assertEqual(b.grid[r], [0]*COLS)

    def test_full_rows_detection(self):
        b = self._make_board()
        b.grid[2] = [1]*COLS
        self.assertIn(2, b.full_rows())
        self.assertEqual(len(b.full_rows()), 1)

    def test_board_dimensions(self):
        b = self._make_board()
        self.assertEqual(len(b.grid), ROWS)
        for row in b.grid:
            self.assertEqual(len(row), COLS)


class TestPiece(unittest.TestCase):
    def test_piece_starts_off_screen(self):
        p = Piece('I')
        cells = p.cells()
        # All cells should have row < ROWS (some may be negative = off screen)
        for r, c in cells:
            self.assertLess(r, ROWS)

    def test_piece_cells_count(self):
        for name in PIECE_NAMES:
            p = Piece(name)
            self.assertEqual(len(p.cells()), 4, f"{name} wrong cell count")

    def test_piece_rotation_cw(self):
        p = Piece('T')
        cells_before = sorted(p.cells())
        p.rot = (p.rot + 1) % 4
        cells_after = sorted(p.cells())
        # After rotation cells should differ (T is not symmetric)
        self.assertNotEqual(cells_before, cells_after)

    def test_piece_rotated_method_returns_4_cells(self):
        for name in PIECE_NAMES:
            p = Piece(name)
            for d in (-1, 1):
                cells = p.rotated(d)
                self.assertEqual(len(cells), 4)

    def test_piece_col_center(self):
        for name in PIECE_NAMES:
            p = Piece(name)
            self.assertEqual(p.col, COLS // 2)


class TestNoteToFreq(unittest.TestCase):
    def test_a4_is_440(self):
        self.assertEqual(_note_to_freq('A4'), 440)

    def test_a5_is_880(self):
        self.assertEqual(_note_to_freq('A5'), 880)

    def test_c4(self):
        # C4 is MIDI 60, freq = 440 * 2^((60-69)/12) ≈ 261.63
        freq = _note_to_freq('C4')
        self.assertAlmostEqual(freq, 261, delta=2)

    def test_e5(self):
        freq = _note_to_freq('E5')
        self.assertAlmostEqual(freq, 659, delta=2)

    def test_invalid_returns_none(self):
        self.assertIsNone(_note_to_freq(''))
        self.assertIsNone(_note_to_freq('XYZ'))


class TestMusicPlayer(unittest.TestCase):
    def test_player_advances_index(self):
        player = MusicPlayer(THEME)
        _fake_time[0] = 10000  # set time well ahead
        player._next_ms = 0
        player.tick()
        self.assertEqual(player.idx, 1)

    def test_player_loops(self):
        player = MusicPlayer(['C4:1'])
        _fake_time[0] = 100000
        player._next_ms = 0
        player.tick()
        self.assertEqual(player.idx, 0)  # wrapped back

    def test_player_respects_cooldown(self):
        player = MusicPlayer(THEME)
        _fake_time[0] = 0
        player._next_ms = 9999
        player.tick()
        self.assertEqual(player.idx, 0)  # did not advance


class TestGameLogic(unittest.TestCase):
    def _make_game(self):
        g = Game()
        # Silence music during test
        g.player._next_ms = 10**9
        return g

    def test_game_creates_board_and_piece(self):
        g = self._make_game()
        self.assertIsInstance(g.board, Board)
        self.assertIsInstance(g.piece, Piece)

    def test_try_move_left(self):
        g = self._make_game()
        # Position piece safely on board
        g.piece = Piece('O')
        g.piece.row = 2
        g.piece.col = 2
        col_before = g.piece.col
        g._try_move(0, -1)
        self.assertEqual(g.piece.col, col_before - 1)

    def test_try_move_blocked_by_wall(self):
        g = self._make_game()
        g.piece = Piece('O')
        g.piece.row = 2
        g.piece.col = 0
        g._try_move(0, -1)
        self.assertEqual(g.piece.col, 0)

    def test_try_move_down(self):
        g = self._make_game()
        g.piece = Piece('O')
        g.piece.row = 0
        g.piece.col = 2
        row_before = g.piece.row
        result = g._try_move(1, 0)
        self.assertTrue(result)
        self.assertEqual(g.piece.row, row_before + 1)

    def test_try_move_blocked_by_bottom(self):
        g = self._make_game()
        g.piece = Piece('O')
        g.piece.row = ROWS - 2  # O piece spans 2 rows
        g.piece.col = 2
        result = g._try_move(1, 0)
        self.assertFalse(result)

    def test_try_rotate_cw(self):
        g = self._make_game()
        g.piece = Piece('T')
        g.piece.row = 2
        g.piece.col = 2
        rot_before = g.piece.rot
        g._try_rotate(1)
        self.assertEqual(g.piece.rot, (rot_before + 1) % 4)

    def test_try_rotate_ccw(self):
        g = self._make_game()
        g.piece = Piece('T')
        g.piece.row = 2
        g.piece.col = 2
        rot_before = g.piece.rot
        g._try_rotate(-1)
        self.assertEqual(g.piece.rot, (rot_before - 1) % 4)

    def test_lock_piece_fills_board(self):
        g = self._make_game()
        g.piece = Piece('O')
        g.piece.row = 1
        g.piece.col = 1
        cells = g.piece.cells()
        g._lock_piece()
        for r, c in cells:
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.assertEqual(g.board.grid[r][c], 1)

    def test_lock_piece_clears_full_row(self):
        g = self._make_game()
        # Fill bottom row except col 0 and 1
        for c in range(2, COLS):
            g.board.grid[ROWS-1][c] = 1
        # Place O piece at bottom-left to fill remaining cols 0,1
        g.piece = Piece('O')
        g.piece.row = ROWS - 2
        g.piece.col = 0
        g._lock_piece()
        # Bottom row(s) should have been cleared
        self.assertEqual(g.board.full_rows(), [])

    def test_game_over_when_stack_too_high(self):
        g = self._make_game()
        # The I piece spawns at row=-2, col=2 with offsets (-1,0),(0,0),(1,0),(2,0),
        # placing a cell at board position (0, 2).  Block just that cell so the
        # row is NOT full (avoids a clear) but the spawn still collides.
        g.board.grid[0][2] = 1
        # Place current piece safely at the bottom, away from row 0
        g.piece = Piece('O')
        g.piece.row = ROWS - 2
        g.piece.col = 0
        # Force the next spawned piece to be an I piece at col=2
        def forced_i_piece():
            p = Piece('I')
            p.row = -2
            p.col = 2
            return p
        g._new_piece = forced_i_piece
        result = g._lock_piece()
        self.assertFalse(result)

    def test_tick_returns_true_normally(self):
        g = self._make_game()
        # Give piece room to fall
        g.piece = Piece('O')
        g.piece.row = 0
        g.piece.col = 2
        _fake_time[0] = 0
        g._last_gravity = 0
        # Ensure gravity doesn't fire
        _fake_time[0] = 100
        result = g.tick()
        self.assertTrue(result)


class TestInput(unittest.TestCase):
    def test_move_left_on_tilt(self):
        inp = Input()
        inp._last_move = 0
        _fake_time[0] = 10000
        microbit_mod.accelerometer.x = -300
        self.assertEqual(inp.get_move(), -1)

    def test_move_right_on_tilt(self):
        inp = Input()
        inp._last_move = 0
        _fake_time[0] = 20000
        microbit_mod.accelerometer.x = 300
        self.assertEqual(inp.get_move(), 1)

    def test_no_move_centered(self):
        inp = Input()
        inp._last_move = 0
        _fake_time[0] = 30000
        microbit_mod.accelerometer.x = 0
        self.assertEqual(inp.get_move(), 0)

    def test_move_cooldown(self):
        inp = Input()
        _fake_time[0] = 40000
        inp._last_move = 40000
        microbit_mod.accelerometer.x = -300
        self.assertEqual(inp.get_move(), 0)

    def test_is_fast_forward_tilt(self):
        inp = Input()
        microbit_mod.accelerometer.y = -300
        self.assertTrue(inp.is_fast())

    def test_is_fast_not_tilted(self):
        inp = Input()
        microbit_mod.accelerometer.y = 0
        self.assertFalse(inp.is_fast())

    def test_rotation_button_a(self):
        inp = Input()
        inp._last_rot = 0
        _fake_time[0] = 50000
        microbit_mod.button_a.press()
        self.assertEqual(inp.get_rotation(), -1)

    def test_rotation_button_b(self):
        inp = Input()
        inp._last_rot = 0
        _fake_time[0] = 60000
        microbit_mod.button_b.press()
        self.assertEqual(inp.get_rotation(), 1)

    def test_rotation_cooldown(self):
        inp = Input()
        _fake_time[0] = 70000
        inp._last_rot = 70000
        microbit_mod.button_a.press()
        self.assertEqual(inp.get_rotation(), 0)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import random
import time


class Minesweeper:
    def __init__(self, rows: int, cols: int, mines: int, state_file: str | None = None, duration_file: str | None = None):
        self.rows = rows
        self.cols = cols
        self.mine_count = mines
        default_state_file = Path(os.environ.get("MINESWEEPER_BOARD_PATH", "/tmp_workspace/results/minesweeper_board.txt"))
        default_duration_file = Path(os.environ.get("MINESWEEPER_DURATION_PATH", "/tmp_workspace/results/minesweeper_duration.txt"))
        self.state_file = Path(state_file) if state_file else default_state_file
        self.duration_file = Path(duration_file) if duration_file else default_duration_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.duration_file.parent.mkdir(parents=True, exist_ok=True)
        self.board = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.flagged = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.game_over = False
        self.won = False
        self.first_move_unix: int | None = None
        self.end_unix: int | None = None
        self._random = random.Random()
        self._place_mines()
        self._calculate_numbers()
        self.write_board()
        self.write_duration()

    def _neighbors(self, row: int, col: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def _place_mines(self) -> None:
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        for row, col in self._random.sample(positions, self.mine_count):
            self.board[row][col] = -1

    def _calculate_numbers(self) -> None:
        for row in range(self.rows):
            for col in range(self.cols):
                if self.board[row][col] == -1:
                    continue
                count = 0
                for nr, nc in self._neighbors(row, col):
                    if self.board[nr][nc] == -1:
                        count += 1
                self.board[row][col] = count

    def score(self) -> float:
        revealed_safe_cells = 0
        correct_flags = 0
        for row in range(self.rows):
            for col in range(self.cols):
                if self.revealed[row][col] and self.board[row][col] != -1:
                    revealed_safe_cells += 1
                if self.flagged[row][col] and self.board[row][col] == -1:
                    correct_flags += 1
        return (revealed_safe_cells + correct_flags) / (self.rows * self.cols)

    def record_move_start(self) -> None:
        if self.first_move_unix is None:
            self.first_move_unix = int(time.time())
            self.write_duration()

    def record_end(self) -> None:
        self.end_unix = int(time.time())
        self.write_duration()

    def reveal(self, row: int, col: int) -> None:
        if self.game_over or self.flagged[row][col] or self.revealed[row][col]:
            return
        self.record_move_start()
        self.revealed[row][col] = True
        if self.board[row][col] == -1:
            self.game_over = True
            self.won = False
            self._reveal_all_mines()
            self.record_end()
            self.write_board()
            return
        if self.board[row][col] == 0:
            self._flood_fill(row, col)
        if self._all_non_mines_revealed():
            self.game_over = True
            self.won = True
            self.record_end()
        self.write_board()

    def toggle_flag(self, row: int, col: int) -> None:
        if self.game_over or self.revealed[row][col]:
            return
        self.record_move_start()
        self.flagged[row][col] = not self.flagged[row][col]
        if self._all_non_mines_revealed():
            self.game_over = True
            self.won = True
            self.record_end()
        self.write_board()

    def _flood_fill(self, row: int, col: int) -> None:
        stack = [(row, col)]
        while stack:
            current_row, current_col = stack.pop()
            for nr, nc in self._neighbors(current_row, current_col):
                if self.revealed[nr][nc] or self.flagged[nr][nc]:
                    continue
                self.revealed[nr][nc] = True
                if self.board[nr][nc] == 0:
                    stack.append((nr, nc))

    def _reveal_all_mines(self) -> None:
        for row in range(self.rows):
            for col in range(self.cols):
                if self.board[row][col] == -1:
                    self.revealed[row][col] = True

    def _all_non_mines_revealed(self) -> bool:
        for row in range(self.rows):
            for col in range(self.cols):
                if self.board[row][col] != -1 and not self.revealed[row][col]:
                    return False
        return True

    def board_lines(self) -> list[str]:
        lines = []
        header = '   ' + ' '.join(f'{col:02d}' for col in range(self.cols))
        lines.append(header)
        for row in range(self.rows):
            values = []
            for col in range(self.cols):
                if self.flagged[row][col]:
                    values.append('F')
                elif not self.revealed[row][col]:
                    values.append('#')
                elif self.board[row][col] == -1:
                    values.append('*')
                else:
                    values.append(str(self.board[row][col]))
            lines.append(f'{row:02d} ' + ' '.join(values))
        score = 1.0 if self.won else self.score()
        lines.append('')
        lines.append(f'Score: {score:.4f}')
        lines.append('Status: WIN' if self.game_over and self.won else 'Status: LOSE' if self.game_over else 'Status: IN_PROGRESS')
        return lines

    def write_board(self) -> None:
        self.state_file.write_text('\n'.join(self.board_lines()) + '\n', encoding='utf-8')

    def write_duration(self) -> None:
        lines = []
        attempt = os.environ.get('MINESWEEPER_ATTEMPT', '')
        if attempt:
            lines.append(f'attempt={attempt}')
        if self.first_move_unix is not None:
            lines.append(f'first_move_unix={self.first_move_unix}')
        if self.end_unix is not None:
            lines.append(f'end_unix={self.end_unix}')
        if self.first_move_unix is not None and self.end_unix is not None:
            lines.append(f'duration_seconds={self.end_unix - self.first_move_unix}')
        elif self.first_move_unix is not None:
            lines.append('duration_seconds=IN_PROGRESS')
        else:
            lines.append('duration_seconds=NOT_STARTED')
        self.duration_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def parse_move(raw: str, rows: int, cols: int):
    parts = raw.strip().split()
    if len(parts) not in (2, 3):
        raise ValueError('Use: row col [F]')
    row = int(parts[0])
    col = int(parts[1])
    if not (0 <= row < rows and 0 <= col < cols):
        raise ValueError('Coordinates out of range')
    flag = len(parts) == 3 and parts[2].upper() == 'F'
    if len(parts) == 3 and not flag:
        raise ValueError('Third token must be F when present')
    return row, col, flag


def main() -> int:
    game = Minesweeper(rows=16, cols=16, mines=40)
    print('Minesweeper ready.')
    print(f'Board file: {game.state_file}')
    print(f'Duration file: {game.duration_file}')
    print('Enter moves as: row col   or   row col F')
    while True:
        if game.game_over:
            print('Game finished. Board file and duration file updated.')
            return 0
        try:
            raw = input('move> ')
        except EOFError:
            game.write_duration()
            return 0
        if not raw.strip():
            continue
        if raw.strip().lower() in {'q', 'quit', 'exit'}:
            game.write_board()
            game.write_duration()
            return 0
        try:
            row, col, flag = parse_move(raw, game.rows, game.cols)
        except Exception as exc:
            print(exc)
            continue
        if flag:
            game.toggle_flag(row, col)
        else:
            game.reveal(row, col)
        print(f'Board file refreshed: {game.state_file}')
        print(f'Duration file refreshed: {game.duration_file}')


if __name__ == '__main__':
    raise SystemExit(main())

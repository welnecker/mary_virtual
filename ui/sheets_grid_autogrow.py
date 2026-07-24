from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import gspread


SHEETS_GRID_AUTOGROW_VERSION = "sheets-grid-autogrow-v1-safe-write-expansion"

_INSTALLED = False


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _garantir_grade(
    worksheet: Any,
    *,
    required_rows: int = 1,
    required_cols: int = 1,
) -> None:
    """Expande a grade da aba antes de uma escrita fora dos limites."""
    required_rows = max(1, _inteiro(required_rows, 1))
    required_cols = max(1, _inteiro(required_cols, 1))

    current_rows = max(1, _inteiro(getattr(worksheet, "row_count", 1), 1))
    current_cols = max(1, _inteiro(getattr(worksheet, "col_count", 1), 1))

    if required_rows > current_rows:
        worksheet.add_rows(required_rows - current_rows)
    if required_cols > current_cols:
        worksheet.add_cols(required_cols - current_cols)


def _dimensoes_valores(values: Any) -> tuple[int, int]:
    if not isinstance(values, (list, tuple)) or not values:
        return 1, 1
    if isinstance(values[0], (list, tuple)):
        rows = len(values)
        cols = max((len(row) for row in values if isinstance(row, (list, tuple))), default=1)
        return max(1, rows), max(1, cols)
    return 1, max(1, len(values))


def _coluna_a1(label: str) -> int:
    result = 0
    for char in str(label or "").upper():
        if not ("A" <= char <= "Z"):
            break
        result = result * 26 + (ord(char) - ord("A") + 1)
    return max(1, result)


def _limites_a1(range_name: Any) -> tuple[int, int]:
    text = str(range_name or "").split("!", 1)[-1].strip()
    if not text:
        return 1, 1
    end = text.split(":", 1)[-1]
    letters = "".join(char for char in end if char.isalpha())
    digits = "".join(char for char in end if char.isdigit())
    return max(1, _inteiro(digits, 1)), _coluna_a1(letters)


def install_sheets_grid_autogrow() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    worksheet_cls = gspread.Worksheet

    original_update_cell: Callable[..., Any] = worksheet_cls.update_cell
    original_append_row: Callable[..., Any] = worksheet_cls.append_row
    original_append_rows: Callable[..., Any] = worksheet_cls.append_rows
    original_update: Callable[..., Any] = worksheet_cls.update

    @wraps(original_update_cell)
    def update_cell(self: Any, row: int, col: int, value: Any) -> Any:
        _garantir_grade(self, required_rows=row, required_cols=col)
        return original_update_cell(self, row, col, value)

    @wraps(original_append_row)
    def append_row(self: Any, values: Any, *args: Any, **kwargs: Any) -> Any:
        _, cols = _dimensoes_valores(values)
        next_row = _inteiro(getattr(self, "row_count", 1), 1)
        _garantir_grade(self, required_rows=next_row, required_cols=cols)
        return original_append_row(self, values, *args, **kwargs)

    @wraps(original_append_rows)
    def append_rows(self: Any, values: Any, *args: Any, **kwargs: Any) -> Any:
        rows, cols = _dimensoes_valores(values)
        current_rows = _inteiro(getattr(self, "row_count", 1), 1)
        _garantir_grade(
            self,
            required_rows=current_rows + max(0, rows - 1),
            required_cols=cols,
        )
        return original_append_rows(self, values, *args, **kwargs)

    @wraps(original_update)
    def update(self: Any, values: Any = None, range_name: Any = None, *args: Any, **kwargs: Any) -> Any:
        # Compatível com assinaturas antigas e novas do gspread.
        actual_values = values
        actual_range = range_name
        if isinstance(values, str) and range_name is not None:
            actual_range = values
            actual_values = range_name

        rows, cols = _dimensoes_valores(actual_values)
        end_row, end_col = _limites_a1(actual_range)
        _garantir_grade(
            self,
            required_rows=max(end_row, rows),
            required_cols=max(end_col, cols),
        )
        return original_update(self, values, range_name, *args, **kwargs)

    worksheet_cls.update_cell = update_cell
    worksheet_cls.append_row = append_row
    worksheet_cls.append_rows = append_rows
    worksheet_cls.update = update
    _INSTALLED = True


__all__ = [
    "SHEETS_GRID_AUTOGROW_VERSION",
    "install_sheets_grid_autogrow",
]

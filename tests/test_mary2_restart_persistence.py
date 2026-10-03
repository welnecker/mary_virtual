import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import gspread
import pytest
from mary2 import persistence as p


def api_error(code=429):
    response = Mock(status_code=code)
    response.json.return_value = {"error": {"code": code, "message": "quota", "status": "RESOURCE_EXHAUSTED"}}
    return gspread.exceptions.APIError(response)


@pytest.fixture
def book(monkeypatch):
    sheets = {}
    for title, headers in [(p.CHECKPOINTS_SHEET, p.CHECKPOINT_HEADERS), (p.RUNS_SHEET, p.RUN_HEADERS)]:
        ws = Mock()
        # Use real storage attributes; Mock invents missing attributes.
        ws._mary_checkpoint_records = None
        ws._mary_run_rows = {}
        ws.row_values.return_value = headers
        ws.get_all_records.return_value = []
        sheets[title] = ws
    book = SimpleNamespace(worksheet=lambda title: sheets[title])
    monkeypatch.setattr(p, 'open_or_create_book', lambda **kwargs: book)
    return book, sheets


def checkpoint(instance='instance1'):
    return dict(service_account_info={}, run_id='run1', checkpoint_type='chapter_entry', source_seq=3,
                source_chapter_id='lanchonete', source_chapter_instance_id=instance,
                source_branch_id='main', choice_point_id='lanchonete', active_user_role='JANIO',
                story_ledger='entry', scene_state={'location': 'entry'}, story_state={'narrative': {}})


def test_warm_restart_needs_no_reads_and_preserves_seq(book):
    _, sheets = book
    ws = sheets[p.CHECKPOINTS_SHEET]
    original = p.save_checkpoint(**checkpoint())
    runs = sheets[p.RUNS_SHEET]
    p._ensure_worksheet(book[0], p.RUNS_SHEET, p.RUN_HEADERS)
    p._remember_run_rows(runs, [{'run_id': 'run1'}])
    for sheet in sheets.values():
        sheet.get_all_records.side_effect = api_error()
        sheet.row_values.side_effect = api_error()
        sheet.find.side_effect = api_error()
    entry = p.load_checkpoint(service_account_info={}, checkpoint_id=original)
    entry['scene_state']['location'] = 'mutated'
    assert p.load_checkpoint(service_account_info={}, checkpoint_id=original)['scene_state']['location'] == 'entry'
    p.save_checkpoint(**checkpoint('instance2'))
    p.update_run_snapshot(service_account_info={}, run_id='run1', active_user_role='JANIO',
                          story_ledger='entry', scene_state={}, story_state={})
    assert ws.get_all_records.call_count == 1
    assert ws.row_values.call_count == 1
    runs.find.assert_not_called()
    ranges = [x['range'] for x in runs.batch_update.call_args.args[0]]
    assert ranges == ['C2', 'E2', 'G2:J2']  # D(created_at) and F(last_seq) untouched.


def test_expired_checkpoint_uses_stale_on_429(book, monkeypatch):
    _, sheets = book
    now = [0.0]
    monkeypatch.setattr(p, 'monotonic', lambda: now[0])
    saved = p.save_checkpoint(**checkpoint())
    now[0] = 100.0
    ws = sheets[p.CHECKPOINTS_SHEET]
    ws.get_all_records.side_effect = api_error()
    assert p.load_checkpoints(service_account_info={}, run_id='run1')[0]['checkpoint_id'] == saved
    assert p.load_checkpoints(service_account_info={}, run_id='run1')[0]['checkpoint_id'] == saved
    assert ws.get_all_records.call_count == 2  # Only one failed refresh.
    p.save_checkpoint(**checkpoint('instance2'))
    assert ws.append_row.call_count == 2


@pytest.mark.parametrize('code', [429, 403])
def test_no_valid_cache_does_not_invent_checkpoint(book, code):
    _, sheets = book
    sheets[p.CHECKPOINTS_SHEET].get_all_records.side_effect = api_error(code)
    with pytest.raises(gspread.exceptions.APIError):
        p.load_checkpoint(service_account_info={}, checkpoint_id='missing')


def test_other_errors_are_not_hidden_by_stale(book, monkeypatch):
    _, sheets = book
    p.save_checkpoint(**checkpoint())
    monkeypatch.setattr(p, 'monotonic', lambda: 1e20)
    sheets[p.CHECKPOINTS_SHEET].get_all_records.side_effect = api_error(403)
    with pytest.raises(gspread.exceptions.APIError):
        p.load_checkpoints(service_account_info={}, run_id='run1')


def test_failed_append_not_cached(book):
    _, sheets = book
    ws = sheets[p.CHECKPOINTS_SHEET]
    ws.append_row.side_effect = api_error()
    with pytest.raises(gspread.exceptions.APIError):
        p.save_checkpoint(**checkpoint())
    assert ws._mary_checkpoint_records == []


def test_book_cache_is_scoped_to_credentials_and_sheet(monkeypatch):
    p._open_book.cache_clear()
    client = Mock()
    monkeypatch.setattr(p, '_client', lambda info: client)
    for account, sheet in [('a', 's1'), ('a', 's1'), ('b', 's1'), ('a', 's2')]:
        p.open_or_create_book(service_account_info={'client_email': account}, spreadsheet_id=sheet)
    assert client.open_by_key.call_count == 3
    p._open_book.cache_clear()


def restart_function(state, **overrides):
    # Execute the actual UI operation without running the whole Streamlit app.
    tree = ast.parse(Path('mary2/app.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'restart_current_chapter')
    env = dict(deepcopy=deepcopy, PersistenceError=p.PersistenceError, st=SimpleNamespace(session_state=state, rerun=Mock()),
               _chapter_id=lambda: 'lanchonete', migrate_state=deepcopy,
               new_chapter_instance_id=lambda _: 'instance2', story_ledger_text=lambda _: 'entry',
               load_checkpoint=lambda **_: {'story_state': {'narrative': {}}, 'scene_state': {'location': 'entry'}, 'active_user_role': 'JANIO'},
               save_checkpoint=Mock(return_value='new-entry'), update_run_snapshot=Mock())
    env.update(overrides)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'mary2/app.py', 'exec'), env)
    return env


class Session(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    __setattr__ = dict.__setitem__


@pytest.mark.parametrize('fail_at', ['save_checkpoint', 'update_run_snapshot', None])
def test_restart_only_changes_local_state_after_confirmed_write(fail_at):
    state = Session(run_id='run1', story_state={'narrative': {'chapter_entry_checkpoint_id': 'entry1'}},
                    scene_state={'location': 'current'}, active_user_role='JANIO', run_last_seq=9,
                    messages=['conversation'], turn_records=['turn'])
    before = deepcopy(state)
    overrides = {fail_at: Mock(side_effect=api_error())} if fail_at else {}
    env = restart_function(state, **overrides)
    config = dict(service_account_info={}, spreadsheet_id='sheet', spreadsheet_title='MARY_CORE_PERSISTENCE', owner_email='')
    if fail_at:
        with pytest.raises(gspread.exceptions.APIError):
            env['restart_current_chapter'](config)
        assert state == before
        env['st'].rerun.assert_not_called()
    else:
        env['restart_current_chapter'](config)
        assert state.scene_state == {'location': 'entry'}
        assert state.story_state['narrative']['chapter_start_seq'] == 10
        assert state.story_state['narrative']['chapter_entry_checkpoint_id'] == 'new-entry'
        assert state.messages == []
        assert state.run_last_seq == 9
        env['st'].rerun.assert_called_once()

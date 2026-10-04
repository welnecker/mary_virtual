from copy import deepcopy
from pathlib import Path

from mary2.chapter_continuity import carry_user_statements
from mary2.chapters import chapter_phase, chapter_prompt, chapter_ready_for_choice, find_choice, get_chapter, apply_choice_to_story
from mary2.state import migrate_state


def test_name_source_survives_transition_and_reload_without_fixed_name():
    for name in ['Rafael', 'Luís Henrique', 'Ana']:
        before = {'narrative': {}, 'current_status': {}, 'story_ledger': []}
        records = [dict(chapter_id='academia_suco_aceito', user_text=f'Me chamo {name}.'),
                   dict(chapter_id='academia_suco_aceito', user_text='Gosto de praia e paraquedas.'),
                   dict(chapter_id='confissao_inicial', user_text='Eu sou Janio.')]
        carried = carry_user_statements(before, 'academia_suco_aceito', records)
        chosen = apply_choice_to_story(story_state=carried, chapter_id='academia_suco_aceito', choice_id='dar_carona')
        restored = migrate_state(chosen)
        statements = restored['current_status']['personal_conversation_reference']['sources'][0]['user_statements']
        assert statements == [f'Me chamo {name}.', 'Gosto de praia e paraquedas.']
        assert before['current_status'] == {}
        assert 'Donisete' not in str(get_chapter('carona_camburi')['initial_scene'])


def test_apartment_keeps_name_and_actual_plan_without_fabricating_acceptance():
    state = carry_user_statements({'current_status': {}}, 'academia_suco_aceito', [dict(user_text='Meu nome é Miguel.')])
    state = carry_user_statements(state, 'carona_camburi', [dict(user_text='Hoje eu não posso ir ao clube.')])
    result = apply_choice_to_story(story_state=state, chapter_id='carona_camburi', choice_id='mary_em_seu_apartamento')
    sources = result['current_status']['personal_conversation_reference']['sources']
    assert sources[0]['user_statements'] == ['Meu nome é Miguel.']
    assert sources[1]['user_statements'] == ['Hoje eu não posso ir ao clube.']
    assert not any('aceitou o convite' in item for item in result['story_ledger'])
    assert 'meeting_time' not in result['current_status']


def test_replayed_introduction_replaces_other_route():
    original = carry_user_statements({'current_status': {}}, 'academia_suco_aceito', [dict(user_text='Sou André.')])
    changed = carry_user_statements(original, 'academia_suco_aceito', [dict(user_text='Sou Felipe.')])
    assert 'André' not in str(changed)
    assert 'Felipe' in str(changed)
    assert 'André' in str(original)


def test_carona_uses_sheet_line_pilot_and_keeps_physical_boundaries():
    chapter = get_chapter('carona_camburi')
    assert chapter['script_mode'] == 'sheet_line_runtime'
    assert chapter['script_name'] == 'Carona'
    assert chapter.get('dramatic_phases', []) == []

    assert not chapter_ready_for_choice('carona_camburi', 11, True)
    assert not chapter_ready_for_choice('carona_camburi', 12, False)
    assert chapter_ready_for_choice('carona_camburi', 12, True)

    prompt = chapter_prompt('carona_camburi', 1)
    assert 'O personal controla direção, rota, velocidade, manobras, parada e estacionamento' in prompt
    assert 'A direção dramática desta interação vem exclusivamente da LINHA ATUAL DA PLANILHA' in prompt
    assert 'Clube Náutico' not in prompt
    assert 'balada eletrônica' not in prompt

    assert find_choice('carona_camburi', 'mary_em_seu_apartamento')['next_chapter'] == 'mary_apartamento_camburi'
    apartment = get_chapter('mary_apartamento_camburi')
    assert apartment['initial_scene']['present_characters'] == ['MARY']
    assert apartment['model_opening'] is False

def test_checkpoint_replay_carries_only_original_instance():
    # Reuse the actual app function in isolation, with its external dependencies
    # stubbed, and stop at apply_choice once the source has been reconstructed.
    import ast
    from types import SimpleNamespace
    tree = ast.parse(Path('mary2/app.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'activate_choice_from_checkpoint')
    checkpoint = dict(run_id='run1', source_chapter_id='academia_suco_aceito', source_chapter_instance_id='original',
                      source_seq=10, story_state={'current_status': {}, 'narrative': {}}, scene_state={})
    rows = [dict(seq=5, chapter_instance_id='original', chapter_id='academia_suco_aceito', user_text='Me chamo Guilherme.'),
            dict(seq=6, chapter_instance_id='other', chapter_id='academia_suco_aceito', user_text='Me chamo Pedro.'),
            dict(seq=11, chapter_instance_id='original', chapter_id='academia_suco_aceito', user_text='Future turn')]
    captured = []
    class Stop(Exception):
        pass
    def capture(**kwargs):
        captured.append(kwargs['story_state'])
        raise Stop
    env = dict(deepcopy=deepcopy, st=SimpleNamespace(session_state=SimpleNamespace(run_id='run1', get=lambda key, default=0: default)),
               load_checkpoint=lambda **_: checkpoint, find_choice=find_choice, migrate_state=migrate_state,
               carry_user_statements=carry_user_statements, load_run_interactions=lambda **_: rows,
               new_branch_id=lambda _: 'branch', new_chapter_instance_id=lambda _: 'instance', apply_choice_to_story=capture)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'app.py', 'exec'), env)
    import pytest
    with pytest.raises(Stop):
        env['activate_choice_from_checkpoint'](checkpoint_id='cp1', choice_id='dar_carona', persistence=dict(
            service_account_info={}, spreadsheet_id='sheet', spreadsheet_title='sheet', owner_email=''))
    assert captured[0]['current_status']['personal_conversation_reference']['sources'][0]['user_statements'] == ['Me chamo Guilherme.']

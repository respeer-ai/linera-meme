#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys

import yaml


class PromptStateValidator:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.board_path = repo_root / 'agents/tasks/board.yaml'
        self.prompt_state_path = repo_root / 'agents/tasks/prompt-state.yaml'

    def run(self) -> int:
        board = self._load_yaml(self.board_path)
        prompt_state = self._load_yaml(self.prompt_state_path)
        errors = []
        errors.extend(self._validate_prompt_state_shape(prompt_state))
        errors.extend(self._validate_task_alignment(board, prompt_state))
        if errors:
            for error in errors:
                print(f'ERROR: {error}')
            return 1
        print('OK prompt-state is aligned with board')
        return 0

    def _load_yaml(self, path: Path) -> dict:
        with path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            raise ValueError(f'{path} must contain a YAML mapping at top level')
        return data

    def _validate_prompt_state_shape(self, prompt_state: dict) -> list[str]:
        errors = []
        if prompt_state.get('type') != 'prompt-state':
            errors.append("agents/tasks/prompt-state.yaml must declare type 'prompt-state'")
        for field in ('active_focus', 'on_demand_done'):
            value = prompt_state.get(field)
            if not isinstance(value, list):
                errors.append(f'agents/tasks/prompt-state.yaml field `{field}` must be a list')
        return errors

    def _validate_task_alignment(self, board: dict, prompt_state: dict) -> list[str]:
        errors = []
        tasks_by_id = self._tasks_by_id(board)
        active_ids = set()
        for entry in prompt_state.get('active_focus', []):
            if not isinstance(entry, dict):
                errors.append('active_focus entries must be mappings')
                continue
            task_id = entry.get('id')
            if not task_id:
                errors.append('active_focus entry missing id')
                continue
            active_ids.add(task_id)
            task = tasks_by_id.get(task_id)
            if task is None:
                errors.append(f'active_focus task `{task_id}` does not exist in board.yaml')
                continue
            status = task.get('status')
            if status not in ('Doing', 'Blocked', 'Done'):
                errors.append(
                    f'active_focus task `{task_id}` has status `{status}`; expected Doing, Blocked, or justified Done'
                )
            if status == 'Done' and not entry.get('why'):
                errors.append(f'active_focus done task `{task_id}` must explain why it remains in prompt-state')
            if not entry.get('summary'):
                errors.append(f'active_focus task `{task_id}` must include a compact summary')
            if not entry.get('canonical_refs'):
                errors.append(f'active_focus task `{task_id}` must include canonical_refs')
        for entry in prompt_state.get('on_demand_done', []):
            if not isinstance(entry, dict):
                errors.append('on_demand_done entries must be mappings')
                continue
            task_id = entry.get('id')
            if not task_id:
                errors.append('on_demand_done entry missing id')
                continue
            if task_id in active_ids:
                errors.append(f'task `{task_id}` cannot be listed in both active_focus and on_demand_done')
            task = tasks_by_id.get(task_id)
            if task is None:
                errors.append(f'on_demand_done task `{task_id}` does not exist in board.yaml')
                continue
            status = task.get('status')
            if status != 'Done':
                errors.append(f'on_demand_done task `{task_id}` must be Done in board.yaml, got `{status}`')
            if not entry.get('why'):
                errors.append(f'on_demand_done task `{task_id}` must include why')
            if not entry.get('canonical_refs'):
                errors.append(f'on_demand_done task `{task_id}` must include canonical_refs')
        return errors

    def _tasks_by_id(self, board: dict) -> dict[str, dict]:
        tasks = {}
        for group in board.get('groups', []):
            if not isinstance(group, dict):
                continue
            for task in group.get('tasks', []):
                if not isinstance(task, dict):
                    continue
                task_id = task.get('id')
                if task_id:
                    tasks[task_id] = task
        return tasks


if __name__ == '__main__':
    raise SystemExit(PromptStateValidator(Path(__file__).resolve().parents[1]).run())

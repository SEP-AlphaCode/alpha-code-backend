import random
import librosa
import numpy as np
from fastapi import UploadFile
from typing import Dict, List

from models.audio_parse import AudioInfo, Section, MusicInfo
from models.dance_action import Activity, ActionBlock, DanceResponse
from pathlib import Path

current_dir = Path(__file__).parent  # Gets directory containing service.py
action_file_path = current_dir.parent / "local_files" / "available_actions.txt"
exp_file_path = current_dir.parent / "local_files" / "expressions.txt"

actions: Dict[str, int] = {}
expressions: Dict[str, int] = {}
has_loaded = False

async def generate_actions(file: UploadFile, change_threshold: float) -> DanceResponse:
    info = await get_music_info(file=file, change_threshold=change_threshold)
    action_pool = await load_data()
    activity_actions = select_actions(info.duration, action_pool)
    set_zero_actions(activity_actions)
    activity_actions.extend(select_expression(info.duration, expressions))
    activity = Activity(actions=activity_actions)
    mus = MusicInfo(duration=info.duration, music_file_url= '', name=file.filename)
    result = DanceResponse(music_info=mus, activity=activity)
    return result

def read_file(path) -> Dict[str, int]:
    file = open(path)
    rs: Dict[str, int] = dict()
    for line in file:
        comp = line.strip().split()
        rs[comp[0]] = int(comp[1])
    return rs

async def load_data() -> Dict[str, int]:
    global actions, has_loaded, expressions
    if not has_loaded:
        actions = read_file(action_file_path)
        expressions = read_file(exp_file_path)
        has_loaded = True
    return actions


async def get_music_info(file: UploadFile, change_threshold: float) -> AudioInfo:
    contents = await file.read()
    import io
    y, sr = librosa.load(io.BytesIO(contents), sr=None)
    duration = librosa.get_duration(y=y, sr=sr)
    # Detect beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)  # in seconds

    # Compute instantaneous BPS between beats
    if len(beat_times) < 2:
        print("Not enough beats detected.")
        exit()

    intervals = np.diff(beat_times)
    bps_list = 1.0 / intervals  # beats per second between consecutive beats

    start_idx = 0

    # Compute where the BPS changes more than threshold
    relative_change = np.abs(np.diff(bps_list) / bps_list[:-1])
    change_indices = np.where(relative_change > change_threshold)[0] + 1  # +1 because diff shifts index

    # Ensure we always include start (0) and end (len(bps_list))
    split_indices = np.concatenate(([0], change_indices, [len(bps_list)]))

    # Build sections from split indices
    sections: List[Section] = []
    for start_idx, end_idx in zip(split_indices[:-1], split_indices[1:]):
        start_time_ms = int(beat_times[start_idx] * 1000)
        end_time_ms = int(beat_times[end_idx] * 1000)
        avg_bps = float(np.mean(bps_list[start_idx:end_idx]))
        sections.append(Section(time=start_time_ms, bps=avg_bps, duration=end_time_ms - start_time_ms))

    # Append last section
    start_time_ms = int(beat_times[start_idx] * 1000)
    end_time_ms = int(beat_times[-1] * 1000)
    avg_bps = float(np.mean(bps_list[start_idx:]))
    sections.append(Section(time=start_time_ms, bps=avg_bps, duration=end_time_ms - start_time_ms))
    info = AudioInfo(duration=duration, sample_rate=sr, sections=sections)
    return info


def select_actions(duration: float, action_pool: Dict[str, int]) -> List[ActionBlock]:
    total_duration_ms = duration * 1000
    current_time_ms = 0
    scheduled_actions = []

    # Separate dances and short actions
    dances = []
    short_actions = []
    for action_id, action_duration_ms in action_pool.items():
        if action_id.startswith("dance_"):
            dances.append((action_id, action_duration_ms))
        else:
            if 1700 <= action_duration_ms <= 6200:  # Check if within short action duration range
                short_actions.append((action_id, action_duration_ms))

    # Sort dances by duration ascending to fit as many as possible
    dances.sort(key=lambda x: x[1])

    # Schedule dances
    last_action_id = None
    i = 0
    while i < len(dances):
        dance_id, dance_duration = dances[i]
        if current_time_ms + dance_duration <= total_duration_ms:
            if dance_id != last_action_id:
                scheduled_actions.append(ActionBlock.create(
                    action_id=dance_id,
                    start_time=current_time_ms / 1000,
                    duration=dance_duration / 1000,
                    action_type='dance'
                ))
                current_time_ms += dance_duration
                last_action_id = dance_id
                i += 1
            else:
                # Try to find another dance that is not the same as the last one
                found = False
                for j in range(i + 1, len(dances)):
                    next_dance_id, next_dance_duration = dances[j]
                    if next_dance_id != last_action_id and current_time_ms + next_dance_duration <= total_duration_ms:
                        scheduled_actions.append(ActionBlock.create(
                            action_id=next_dance_id,
                            start_time=current_time_ms / 1000,
                            duration=next_dance_duration / 1000,
                            action_type='dance'
                        ))
                        current_time_ms += next_dance_duration
                        last_action_id = next_dance_id
                        dances.pop(j)
                        found = True
                        break
                if not found:
                    i += 1
        else:
            i += 1

    # Now try to fill remaining time with short actions
    remaining_time_ms = total_duration_ms - current_time_ms
    if remaining_time_ms >= 1700:  # Minimum duration for short actions
        # Sort short actions by duration descending to minimize leftover time
        short_actions.sort(key=lambda x: -x[1])
        last_short_action_id = last_action_id
        for action_id, action_duration in short_actions:
            if action_duration <= remaining_time_ms and action_id != last_short_action_id:
                scheduled_actions.append(ActionBlock.create(
                    action_id=action_id,
                    start_time=current_time_ms / 1000,
                    duration=action_duration / 1000,
                    action_type='action',
                ))
                current_time_ms += action_duration
                remaining_time_ms -= action_duration
                last_short_action_id = action_id
                if remaining_time_ms < 1700:
                    break
    return scheduled_actions


def select_expression(duration: float, expression_pool: Dict[str, int]) -> List[ActionBlock]:
    total_duration_ms = duration * 1000
    current_time_ms = 0
    scheduled_expressions = []
    expression_ids = list(expression_pool.keys())

    if not expression_ids:
        return scheduled_expressions

    last_expression_id = None
    while current_time_ms < total_duration_ms:
        # Filter out the last used expression to avoid consecutive repeats
        available_expressions = [expr for expr in expression_ids if expr != last_expression_id]
        if not available_expressions:
            # If no other expressions are available, break to avoid infinite loop
            break

        # Randomly select an expression
        selected_expr = random.choice(available_expressions)
        expr_duration = expression_pool[selected_expr]

        if current_time_ms + expr_duration > total_duration_ms:
            # If adding this expression exceeds the duration, try to find a shorter one
            shorter_expressions = [expr for expr in available_expressions if
                                   expression_pool[expr] <= (total_duration_ms - current_time_ms)]
            if shorter_expressions:
                selected_expr = random.choice(shorter_expressions)
                expr_duration = expression_pool[selected_expr]
            else:
                # No shorter expressions available that fit, break the loop
                break

        # Add the selected expression to the schedule
        scheduled_expressions.append(ActionBlock.create(
            action_id=selected_expr,
            start_time=current_time_ms / 1000,
            duration=expr_duration / 1000,
            action_type='expression'
        ))
        current_time_ms += expr_duration
        last_expression_id = selected_expr

    return scheduled_expressions

# Make actions do not interrupt with the mouth LED
def set_zero_actions(param: List[ActionBlock]):
    for block in param:
        block.duration = 0
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
    activity_actions = select_actions(action_pool, info)
    #set_zero_actions(activity_actions)
    #activity_actions.extend(select_expression(info.duration, expressions))
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


def select_actions(action_pool: Dict[str, int], audio_info: AudioInfo) -> List[ActionBlock]:
    # Filter dances shorter than audio duration
    dances = {k: v for k, v in action_pool.items()
              if k.startswith("dance_") and v < audio_info.duration * 600}
    others = {k: v for k, v in action_pool.items()
              if not k.startswith("dance_")}

    # Choose terminating dance
    term_dance_id, term_dance_dur = random.choice(list(dances.items()))
    term_dance_start = audio_info.duration * 1000 - term_dance_dur

    actions = []

    # Fill sections up until term_dance_start
    for section in audio_info.sections:
        section_start = section.time
        section_end = section.time + section.duration

        # If section starts after terminating dance, skip
        if section_start >= term_dance_start:
            continue

        # Limit section end so it doesn't overlap terminating dance
        section_end = min(section_end, term_dance_start)
        t = section_start

        while t < section_end:
            dance_id, dance_dur = random.choice(list(dances.items()))
            if dance_id == term_dance_id:
                continue

            # If this dance would cross section_end, truncate
            if t + dance_dur > section_end:
                dance_dur = section_end - t
                if dance_dur <= 0:
                    break

            # Add the dance
            actions.append(ActionBlock.create(
                action_id=dance_id,
                start_time=t / 1000,
                duration=dance_dur / 1000,
                action_type='dance'
            ))

            # Insert another action before bow (last 4s), if fits
            if others and dance_dur > 4000:
                other_id, other_dur = random.choice(list(others.items()))
                insert_start = t + (dance_dur - 4000) - other_dur
                if t < insert_start < section_end:
                    actions.append(ActionBlock.create(
                        action_id=other_id,
                        start_time=insert_start / 1000,
                        duration=other_dur / 1000,
                        action_type='dance'
                    ))

            t += dance_dur

    # Add terminating dance at the end
    actions.append(ActionBlock.create(
        action_id=term_dance_id,
        start_time=term_dance_start / 1000,
        duration=term_dance_dur / 1000,
        action_type='dance'
    ))

    # Sort all actions by start time
    actions.sort(key=lambda a: a.start_time)

    return actions

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
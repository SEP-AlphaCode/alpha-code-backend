import librosa
import numpy as np
from fastapi import UploadFile
from typing import Dict, List

from models.audio_parse import MusicInfo, Section
from models.dance_action import DanceSequence, ActionBlock
from pathlib import Path

current_dir = Path(__file__).parent  # Gets directory containing service.py
action_file_path = current_dir.parent / "local_files" / "available_actions.txt"

data: Dict[str, int] = {}
has_loaded = False

async def generate_actions(file: UploadFile, change_threshold: float) -> DanceSequence:
    info = await get_music_info(file=file, change_threshold=change_threshold)
    action_pool = await load_data()
    actions = select_actions(info.duration, action_pool)
    result = DanceSequence()
    result.actions = actions
    return result


async def load_data() -> Dict[str, int]:
    global data, has_loaded
    if not has_loaded:
        print('Load file')
        file = open(action_file_path)
        rs: Dict[str, int] = dict()
        for line in file:
            comp = line.strip().split()
            rs[comp[0]] = int(comp[1])
        has_loaded = True
        data = rs
    return data


async def get_music_info(file: UploadFile, change_threshold: float) -> MusicInfo:
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
    info = MusicInfo(duration=duration, sample_rate=sr, sections=sections)
    return info


def select_actions(duration: float, action_pool: Dict[str, int]) -> List[ActionBlock]:
    # Separate dances and other actions, convert ms to seconds
    dances = {}
    other_actions = {}
    for action, dur_ms in action_pool.items():
        dur_s = dur_ms / 1000
        if action.startswith('dance_'):
            dances[action] = dur_s
        else:
            other_actions[action] = dur_s
    print(dances)
    print(other_actions)
    # Sort by duration (ascending)
    sorted_dances = sorted(dances.items(), key=lambda x: x[1])
    sorted_other = sorted(other_actions.items(), key=lambda x: x[1])

    selected_components = []
    current_time = 0.0
    last_action = None

    def find_next_action(actions, max_dur, last):
        for action, dur in actions:
            if dur <= max_dur and action != last:
                return action, dur
        return None, 0

    # Add as many dances as possible
    while True:
        next_dance, next_dur = find_next_action(sorted_dances, duration - current_time, last_action)
        if next_dance:
            component = ActionBlock(
                action_id=next_dance,
                start_time=current_time,
                duration=next_dur,
                action_type='action'
            )
            selected_components.append(component)
            current_time += next_dur
            last_action = next_dance
        else:
            break

    # If remaining time is within other actions' duration, add one
    remaining_time = duration - current_time
    if sorted_other:
        min_other = sorted_other[0][1]
        max_other = sorted_other[-1][1]
        if min_other <= remaining_time <= max_other:
            next_other, next_other_dur = find_next_action(sorted_other, remaining_time, last_action)
            if next_other:
                component = ActionBlock(
                    duration=next_other_dur,
                    action_id=next_other,
                    action_type='action',
                    start_time=current_time
                    )
                selected_components.append(component)
                current_time += next_other_dur

    return selected_components
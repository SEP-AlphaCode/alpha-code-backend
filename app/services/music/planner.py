from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import io
import random
import requests
import colorsys
try:
    import librosa
except Exception:
    librosa = None
import numpy as np

# from .durations import (
#     DANCE_DURATIONS_MS,
#     ACTION_DURATIONS_MS,
#     EXPRESSION_DURATIONS_MS,
# )
from app.services.music.durations import (
    load_all_durations, load_all_durations_with_exclusion,
)

# DANCE_DURATIONS = {k: v/1000.0 for k, v in DANCE_DURATIONS_MS.items()}
# ACTION_DURATIONS = {k: v/1000.0 for k, v in ACTION_DURATIONS_MS.items()}
# EXPRESSION_DURATIONS = {k: v/1000.0 for k, v in EXPRESSION_DURATIONS_MS.items()}

@dataclass
class PlannedSegment:
    action_id: str
    start_time: float
    duration: float
    action_type: str

class MusicActivityPlanner:
    def __init__(self, durations: dict):
        """Initialize planner with dynamic durations dict."""
        def _normalize(d: dict):
            return {k: v / 1000.0 for k, v in d.items() if isinstance(v, (int, float))}

        self.dances = _normalize(durations.get("dance", {}))
        self.actions = _normalize(durations.get("action", {}))
        self.expressions = _normalize(durations.get("expression", {}))

        if not any([self.dances, self.actions, self.expressions]):
            raise ValueError("No duration data available for this robot model")
        # self.dances = DANCE_DURATIONS
        # self.actions = ACTION_DURATIONS
        # self.expressions = EXPRESSION_DURATIONS
        self._dance_cycle = list(self.dances.items())
        self._action_cycle = list(self.actions.items())
        self._expr_cycle = list(self.expressions.items())
        self._dance_index = 0
        self._action_index = 0
        self._expr_index = 0

    def _next_dance(self) -> tuple[str, float]:
        item = self._dance_cycle[self._dance_index]
        self._dance_index = (self._dance_index + 1) % len(self._dance_cycle)
        return item

    def _next_action(self) -> tuple[str, float]:
        item = self._action_cycle[self._action_index]
        self._action_index = (self._action_index + 1) % len(self._action_cycle)
        return item

    def _next_expression(self) -> tuple[str, float]:
        item = self._expr_cycle[self._expr_index]
        self._expr_index = (self._expr_index + 1) % len(self._expr_cycle)
        return item

    def plan(self, music_duration: float, beats: Optional[List[float]] = None, energies: Optional[List[float]] = None, seed: Optional[int] = None) -> List[PlannedSegment]:
        rng = random.Random(seed)
        if not beats or len(beats) < 4:
            interval = 2.0
            beats = [i * interval for i in range(int(music_duration / interval) + 1)]
        if beats[-1] < music_duration:
            beats.append(music_duration)
        if not energies or len(energies) < len(beats) - 1:
            energies = [1.0] * (len(beats) - 1)
        arr = np.array(energies[: len(beats) - 1])
        if arr.max() > 0:
            arr = arr / arr.max()
        med = float(np.median(arr)) if arr.size else 0.5
        segments: List[PlannedSegment] = []

        dance_pool = list(self.dances.items())
        action_pool = list(self.actions.items())
        expr_pool = list(self.expressions.items())
        if dance_pool:
            rng.shuffle(dance_pool)
        if action_pool:
            rng.shuffle(action_pool)
        if expr_pool:
            rng.shuffle(expr_pool)
        d_idx = a_idx = e_idx = 0

        def next_dance() -> tuple[str, float]:
            if len(dance_pool) == 0:
                return '', 0
            nonlocal d_idx
            if not dance_pool:
                return self._next_dance()
            if rng.random() < 0.30:
                return rng.choice(dance_pool)
            item = dance_pool[d_idx]
            d_idx = (d_idx + 1) % len(dance_pool)
            return item

        def next_action() -> tuple[str, float]:
            if len(action_pool) == 0:
                return '', 0
            nonlocal a_idx
            if not action_pool:
                return self._next_action()
            if rng.random() < 0.30:
                return rng.choice(action_pool)
            item = action_pool[a_idx]
            a_idx = (a_idx + 1) % len(action_pool)
            return item

        def next_expression() -> tuple[str, float]:
            if len(expr_pool) == 0:
                return '', 0
            nonlocal e_idx
            if not expr_pool:
                return self._next_expression()
            if rng.random() < 0.25:
                return rng.choice(expr_pool)
            item = expr_pool[e_idx]
            e_idx = (e_idx + 1) % len(expr_pool)
            return item

        def fill_expression_chain(a: float, b: float):
            if len(expr_pool) == 0:
                return
            t_expr = a + 0.25
            safety = 0.05
            while t_expr < b - 0.4:
                eid, edur = next_expression()
                max_allow = max(0.6, (b - t_expr) - safety)
                if max_allow <= 0.6:
                    break
                slice_dur = min(max_allow, max(0.6, min(edur, 2.5)))
                segments.append(PlannedSegment(eid, t_expr, slice_dur, 'expression'))
                step = slice_dur + rng.uniform(0.1, 0.3)
                t_expr += step

        def fill_action_chain(a: float, b: float):
            if len(action_pool) == 0:
                return
            t = a
            safety = 0.05
            while t < b - 0.4:
                aid, adur = next_action()
                max_allow = max(0.6, (b - t) - safety)
                if max_allow <= 0.6:
                    break
                slice_dur = min(max_allow, max(0.8, min(adur, 2.2)))
                segments.append(PlannedSegment(aid, t, slice_dur, 'action'))
                t += slice_dur + rng.uniform(0.05, 0.2)

        i = 0
        while i < len(beats) - 1:
            window_energy = arr[i : min(i + 2, len(arr))].mean() if arr.size else 0.5
            high = window_energy >= med
            if i + 1 < len(beats) and rng.random() < 0.15:
                group_len = 1
            elif high and i + 3 < len(beats) and rng.random() < 0.6:
                group_len = 3
            else:
                group_len = 2
            start = beats[i]
            end_idx = min(i + group_len, len(beats) - 1)
            end = beats[end_idx]
            dur = max(0.4, end - start)
            action_bias = 0.5 if high else 0.65
            if rng.random() < action_bias:
                aid, _ = next_action()
                segments.append(PlannedSegment(aid, start, dur, 'action'))
                fill_expression_chain(start, end)
            else:
                did, _ = next_dance()
                segments.append(PlannedSegment(did, start, dur, 'dance'))
                fill_expression_chain(start, end)
            i = end_idx

        # Always end with an ACTION that finishes exactly at the music end.
        action_items_sorted = sorted(self.actions.items(), key=lambda kv: kv[1])
        fit_actions = [(aid, alen) for aid, alen in action_items_sorted if alen <= music_duration]
        if fit_actions:
            close_id, close_len = fit_actions[-1]
            close_start = max(0.0, music_duration - close_len)
            segments = [s for s in segments if (s.start_time + s.duration) <= close_start]
            # Fill entire gap before closing with actions + expressions (no idle)
            last_end = max((s.start_time + s.duration) for s in segments) if segments else 0.0
            if last_end < close_start - 0.05:
                fill_action_chain(last_end, close_start)
                fill_expression_chain(last_end, close_start)
            segments.append(PlannedSegment(close_id, close_start, close_len, 'action'))
            fill_expression_chain(close_start, music_duration)
        else:
            if action_items_sorted:
                close_id, _ = action_items_sorted[0]
            else:
                close_id = list(self.expressions.keys())[0]
            segments = []
            segments.append(PlannedSegment(close_id, 0.0, max(0.2, music_duration), 'action'))
            fill_expression_chain(0.0, music_duration)

        cleaned: List[PlannedSegment] = []
        for s in segments:
            if s.action_type == 'expression' and s.start_time + s.duration > music_duration:
                s = PlannedSegment(
                    s.action_id,
                    s.start_time,
                    max(0.4, music_duration - s.start_time - 0.05),
                    'expression',
                )
                if s.duration <= 0:
                    continue
            cleaned.append(s)
        cleaned.sort(key=lambda s: (s.start_time, 0 if s.action_type in ('dance', 'action') else 1))
        return cleaned


def detect_beats_and_energy(audio_bytes: bytes, sr: int = 22050) -> tuple[List[float], List[float]]:
    if not librosa:
        return [], []
    try:
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=sr, mono=True)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, trim=False)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        energies: List[float] = []
        for j in range(len(beat_frames)-1):
            a = beat_frames[j]; b = beat_frames[j+1]
            energies.append(float(onset_env[a:b].sum()))
        return beat_times.tolist(), energies
    except Exception:
        return [], []


def fetch_audio(url: str) -> bytes:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


async def build_activity_json(music_name: str, music_url: str, music_duration: float, robot_model_id: str) -> dict:
    durations = await load_all_durations_with_exclusion(robot_model_id)
    planner = MusicActivityPlanner(durations)
    beats: List[float] = []
    energies: List[float] = []
    seed = None
    try:
        audio_bytes = fetch_audio(music_url)
        beats, energies = detect_beats_and_energy(audio_bytes)
        import hashlib
        h = hashlib.sha1(audio_bytes[:100000]).hexdigest()
        seed = int(h[:8], 16)
    except Exception:
        beats, energies = [], []
    plan = planner.plan(music_duration, beats, energies, seed)
    activity_actions = []
    golden = 0.618033988749895
    def gen_color(idx: int, atype: str):
        h = (idx * golden) % 1.0
        if atype == 'expression':
            s, v = 0.85, 0.95
        else:
            s, v = 0.70, 0.90
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return {'a': 0, 'r': int(r*255), 'g': int(g*255), 'b': int(b*255)}

    for idx, seg in enumerate(plan):
        # atype = 'expression' if seg.action_id in EXPRESSION_DURATIONS else 'dance'
        atype = 'expression' if seg.action_id in planner.expressions else 'dance'

        activity_actions.append({
            'action_id': seg.action_id,
            'start_time': round(seg.start_time, 2),
            'duration': round(seg.duration, 2),
            'action_type': atype,
            'color': gen_color(idx, atype)
        })
    return {
        'type': 'dance_with_music',
        'data': {
            'music_info': {
                'name': music_name,
                'music_file_url': music_url,
                'duration': music_duration
            },
            'activity': {
                'actions': activity_actions
            },
            'robot_model_id': robot_model_id
        }

    }

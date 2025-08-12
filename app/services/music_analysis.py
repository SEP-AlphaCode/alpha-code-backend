from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import io
import random
import requests
import colorsys
try:
    import librosa
except Exception:
    librosa = None  # Fallback if not installed yet
import numpy as np

# Durations (ms) provided by user for dances, actions, expressions (emo/codemao/w_basic etc.)
# We'll normalize everything to seconds when used.
DANCE_DURATIONS_MS: Dict[str, int] = {
    'dance_0001en': 48752,
    'dance_0002en': 51980,
    'dance_0003en': 71100,
    'dance_0004en': 43432,
    'dance_0005en': 50972,
    'dance_0006en': 213100,
    'dance_0007en': 64416,
    'dance_0008en': 49491,
    'dance_0009en': 64168,
    'dance_0010en': 34731,
    'dance_0011en': 109368,
}

ACTION_DURATIONS_MS: Dict[str, int] = {
    'action_020': 6200,
    '009': 1700,
    '010': 2200,
    'random_short2': 3300,
    '017': 3500,
    '015': 3500,
    '011': 1900,
    'random_short3': 3300,
    'random_short4': 3200,
    '028': 2000,
    '037': 2300,
    '038': 3000,
    'Surveillance_001': 2500,
    'Surveillance_003': 2200,
    'Surveillance_004': 2250,
    'Surveillance_006': 2500,
    'action_014': 4300,
    'action_016': 3900,
    'action_012': 4500,
    'action_004': 3700,
    'action_005': 2600,
    'action_018': 5500,
    'action_011': 4900,
    'action_013': 4500,
    'action_015': 4400,  # duplicate key allowed? keep last
    'action_019': 3900,
}

EXPRESSION_DURATIONS_MS: Dict[str, int] = {
    'codemao1': 4599,
    'codemao2': 2039,
    'codemao3': 4439,
    'codemao4': 7999,
    'codemao5': 2319,
    'codemao6': 4599,
    'codemao7': 1159,
    'codemao8': 1079,
    'codemao9': 7999,
    'codemao10': 2039,
    'codemao11': 2839,
    'codemao12': 839,
    'codemao13': 2999,
    'codemao14': 7279,
    'codemao15': 1839,
    'codemao16': 1319,
    'codemao17': 2039,
    'codemao18': 2319,
    'codemao19': 2679,
    'codemao20': 1039,
    'w_basic_0007_1': 2999,
    'w_basic_0003_1': 1999,
    'w_basic_0005_1': 4999,
    'w_basic_0010_1': 4999,
    'w_basic_0011_1': 4999,
    'w_basic_0012_1': 4999,
    'emo_007': 3000,
    'emo_010': 4240,
    'emo_016': 2040,
    'emo_028': 2200,
    'emo_008': 3520,
    'emo_014': 3440,
    'emo_009': 4040,
    'emo_011': 2800,
    'emo_023': 3120,
    'emo_013': 2440,
    'emo_015': 2999,
    'emo_026': 2999,
    'emo_022': 3000,
    'emo_019': 2680,
    'emo_020': 2999,
    'emo_027': 6960,
    'emo_029': 1520,
    'emo_030': 2999,
    'emo_031': 3800,
    'emo_032': 2840,
}

# Convert ms dicts to seconds (float) for scheduling
DANCE_DURATIONS = {k: v / 1000.0 for k, v in DANCE_DURATIONS_MS.items()}
ACTION_DURATIONS = {k: v / 1000.0 for k, v in ACTION_DURATIONS_MS.items()}
EXPRESSION_DURATIONS = {k: v / 1000.0 for k, v in EXPRESSION_DURATIONS_MS.items()}

@dataclass
class PlannedSegment:
    action_id: str
    start_time: float
    duration: float
    action_type: str  # 'dance' | 'action' | 'expression'
    color: Tuple[int, int, int, int] = (0, 255, 0, 0)  # (a,r,g,b) just placeholder

COLOR_PALETTE = {
    'dance': (0, 255, 0, 0),
    'expression': (0, 0, 255, 0),
    'action': (0, 0, 0, 255),
}

class MusicActivityPlanner:
    """Beat-aware planner.

    Steps:
    1. Detect beats from audio (librosa).
    2. Use beats to schedule base movement segments (alternating dance/action treated as dance type) spanning intervals between selected beats.
    3. Inject expressions frequently (every 2-3 beat intervals) overlaying base movement.
    4. Force last exact-ending dance: choose a dance whose (possibly truncated or stretched logically) duration ends at music end.
    """

    def __init__(self):
        self.dances = DANCE_DURATIONS
        self.actions = ACTION_DURATIONS
        self.expressions = EXPRESSION_DURATIONS
        # Pre-sort lists for selection strategies
        self._dance_cycle = list(self.dances.items())
        self._action_cycle = list(self.actions.items())
        self._expr_cycle = list(self.expressions.items())
        self._dance_index = 0
        self._action_index = 0
        self._expr_index = 0

    def _next_dance(self) -> Tuple[str, float]:
        item = self._dance_cycle[self._dance_index]
        self._dance_index = (self._dance_index + 1) % len(self._dance_cycle)
        return item

    def _next_action(self) -> Tuple[str, float]:
        item = self._action_cycle[self._action_index]
        self._action_index = (self._action_index + 1) % len(self._action_cycle)
        return item

    def _next_expression(self) -> Tuple[str, float]:
        item = self._expr_cycle[self._expr_index]
        self._expr_index = (self._expr_index + 1) % len(self._expr_cycle)
        return item

    def plan(self, music_duration: float, beats: Optional[List[float]] = None, energies: Optional[List[float]] = None, seed: Optional[int] = None) -> List[PlannedSegment]:
        rng = random.Random(seed)
        # Fallback beats grid
        if not beats or len(beats) < 4:
            interval = 2.0
            beats = [i*interval for i in range(int(music_duration/interval)+1)]
        if beats[-1] < music_duration:
            beats.append(music_duration)
        # Energies normalization
        if not energies or len(energies) < len(beats)-1:
            energies = [1.0]*(len(beats)-1)
        arr = np.array(energies[:len(beats)-1])
        if arr.max() > 0:
            arr = arr / arr.max()
        med = float(np.median(arr)) if arr.size else 0.5
        segments: List[PlannedSegment] = []

        # Build per-song shuffled pools so selection isn't monotonic
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

        def next_dance() -> Tuple[str, float]:
            nonlocal d_idx
            if not dance_pool:
                return self._next_dance()
            # 30% pick a random entry, otherwise cycle
            if rng.random() < 0.30:
                return rng.choice(dance_pool)
            item = dance_pool[d_idx]
            d_idx = (d_idx + 1) % len(dance_pool)
            return item

        def next_action() -> Tuple[str, float]:
            nonlocal a_idx
            if not action_pool:
                return self._next_action()
            if rng.random() < 0.30:
                return rng.choice(action_pool)
            item = action_pool[a_idx]
            a_idx = (a_idx + 1) % len(action_pool)
            return item

        def next_expression() -> Tuple[str, float]:
            nonlocal e_idx
            if not expr_pool:
                return self._next_expression()
            if rng.random() < 0.25:
                return rng.choice(expr_pool)
            item = expr_pool[e_idx]
            e_idx = (e_idx + 1) % len(expr_pool)
            return item

        # helper: fill expressions continuously between [a, b)
        def fill_expression_chain(a: float, b: float):
            t_expr = a + 0.25
            safety = 0.05
            while t_expr < b - 0.4:
                eid, edur = next_expression()
                # choose a practical slice (cap long expressions to fit nicely)
                max_allow = max(0.6, (b - t_expr) - safety)
                if max_allow <= 0.6:
                    break
                # prefer 1.0–2.5s slices for frequent changes
                slice_dur = min(max_allow, max(0.6, min(edur, 2.5)))
                segments.append(PlannedSegment(eid, t_expr, slice_dur, 'expression', COLOR_PALETTE['expression']))
                # small gap before next expression to create clear change
                step = slice_dur + rng.uniform(0.1, 0.3)
                t_expr += step
        
        # helper: fill rapid action chain between [a, b)
        def fill_action_chain(a: float, b: float):
            t = a
            safety = 0.05
            while t < b - 0.4:
                aid, adur = next_action()
                max_allow = max(0.6, (b - t) - safety)
                if max_allow <= 0.6:
                    break
                # prefer short, punchy actions 0.8–2.2s
                slice_dur = min(max_allow, max(0.8, min(adur, 2.2)))
                segments.append(PlannedSegment(aid, t, slice_dur, 'action', COLOR_PALETTE['action']))
                t += slice_dur + rng.uniform(0.05, 0.2)
        i = 0
        while i < len(beats)-1:
            # energy for next window
            window_energy = arr[i:min(i+2, len(arr))].mean() if arr.size else 0.5
            high = window_energy >= med
            # choose group length
            # occasional single-beat groups for variety
            if i+1 < len(beats) and rng.random() < 0.15:
                group_len = 1
            elif high and i+3 < len(beats) and rng.random() < 0.6:
                group_len = 3
            else:
                group_len = 2
            start = beats[i]
            end_idx = min(i+group_len, len(beats)-1)
            end = beats[end_idx]
            dur = max(0.4, end - start)
            # choose movement type with action-biased randomness
            # normal energy: prefer actions ~65%; high energy: closer to 50/50 to allow dances
            action_bias = 0.5 if high else 0.65
            if rng.random() < action_bias:
                aid, _ = next_action()
                segments.append(PlannedSegment(aid, start, dur, 'action', COLOR_PALETTE['action']))
                fill_expression_chain(start, end)
            else:
                did, _ = next_dance()
                segments.append(PlannedSegment(did, start, dur, 'dance', COLOR_PALETTE['dance']))
                fill_expression_chain(start, end)
            i = end_idx
        # Closing segment: prefer a dance that fits; if none fits, use actions instead of forcing a dance
        dance_items_sorted = sorted(self.dances.items(), key=lambda kv: kv[1])
        fit_candidates = [(did, dlen) for did, dlen in dance_items_sorted if dlen <= music_duration]
        if fit_candidates:
            # pick the longest dance that still fits to look natural
            close_id, close_len = fit_candidates[-1]
            close_start = max(0.0, music_duration - close_len)
            # Remove any segments that overlap the closing window [close_start, music_duration]
            segments = [s for s in segments if (s.start_time + s.duration) <= close_start]

            # Optional pre-closing window: allow chaining actions right before the final dance
            if close_start > 0.6:
                last_end = max((s.start_time + s.duration) for s in segments) if segments else 0.0
                pre_window = rng.uniform(3.0, 6.0)
                pre_start = max(last_end, close_start - pre_window)
                if close_start - pre_start >= 1.0:
                    fill_action_chain(pre_start, close_start)
                    fill_expression_chain(pre_start, close_start)

            segments.append(PlannedSegment(close_id, close_start, close_len, 'dance', COLOR_PALETTE['dance']))
            # also layer expressions continuously during the closing dance window
            fill_expression_chain(close_start, music_duration)
        else:
            # No dance fits within the song duration: finish with a precise-ending ACTION
            action_items_sorted = sorted(self.actions.items(), key=lambda kv: kv[1])
            fit_actions = [(aid, alen) for aid, alen in action_items_sorted if alen <= music_duration]
            if fit_actions:
                close_id, close_len = fit_actions[-1]  # longest action that still fits
                close_start = max(0.0, music_duration - close_len)
                # Remove any segments that overlap the closing window [close_start, music_duration]
                segments = [s for s in segments if (s.start_time + s.duration) <= close_start]

                # Optional pre-closing window with quick actions and expressions
                if close_start > 0.6:
                    last_end = max((s.start_time + s.duration) for s in segments) if segments else 0.0
                    pre_window = rng.uniform(2.0, 4.0)
                    pre_start = max(last_end, close_start - pre_window)
                    if close_start - pre_start >= 0.8:
                        fill_action_chain(pre_start, close_start)
                        fill_expression_chain(pre_start, close_start)

                segments.append(PlannedSegment(close_id, close_start, close_len, 'action', COLOR_PALETTE['action']))
                # layer expressions during the closing action window
                fill_expression_chain(close_start, music_duration)
            else:
                # Extremely short song: use the shortest action trimmed to end exactly at music end
                if action_items_sorted:
                    close_id, _ = action_items_sorted[0]
                else:
                    # fallback to any expression if actions list is empty (shouldn't happen)
                    close_id = list(self.expressions.keys())[0]
                # Clear any prior segments; do one final block ending exactly at song end
                segments = []
                segments.append(PlannedSegment(close_id, 0.0, max(0.2, music_duration), 'action', COLOR_PALETTE['action']))
                fill_expression_chain(0.0, music_duration)
        # trim expression overflow
        cleaned: List[PlannedSegment] = []
        for s in segments:
            # Trim any expression that might accidentally exceed boundaries
            if s.action_type == 'expression' and s.start_time + s.duration > music_duration:
                s = PlannedSegment(s.action_id, s.start_time, max(0.4, music_duration - s.start_time - 0.05), 'expression', s.color)
                if s.duration <= 0:
                    continue
            cleaned.append(s)
        cleaned.sort(key=lambda s: (s.start_time, 0 if s.action_type in ('dance','action') else 1))
        return cleaned

def detect_beats_and_energy(audio_bytes: bytes, sr: int = 22050) -> Tuple[List[float], List[float]]:
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


def build_activity_json(music_name: str, music_url: str, music_duration: float) -> dict:
    planner = MusicActivityPlanner()
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
    random.seed(2025)
    def gen_color(idx: int, atype: str):
        h = (idx * golden) % 1.0
        if atype == 'expression':
            s, v = 0.85, 0.95
        else:
            s, v = 0.70, 0.90
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return {'a': 0, 'r': int(r*255), 'g': int(g*255), 'b': int(b*255)}

    for idx, seg in enumerate(plan):
        atype = 'expression' if seg.action_id in EXPRESSION_DURATIONS else 'dance'
        activity_actions.append({
            'action_id': seg.action_id,
            'start_time': round(seg.start_time, 2),
            'duration': round(seg.duration, 2),
            'action_type': atype,
            'color': gen_color(idx, atype)
        })
    return {
        'type': 'dance-with-music',
        'data': {
            'music_info': {
                'name': music_name,
                'music_file_url': music_url,
                'duration': music_duration
            },
            'activity': {
                'actions': activity_actions
            }
        }
    }

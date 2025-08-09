"""
AI Choreographer Service
Tạo choreography tự động dựa trên phân tích âm nhạc và AI
"""

from typing import List, Dict, Any
from datetime import datetime
import uuid
import random

from app.services.alpha_mini_actions import (
    alpha_mini_actions_service,
    AlphaAction,
    AlphaExpression,
)
from app.models.schemas import (
    MusicAnalysisResult,
    ChoreographyData,
    ChoreographySegment,
    RobotActionData,
)


class AIChoreographerService:
    """Service tạo choreography thông minh dựa trên AI và phân tích nhạc"""

    def __init__(self):
        self.actions_service = alpha_mini_actions_service
        # Track recent selections to increase variety
        self._recent_actions: List[str] = []
        self._recent_expressions: List[str] = []
        self._recent_max = 6
        # Switch OFF dance-only; use actions+expressions so robot doesn't play its own music
        self.dance_only_mode = False
        # Enable action-only continuous mode
        self.full_body_mode = True
        # Allowed action names for intro/outro and continuous small moves
        self._allowed_action_names = {"017", "random_short3", "random_short4", "037", "038"}

    async def create_intelligent_choreography(self, music_analysis: MusicAnalysisResult) -> ChoreographyData:
        """Tạo choreography thông minh từ kết quả phân tích nhạc"""
        # Reset recent caches per run
        self._recent_actions.clear()
        self._recent_expressions.clear()

        # 1) Phân tích cảm xúc tổng quan từ đặc trưng âm nhạc
        emotion_analysis = self._analyze_music_emotion(music_analysis)

        # 2) Tạo các segments theo beats hoặc theo thời gian
        segments = self._create_segments(music_analysis, emotion_analysis)

        # 3) Gói dữ liệu choreography
        choreography_id = str(uuid.uuid4())
        choreography = ChoreographyData(
            id=choreography_id,
            music_analysis_id=music_analysis.id,
            filename=music_analysis.filename,
            duration=music_analysis.duration,
            segments=segments,
            style="ai_generated",
            created_at=datetime.now().isoformat(),
            metadata={
                "emotion_analysis": emotion_analysis,
                "total_segments": len(segments),
                "total_actions": sum(len(seg.actions) for seg in segments),
            },
        )
        return choreography

    # ------------------------- Emotion analysis -------------------------
    def _analyze_music_emotion(self, music: MusicAnalysisResult) -> Dict[str, Any]:
        tempo = music.tempo or 120.0

        # Energy mean từ energy_analysis
        energy_mean = 0.1
        if music.energy_analysis and isinstance(music.energy_analysis, dict):
            energy_mean = float(music.energy_analysis.get("energy_mean", 0.1))

        # Spectral centroid mean từ spectral_features
        spectral_centroid_mean = 1000.0
        if music.spectral_features and isinstance(music.spectral_features, dict):
            spectral_centroid_mean = float(music.spectral_features.get("spectral_centroid_mean", 1000.0))

        # Chuẩn hóa về [0,1]
        energy_score = max(0.0, min(1.0, energy_mean * 2.0))  # energy_mean ~0-0.5
        spectral_brightness = max(0.0, min(1.0, spectral_centroid_mean / 4000.0))

        # Phân loại tempo
        tempo_category = self._classify_tempo(tempo)

        # Xác định emotion chính
        primary_emotion = self._determine_primary_emotion(energy_score, spectral_brightness, tempo_category)

        # Trọng số cho các emotion phụ
        emotion_weights = self._emotion_weights(energy_score, spectral_brightness, tempo_category, primary_emotion)

        return {
            "primary_emotion": primary_emotion,
            "energy_score": energy_score,
            "spectral_brightness": spectral_brightness,
            "tempo": tempo,
            "tempo_category": tempo_category,
            "emotion_weights": emotion_weights,
        }

    def _classify_tempo(self, tempo: float) -> str:
        if tempo < 60:
            return "very_slow"
        if tempo < 90:
            return "slow"
        if tempo < 120:
            return "moderate"
        if tempo < 140:
            return "fast"
        return "very_fast"

    def _determine_primary_emotion(self, energy: float, spectral: float, tempo_cat: str) -> str:
        scores = {
            "energetic": energy * 0.5 + spectral * 0.2,
            "happy": energy * 0.3 + spectral * 0.2 + 0.1,
            "calm": (1 - energy) * 0.5 + (1 - spectral) * 0.2,
            "powerful": energy * 0.6,
            "gentle": (1 - energy) * 0.6,
            "excited": energy * 0.45 + spectral * 0.35,
            "peaceful": (1 - energy) * 0.4 + (1 - spectral) * 0.3,
            "playful": energy * 0.3 + spectral * 0.3,
        }
        if tempo_cat in ("fast", "very_fast"):
            scores["energetic"] += 0.2
            scores["excited"] += 0.2
            scores["powerful"] += 0.15
        elif tempo_cat in ("slow", "very_slow"):
            scores["calm"] += 0.25
            scores["peaceful"] += 0.2
            scores["gentle"] += 0.2
        return max(scores.items(), key=lambda kv: kv[1])[0]

    def _emotion_weights(self, energy: float, spectral: float, tempo_cat: str, primary: str) -> Dict[str, float]:
        base = {
            "energetic": energy * 0.4 + spectral * 0.2,
            "happy": energy * 0.3 + spectral * 0.2 + 0.1,
            "calm": (1 - energy) * 0.5 + (1 - spectral) * 0.2,
            "powerful": energy * 0.45,
            "gentle": (1 - energy) * 0.45,
            "excited": energy * 0.4 + spectral * 0.35,
            "peaceful": (1 - energy) * 0.35 + (1 - spectral) * 0.3,
            "playful": energy * 0.3 + spectral * 0.25 + 0.05,
            "confident": energy * 0.25 + 0.15,
            "graceful": (1 - energy) * 0.3 + 0.1,
            "athletic": energy * 0.35,
            "friendly": 0.25,
            "balanced": 0.2,
        }
        if tempo_cat == "very_slow":
            base["peaceful"] += 0.3
            base["calm"] += 0.25
            base["gentle"] += 0.2
        elif tempo_cat == "slow":
            base["calm"] += 0.25
            base["gentle"] += 0.2
            base["graceful"] += 0.15
        elif tempo_cat == "moderate":
            base["happy"] += 0.2
            base["friendly"] += 0.2
            base["balanced"] += 0.2
        elif tempo_cat == "fast":
            base["energetic"] += 0.3
            base["excited"] += 0.2
            base["athletic"] += 0.2
        elif tempo_cat == "very_fast":
            base["powerful"] += 0.3
            base["energetic"] += 0.3
            base["excited"] += 0.2
        # Boost primary
        base[primary] *= 1.5
        # Normalize
        s = sum(base.values()) or 1.0
        return {k: v / s for k, v in base.items()}

    # ------------------------- Segments and actions -------------------------
    def _create_segments(self, music: MusicAnalysisResult, emo: Dict[str, Any]) -> List[ChoreographySegment]:
        beats = music.beats or []
        segments: List[ChoreographySegment] = []

        def avg_beat_duration() -> float:
            if not beats or len(beats) < 2:
                return 60.0 / (music.tempo or 120.0)
            diffs = [beats[i + 1] - beats[i] for i in range(len(beats) - 1)]
            return max(0.2, sum(diffs) / len(diffs))

        # Helper to build a segment of dance+expression+light
        def build_segment_actions(start_time: float, end_time: float, is_first: bool, is_last: bool) -> List[RobotActionData]:
            duration = max(0.8, end_time - start_time)
            actions: List[RobotActionData] = []
            # Light spanning the segment
            actions.append(RobotActionData(
                type="light",
                name="mouth_lamp",
                start_time=start_time,
                duration=duration,
                intensity="medium",
                parameters={
                    "color": self._light_color_for_emotion(emo["primary_emotion"]),
                    "mode": "breath" if duration >= 3.0 else "normal",
                },
            ))
            # Intro action at very start
            if is_first and start_time <= 0.01:
                intro_name = self._pick_intro_action()
                actions.append(RobotActionData(
                    type="action",
                    name=intro_name,
                    start_time=max(0.0, start_time - 0.01),
                    duration=min(2.0, duration * 0.3),
                    intensity="medium",
                    parameters={"purpose": "intro"},
                ))
            # Main dance for this segment
            dance_name = self._select_dance_for_segment(emo)
            actions.append(RobotActionData(
                type="dance",
                name=dance_name,
                start_time=start_time + (0.2 if is_first else 0.0),
                duration=duration,
                intensity="high",
                parameters={"source": "dance_only_mode"},
            ))
            # Expression (1 per segment, mid-segment)
            exprs = self._select_expressions_for_segment(emo, 1)
            if exprs:
                actions.append(RobotActionData(
                    type="expression",
                    name=exprs[0].name,
                    start_time=start_time + min(1.0, duration * 0.4),
                    duration=min(2.5, duration * 0.4),
                    intensity=exprs[0].intensity,
                    parameters={"emotion": exprs[0].emotion_type},
                ))
            # Outro near end (only once at last segment)
            if is_last:
                outro_name = self._pick_outro_action()
                end_start = max(start_time, end_time - 1.6)
                actions.append(RobotActionData(
                    type="action",
                    name=outro_name,
                    start_time=end_start,
                    duration=min(1.6, max(0.8, end_time - end_start)),
                    intensity="medium",
                    parameters={"purpose": "outro"},
                ))
            return actions

        if self.dance_only_mode:
            # Build non-overlapping segments from beats (8-beat blocks) or 4s fallback
            built_segments = []
            if len(beats) >= 4:
                step_beats = 8
                beat_len = avg_beat_duration()
                i = 0
                while i < len(beats):
                    start_time = beats[i]
                    if i + step_beats < len(beats):
                        end_time = beats[i + step_beats]
                    else:
                        end_time = min(start_time + step_beats * beat_len, music.duration)
                    built_segments.append((start_time, min(end_time, music.duration)))
                    if end_time >= music.duration:
                        break
                    i += step_beats
            else:
                seg_len = 4.0
                t = 0.0
                while t < max(0.0, music.duration - 0.5):
                    built_segments.append((t, min(t + seg_len, music.duration)))
                    t += seg_len
            # Compose segments with dance+expression+light, and intro/outro
            for idx, (st, et) in enumerate(built_segments):
                actions = build_segment_actions(st, et, is_first=(idx == 0), is_last=(idx == len(built_segments) - 1))
                seg = ChoreographySegment(
                    start_time=st,
                    end_time=et,
                    actions=actions,
                    tempo=music.tempo,
                    energy_level=emo["energy_score"],
                    primary_emotion=emo["primary_emotion"],
                )
                segments.append(seg)
            return segments

        # Mixed/action-only fallback (no dances): non-overlapping 8-beat blocks or 4s
        built_segments = []
        def avg_beat_duration() -> float:
            if not beats or len(beats) < 2:
                return 60.0 / (music.tempo or 120.0)
            diffs = [beats[i + 1] - beats[i] for i in range(len(beats) - 1)]
            return max(0.2, sum(diffs) / len(diffs))
        if len(beats) >= 4:
            step_beats = 8
            beat_len = avg_beat_duration()
            i = 0
            while i < len(beats):
                st = beats[i]
                et = beats[i + step_beats] if i + step_beats < len(beats) else min(st + step_beats * beat_len, music.duration)
                built_segments.append((st, min(et, music.duration)))
                if et >= music.duration:
                    break
                i += step_beats
        else:
            seg_len = 4.0
            t = 0.0
            while t < max(0.0, music.duration - 0.5):
                built_segments.append((t, min(t + seg_len, music.duration)))
                t += seg_len
        for st, et in built_segments:
            duration = max(0.8, et - st)
            actions = self._select_actions_for_segment(emo, duration)
            expressions = self._select_expressions_for_segment(emo, len(actions))
            robot_actions = self._build_robot_actions(actions, expressions, st, duration)
            seg = ChoreographySegment(
                start_time=st,
                end_time=et,
                actions=robot_actions,
                tempo=music.tempo,
                energy_level=emo["energy_score"],
                primary_emotion=emo["primary_emotion"],
            )
            segments.append(seg)
        return segments

    # Map emotion/tempo to dances from the provided list
    def _select_dance_for_segment(self, emo: Dict[str, Any]) -> str:
        tempo_cat = emo.get("tempo_category", "moderate")
        energy = emo.get("energy_score", 0.5)
        fast = ["dance_0001en", "dance_0003en", "dance_0008en", "dance_0011en"]
        moderate = ["dance_0002en", "dance_0006en", "dance_0007en", "dance_0009en"]
        gentle = ["dance_0004en", "dance_0005en", "dance_0013", "custom_0035"]
        if tempo_cat in ("fast", "very_fast") or energy > 0.6:
            pool = fast
        elif tempo_cat in ("slow", "very_slow") or energy < 0.35:
            pool = gentle
        else:
            pool = moderate
        # avoid repeating last selected dance
        recent = set(self._recent_actions)
        candidates = [d for d in pool if d not in recent] or pool
        choice = random.choice(candidates)
        self._recent_actions.append(choice)
        if len(self._recent_actions) > self._recent_max:
            self._recent_actions.pop(0)
        return choice

    # Restrict actions to intro/outro only
    def _pick_intro_action(self) -> str:
        # Prefer raising hands then a wave variant
        options = ["017", "random_short3", "random_short4"]
        for name in options:
            if name not in self._recent_actions:
                return name
        return random.choice(options)

    def _pick_outro_action(self) -> str:
        options = ["037", "038", "random_short3", "random_short4"]
        for name in options:
            if name not in self._recent_actions:
                return name
        return random.choice(options)

    # Pool of allowed actions to avoid unsuitable moves and robot music
    def _allowed_action_pool(self) -> List[AlphaAction]:
        pool = []
        all_actions = self.actions_service.get_all_actions() or []
        for a in all_actions:
            if a.name in self._allowed_action_names:
                pool.append(a)
        return pool

    def _select_actions_for_segment(self, emo: Dict[str, Any], seg_duration: float) -> List[AlphaAction]:
        # In action-only mode, schedule only allowed small moves, packed for continuity
        if getattr(self, "full_body_mode", False) and not getattr(self, "dance_only_mode", False):
            base_pool = self._allowed_action_pool()
            if not base_pool:
                return []
            # remove recently used
            names_recent = set(self._recent_actions)
            pool = [a for a in base_pool if a.name not in names_recent] or base_pool
            # more actions for longer segments
            target = 2 if seg_duration < 3.0 else 3
            if seg_duration >= 6.0:
                target = 4
            chosen: List[AlphaAction] = []
            random.shuffle(pool)
            for a in pool:
                if len(chosen) >= target:
                    break
                chosen.append(a)
            # if not enough, fill by reusing but avoid immediate repeats across segments
            if len(chosen) < target:
                for a in base_pool:
                    if a.name not in {x.name for x in chosen}:
                        chosen.append(a)
                        if len(chosen) >= target:
                            break
            # update recent
            for a in chosen:
                self._recent_actions.append(a.name)
                if len(self._recent_actions) > self._recent_max:
                    self._recent_actions.pop(0)
            return chosen

        # Default previous behavior (won't be used when full_body_mode is on)
        # Prefer 1-2 actions per segment for clarity
        num_actions = 1 if seg_duration < 3.0 else 2
        primary = emo["primary_emotion"]
        weights = emo.get("emotion_weights", {})
        chosen: List[AlphaAction] = []
        def filtered_pool(emotion: str) -> List[AlphaAction]:
            pool_all = self.actions_service.get_actions_by_emotion(emotion) or []
            pool = [a for a in pool_all if a.category != "dance"]
            names_recent = set(self._recent_actions)
            pool = [a for a in pool if a.name not in names_recent]
            return pool
        main_pool = filtered_pool(primary)
        if main_pool:
            a = random.choice(main_pool)
            chosen.append(a)
        emo_choices = [e for e, w in weights.items() if w > 0.08 and e != primary]
        emo_weights = [weights[e] for e in emo_choices] or [1.0]
        while len(chosen) < num_actions and emo_choices:
            e = random.choices(emo_choices, weights=emo_weights, k=1)[0]
            pool = filtered_pool(e)
            if not pool:
                fallback = [a for a in (self.actions_service.get_all_actions() or [])
                            if a.category != 'dance' and a.name not in self._recent_actions]
                if not fallback:
                    break
                chosen.append(random.choice(fallback))
            else:
                names = {a.name for a in chosen}
                pool2 = [a for a in pool if a.name not in names] or pool
                chosen.append(random.choice(pool2))
        for a in chosen:
            self._recent_actions.append(a.name)
            if len(self._recent_actions) > self._recent_max:
                self._recent_actions.pop(0)
        return chosen

    def _select_expressions_for_segment(self, emo: Dict[str, Any], num_actions: int) -> List[AlphaExpression]:
        # Keep expressions (1 per segment)
        primary = emo["primary_emotion"]
        exprs = self.actions_service.get_expressions_by_emotion(primary) or []
        if not exprs:
            return []
        names_recent = set(self._recent_expressions)
        pool = [e for e in exprs if e.name not in names_recent] or exprs
        selected = [random.choice(pool)]
        for e in selected:
            self._recent_expressions.append(e.name)
            if len(self._recent_expressions) > self._recent_max:
                self._recent_expressions.pop(0)
        return selected

    def _light_color_for_emotion(self, emotion: str) -> str:
        # Map only to supported colors {red, green, blue, yellow, purple, cyan, white}
        return {
            "energetic": "red",
            "happy": "yellow",
            "excited": "yellow",
            "powerful": "red",
            "calm": "blue",
            "peaceful": "blue",
            "gentle": "green",
            "graceful": "purple",
            "playful": "purple",
            "confident": "yellow",
            "athletic": "red",
            "friendly": "yellow",
            "balanced": "white",
        }.get(emotion, "white")

    def _build_robot_actions(
        self,
        actions: List[AlphaAction],
        expressions: List[AlphaExpression],
        start: float,
        duration: float,
    ) -> List[RobotActionData]:
        result: List[RobotActionData] = []
        # Light across segment
        result.append(RobotActionData(
            type="light",
            name="mouth_lamp",
            start_time=start,
            duration=duration,
            intensity="medium",
            parameters={
                "color": self._light_color_for_emotion(expressions[0].emotion_type if expressions else "happy"),
                "mode": "breath" if duration >= 3.0 else "normal",
            },
        ))
        # Build sequence: prefer actions only in full_body_mode (no dance)
        ordered: List[Dict[str, Any]] = []
        if getattr(self, "full_body_mode", False) and not getattr(self, "dance_only_mode", False):
            for a in actions:
                ordered.append({"kind": "action", "obj": a})
        else:
            ai = 0
            ei = 0
            while ai < len(actions) or ei < len(expressions):
                if ai < len(actions):
                    ordered.append({"kind": "action", "obj": actions[ai]})
                    ai += 1
                if ei < len(expressions):
                    ordered.append({"kind": "expression", "obj": expressions[ei]})
                    ei += 1
        slots = max(1, len(ordered))
        slot_dur = max(0.8, duration / slots) if getattr(self, "full_body_mode", False) else max(0.6, duration / slots)
        t = start
        for item in ordered:
            if item["kind"] == "action":
                a: AlphaAction = item["obj"]
                result.append(RobotActionData(
                    type="action",
                    name=a.name,
                    start_time=t,
                    duration=slot_dur,
                    intensity=a.intensity,
                    parameters={"purpose": "move"},
                ))
            else:
                e: AlphaExpression = item["obj"]
                result.append(RobotActionData(
                    type="expression",
                    name=e.name,
                    start_time=t,
                    duration=min(2.5, slot_dur),
                    intensity=e.intensity,
                    parameters={"emotion": e.emotion_type},
                ))
            t += slot_dur
        return result


# Global instance
ai_choreographer_service = AIChoreographerService()

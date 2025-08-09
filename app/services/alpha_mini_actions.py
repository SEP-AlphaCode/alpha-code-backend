"""
Alpha Mini Robot Built-in Actions và Expressions
Định nghĩa tất cả các hành động và biểu cảm có sẵn của robot Alpha Mini
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

@dataclass
class AlphaAction:
    """Định nghĩa một hành động của Alpha Mini"""
    name: str
    description: str
    can_interrupt: bool
    category: str
    intensity: str  # low, medium, high
    duration_estimate: float  # giây
    emotion_type: str  # happy, sad, energetic, calm, etc.

@dataclass
class AlphaExpression:
    """Định nghĩa một biểu cảm của Alpha Mini"""
    name: str
    description: str
    emotion_type: str
    intensity: str  # low, medium, high

class ActionCategory(Enum):
    DANCE = "dance"
    BASIC_ACTION = "basic_action"
    EXPRESSION = "expression"
    GREETING = "greeting"
    EMOTION = "emotion"

class AlphaMiniActionsService:
    """Service quản lý tất cả actions và expressions của Alpha Mini"""
    
    def __init__(self):
        self.built_in_dances = self._init_built_in_dances()
        self.built_in_actions = self._init_built_in_actions()
        self.built_in_expressions = self._init_built_in_expressions()
    
    def _init_built_in_dances(self) -> Dict[str, AlphaAction]:
        """Khởi tạo các điệu nhảy có sẵn"""
        return {
            "w_stand_0001": AlphaAction("w_stand_0001", "Hiccup", True, ActionCategory.BASIC_ACTION.value, "low", 2.0, "funny"),
            "w_stand_0002": AlphaAction("w_stand_0002", "Fart", True, ActionCategory.BASIC_ACTION.value, "low", 1.5, "funny"),
            "w_stand_0003": AlphaAction("w_stand_0003", "Stretching", True, ActionCategory.BASIC_ACTION.value, "medium", 3.0, "calm"),
            "w_stand_0008": AlphaAction("w_stand_0008", "Sneeze", True, ActionCategory.BASIC_ACTION.value, "low", 1.0, "funny"),
            "w_stand_0009": AlphaAction("w_stand_0009", "Tickle", True, ActionCategory.BASIC_ACTION.value, "medium", 2.5, "happy"),
            "w_stand_0010": AlphaAction("w_stand_0010", "Scare", True, ActionCategory.BASIC_ACTION.value, "high", 2.0, "surprise"),
            
            # Các điệu nhảy chính
            "dance_0001en": AlphaAction("dance_0001en", "Healthy Song and Dance", False, ActionCategory.DANCE.value, "high", 15.0, "energetic"),
            "dance_0002en": AlphaAction("dance_0002en", "Shaolin Hero Dance", False, ActionCategory.DANCE.value, "high", 12.0, "powerful"),
            "dance_0003en": AlphaAction("dance_0003en", "Youth Training Manual Dance", False, ActionCategory.DANCE.value, "high", 18.0, "energetic"),
            "dance_0004en": AlphaAction("dance_0004en", "Little Star", False, ActionCategory.DANCE.value, "medium", 10.0, "gentle"),
            "dance_0005en": AlphaAction("dance_0005en", "Grass Dance", False, ActionCategory.DANCE.value, "medium", 8.0, "calm"),
            "dance_0006en": AlphaAction("dance_0006en", "Seaweed Dance", False, ActionCategory.DANCE.value, "medium", 12.0, "flowing"),
            "dance_0007en": AlphaAction("dance_0007en", "I love taking a bath", False, ActionCategory.DANCE.value, "medium", 10.0, "happy"),
            "dance_0008en": AlphaAction("dance_0008en", "Chongerfei", False, ActionCategory.DANCE.value, "high", 14.0, "energetic"),
            "dance_0009en": AlphaAction("dance_0009en", "Learn to Meow", False, ActionCategory.DANCE.value, "medium", 8.0, "cute"),
            "dance_0011en": AlphaAction("dance_0011en", "Dura Dance", False, ActionCategory.DANCE.value, "high", 16.0, "energetic"),
            "dance_0013": AlphaAction("dance_0013", "Buddha Girl", False, ActionCategory.DANCE.value, "medium", 12.0, "graceful"),
            "custom_0035": AlphaAction("custom_0035", "Happy birthday", False, ActionCategory.DANCE.value, "medium", 8.0, "happy"),
        }
    
    def _init_built_in_actions(self) -> Dict[str, AlphaAction]:
        """Khởi tạo các hành động cơ bản"""
        return {
            "009": AlphaAction("009", "Reset", True, ActionCategory.BASIC_ACTION.value, "low", 2.0, "neutral"),
            "016": AlphaAction("016", "Golden Rooster Independent", False, ActionCategory.BASIC_ACTION.value, "medium", 5.0, "balanced"),
            "010": AlphaAction("010", "Laughing", True, ActionCategory.EMOTION.value, "medium", 3.0, "happy"),
            "random_short2": AlphaAction("random_short2", "Hug", True, ActionCategory.GREETING.value, "medium", 2.0, "affectionate"),
            "027": AlphaAction("027", "Sit down", False, ActionCategory.BASIC_ACTION.value, "low", 3.0, "calm"),
            "031": AlphaAction("031", "Squat", False, ActionCategory.BASIC_ACTION.value, "medium", 2.0, "neutral"),
            "021": AlphaAction("021", "Bent over", False, ActionCategory.BASIC_ACTION.value, "medium", 2.0, "neutral"),
            "018": AlphaAction("018", "Raise your right leg", False, ActionCategory.BASIC_ACTION.value, "medium", 3.0, "balanced"),
            "019": AlphaAction("019", "Raise left leg", False, ActionCategory.BASIC_ACTION.value, "medium", 3.0, "balanced"),
            "017": AlphaAction("017", "Raise your hands", True, ActionCategory.BASIC_ACTION.value, "medium", 2.0, "victorious"),
            "015": AlphaAction("015", "Welcome", True, ActionCategory.GREETING.value, "medium", 2.0, "friendly"),
            "011": AlphaAction("011", "Nodding", True, ActionCategory.BASIC_ACTION.value, "low", 1.0, "agreeing"),
            "random_short3": AlphaAction("random_short3", "Waving left hand", True, ActionCategory.GREETING.value, "low", 1.5, "friendly"),
            "random_short4": AlphaAction("random_short4", "Waving right hand", True, ActionCategory.GREETING.value, "low", 1.5, "friendly"),
            "028": AlphaAction("028", "Right Lunge", True, ActionCategory.BASIC_ACTION.value, "medium", 2.0, "athletic"),
            "037": AlphaAction("037", "Shaking his head", True, ActionCategory.BASIC_ACTION.value, "low", 1.0, "disagreeing"),
            "038": AlphaAction("038", "Tilt head", True, ActionCategory.BASIC_ACTION.value, "low", 1.0, "curious"),
            "Surveillance_001": AlphaAction("Surveillance_001", "Say hello", True, ActionCategory.GREETING.value, "medium", 2.0, "friendly"),
            "Surveillance_003": AlphaAction("Surveillance_003", "Handshake", True, ActionCategory.GREETING.value, "medium", 3.0, "formal"),
            "Surveillance_004": AlphaAction("Surveillance_004", "Blow kisses", True, ActionCategory.EMOTION.value, "medium", 2.0, "affectionate"),
            "Surveillance_006": AlphaAction("Surveillance_006", "Selling cute", True, ActionCategory.EMOTION.value, "medium", 3.0, "cute"),
            "007": AlphaAction("007", "Sit and stand", False, ActionCategory.BASIC_ACTION.value, "medium", 4.0, "neutral"),
            "action_014": AlphaAction("action_014", "Invite", True, ActionCategory.GREETING.value, "medium", 2.0, "welcoming"),
            "action_016": AlphaAction("action_016", "Goodbye", True, ActionCategory.GREETING.value, "medium", 2.0, "farewell"),
            "action_012": AlphaAction("action_012", "Seeking hug", True, ActionCategory.EMOTION.value, "medium", 2.5, "needy"),
            "action_004": AlphaAction("action_004", "Wow", True, ActionCategory.EMOTION.value, "high", 1.5, "amazed"),
            "action_005": AlphaAction("action_005", "Like", True, ActionCategory.EMOTION.value, "medium", 1.5, "approval"),
            "action_006": AlphaAction("action_006", "OK", True, ActionCategory.BASIC_ACTION.value, "low", 1.0, "agreeing"),
            "action_018": AlphaAction("action_018", "Hey ha", True, ActionCategory.EMOTION.value, "high", 2.0, "excited"),
            "action_020": AlphaAction("action_020", "嘚瑟", True, ActionCategory.EMOTION.value, "medium", 2.0, "proud"),
            "action_011": AlphaAction("action_011", "Pretend to fly", True, ActionCategory.BASIC_ACTION.value, "high", 4.0, "playful"),
            "action_013": AlphaAction("action_013", "Make faces", True, ActionCategory.EMOTION.value, "medium", 2.0, "funny"),
            "action_015": AlphaAction("action_015", "Ass Twist", True, ActionCategory.DANCE.value, "medium", 3.0, "playful"),
            "action_007": AlphaAction("action_007", "Kill you", True, ActionCategory.EMOTION.value, "high", 2.0, "aggressive"),
            "action_019": AlphaAction("action_019", "Hold your head", True, ActionCategory.EMOTION.value, "medium", 2.0, "frustrated"),
        }
    
    def _init_built_in_expressions(self) -> Dict[str, AlphaExpression]:
        """Khởi tạo các biểu cảm có sẵn"""
        return {
            # Basic expressions
            "codemao1": AlphaExpression("codemao1", "Looking around", "curious", "low"),
            "codemao2": AlphaExpression("codemao2", "Sad", "sad", "medium"),
            "codemao3": AlphaExpression("codemao3", "Stretching sadness", "sad", "high"),
            "codemao4": AlphaExpression("codemao4", "Falling asleep", "sleepy", "medium"),
            "codemao5": AlphaExpression("codemao5", "Frightened", "scared", "high"),
            "codemao6": AlphaExpression("codemao6", "Sleepy", "sleepy", "medium"),
            "codemao7": AlphaExpression("codemao7", "Strange", "confused", "medium"),
            "codemao8": AlphaExpression("codemao8", "Surprised", "surprised", "high"),
            "codemao9": AlphaExpression("codemao9", "Sneeze", "neutral", "low"),
            "codemao10": AlphaExpression("codemao10", "Exciting", "excited", "high"),
            "codemao11": AlphaExpression("codemao11", "Fighting Spirit", "determined", "high"),
            "codemao12": AlphaExpression("codemao12", "Hard work", "focused", "medium"),
            "codemao13": AlphaExpression("codemao13", "Question", "confused", "medium"),
            "codemao14": AlphaExpression("codemao14", "Wake up", "alert", "medium"),
            "codemao15": AlphaExpression("codemao15", "Distress", "worried", "medium"),
            "codemao16": AlphaExpression("codemao16", "Cheap laugh", "amused", "medium"),
            "codemao17": AlphaExpression("codemao17", "Depressed", "sad", "high"),
            "codemao18": AlphaExpression("codemao18", "Desire", "wanting", "medium"),
            "codemao19": AlphaExpression("codemao19", "Love", "loving", "high"),
            "codemao20": AlphaExpression("codemao20", "Blink", "neutral", "low"),
            
            # W type expressions
            "w_basic_0007-1": AlphaExpression("w_basic_0007-1", "W type mobile", "neutral", "low"),
            "w_basic_0003-1": AlphaExpression("w_basic_0003-1", "Look right", "curious", "low"),
            "w_basic_0005-1": AlphaExpression("w_basic_0005-1", "Look left", "curious", "low"),
            "w_basic_0010-1": AlphaExpression("w_basic_0010-1", "Look up", "curious", "low"),
            "w_basic_0011-1": AlphaExpression("w_basic_0011-1", "Look left and right", "searching", "medium"),
            "w_basic_0012-1": AlphaExpression("w_basic_0012-1", "Look up and down", "searching", "medium"),
            
            # Emo expressions
            "emo_007": AlphaExpression("emo_007", "Smile", "happy", "medium"),
            "emo_010": AlphaExpression("emo_010", "Shy", "shy", "medium"),
            "emo_016": AlphaExpression("emo_016", "Smile", "happy", "medium"),
            "emo_028": AlphaExpression("emo_028", "Cover your face", "embarrassed", "medium"),
            "emo_008": AlphaExpression("emo_008", "Irritation", "annoyed", "medium"),
            "emo_014": AlphaExpression("emo_014", "Poor", "pitiful", "medium"),
            "emo_009": AlphaExpression("emo_009", "Tears", "crying", "high"),
            "emo_011": AlphaExpression("emo_011", "Crying", "crying", "high"),
            "emo_023": AlphaExpression("emo_023", "Pain", "hurt", "high"),
            "emo_013": AlphaExpression("emo_013", "Get angry", "angry", "high"),
            "emo_015": AlphaExpression("emo_015", "Arrogance", "proud", "high"),
            "emo_026": AlphaExpression("emo_026", "White eyes", "dismissive", "medium"),
            "emo_022": AlphaExpression("emo_022", "Squeeze", "focused", "medium"),
            "emo_019": AlphaExpression("emo_019", "Hazy", "dreamy", "low"),
            "emo_020": AlphaExpression("emo_020", "Daze", "confused", "medium"),
            "emo_027": AlphaExpression("emo_027", "Cool", "confident", "medium"),
            "emo_029": AlphaExpression("emo_029", "Witty", "clever", "medium"),
            "emo_030": AlphaExpression("emo_030", "Cross Eyes", "silly", "medium"),
            "emo_031": AlphaExpression("emo_031", "Reading glasses", "studious", "low"),
            "emo_032": AlphaExpression("emo_032", "Golden Glasses", "cool", "medium"),
        }
    
    def get_actions_by_emotion(self, emotion: str, intensity: str = None) -> List[AlphaAction]:
        """Lấy các actions phù hợp với emotion"""
        matching_actions = []
        for action in self.built_in_actions.values():
            if action.emotion_type == emotion:
                if intensity is None or action.intensity == intensity:
                    matching_actions.append(action)
        
        # Thêm dances phù hợp
        for dance in self.built_in_dances.values():
            if dance.emotion_type == emotion:
                if intensity is None or dance.intensity == intensity:
                    matching_actions.append(dance)
                    
        return matching_actions
    
    def get_expressions_by_emotion(self, emotion: str, intensity: str = None) -> List[AlphaExpression]:
        """Lấy các expressions phù hợp với emotion"""
        matching_expressions = []
        for expression in self.built_in_expressions.values():
            if expression.emotion_type == emotion:
                if intensity is None or expression.intensity == intensity:
                    matching_expressions.append(expression)
        return matching_expressions
    
    def get_actions_by_category(self, category: str) -> List[AlphaAction]:
        """Lấy actions theo category"""
        matching_actions = []
        for action in self.built_in_actions.values():
            if action.category == category:
                matching_actions.append(action)
        
        for dance in self.built_in_dances.values():
            if dance.category == category:
                matching_actions.append(dance)
                
        return matching_actions
    
    def get_interruptible_actions(self) -> List[AlphaAction]:
        """Lấy các actions có thể bị interrupt (phù hợp cho beat nhanh)"""
        interruptible = []
        for action in self.built_in_actions.values():
            if action.can_interrupt:
                interruptible.append(action)
        return interruptible

    # NEW: helpers to return all actions/expressions
    def get_all_actions(self) -> List[AlphaAction]:
        return list(self.built_in_actions.values()) + list(self.built_in_dances.values())

    def get_all_expressions(self) -> List[AlphaExpression]:
        return list(self.built_in_expressions.values())

# Singleton instance
alpha_mini_actions_service = AlphaMiniActionsService()

"""
UBX File Manager - Quản lý các file UBX và phân loại theo chức năng
"""
from typing import Dict, List, Any
from app.models.schemas import RobotAction

class UBXManager:
    """Manager để quản lý và phân loại các file UBX"""

    def __init__(self):
        self.ubx_database = self._create_ubx_database()

    def _create_ubx_database(self) -> Dict[str, Dict[str, Any]]:
        """Tạo database chứa thông tin về tất cả file UBX"""
        return {
            # Basic movements and poses
            "007": {"name": "Rise from a seated position", "category": "pose", "energy": "medium", "duration": 3.0},
            "009": {"name": "Reset", "category": "pose", "energy": "low", "duration": 2.0},
            "011": {"name": "Nod", "category": "head", "energy": "low", "duration": 1.5},
            "012": {"name": "Push-ups", "category": "exercise", "energy": "high", "duration": 4.0},
            "013": {"name": "Kung fu", "category": "dance", "energy": "high", "duration": 3.0},
            "015": {"name": "Welcome", "category": "greeting", "energy": "medium", "duration": 2.5},
            "017": {"name": "Raise both hands", "category": "arm", "energy": "medium", "duration": 2.0},
            "018": {"name": "Lift the right leg", "category": "leg", "energy": "medium", "duration": 2.0},
            "019": {"name": "Lift the left leg", "category": "leg", "energy": "medium", "duration": 2.0},
            "021": {"name": "Bend at the waist", "category": "pose", "energy": "low", "duration": 2.5},
            "024": {"name": "Yoga", "category": "pose", "energy": "low", "duration": 4.0},
            "027": {"name": "Sit down", "category": "pose", "energy": "low", "duration": 3.0},
            "028": {"name": "Do a right lunge", "category": "exercise", "energy": "high", "duration": 3.0},
            "031": {"name": "Squat down", "category": "exercise", "energy": "medium", "duration": 2.5},
            "037": {"name": "Shake the head", "category": "head", "energy": "medium", "duration": 2.0},
            "038": {"name": "Tilt the head", "category": "head", "energy": "low", "duration": 1.5},
            "039": {"name": "Laugh out loud", "category": "expression", "energy": "high", "duration": 2.5},

            # Random short actions
            "random_short2": {"name": "Hug", "category": "arm", "energy": "medium", "duration": 2.0},
            "random_short3": {"name": "Wave the left hand", "category": "arm", "energy": "low", "duration": 1.5},
            "random_short4": {"name": "Wave the right hand", "category": "arm", "energy": "low", "duration": 1.5},

            # Surveillance actions
            "Surveillance_001": {"name": "Say hi", "category": "greeting", "energy": "medium", "duration": 2.0},
            "Surveillance_003": {"name": "Shake hands", "category": "arm", "energy": "medium", "duration": 2.5},
            "Surveillance_004": {"name": "Blow a kiss", "category": "expression", "energy": "medium", "duration": 2.0},
            "Surveillance_006": {"name": "Act cute", "category": "expression", "energy": "medium", "duration": 2.5},

            # Action series
            "action_004": {"name": "Wow", "category": "expression", "energy": "high", "duration": 2.0},
            "action_005": {"name": "Give a thumb-up", "category": "arm", "energy": "medium", "duration": 2.0},
            "action_006": {"name": "OK", "category": "arm", "energy": "low", "duration": 1.5},
            "action_007": {"name": "Beat you up", "category": "dance", "energy": "high", "duration": 3.0},
            "action_012": {"name": "Ask for a hug", "category": "arm", "energy": "medium", "duration": 2.5},
            "action_013": {"name": "Make faces", "category": "expression", "energy": "medium", "duration": 2.0},
            "action_014": {"name": "Invite", "category": "arm", "energy": "medium", "duration": 2.0},
            "action_015": {"name": "Wiggle the hips", "category": "dance", "energy": "high", "duration": 2.5},
            "action_016": {"name": "Say goodbye", "category": "arm", "energy": "medium", "duration": 2.0},
            "action_018": {"name": "Hey ha", "category": "dance", "energy": "high", "duration": 2.5},
            "action_011": {"name": "Pretend to fly", "category": "dance", "energy": "high", "duration": 3.0},
            "action_019": {"name": "Hold the head", "category": "head", "energy": "low", "duration": 2.0},
            "action_020": {"name": "A smug face", "category": "expression", "energy": "medium", "duration": 2.0},

            # Codemao expressions
            "codemao1": {"name": "Look around", "category": "head", "energy": "low", "duration": 2.0},
            "codemao2": {"name": "Heartbreaking", "category": "expression", "energy": "medium", "duration": 2.5},
            "codemao3": {"name": "Sad", "category": "expression", "energy": "low", "duration": 2.0},
            "codemao4": {"name": "Asleep", "category": "expression", "energy": "low", "duration": 3.0},
            "codemao5": {"name": "Frightened", "category": "expression", "energy": "high", "duration": 2.0},
            "codemao6": {"name": "Sleepy", "category": "expression", "energy": "low", "duration": 2.5},
            "codemao7": {"name": "Strange", "category": "expression", "energy": "medium", "duration": 2.0},
            "codemao8": {"name": "Shocked", "category": "expression", "energy": "high", "duration": 2.0},
            "codemao9": {"name": "Sneeze", "category": "expression", "energy": "medium", "duration": 1.5},
            "codemao10": {"name": "Cheer up", "category": "expression", "energy": "high", "duration": 2.0},
            "codemao11": {"name": "Fighting", "category": "dance", "energy": "high", "duration": 2.5},
            "codemao12": {"name": "Exert strength", "category": "exercise", "energy": "high", "duration": 2.5},
            "codemao13": {"name": "Doubt", "category": "expression", "energy": "low", "duration": 2.0},
            "codemao14": {"name": "Wake up", "category": "expression", "energy": "medium", "duration": 2.0},
            "codemao15": {"name": "Distressed", "category": "expression", "energy": "medium", "duration": 2.0},
            "codemao16": {"name": "A sly smile", "category": "expression", "energy": "medium", "duration": 2.0},
            "codemao17": {"name": "Depressed", "category": "expression", "energy": "low", "duration": 2.0},
            "codemao18": {"name": "Eager", "category": "expression", "energy": "high", "duration": 2.0},
            "codemao19": {"name": "Love", "category": "expression", "energy": "medium", "duration": 2.5},
            "codemao20": {"name": "Blink", "category": "expression", "energy": "low", "duration": 1.0},

            # Basic head movements
            "w_basic_0003_1": {"name": "Look to the right", "category": "head", "energy": "low", "duration": 1.5},
            "w_basic_0005_1": {"name": "Look to the left", "category": "head", "energy": "low", "duration": 1.5},
            "w_basic_0010_1": {"name": "Look up", "category": "head", "energy": "low", "duration": 1.5},
            "w_basic_0011_1": {"name": "Look left and right", "category": "head", "energy": "low", "duration": 2.0},
            "w_basic_0012_1": {"name": "Look up and down", "category": "head", "energy": "low", "duration": 2.0},

            # Emotions
            "emo_007": {"name": "Smile", "category": "expression", "energy": "medium", "duration": 2.0},
            "emo_008": {"name": "Agitated", "category": "expression", "energy": "high", "duration": 2.0},
            "emo_009": {"name": "Tears", "category": "expression", "energy": "low", "duration": 2.5},
            "emo_010": {"name": "Shy", "category": "expression", "energy": "low", "duration": 2.0},
            "emo_011": {"name": "Cry aloud", "category": "expression", "energy": "high", "duration": 2.5},
            "emo_013": {"name": "Angry", "category": "expression", "energy": "high", "duration": 2.0},
            "emo_014": {"name": "Pathetic", "category": "expression", "energy": "low", "duration": 2.0},
            "emo_015": {"name": "Arrogant", "category": "expression", "energy": "medium", "duration": 2.0},
            "emo_016": {"name": "Simper", "category": "expression", "energy": "low", "duration": 1.5},
            "emo_019": {"name": "Dizzy", "category": "expression", "energy": "medium", "duration": 2.0},
            "emo_020": {"name": "Daze", "category": "expression", "energy": "low", "duration": 2.0},
            "emo_022": {"name": "Wipe eye gunk", "category": "expression", "energy": "low", "duration": 1.5},
            "emo_023": {"name": "Hurt", "category": "expression", "energy": "medium", "duration": 2.0},
            "emo_026": {"name": "Contemptuous look", "category": "expression", "energy": "medium", "duration": 2.0},
            "emo_028": {"name": "Cover up the face", "category": "expression", "energy": "low", "duration": 2.0},
            
            # Built-in dance sequences (những cái này làm robot nhảy thật sự!)
            "dance_0001en": {"name": "Healthy Song and Dance", "category": "dance", "energy": "high", "duration": 15.0},
            "dance_0002en": {"name": "Shaolin Hero Dance", "category": "dance", "energy": "high", "duration": 12.0},
            "dance_0003en": {"name": "Youth Training Manual Dance", "category": "dance", "energy": "high", "duration": 14.0},
            "dance_0004en": {"name": "Little Star", "category": "dance", "energy": "medium", "duration": 10.0},
            "dance_0005en": {"name": "Grass Dance", "category": "dance", "energy": "medium", "duration": 12.0},
            "dance_0006en": {"name": "Seaweed Dance", "category": "dance", "energy": "high", "duration": 13.0},
            "dance_0007en": {"name": "I love taking a bath", "category": "dance", "energy": "medium", "duration": 11.0},
            "dance_0008en": {"name": "Chongerfei", "category": "dance", "energy": "high", "duration": 14.0},
            "dance_0009en": {"name": "Learn to Meow", "category": "dance", "energy": "medium", "duration": 10.0},
            "dance_0011en": {"name": "Dura Dance", "category": "dance", "energy": "high", "duration": 15.0},
            "dance_0013": {"name": "Buddha Girl", "category": "dance", "energy": "medium", "duration": 12.0},
            "custom_0035": {"name": "Happy birthday", "category": "dance", "energy": "medium", "duration": 8.0},
            
            # Additional movement actions
            "014": {"name": "Tai Chi", "category": "dance", "energy": "low", "duration": 8.0},
            "016": {"name": "Golden Rooster Independent", "category": "pose", "energy": "medium", "duration": 4.0},
            "010": {"name": "Laughing", "category": "expression", "energy": "high", "duration": 3.0}
        }

    def get_actions_by_category(self, category: str) -> List[str]:
        """Lấy danh sách actions theo category"""
        return [action_id for action_id, info in self.ubx_database.items()
                if info.get("category") == category]

    def get_actions_by_energy(self, energy_level: str) -> List[str]:
        """Lấy danh sách actions theo mức năng lượng"""
        return [action_id for action_id, info in self.ubx_database.items()
                if info.get("energy") == energy_level]

    def get_actions_by_duration(self, min_duration: float, max_duration: float) -> List[str]:
        """Lấy danh sách actions theo khoảng thời gian"""
        return [action_id for action_id, info in self.ubx_database.items()
                if min_duration <= info.get("duration", 2.0) <= max_duration]

    def get_action_info(self, action_id: str) -> Dict[str, Any]:
        """Lấy thông tin chi tiết của một action"""
        return self.ubx_database.get(action_id, {})

    def map_to_robot_action(self, action_id: str) -> RobotAction:
        """Map UBX action sang RobotAction enum"""
        if not action_id or action_id not in self.ubx_database:
            return RobotAction.DANCE

        category = self.ubx_database[action_id].get("category", "dance")

        # Mapping categories to RobotAction
        category_mapping = {
            "dance": RobotAction.DANCE,
            "arm": RobotAction.ARM_MOVEMENT,
            "head": RobotAction.HEAD_MOVEMENT,
            "leg": RobotAction.WALK,
            "pose": RobotAction.POSE,
            "exercise": RobotAction.DANCE,  # Exercise actions can be considered as dance
            "greeting": RobotAction.ARM_MOVEMENT,
            "expression": RobotAction.HEAD_MOVEMENT  # Expressions often involve head/face
        }

        return category_mapping.get(category, RobotAction.DANCE)

    def get_suitable_actions(self, energy_level: str, duration: float, tempo: float) -> List[str]:
        """Lấy danh sách actions phù hợp với điều kiện"""
        suitable_actions = []

        # Ưu tiên dance actions cho các segments có energy cao hoặc tempo nhanh
        dance_priority_actions = ["013", "action_007", "action_015", "012", "024"]  # Kung fu, Beat you up, Wiggle hips, Push-ups, Yoga

        # Điều chỉnh energy level dựa trên tempo
        if tempo > 140:
            target_energy = "high"
            # Với tempo cao, ưu tiên dance actions
            suitable_actions.extend(dance_priority_actions)
        elif tempo > 100:
            target_energy = "medium"
            # Tempo trung bình, mix dance và gesture actions
            suitable_actions.extend(dance_priority_actions[:3])  # Top 3 dance actions
        else:
            target_energy = "low"

        # Lấy actions theo energy level
        primary_actions = self.get_actions_by_energy(target_energy)
        secondary_actions = self.get_actions_by_energy(energy_level) if energy_level != target_energy else []

        # Ưu tiên các actions có thể tạo dance behaviors - CẬP NHẬT với dance sequences thật
        dance_capable_actions = ["dance_0004en", "dance_0006en", "dance_0009en", "013", "action_007", "action_015", "action_011", "action_018"]

        # Lọc theo duration (cho phép sai số 1.0s để có nhiều options hơn)
        duration_tolerance = 1.0
        for action_id in primary_actions + secondary_actions + dance_capable_actions:
            if action_id not in suitable_actions:  # Tránh duplicate
                action_duration = self.ubx_database[action_id].get("duration", 2.0)
                if abs(action_duration - duration) <= duration_tolerance or duration >= action_duration:
                    suitable_actions.append(action_id)

        # Đảm bảo có ít nhất một số actions để chọn
        if not suitable_actions:
            # Fallback với priority cho dance actions
            suitable_actions = dance_priority_actions + ["015", "017", "011", "action_005", "emo_007"]

        # Shuffle để tạo variety trong choreography
        import random
        random.shuffle(suitable_actions)

        return suitable_actions[:10]  # Trả về tối đa 10 options

    def get_transition_actions(self) -> List[str]:
        """Lấy danh sách actions phù hợp để làm transition giữa các segments"""
        return ["009", "011", "038", "w_basic_0011_1", "codemao20"]  # Reset, Nod, Tilt head, Look left/right, Blink

    def get_opening_actions(self) -> List[str]:
        """Lấy danh sách actions phù hợp để mở đầu"""
        return ["015", "Surveillance_001", "action_014", "emo_007", "codemao14"]  # Welcome, Say hi, Invite, Smile, Wake up

    def get_closing_actions(self) -> List[str]:
        """Lấy danh sách actions phù hợp để kết thúc"""
        return ["action_016", "random_short2", "action_005", "027", "009"]  # Say goodbye, Hug, Thumbs up, Sit down, Reset


# Global instance
ubx_manager = UBXManager()

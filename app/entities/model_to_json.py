from datetime import datetime
from uuid import UUID

def to_serializable(value):
    """Convert non-serializable SQLAlchemy types (UUID, datetime) to JSON-safe values."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def robot_to_dict(robot):
    if robot is None:
        return None
    return {
        "id": to_serializable(robot.id),
        "account_id": to_serializable(robot.account_id),
        "created_date": to_serializable(robot.created_date),
        "last_updated": to_serializable(robot.last_updated),
        "robot_model_id": to_serializable(robot.robot_model_id),
        "serial_number": robot.serial_number,
        "status": robot.status,
    }

def subscription_to_dict(subscription):
    if subscription is None:
        return None
    return {
        "id": to_serializable(subscription.id),
        "created_date": to_serializable(subscription.created_date),
        "last_updated": to_serializable(subscription.last_updated),
        "status": subscription.status,
        "account_id": to_serializable(subscription.account_id),
        "end_date": to_serializable(subscription.end_date),
        "plan_id": to_serializable(subscription.plan_id),
        "start_date": to_serializable(subscription.start_date),
    }

def account_quota_to_dict(account_quota):
    if account_quota is None:
        return None
    return {
        "id": to_serializable(account_quota.id),
        "created_date": to_serializable(account_quota.created_date),
        "last_updated": to_serializable(account_quota.last_updated),
        "status": account_quota.status,
        "account_id": to_serializable(account_quota.account_id),
        "quota": account_quota.quota,
    }

def skill_to_dict(skill):
    if skill is None:
        return None
    return {
        "id": to_serializable(skill.id),
        "name": skill.name,
        "code": skill.code,
        "status": skill.status,
        "icon": skill.icon,
        "robot_model_id": to_serializable(skill.robot_model_id),
        "last_updated": to_serializable(skill.last_updated),
        "created_date": to_serializable(skill.created_date),
    }


def esp32_to_dict(esp32):
    """Chuyển đổi đối tượng ESP32 sang dictionary"""
    if esp32 is None:
        return None
    
    return {
        "id": to_serializable(esp32.id),
        "account_id": to_serializable(esp32.account_id),
        "firmware_version": esp32.firmware_version,
        "metadata": esp32.metadata,
        "name": esp32.name,
        "status": esp32.status,
        "topic_pub": esp32.topic_pub,
        "topic_sub": esp32.topic_sub,
        "message": esp32.message,
        "created_at": to_serializable(esp32.created_at),
        "last_updated": to_serializable(esp32.last_updated),
    }
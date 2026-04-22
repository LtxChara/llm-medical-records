# chat_memory.py

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Dict, Optional, List, Union, Any, Set
from dataclasses import dataclass, asdict
from med_prompt import system_prompt_templates
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MedicalHistoryConfig:
    """Configuration for a specific medical history type."""
    max_length: int = 10
    system_prompt: Optional[str] = None
    required: bool = False


class HistoryTypeConfigs:
    """Predefined configurations for standard history types."""
    主诉 = MedicalHistoryConfig(
        max_length=10, system_prompt=system_prompt_templates.get("主诉"), required=True
    )
    现病史 = MedicalHistoryConfig(
        max_length=15, system_prompt=system_prompt_templates.get("现病史"), required=True
    )
    既往史 = MedicalHistoryConfig(
        max_length=10, system_prompt=system_prompt_templates.get("既往史"), required=True
    )
    过敏史 = MedicalHistoryConfig(
        max_length=5, system_prompt=system_prompt_templates.get("过敏史"), required=False
    )
    诊断 = MedicalHistoryConfig(
        max_length=5, system_prompt=system_prompt_templates.get("诊断"), required=True
    )


class MedicalHistoryManager:
    """Manages conversation history for different medical information fields."""

    def __init__(self, configs: Optional[Dict[str, MedicalHistoryConfig]] = None):
        self.histories: Dict[str, Dict[str, Any]] = {}
        self.configs = configs if configs is not None else self._get_default_configs()
        self.supplement_counts: Dict[str, int] = {ht: 0 for ht in self.configs}

        # 字段结果持久化：存储已成功提取的字段值
        self.field_results: Dict[str, str] = {}
        # 已完成字段集合
        self.completed_fields: Set[str] = set()

        # Initialize history storage based on provided configs
        for ht, config in self.configs.items():
            if not isinstance(ht, str) or not ht:
                logger.warning("Invalid history type key ignored during initialization.")
                continue
            self.add_history_type(ht, config)

    def _get_default_configs(self) -> Dict[str, MedicalHistoryConfig]:
        """Provides default configurations."""
        return {
            "主诉": HistoryTypeConfigs.主诉,
            "现病史": HistoryTypeConfigs.现病史,
            "既往史": HistoryTypeConfigs.既往史,
            "过敏史": HistoryTypeConfigs.过敏史,
            "诊断": HistoryTypeConfigs.诊断,
        }

    def add_history_type(self, history_type: str, config: MedicalHistoryConfig):
        """Adds or updates a history type configuration and initializes storage."""
        if not isinstance(history_type, str) or not history_type:
            raise ValueError("History type must be a non-empty string.")
        if not isinstance(config, MedicalHistoryConfig):
            raise TypeError("Config must be an instance of MedicalHistoryConfig.")

        new_history = ChatMessageHistory()
        if config.system_prompt:
            # Ensure system prompt is only added once
            if not any(isinstance(msg, SystemMessage) for msg in new_history.messages):
                new_history.add_message(SystemMessage(content=config.system_prompt))

        self.histories[history_type] = {
            "config": config,
            "history": new_history
        }
        logger.debug(f"Added or updated history type: {history_type}")

    def add_message(self, history_type: str, role: str, content: str):
        """Adds a message to the specified history type, enforcing constraints."""
        if history_type not in self.histories:
            raise ValueError(f"Unknown history type: {history_type}")
        if role not in ["user", "ai"]:
            raise ValueError(f"Unknown role type: {role}. Must be 'user' or 'ai'.")
        if not isinstance(content, str) or not content.strip():
            if role == "user":
                raise ValueError("User message content cannot be empty or whitespace only.")
            else:
                logger.warning(f"Adding empty AI message content to {history_type}")
                content = ""

        history_entry = self.histories[history_type]
        history = history_entry["history"]
        config = history_entry["config"]

        if role == "user":
            history.add_user_message(content.strip())
        elif role == "ai":
            history.add_ai_message(content.strip())

        # Trim history if it exceeds max_length (excluding system prompt)
        system_prompt_offset = 1 if config.system_prompt and isinstance(history.messages[0], SystemMessage) else 0
        while len(history.messages) > config.max_length + system_prompt_offset:
            history.messages.pop(system_prompt_offset)
        logger.debug(f"Added {role} message to {history_type}. Current length: {len(history.messages)}")

    def add_supplement(self, history_type: str, content: str):
        """Adds supplementary information provided by the user."""
        logger.info(f"Adding supplement to history type: {history_type}")
        if history_type in self.supplement_counts:
            self.supplement_counts[history_type] += 1
        # Supplementary info is treated as regular user input for that field
        self.add_message(history_type, "user", content)
        # 补充后，该字段可能需要重新评估，标记为未完成
        self.reset_field_status(history_type)

    def get_supplement_count(self, history_type: str) -> int:
        """Returns the number of supplements added for a history type."""
        return self.supplement_counts.get(history_type, 0)

    def get_history(self, history_type: str) -> List[Union[SystemMessage, HumanMessage, AIMessage]]:
        """Retrieves the complete message list for a history type."""
        if history_type not in self.histories:
            raise ValueError(f"Unknown history type: {history_type}")
        return self.histories[history_type]["history"].messages

    def get_user_all_input(self, history_type: str) -> str:
        """Concatenates all user inputs for a history type."""
        if history_type not in self.histories:
            raise ValueError(f"Unknown history type: {history_type}")

        user_inputs = []
        for msg in self.histories[history_type]["history"].messages:
            if isinstance(msg, HumanMessage):
                user_inputs.append(msg.content)

        if not user_inputs:
            logger.warning(f"No user input found for history type: {history_type}")
            return ""

        return "\n".join(user_inputs)

    def to_openai_format(self, history_type: str) -> List[Dict[str, str]]:
        """Converts history to the format expected by OpenAI API."""
        if history_type not in self.histories:
            raise ValueError(f"Unknown history type: {history_type}")

        formatted_messages = []
        for msg in self.histories[history_type]["history"].messages:
            role = ""
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"

            if role:
                formatted_messages.append({"role": role, "content": msg.content})
            else:
                logger.warning(f"Unsupported message type encountered in {history_type}: {type(msg)}")

        return formatted_messages

    # --- 字段结果状态管理方法 ---

    def get_field_result(self, field: str) -> str:
        """获取指定字段的已提取结果。"""
        return self.field_results.get(field, "")

    def set_field_result(self, field: str, value: str):
        """设置指定字段的提取结果。"""
        self.field_results[field] = value
        logger.debug(f"Field result set for '{field}': {value}")

    def is_field_completed(self, field: str) -> bool:
        """检查指定字段是否已完成提取。"""
        return field in self.completed_fields

    def mark_field_completed(self, field: str):
        """标记指定字段为已完成。"""
        self.completed_fields.add(field)
        logger.info(f"Field '{field}' marked as completed.")

    def reset_field_status(self, field: str):
        """重置指定字段的完成状态（例如补充后需要重新评估）。"""
        self.completed_fields.discard(field)
        logger.info(f"Field '{field}' status reset to incomplete.")

    def clear_all_field_results(self):
        """清除所有字段结果和完成状态。"""
        self.field_results.clear()
        self.completed_fields.clear()
        logger.info("All field results and completion statuses cleared.")

    def save_to_json(self, file_path: str):
        """Saves the current state of all histories to a JSON file."""
        try:
            save_data = {}
            for ht, data in self.histories.items():
                save_data[ht] = {
                    "config": asdict(data["config"]),
                    "messages": [
                        {"type": msg.type, "content": msg.content}
                        for msg in data["history"].messages
                    ],
                    "field_result": self.field_results.get(ht, ""),
                    "is_completed": ht in self.completed_fields
                }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved histories to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save histories to {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during saving: {e}")
            raise

    @classmethod
    def load_from_json(cls, file_path: str):
        """Loads histories from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            instance = cls(configs={})
            for ht, ht_data in data.items():
                try:
                    config_dict = ht_data.get("config", {})
                    config = MedicalHistoryConfig(
                        max_length=config_dict.get("max_length", 10),
                        system_prompt=config_dict.get("system_prompt"),
                        required=config_dict.get("required", False)
                    )
                    instance.add_history_type(ht, config)

                    history = instance.histories[ht]["history"]
                    loaded_messages = ht_data.get("messages", [])
                    for msg_data in loaded_messages:
                        msg_type = msg_data.get("type")
                        content = msg_data.get("content", "")
                        if msg_type == "system":
                            if not any(isinstance(m, SystemMessage) for m in history.messages):
                                history.add_message(SystemMessage(content=content))
                        elif msg_type == "human":
                            history.add_message(HumanMessage(content=content))
                        elif msg_type == "ai":
                            history.add_message(AIMessage(content=content))
                        else:
                            logger.warning(f"Unknown message type '{msg_type}' encountered during loading for {ht}")

                    instance.field_results[ht] = ht_data.get("field_result", "")
                    if ht_data.get("is_completed", False):
                        instance.completed_fields.add(ht)

                except (KeyError, TypeError, ValueError) as e:
                    logger.error(f"Error processing history type '{ht}' during loading: {e}. Skipping this type.")
                    if ht in instance.histories:
                        del instance.histories[ht]

            logger.info(f"Successfully loaded histories from {file_path}")
            return instance
        except FileNotFoundError:
            logger.error(f"History file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during loading: {e}")
            raise

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("neo.utils")

class NeoUtils:
    @staticmethod
    def get_workspace_path(relative_path: str) -> str:
        """ワークスペース内の絶対パスを返す"""
        base_dir = "/data/.openclaw/workspace"
        return os.path.join(base_dir, relative_path.lstrip("./"))

    @staticmethod
    def read_json(file_path: str) -> Optional[Dict[str, Any]]:
        """JSONファイルを安全に読み込む"""
        abs_path = NeoUtils.get_workspace_path(file_path)
        if not os.path.exists(abs_path):
            logger.warning(f"File not found: {abs_path}")
            return None
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON {file_path}: {e}")
            return None

    @staticmethod
    def write_json(file_path: str, data: Dict[str, Any], indent: int = 4) -> bool:
        """JSONファイルを安全に書き込む"""
        abs_path = NeoUtils.get_workspace_path(file_path)
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error writing JSON {file_path}: {e}")
            return False

    @staticmethod
    def backup_file(file_path: str) -> bool:
        """変更前にファイルを .bak として保存する (Atomic Change Protocol)"""
        abs_path = NeoUtils.get_workspace_path(file_path)
        if not os.path.exists(abs_path):
            return False
        try:
            import shutil
            shutil.copy2(abs_path, abs_path + ".bak")
            logger.info(f"Backup created: {file_path}.bak")
            return True
        except Exception as e:
            logger.error(f"Backup failed for {file_path}: {e}")
            return False

    @staticmethod
    def log_event(category: str, message: str, level: str = "info"):
        """標準化されたイベントログ記録 (将来的にDiscord/Webhook連動)"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{category.upper()}] {message}"
        if level == "error":
            logger.error(log_entry)
        else:
            logger.info(log_entry)

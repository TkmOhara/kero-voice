import psutil
import subprocess
from typing import Optional


class SystemMonitor:
    """システムリソースの監視クラス"""

    @staticmethod
    def get_cpu_usage() -> float:
        """CPU使用率を取得 (%)"""
        return psutil.cpu_percent(interval=None)

    @staticmethod
    def get_cpu_count() -> tuple[int, int]:
        """CPUコア数を取得 (物理, 論理)"""
        return psutil.cpu_count(logical=False) or 0, psutil.cpu_count(logical=True) or 0

    @staticmethod
    def get_gpu_info() -> Optional[dict]:
        """GPU情報を取得 (nvidia-smi使用)"""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            line = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]

            if len(parts) < 4:
                return None

            name = parts[0]
            mem_total = int(parts[1]) * 1024 * 1024  # MiB to bytes
            mem_used = int(parts[2]) * 1024 * 1024
            gpu_util = float(parts[3])

            return {
                "name": name,
                "total_memory": mem_total,
                "used": mem_used,
                "percent": (mem_used / mem_total * 100) if mem_total > 0 else 0,
                "gpu_util": gpu_util
            }
        except Exception:
            return None

    @staticmethod
    def format_bytes(b: int) -> str:
        """バイトを人間が読みやすい形式に変換"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024.0:
                return f"{b:.1f}{unit}"
            b /= 1024.0
        return f"{b:.1f}PB"

    @staticmethod
    def create_bar(percent: float, width: int = 25) -> str:
        """プログレスバーを作成"""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]{percent:6.1f}%"

    @classmethod
    def generate_status_message(cls) -> str:
        """ステータスメッセージを生成"""
        W = 44  # 内側の幅

        lines = []
        lines.append("```")
        lines.append("╔" + "═" * W + "╗")
        lines.append("║" + "SYSTEM STATUS".center(W) + "║")
        lines.append("╠" + "═" * W + "╣")

        # CPU情報
        cpu_percent = cls.get_cpu_usage()
        physical, logical = cls.get_cpu_count()
        lines.append("║" + " CPU".ljust(W) + "║")
        lines.append("║" + f"   Cores: {physical}P / {logical}L".ljust(W) + "║")
        lines.append("║" + f"   {cls.create_bar(cpu_percent)}".ljust(W) + "║")

        # GPU情報（利用可能な場合）
        gpu = cls.get_gpu_info()
        if gpu:
            lines.append("╠" + "═" * W + "╣")
            lines.append("║" + " GPU".ljust(W) + "║")
            lines.append("║" + f"   {gpu['name'][:38]}".ljust(W) + "║")
            vram_info = f"   VRAM: {cls.format_bytes(gpu['used'])} / {cls.format_bytes(gpu['total_memory'])}"
            lines.append("║" + vram_info.ljust(W) + "║")
            lines.append("║" + f"   {cls.create_bar(gpu['percent'])}".ljust(W) + "║")
            lines.append("║" + f"   GPU:  {cls.create_bar(gpu['gpu_util'])}".ljust(W) + "║")

        lines.append("╚" + "═" * W + "╝")
        lines.append("```")

        return "\n".join(lines)

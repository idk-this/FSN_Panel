import os
import shutil
import stat
import subprocess
import time

from Utils.SystemUtils import SystemUtils


def _force_remove_readonly(func, path, exc_info):
    """Обработчик для shutil.rmtree — снимает read-only и повторяет."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


class ConfigHelper:
    @staticmethod
    def update_video_cfg(src, dst, updates):
        if not os.path.exists(src):
            print(f"[ConfigHelper] Исходный файл не найден: {src}")
            return

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        with open(src, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_content = []
        for line in lines:
            for k, v in updates.items():
                if f'"{k}"' in line:
                    line = f'\t"{k}"\t\t"{v}"\n'
                    break
            new_content.append(line)

        ConfigHelper._write_with_retry(dst, new_content)

    @staticmethod
    def _write_with_retry(dst, content, max_attempts=3):
        """Записывает файл с несколькими попытками при PermissionError."""
        for attempt in range(1, max_attempts + 1):
            try:
                # Снимаем атрибут read-only если файл существует
                if os.path.exists(dst):
                    try:
                        os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
                    except Exception:
                        pass
                    # Также через attrib
                    subprocess.run(
                        f'attrib -R -S -H "{dst}"',
                        shell=True, capture_output=True
                    )
                    time.sleep(0.1)

                with open(dst, 'w', encoding='utf-8') as f:
                    f.writelines(content)
                return  # Успешно

            except PermissionError as e:
                print(f"[ConfigHelper] Попытка {attempt}/{max_attempts} — PermissionError: {e}")
                if attempt == max_attempts:
                    # Крайний вариант: снести папку и пересоздать
                    parent_dir = os.path.dirname(dst)
                    try:
                        subprocess.run(
                            f'attrib -R -A -S -H "{parent_dir}" /D /S',
                            shell=True, capture_output=True
                        )
                        time.sleep(0.2)
                        shutil.rmtree(parent_dir, onerror=_force_remove_readonly)
                        os.makedirs(parent_dir, exist_ok=True)
                        with open(dst, 'w', encoding='utf-8') as f:
                            f.writelines(content)
                    except Exception as e2:
                        SystemUtils.show_error(
                            f"Не удалось записать файл: {dst}\n"
                            f"Ошибка: {e2}\n\n"
                            "Пожалуйста, вручную удалите папку 'userdata' в директории Steam."
                        )
                else:
                    time.sleep(0.5 * attempt)

            except Exception as e:
                print(f"[ConfigHelper] Неожиданная ошибка при записи {dst}: {e}")
                break
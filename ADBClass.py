import subprocess
import time
from pathlib import Path

import yaml

from EASLogger import EASloggerSingleton


class NativeWindow:
    def __init__(self, hwnd):
        self.hwnd = hwnd

    @property
    def title(self):
        import win32gui

        return win32gui.GetWindowText(self.hwnd)

    @property
    def left(self):
        return self._rect()[0]

    @property
    def top(self):
        return self._rect()[1]

    @property
    def width(self):
        left, top, right, bottom = self._rect()
        return right - left

    @property
    def height(self):
        left, top, right, bottom = self._rect()
        return bottom - top

    @property
    def isMinimized(self):
        import win32gui

        return bool(win32gui.IsIconic(self.hwnd))

    @property
    def isVisible(self):
        import win32gui

        return bool(win32gui.IsWindowVisible(self.hwnd))

    def restore(self):
        import win32con
        import win32gui

        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)

    def activate(self):
        import win32con
        import win32gui

        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(self.hwnd)

    def _rect(self):
        import win32gui

        return win32gui.GetWindowRect(self.hwnd)


class AdbSingleton:
    instance = None
    APP_ACTIVITY = ""
    APP_PACKAGE = "com.xd.ssrpg"
    APP_PACKAGE_CANDIDATES = ["com.xd.ssrpg", "com.xd.ssrpgtw"]
    # APP_ACTIVITY = "com.boltrend.octopath.tc/com.epicgames.ue4.SplashActivity"
    # APP_PACKAGE = "com.boltrend.octopath.tc"
    def __init__(self, adb_path='', adb_port='', retryCount=5):
        self.deviceConnected = False
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.retry_count = retryCount
        self.control_mode = "adb"
        self.window_title = ""
        self.process_name = "SoC.exe"
        self.base_resolution = (1280, 720)
        self._window = None
        self._last_window_match_summary = ""
        self.stop_requested = False

    @staticmethod
    def getInstance():
        if AdbSingleton.instance is None:
            AdbSingleton.instance = AdbSingleton()
        return AdbSingleton.instance

    def connectDevice(self, adb_path='', adb_port='', retryCount=5):
        self._load_runtime_config()
        if self.control_mode == "window":
            print("connectWindow", self.window_title, self.process_name, self.base_resolution, retryCount)
        else:
            print("connectDevice", adb_path, adb_port, retryCount)
        EASloggerSingleton.getInstance().info('./logs/log_test.txt', "正在连接模拟器")
        if adb_path and adb_path != self.adb_path:
            self.adb_path = adb_path
        if adb_port and adb_port != self.adb_port:
            self.adb_port = adb_port
        if retryCount != self.retry_count:
            self.retry_count = retryCount

        if self.control_mode == "window":
            return self._connect_window()

        for i in range(self.retry_count):
            if not self.deviceConnected:
                res = self.adb_connect()
                print("runCmd adb_connect:", res[0])
                if b'connected to' in res[0] or b'already connected' in res[0]:
                    self.setDeviceConnected(True)
                    print("Device Connected")
                    break
                    # sizeMatch = self.get_screen_resolution()
                    # print(sizeMatch)
                    # if sizeMatch:
                    #     x = int(sizeMatch[0])
                    #     y = int(sizeMatch[1])
                    #     self.deviceDimension = [x, y]
                    #     print('Device Dimension:', self.deviceDimension)
                else:
                    self.setDeviceConnected(False)
        return self.deviceConnected

    def _load_runtime_config(self):
        config_path = Path("app_config.yaml")
        if not config_path.exists():
            return

        with config_path.open("r", encoding="utf-8") as config_file:
            config_data = yaml.safe_load(config_file) or []

        for item in config_data:
            if not isinstance(item, dict):
                continue
            adb_dir = item.get("adbDir")
            if adb_dir:
                self.adb_path = str(adb_dir)
            connection_port = item.get("connectionPort")
            if connection_port:
                self.adb_port = str(connection_port)
            self.control_mode = str(item.get("controlMode", self.control_mode)).lower()
            self.window_title = str(item.get("windowTitle", self.window_title))
            self.process_name = str(item.get("processName", self.process_name))
            app_package = item.get("appPackage")
            if app_package:
                AdbSingleton.APP_PACKAGE = str(app_package)
            app_activity = item.get("appActivity")
            if app_activity:
                AdbSingleton.APP_ACTIVITY = str(app_activity)
            package_candidates = item.get("appPackageCandidates")
            if isinstance(package_candidates, list) and package_candidates:
                AdbSingleton.APP_PACKAGE_CANDIDATES = [str(package) for package in package_candidates]
            base_resolution = item.get("baseResolution")
            if isinstance(base_resolution, list) and len(base_resolution) == 2:
                self.base_resolution = (int(base_resolution[0]), int(base_resolution[1]))

    def _connect_window(self):
        window = self._find_window()
        if window is None:
            self.setDeviceConnected(False)
            EASloggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"未找到可用的官方模拟器窗口：标题={self.window_title or '未设置'}，"
                f"进程={self.process_name or '未设置'}"
            )
            if self._last_window_match_summary:
                EASloggerSingleton.getInstance().info('./logs/log_test.txt', self._last_window_match_summary)
            return False

        self._window = window
        self._activate_window()
        bounds = self._window_bounds()
        base_width, base_height = self.base_resolution
        if bounds["width"] < base_width * 0.5 or bounds["height"] < base_height * 0.5:
            self.setDeviceConnected(False)
            EASloggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"官方模拟器窗口尺寸过小：{bounds['width']}x{bounds['height']}，"
                "请确认窗口未最小化且游戏画面已打开"
            )
            return False
        if (bounds["width"], bounds["height"]) != self.base_resolution:
            EASloggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"窗口分辨率 {bounds['width']}x{bounds['height']} 与基准 "
                f"{self.base_resolution[0]}x{self.base_resolution[1]} 不一致，请确认模拟器画面设置"
            )
        self.setDeviceConnected(True)
        return True

    def _find_window(self):
        try:
            import pygetwindow as gw
        except ImportError as exc:
            raise RuntimeError("缺少 pygetwindow，请先运行 uv sync") from exc

        title = self.window_title.strip()
        windows = gw.getAllWindows()
        if title:
            title_matches = [window for window in windows if title.lower() in window.title.lower()]
        else:
            title_matches = [window for window in windows if window.title]

        summary_parts = []
        self._restore_candidate_windows(title_matches)
        title_match = self._select_usable_window(title_matches)
        if title_match is not None:
            return title_match
        title_summary = self._format_window_match_summary("标题", title_matches)
        if title_summary:
            summary_parts.append(title_summary)

        process_matches = self._find_windows_by_process_name()
        self._restore_candidate_windows(process_matches)
        process_match = self._select_usable_window(process_matches)
        if process_match is not None:
            return process_match
        process_summary = self._format_window_match_summary("进程", process_matches)
        if process_summary:
            summary_parts.append(process_summary)

        self._last_window_match_summary = "；".join(summary_parts)
        return None

    def _select_usable_window(self, windows):
        base_width, base_height = self.base_resolution
        min_width = base_width * 0.5
        min_height = base_height * 0.5
        visible_matches = [
            window for window in windows
            if getattr(window, "width", 0) > 0
            and getattr(window, "height", 0) > 0
            and getattr(window, "isVisible", True)
            and not getattr(window, "isMinimized", False)
            and getattr(window, "width", 0) >= min_width
            and getattr(window, "height", 0) >= min_height
        ]
        if visible_matches:
            return max(visible_matches, key=lambda window: window.width * window.height)
        return None

    def _restore_candidate_windows(self, windows):
        for window in windows:
            if not getattr(window, "isMinimized", False):
                continue
            try:
                window.restore()
                time.sleep(0.2)
            except Exception as exc:
                print("restore candidate window failed:", exc)

    def _find_windows_by_process_name(self):
        process_name = self.process_name.strip().lower()
        if not process_name:
            return []

        try:
            import win32api
            import win32con
            import win32gui
            import win32process
        except ImportError as exc:
            raise RuntimeError("缺少 pywin32，请先运行 uv sync") from exc

        matched_windows = []

        def get_process_name(pid):
            try:
                process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                try:
                    return Path(win32process.GetModuleFileNameEx(process, 0)).name.lower()
                finally:
                    win32api.CloseHandle(process)
            except Exception:
                return ""

        def collect_window(hwnd, _):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if get_process_name(pid) == process_name:
                matched_windows.append(NativeWindow(hwnd))

        win32gui.EnumWindows(collect_window, None)
        return matched_windows

    def _format_window_match_summary(self, match_type, windows):
        if not windows:
            return ""
        summaries = []
        for window in windows[:5]:
            summaries.append(
                f"'{window.title}' {window.width}x{window.height} "
                f"minimized={getattr(window, 'isMinimized', False)}"
            )
        return f"{match_type}匹配到窗口但没有可用游戏画面：" + "，".join(summaries)

    def _activate_window(self):
        if self._window is None:
            return
        try:
            if self._window.isMinimized:
                self._window.restore()
                time.sleep(0.5)
                self._window = self._find_window()
                if self._window is None:
                    return
            self._window.activate()
            time.sleep(0.2)
        except Exception as exc:
            print("activate window failed:", exc)

    def _window_bounds(self):
        if self._window is None:
            self._window = self._find_window()
        if self._window is None:
            raise RuntimeError("未找到官方模拟器窗口，请检查 app_config.yaml 的 windowTitle")
        hwnd = self._window_hwnd()
        if hwnd is not None:
            try:
                import win32gui

                left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
                return {
                    "left": int(left),
                    "top": int(top),
                    "width": int(client_right - client_left),
                    "height": int(client_bottom - client_top),
                }
            except Exception as exc:
                print("get client bounds failed:", exc)
        return {
            "left": int(self._window.left),
            "top": int(self._window.top),
            "width": int(self._window.width),
            "height": int(self._window.height),
        }

    def _window_hwnd(self):
        return getattr(self._window, "hwnd", None) or getattr(self._window, "_hWnd", None)

    def _to_screen_pos(self, pos):
        bounds = self._window_bounds()
        base_width, base_height = self.base_resolution
        scale_x = bounds["width"] / base_width
        scale_y = bounds["height"] / base_height
        return (
            bounds["left"] + int(float(pos[0]) * scale_x),
            bounds["top"] + int(float(pos[1]) * scale_y),
        )

    def adb_connect(self):
        command = [self.adb_path, "connect", self.adb_port]
        print(" ".join(command))
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        return [output, error]

    def adb_device(self):
        command = [self.adb_path, "devices"]
        print(" ".join(command))
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        return [output, error]

    def adb_shell(self, command):
        full_command = [self.adb_path, "-s", self.adb_port, "shell", command]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        return [output, error]

    def resolve_app_package(self, installed_packages):
        candidates = []
        for package in [AdbSingleton.APP_PACKAGE, *AdbSingleton.APP_PACKAGE_CANDIDATES]:
            if package and package not in candidates:
                candidates.append(package)
        installed_set = set(installed_packages)
        for package in candidates:
            if package in installed_set:
                AdbSingleton.APP_PACKAGE = package
                return package
        return None

    def trigger_key_event(self, key):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            self._activate_window()
            pyautogui.press(str(key))
            return
        command = ["input", "keyevent", str(key)]
        self.adb_shell(" ".join(command))

    def screen_capture(self, path):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            return self._window_screen_capture(path)

        # ./adb_server.exe -s 127.0.0.1:7555 exec-out screencap -p > ./test/screencap.png
        full_command = [self.adb_path, "-s", self.adb_port, "exec-out", "screencap", "/sdcard/cache.png"]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        full_command = [self.adb_path, "-s", self.adb_port, "pull", "/sdcard/cache.png", path]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        full_command = [self.adb_path, "-s", self.adb_port, "shell", "rm", "/sdcard/cache.png"]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return path

    def _window_screen_capture(self, path):
        try:
            import mss
            import mss.tools
        except ImportError as exc:
            raise RuntimeError("缺少 mss，请先运行 uv sync") from exc

        self._activate_window()
        bounds = self._window_bounds()
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with mss.mss() as sct:
            sct_img = sct.grab(bounds)
            base_width, base_height = self.base_resolution
            if sct_img.size != self.base_resolution:
                from PIL import Image

                image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
                image = image.resize((base_width, base_height), Image.Resampling.LANCZOS)
                image.save(output_path)
            else:
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
        return str(output_path)

    def swipe(self, posStart, posEnd, duration=None):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            self._activate_window()
            start_x, start_y = self._to_screen_pos(posStart)
            end_x, end_y = self._to_screen_pos(posEnd)
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=(duration or 300) / 1000, button="left")
            return

        command = ["input", "swipe", str(posStart[0]), str(posStart[1]), str(posEnd[0]), str(posEnd[1])]
        if duration:
            command.append(str(duration))
        self.adb_shell(" ".join(command))

    def tap(self, pos):
        self._raise_if_stop_requested()
        if pos is None:
            return
        if self.control_mode == "window":
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            self._activate_window()
            screen_pos = self._to_screen_pos(pos)
            print("window tap", pos, "->", screen_pos)
            EASloggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"点击窗口坐标 {pos} -> 屏幕坐标 {screen_pos}"
            )
            pyautogui.moveTo(*screen_pos, duration=0.05)
            pyautogui.mouseDown()
            time.sleep(0.08)
            pyautogui.mouseUp()
            return

        command = ["input", "tap", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def tap_down(self, pos):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            self._activate_window()
            pyautogui.mouseDown(*self._to_screen_pos(pos))
            return
        command = ["input", "touchscreen", "touch", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def tap_up(self, pos):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            self._activate_window()
            pyautogui.mouseUp(*self._to_screen_pos(pos))
            return
        command = ["input", "touchscreen", "release", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def get_screen_resolution(self):
        if self.control_mode == "window":
            bounds = self._window_bounds()
            return (bounds["width"], bounds["height"])
        output, error = self.adb_shell("wm size")
        print(output)
        resolution_str = output.decode("utf-8").strip().split(" ")[2]
        width, height = map(int, resolution_str.split("x"))
        return (width, height)

    def capture_screen(self, filename):
        filepath = Path(__file__).parent / "img" / filename
        self.screen_capture(str(filepath))
        return filepath

    def getAllPackages(self):
        if self.control_mode == "window":
            return [AdbSingleton.APP_PACKAGE]
        output, error = self.adb_shell("pm list packages")
        output_array = [
            item.replace("package:", "", 1)
            for item in output.decode(errors="ignore").splitlines()
            if item.startswith("package:")
        ]
        print("res: ", output_array)
        resolved_package = self.resolve_app_package(output_array)
        if resolved_package:
            print("Resolved app package:", resolved_package)
        else:
            EASloggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"未找到游戏包，已安装包中没有：{', '.join(AdbSingleton.APP_PACKAGE_CANDIDATES)}"
            )
        return output_array

    def startApp(self):
        if self.control_mode == "window":
            self._activate_window()
            return b"window activated"
        if AdbSingleton.APP_ACTIVITY:
            output, error = self.adb_shell("am start -n " + AdbSingleton.APP_ACTIVITY)
        else:
            output, error = self.adb_shell(
                f"monkey -p {AdbSingleton.APP_PACKAGE} -c android.intent.category.LAUNCHER 1"
            )
        print(output)
        return output
    def setDeviceConnected(self, connected):
        self.deviceConnected = connected

    def isDeviceConnected(self):
        return self.deviceConnected

    def requestStop(self):
        self.stop_requested = True

    def resetStop(self):
        self.stop_requested = False

    def _raise_if_stop_requested(self):
        if self.stop_requested:
            raise RuntimeError("流程已停止")
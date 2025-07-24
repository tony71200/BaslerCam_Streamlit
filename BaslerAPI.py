# basler_api.py

from pypylon import pylon
import numpy as np

class CameraInfo:
    def __init__(self, friendly_name, serial_number, info):
        self.friendly_name = friendly_name
        self.serial_number = serial_number
        self.info = info

    def __repr__(self):
        return f"CameraInfo(friendly_name='{self.friendly_name}', serial_number='{self.serial_number}')"

class BaslerCameraAPI:
    def __init__(self):
        self.camera = None
        self.is_connected = False

    @staticmethod
    def list_cameras():
        """
        Liệt kê các camera hiện có, trả về list[CameraInfo]
        """
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        camera_list = []
        for dev in devices:
            friendly_name = dev.GetFriendlyName()
            serial_number = dev.GetSerialNumber()
            info = str(dev)  # hoặc dev.GetModelName(), dev.GetDeviceClass(), dev.GetFullName() tùy nhu cầu
            camera_list.append(CameraInfo(friendly_name, serial_number, info))
        return camera_list

    def connect(self, serial=None):
        """
        Kết nối với camera Basler.
        Nếu có serial, sẽ chọn đúng camera đó. Nếu không, chọn camera đầu tiên tìm thấy.
        """
        if self.is_connected:
            return True
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            device = None
            if serial:
                for dev in tl_factory.EnumerateDevices():
                    if dev.GetSerialNumber() == str(serial):
                        device = dev
                        break
                if device is None:
                    print(f"[BaslerCameraAPI] Không tìm thấy camera serial: {serial}")
                    return False
                self.camera = pylon.InstantCamera(tl_factory.CreateDevice(device))
            else:
                self.camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
            self.camera.Open()
            self.is_connected = True
            print(f"[BaslerCameraAPI] Đã kết nối: {self.camera.GetDeviceInfo().GetModelName()} ({self.camera.GetDeviceInfo().GetSerialNumber()})")
            return True
        except Exception as e:
            print(f"[BaslerCameraAPI] Lỗi khi kết nối: {e}")
            self.camera = None
            self.is_connected = False
            return False

    def disconnect(self):
        """
        Ngắt kết nối camera.
        """
        try:
            if self.camera:
                if self.camera.IsGrabbing():
                    self.camera.StopGrabbing()
                self.camera.Close()
                print("[BaslerCameraAPI] Đã ngắt kết nối camera.")
            self.camera = None
            self.is_connected = False
        except Exception as e:
            print(f"[BaslerCameraAPI] Lỗi khi disconnect: {e}")

    def start_stream(self):
        """
        Bắt đầu stream (grabbing liên tục).
        """
        if self.camera is None or not self.camera.IsOpen():
            raise RuntimeError(f"{self.camera} and {self.camera.IsOpen()} Camera chưa kết nối!")
        if not self.camera.IsGrabbing():
            # Đảm bảo TriggerMode = 'Off' (Freerun)
            if hasattr(self.camera, 'TriggerMode'):
                try:
                    self.camera.TriggerMode.Value = 'Off'
                except Exception:
                    pass  # Không phải camera nào cũng có TriggerMode
            self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
            print("[BaslerCameraAPI] Bắt đầu grabbing.")

    def stop_stream(self):
        """
        Dừng stream (grabbing).
        """
        if self.camera and self.camera.IsGrabbing():
            self.camera.StopGrabbing()
            print("[BaslerCameraAPI] Đã dừng grabbing.")

    def get_image(self, timeout=500):
        """
        Lấy 1 frame hiện tại (numpy array).
        Nếu đang grabbing thì lấy luôn frame tiếp theo.
        Nếu không grabbing, sẽ thực hiện grab one.
        """
        if self.camera is None or not self.camera.IsOpen():
            print("[BaslerCameraAPI] Camera chưa kết nối!")
            return None
        try:
            if not self.camera.IsGrabbing():
                self.camera.StartGrabbingMax(1)
            grab = self.camera.RetrieveResult(timeout, pylon.TimeoutHandling_ThrowException)
            img = None
            if grab.GrabSucceeded():
                img = grab.Array  # numpy array (shape HxW hoặc HxWx3)
            grab.Release()
            return img
        except Exception as e:
            print(f"[BaslerCameraAPI] Lỗi get_image: {e}")
            return None

    def get_settings(self):
        """
        Lấy các thông số hiện tại (trả về dict).
        """
        if self.camera is None or not self.camera.IsOpen():
            print("[BaslerCameraAPI] Camera chưa kết nối!")
            return {}
        s = {}
        def getval(node, attr='Value', default=None):
            try:
                return getattr(getattr(self.camera, node), attr)
            except Exception:
                return default
        basic_settings = [
            "ExposureTime", "Gain", "Width", "Height",
            "OffsetX", "OffsetY", "ReverseX", "ReverseY",
            "TriggerMode", "BalanceWhiteAuto", "AcquisitionFrameRate"
        ]
        for name in basic_settings:
            s[name] = getval(name)
        # Lấy thêm min/max cho các thông số số học
        for name in ["ExposureTime", "Gain", "Width", "Height", "OffsetX", "OffsetY", "AcquisitionFrameRate"]:
            s[f"{name}_Min"] = getval(name, "Min")
            s[f"{name}_Max"] = getval(name, "Max")
        return s

    def update_setting(self, name, value):
        """
        Đặt 1 giá trị setting (tự động kiểm tra kiểu dữ liệu).
        Một số setting như Width/Height/Offset khi đang grabbing cần stop stream.
        """
        if self.camera is None or not self.camera.IsOpen():
            print("[BaslerCameraAPI] Camera chưa kết nối!")
            return False
        try:
            node = getattr(self.camera, name)
            # Nếu đang grabbing mà set ROI, cần stop
            need_restart = False
            if self.camera.IsGrabbing() and name in ("Width","Height","OffsetX","OffsetY"):
                self.camera.StopGrabbing()
                need_restart = True
            # Đặt giá trị
            if hasattr(node, "Value"):
                # Tự động ép kiểu nếu cần
                cur_type = type(node.Value)
                if cur_type is bool:
                    node.Value = bool(value)
                elif cur_type is int:
                    node.Value = int(value)
                elif cur_type is float:
                    node.Value = float(value)
                else:
                    node.Value = value
            else:
                setattr(self.camera, name, value)
            if need_restart:
                self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
            print(f"[BaslerCameraAPI] Đã set {name} = {value}")
            return True
        except Exception as e:
            print(f"[BaslerCameraAPI] Lỗi update_setting {name}: {e}")
            return False

    def parse_settings(self, settings_dict):
        """
        Nhận 1 dict {setting: value} và update lần lượt.
        """
        if not isinstance(settings_dict, dict):
            print("[BaslerCameraAPI] Dữ liệu không phải dict!")
            return False
        ok = True
        for k, v in settings_dict.items():
            if not self.update_setting(k, v):
                ok = False
        return ok

# --------- Ví dụ sử dụng (Có thể xoá khi dùng import sang Streamlit) ----------
if __name__ == "__main__":
    api = BaslerCameraAPI()
    print("Danh sách camera:")
    for cam in BaslerCameraAPI.list_cameras():
        print(f" - {cam.friendly_name} | Serial: {cam.serial_number} | Info: {cam.info}")
    if api.connect(serial="24244200"):
        print("Settings hiện tại:", api.get_settings())
        api.start_stream()
        img = api.get_image()
        if img is not None:
            print("Đã lấy 1 frame hình:", img.shape, img.dtype)
        api.update_setting("ExposureTime", 12000)
        api.stop_stream()
        api.disconnect()

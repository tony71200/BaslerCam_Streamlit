import streamlit as st
import numpy as np
from Resource import LOGO_BASE64

class VisionUI:
    """
    Một lớp để đóng gói và quản lý toàn bộ giao diện người dùng (UI)
    của ứng dụng Vision AI Assistant trên Streamlit.
    """
    def __init__(self, camera_api):
        """Khởi tạo các giá trị và cấu hình ban đầu."""
        st.set_page_config(
            page_title="Vision AI Assistant",
            layout="wide"
        )
        # Lưu camera_api để sử dụng trong các hàm khác
        self.api = camera_api

        self._initialize_session_state()
        self.cameras_info = self._get_camera_list()
        self.image_placeholder = None

    def _initialize_session_state(self):
        """Khởi tạo các biến cần thiết trong st.session_state."""
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]
        if "selected_serial" not in st.session_state:
            st.session_state.selected_serial = None

        # Khởi tạo trạng thái cho các toggle, mặc định là TẮT (False)
        if "connect_status" not in st.session_state:
            st.session_state.connect_status = False
        if "stream_status" not in st.session_state:
            st.session_state.stream_status = False
            
    def _get_camera_list(self):
        try:
            available_cameras = self.api.list_cameras()
            if not available_cameras:
                st.warning("No cameras found. Please connect a camera.")
                return {"No Camera Found": {"serial": None, "model": "N/A", "info": "N/A"}}
            # Chuyển đổi list[CameraInfo] thành dict mong muốn
            cam_dict = {}
            for cam in available_cameras:
                label = f"{cam.friendly_name}"
                cam_dict[label] = {
                    "serial": cam.serial_number,
                    "model": cam.friendly_name,
                    "info": cam.info
                }
            return cam_dict
        except Exception as e:
            st.error(f"Error fetching camera list: {e}")
            return {"Error": {"serial": None, "model": str(e), "info": "N/A"}}
    
    # Các hàm callback để xử lý khi toggle thay đổi
    def _handle_connect_toggle(self):
        """Hàm được gọi khi toggle 'Connect/Disconnect' thay đổi."""
        # st.session_state.connect_status đã được tự động cập nhật
        # trước khi hàm này được gọi.
        serial = st.session_state.selected_serial
        st.toast(f"🔌 Connecting/Disconnecting camera...{serial}")
        if st.session_state.connect_status:
            if not serial:
                st.toast("⚠️ Please select a camera first!", icon="⚠️")
                st.session_state.connect_status = False
                return
            st.toast(f"🚀 Connecting to camera {serial}...")
            is_ok = self.api.connect(serial=serial)
            if is_ok:
                st.toast("✅ Connection successful!", icon="✅")
                st.session_state.connect_status = True
                  # Bắt đầu stream ngay khi kết nối thành công
            else:
                st.toast("❌ Connection failed!", icon="❌")
                st.session_state.stream_status = False
        else:
            st.toast("🔌 Disconnecting camera...")
            # << THÊM LOGIC NGẮT KẾT NỐI PYPYLON CỦA BẠN VÀO ĐÂY >>
            self.api.disconnect()
            st.toast("✅ Disconnected successfully!", icon="✅")
            # Khi ngắt kết nối, cũng nên tắt stream
            st.session_state.stream_status = False
            st.session_state.connect_status = False

    def _handle_stream_toggle(self):
        """Hàm được gọi khi toggle 'Start/Stop Stream' thay đổi."""
        if st.session_state.stream_status:
            try:
                self.api.start_stream()
            except Exception as e:
                st.toast(f"❌ Failed to start stream: {e}", icon="❌")
                st.session_state.stream_status = False
                return
            # Chỉ cho phép stream khi đã kết nối
            if not self.api.is_connected:
                st.toast("⚠️ Please connect to a camera first!", icon="⚠️")
                st.session_state.stream_status = False # Tự động gạt lại về Off
                return
            
            st.toast("🎥 Starting stream...")
            # << THÊM LOGIC BẮT ĐẦU STREAM CỦA BẠN VÀO ĐÂY >>
            self.api.start_stream()
            st.session_state.stream_status = True
        else:
            if self.api.is_connected:
                
                st.toast("🛑 Stopping stream.")
                self.api.stop_stream()
                # << THÊM LOGIC DỪNG STREAM CỦA BẠN VÀO ĐÂY >>
                st.session_state.stream_status = False
    
    def handle_capture_button(self):
        """Xử lý sự kiện khi người dùng nhấn nút 'Capture'."""
        if not self.api.is_connected:
            st.toast("⚠️ Please connect to a camera first!", icon="⚠️")
            return
        
        st.toast("📸 Capturing image...")
        img = self.api.get_image()
        if img is not None:
            st.session_state.captured_image = img
            with st.dialog("Captured Image"):
                st.image(img, caption=f"Captured from {st.session_state.selected_serial}", use_column_width=True)
            st.session_state.messages.append({"role": "assistant", "content": "Image captured successfully!"})
        else:
            st.toast("❌ Failed to capture image!", icon="❌")

    def _inject_custom_css(self):
        """Nhúng mã CSS tùy chỉnh vào ứng dụng."""
        st.markdown("""
        <style>
            /* --- Background chính và màu chữ mặc định --- */
            [data-testid="stAppViewContainer"] > .main {
                background-color: #57564F;
            }
            body, [data-testid="stMarkdown"], [data-testid="stHeader"] {
                color: #F8F3CE;
            }

            /* --- Style chung cho các widget --- */
            [data-testid="stSelectbox"], [data-testid="stChatMessage"] {
                background-color: #7A7A73;
                border-radius: 10px;
            }
            
            /* --- Style cho các container cụ thể bằng class --- */
            /* Container cho lịch sử chat */
            .chat-container {
                background-color: #7A7A73; /* Màu mặc định */
                border-radius: 10px;
                padding: 10px;
            }
            /* Container cho parser setting, có màu nền khác */
            .parser-container {
                background-color: #4a4a44; /* Màu tối hơn để phân biệt */
                border-radius: 10px;
                padding: 15px;
            }
            
            /* --- Các style khác --- */
            [data-testid="stSelectbox"] div, [data-testid="stChatMessage"] p, [data-testid="stTextInput"] div {
                color: #000000 !important;
            }
            [data-testid="stButton"] button {
                background-color: #7A7A73; color: #F8F3CE; border: 1px solid #F8F3CE;
                border-radius: 5px; width: 100%;
            }
            [data-testid="stButton"] button:hover {
                background-color: #57564F; color: #F8F3CE; border: 1px solid #FFFFFF;
            }
            [data-testid="stImage"] img {
                background-color: white; padding: 5px; border-radius: 10px;
            }
            .block-container { padding: 2rem; }
        </style>
        """, unsafe_allow_html=True)

    def _render_left_panel(self):
        """Vẽ cột bên trái chứa các thành phần điều khiển camera."""
        with st.container():
            st.header("Camera Control")

            top_cols = st.columns([1, 3, 2, 1], gap="medium")
            with top_cols[0]:
                st.image(f"data:image/png;base64,{LOGO_BASE64}", width=120)

            with top_cols[1]:
                is_disabled = not st.session_state.connect_status
                camera_options = list(self.cameras_info.keys())
                selected_camera_name = st.selectbox("List Camera", options=camera_options, label_visibility="collapsed")
                
                if selected_camera_name:
                    st.session_state.selected_serial = self.cameras_info[selected_camera_name]["serial"]
                    with st.expander(f"Details for {selected_camera_name}"):
                        st.json(self.cameras_info[selected_camera_name])
            with top_cols[2]:
                
                connect_label = "Disconnect" if st.session_state.connect_status else "Connect"
                st.toggle(
                    label=connect_label,
                    key="connect_status",
                    on_change=self._handle_connect_toggle,
                )

                stream_label = "Stop" if st.session_state.stream_status else "Start"
                st.toggle(
                    label=stream_label,
                    key="stream_status",
                    on_change=self._handle_stream_toggle,
                )
                
            top_cols[3].button("Capture", key="capture_image", on_click=self.handle_capture_button, use_container_width=True)
            top_cols[3].button("Analyze", key="analyze", use_container_width=True)
            
            st.markdown("---")
            st.subheader("Show Image Stream")
            self.image_placeholder = st.empty()
            placeholder_frame = np.full((720, 1280, 3), 122, dtype=np.uint8)
            self.image_placeholder.image(placeholder_frame, caption="Camera feed will appear here.", use_column_width=True)

    def _render_right_panel(self):
        """Vẽ cột bên phải chứa các thành phần chat."""
        with st.container():
            st.header("AI Assistant")

            # --- Lịch sử Chat với class CSS tùy chỉnh ---
            st.subheader("History Chat")
            # Bọc container trong một div với class tùy chỉnh
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            with st.container(height=400, border=False):
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")

            # --- Parser Setting với class CSS tùy chỉnh ---
            st.subheader("Parser Setting")
            # Bọc text_area trong một div với class tùy chỉnh khác
            st.markdown('<div class="parser-container">', unsafe_allow_html=True)
            st.text_area(
                "Agent's processed result",
                value="{\n  \"object_detected\": \"gear\",\n  \"status\": \"OK\",\n  \"confidence\": 0.98\n}",
                height=150,
                disabled=True,
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # --- Input prompt ---
            if prompt := st.chat_input("Prompt request..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                # ... logic xử lí và phản hồi của bot ...
                response = f"Echo from bot: {prompt}"
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() # Chạy lại script để cập nhật giao diện chat

    def render(self):
        """Phương thức chính để vẽ toàn bộ giao diện."""
        self._inject_custom_css()
        
        col_cam, col_chat = st.columns([3, 2], gap="large")

        with col_cam:
            self._render_left_panel()

        with col_chat:
            self._render_right_panel()


# --- Điểm bắt đầu chạy ứng dụng ---
if __name__ == "__main__":
    app = VisionUI(None)
    app.render()

#streamlit run StreamlitUI.py --logger.level=debug
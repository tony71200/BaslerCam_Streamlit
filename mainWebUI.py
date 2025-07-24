# mainWebUI.py
#streamlit run mainWebUI.py --logger.level=debug
import streamlit as st
import time
import numpy as np
from BaslerAPI import BaslerCameraAPI
from PIL import Image
from io import BytesIO
from StreamlitUI import VisionUI

def main():
    # --- KHỞI TẠO ---
    # Sử dụng session_state để API chỉ được khởi tạo 1 lần duy nhất
    if 'camera_api' not in st.session_state:
        st.session_state.camera_api = BaslerCameraAPI()

    # Lấy đối tượng API từ session_state
    api = st.session_state.camera_api
    # baslerapi = BaslerCameraAPI()
    # Khởi tạo UI và truyền đối tượng API vào
    # Giao diện UI giờ đây có thể truy cập các hàm của API
    ui = VisionUI(camera_api=api)
    # --- VẼ GIAO DIỆN ---
    ui.render()

    while st.session_state.stream_status:
        # Lấy ảnh từ camera
        image = api.get_image(timeout=100) # timeout thấp để không bị treo
        if image is not None:
            # Chuyển đổi ảnh sang định dạng phù hợp với Streamlit
            img = Image.fromarray(image)
            # Hiển thị ảnh trong placeholder
            ui.image_placeholder.image(img, caption="Camera feed", use_column_width=True)
        else:
            # Hiển thị ảnh mặc định nếu không có dữ liệu
            placeholder_frame = np.full((720, 1280, 3), 122, dtype=np.uint8)
            ui.image_placeholder.image(placeholder_frame, caption="No camera feed available.", use_column_width=True)
        time.sleep(0.01)
        # Kiểm tra lại trạng thái, nếu người dùng đã tắt stream thì thoát vòng lặp
        if not st.session_state.stream_status:
            break
    # Hiển thị ảnh mặc định khi không stream
    if not st.session_state.stream_status:
        placeholder_frame = np.full((720, 1280, 3), 122, dtype=np.uint8)
        if ui.image_placeholder:
            ui.image_placeholder.image(placeholder_frame, caption="Camera feed will appear here.", use_column_width=True)

if __name__ == "__main__":
    # Chạy ứng dụng Streamlit
    main()
    # Hoặc nếu muốn chạy trực tiếp từ terminal: streamlit run mainWebUI.py --logger.level=debug
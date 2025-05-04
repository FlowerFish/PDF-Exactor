import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
from io import BytesIO
import zipfile

# 初始化 session state
if 'display_page_numbers' not in st.session_state:
    st.session_state.display_page_numbers = False
if 'image_count' not in st.session_state:
    st.session_state.image_count = 0
if 'selected_images' not in st.session_state:
    st.session_state.selected_images = {}
if 'image_bytes_list' not in st.session_state:
    st.session_state.image_bytes_list = []
if 'pdf_content' not in st.session_state:
    st.session_state.pdf_content = None

# 自訂 CSS 樣式
st.markdown("""
    <style>
    .main-title { font-size: 2.2em; font-weight: bold; color: #2c3e50; margin-bottom: 10px; text-align: center; }
    .subheader { font-size: 1.5em; color: #34495e; margin-top: 20px; }
    .status-light { width: 20px; height: 20px; border-radius: 50%; display: inline-block; margin-right: 10px; }
    .stButton>button { background-color: #3498db; color: white; border-radius: 5px; padding: 8px 16px; }
    .stButton>button:hover { background-color: #2980b9; }
    .image-preview { border: 1px solid #ddd; border-radius: 5px; padding: 8px; background-color: #f9f9f9; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .footer { text-align: center; color: #7f8c8d; font-size: 0.9em; margin-top: 20px; }
    .expander-header { font-size: 1.2em; font-weight: bold; }
    .info-text { font-size: 0.95em; color: #7f8c8d; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# 頁碼顯示切換
def toggle_page_numbers():
    st.session_state.display_page_numbers = not st.session_state.display_page_numbers

# 全選/取消全選
def toggle_all_images(select_all):
    for i in range(st.session_state.image_count):
        st.session_state.selected_images[i] = select_all
    st.rerun()

# PDF 轉 TXT 功能
def convert_pdf_to_txt(pdf_file):
    try:
        output = BytesIO()
        with pdfplumber.open(pdf_file) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    if st.session_state.display_page_numbers:
                        output.write(f"--- Page {page_number} ---\n".encode('utf-8'))
                    output.write((text + "\n\n").encode('utf-8'))
                
                tables = page.extract_tables()
                for table in tables:
                    output.write(f"--- Table on Page {page_number} ---\n".encode('utf-8'))
                    for row in table:
                        output.write(" | ".join(str(cell) for cell in row).encode('utf-8') + b"\n")
                    output.write(b"\n")
        
        output.seek(0)
        return output, True
    except Exception as e:
        st.error(f"轉換失敗: {str(e)}")
        return None, False

# 圖像提取功能
def extract_images(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        st.session_state.image_count = 0
        image_bytes_list = []

        for page in doc:
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                image_bytes_list.append(image_bytes)
                st.session_state.image_count += 1
        
        st.session_state.selected_images = {i: True for i in range(st.session_state.image_count)}
        st.session_state.image_bytes_list = image_bytes_list
        return True
    except Exception as e:
        st.error(f"提取失敗: {str(e)}")
        return False

# 創建 ZIP 文件
def create_zip():
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, img_bytes in enumerate(st.session_state.image_bytes_list):
            if st.session_state.selected_images.get(i, False):
                zip_file.writestr(f"image_{i}.png", img_bytes)
    zip_buffer.seek(0)
    return zip_buffer

# Streamlit 介面
st.markdown('<div class="main-title">PDF 圖片擷取-轉TXT工具</div>', unsafe_allow_html=True)

# 左右分欄佈局
left_col, right_col = st.columns([1, 3])

# 左欄：功能項
with left_col:
    with st.container():
        # 頁碼顯示模組
        st.markdown('<div class="subheader">頁碼顯示</div>', unsafe_allow_html=True)
        st.markdown('<p class="info-text">切換是否在轉換的 TXT 檔案中顯示頁碼。</p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 5])
        with col1:
            status_color = "green" if st.session_state.display_page_numbers else "gray"
            st.markdown(f'<div class="status-light" style="background-color:{status_color};"></div>', unsafe_allow_html=True)
        with col2:
            if st.button(f"頁碼顯示：{'開啟' if st.session_state.display_page_numbers else '關閉'}"):
                toggle_page_numbers()

        # PDF 轉 TXT 模組
        with st.expander("PDF 轉 TXT", expanded=True):
            st.markdown('<p class="info-text">上傳 PDF 檔案並轉換為 TXT 格式。</p>', unsafe_allow_html=True)
            txt_pdf_file = st.file_uploader("選擇 PDF 檔案 (轉換為 TXT)", type=["pdf"], key="txt_pdf")
            if txt_pdf_file and st.button("開始轉換", key="txt_convert"):
                txt_output, success = convert_pdf_to_txt(txt_pdf_file)
                if success:
                    st.download_button(
                        label="下載 TXT 檔案",
                        data=txt_output,
                        file_name="converted_output.txt",
                        mime="text/plain"
                    )
                    st.success("轉換成功！請下載 TXT 檔案。")

        # 圖像提取模組
        with st.expander("PDF 圖像提取", expanded=True):
            st.markdown('<p class="info-text">上傳 PDF 檔案並提取其中的圖片。</p>', unsafe_allow_html=True)
            img_pdf_file = st.file_uploader("選擇 PDF 檔案 (提取圖像)", type=["pdf"], key="img_pdf")
            if img_pdf_file and st.button("開始提取", key="img_extract"):
                st.session_state.pdf_content = img_pdf_file.getvalue()
                success = extract_images(BytesIO(st.session_state.pdf_content))
                if success:
                    st.success(f"已提取 {st.session_state.image_count} 張圖片！")

# 右欄：預覽畫面
with right_col:
    with st.container():
        if st.session_state.image_bytes_list:
            # 全選/取消全選
            st.markdown('<p class="info-text">選擇要下載的圖片：</p>', unsafe_allow_html=True)
            col_select, _ = st.columns([3, 1])
            with col_select:
                if st.button("全選", key="select_all"):
                    toggle_all_images(True)
                if st.button("取消全選", key="deselect_all"):
                    toggle_all_images(False)
            
            # 圖片預覽網格
            num_columns = 4 if st.session_state.image_count > 3 else st.session_state.image_count
            cols = st.columns(num_columns) if st.session_state.image_count > 0 else []
            for i, img_bytes in enumerate(st.session_state.image_bytes_list):
                with cols[i % num_columns]:
                    st.markdown('<div class="image-preview">', unsafe_allow_html=True)
                    st.image(img_bytes, caption=f"image_{i}.png", use_container_width=True)
                    st.session_state.selected_images[i] = st.checkbox(
                        f"選擇 image_{i}.png",
                        value=st.session_state.selected_images.get(i, True),
                        key=f"img_{i}"
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # 下載選中圖片
            selected_count = sum(1 for i in st.session_state.selected_images.values() if i)
            if selected_count > 0:
                zip_buffer = create_zip()
                st.download_button(
                    label=f"下載選中的圖片 ({selected_count} 張)",
                    data=zip_buffer,
                    file_name="selected_images.zip",
                    mime="application/zip"
                )
                st.success(f"請下載選中的 {selected_count} 張圖片。")
            else:
                st.warning("請至少選擇一張圖片進行下載！")
        else:
            st.markdown('<p class="info-text" style="text-align:center;">請在左側上傳 PDF 並提取圖片以查看預覽。</p>', unsafe_allow_html=True)

# 頁腳
st.markdown('<hr><div class="footer">版本 Ver: 1.3 | 2025 | 作者：Aries Yeh</div>', unsafe_allow_html=True)
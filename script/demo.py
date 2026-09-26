import streamlit as st
import os
import sys

# Thêm thư mục src vào PYTHONPATH để có thể import các module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🤖",
    layout="centered"
)

# Thêm một chút CSS để giao diện nhìn hiện đại hơn
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6
    }
    .main {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1e3a8a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .source-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 10px 15px;
        margin-top: 10px;
        border-radius: 4px;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Kho Tri Thức AI (RAG Demo)")
st.write("Đặt câu hỏi về các bài báo khoa học AI trong cơ sở dữ liệu để nhận câu trả lời từ AI kèm theo nguồn trích dẫn.")

# Load dữ liệu (cache để không load lại nhiều lần)
@st.cache_resource
def load_rag_system():
    settings = load_settings()
    # Tải index từ baseline
    index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    return settings, index

try:
    settings, index = load_rag_system()
except Exception as e:
    st.error(f"Lỗi khi tải hệ thống RAG. Vui lòng chạy `py script/run_phase1.py` trước để xây dựng CSDL. Lỗi: {e}")
    st.stop()

# Khởi tạo session state để lưu lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("Nguồn trích dẫn"):
                for src in message["sources"]:
                    st.markdown(f"<div class='source-box'>{src}</div>", unsafe_allow_html=True)

# Ô nhập liệu cho người dùng
if prompt := st.chat_input("Nhập câu hỏi của bạn (VD: Summary của bài Attention is all you need là gì?)..."):
    # Thêm câu hỏi của người dùng vào lịch sử
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Hiện hiệu ứng đang nghĩ
    with st.chat_message("assistant"):
        with st.spinner("AI đang tìm kiếm tài liệu và suy nghĩ..."):
            try:
                # Gọi pipeline RAG
                result = answer_question(prompt, settings=settings, index=index)
                answer = result.answer
                
                # Trích xuất nguồn (nếu có)
                sources = []
                for doc_id, context in zip(result.retrieved_doc_ids, result.retrieved_contexts):
                    # Hiển thị một đoạn ngắn của nguồn
                    preview = context[:200] + "..." if len(context) > 200 else context
                    sources.append(f"**ID:** {doc_id}<br>{preview}")
                
                st.markdown(answer)
                if sources:
                    with st.expander("Nguồn trích dẫn"):
                        for src in sources:
                            st.markdown(f"<div class='source-box'>{src}</div>", unsafe_allow_html=True)
                
                # Lưu vào lịch sử
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
            except Exception as e:
                error_msg = f"Đã xảy ra lỗi khi gọi AI: {e}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

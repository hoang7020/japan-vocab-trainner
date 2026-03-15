import pathlib
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st


APP_TITLE = "Luyện từ vựng Nhật từ file Excel"

# Cấu hình cột trong file Excel.
# Bạn có thể chỉnh lại tên cột bên dưới cho khớp với file vocabulary.xlsx của mình.
COLUMN_CONFIG = {
    "index": "STT",          # cột số thứ tự (dùng để chọn 1-10, 20-40, ...)
    "kanji": "Kanji",        # cột kanji
    "hiragana": "Hiragana",  # cột hiragana (đáp án)
    "viet": "TiengViet",     # cột nghĩa tiếng Việt
    "hanviet": "HanViet",    # cột Hán Việt
}

def load_vocabulary(path: pathlib.Path) -> pd.DataFrame:
    if not path.exists():
        st.error(
            f"Không tìm thấy file Excel: {path.name}. "
            f"Hãy đặt file `{path.name}` chung thư mục với file `vocab_trainer_app.py`."
        )
        st.stop()

    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        st.error(f"Không đọc được file Excel: {e}")
        st.stop()

    # Đảm bảo các cột cần thiết tồn tại
    missing = [col_name for col_name in COLUMN_CONFIG.values() if col_name not in df.columns]
    if missing:
        st.error(
            "File Excel thiếu các cột sau:\n"
            + ", ".join(f"`{c}`" for c in missing)
            + "\nHãy chỉnh `COLUMN_CONFIG` ở đầu file Python hoặc cập nhật tên cột trong Excel."
        )
        st.write("Các cột hiện có trong file:", list(df.columns))
        st.stop()

    # Chuẩn hóa, chỉ giữ các cột cần dùng
    df = df[
        [
            COLUMN_CONFIG["index"],
            COLUMN_CONFIG["kanji"],
            COLUMN_CONFIG["hiragana"],
            COLUMN_CONFIG["viet"],
            COLUMN_CONFIG["hanviet"],
        ]
    ].copy()

    df.rename(
        columns={
            COLUMN_CONFIG["index"]: "index",
            COLUMN_CONFIG["kanji"]: "kanji",
            COLUMN_CONFIG["hiragana"]: "hiragana",
            COLUMN_CONFIG["viet"]: "viet",
            COLUMN_CONFIG["hanviet"]: "hanviet",
        },
        inplace=True,
    )

    # Bỏ các dòng không có kanji hoặc hiragana
    df.dropna(subset=["kanji", "hiragana"], inplace=True)

    return df


def normalize_answer(text: str) -> str:
    """Chuẩn hóa chuỗi để so sánh (bỏ khoảng trắng thừa, chữ thường)."""
    return "".join(text.strip().lower().split())


def init_session_state():
    st.session_state.setdefault("words_queue", [])   # danh sách index của các từ sẽ hỏi
    st.session_state.setdefault("current_idx", None) # index (dòng) hiện tại trong DataFrame
    st.session_state.setdefault("answered_correct", set())  # index các từ đã trả lời đúng
    st.session_state.setdefault("last_result", None)        # "correct" | "wrong" | None
    st.session_state.setdefault("last_meaning", "")         # nội dung nghĩa để hiển thị lại
    st.session_state.setdefault("started", False)
    st.session_state.setdefault("range_indices", [])        # toàn bộ index trong khoảng đã chọn
    st.session_state.setdefault("total_words", 0)           # tổng số từ trong khoảng đã chọn
    st.session_state.setdefault("mode", "Kanji → Hiragana")  # chế độ học hiện tại
    st.session_state.setdefault("show_answer", False)        # dùng cho chế độ flashcard
    st.session_state.setdefault("order_mode", "Tăng dần")    # thứ tự xuất hiện từ vựng


def build_initial_queue(df: pd.DataFrame, start_n: int, end_n: int, order_mode: str) -> List[int]:
    """Tạo danh sách index (dòng DataFrame) cần học trong khoảng [start_n, end_n]
    với thứ tự xuất hiện theo order_mode."""
    subset = df[(df["index"] >= start_n) & (df["index"] <= end_n)]

    if order_mode == "Giảm dần":
        subset = subset.sort_values("index", ascending=False)
    elif order_mode == "Ngẫu nhiên":
        subset = subset.sample(frac=1, random_state=None)
    else:
        # Mặc định: tăng dần theo STT
        subset = subset.sort_values("index", ascending=True)

    # Dùng index thực của DataFrame để truy cập nhanh
    return list(subset.index)


def pick_next_word() -> Optional[int]:
    """Lấy từ tiếp theo trong hàng đợi."""
    queue: List[int] = st.session_state["words_queue"]
    if not queue:
        return None
    # Lấy phần tử đầu
    next_idx = queue.pop(0)
    st.session_state["current_idx"] = next_idx
    return next_idx


def requeue_word(word_idx: int):
    """Đưa từ sai vào lại cuối hàng đợi, để hỏi lại sau."""
    st.session_state["words_queue"].append(word_idx)


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")

    # Giảm khoảng trắng trên/dưới để hạn chế phải scroll
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 0.5rem;
            max-width: 900px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title(APP_TITLE)

    init_session_state()

    # Lấy danh sách file Excel trong thư mục docs
    docs_dir = pathlib.Path(__file__).parent / "docs"
    excel_files = []
    if docs_dir.exists():
        excel_files = sorted(p for p in docs_dir.glob("*.xlsx") if p.is_file())

    if not excel_files:
        st.error(
            "Không tìm thấy file .xlsx nào trong thư mục `docs`.\n"
            "Hãy đặt các file từ vựng (ví dụ `chap2.xlsx`, `vocabulary.xlsx`) vào thư mục `docs`."
        )
        return

    file_options = [p.name for p in excel_files]
    default_file_index = 0
    if "selected_file_name" in st.session_state and st.session_state["selected_file_name"] in file_options:
        default_file_index = file_options.index(st.session_state["selected_file_name"])

    with st.sidebar:
        st.header("Cài đặt bài học")

        selected_file_name = st.selectbox(
            "Chọn file từ vựng (trong thư mục docs)",
            file_options,
            index=default_file_index,
        )
        st.session_state["selected_file_name"] = selected_file_name
        excel_path = next(p for p in excel_files if p.name == selected_file_name)

        df = load_vocabulary(excel_path)

        mode = st.radio(
            "Chế độ học",
            ["Kanji → Hiragana", "Nghĩa → Hiragana", "Flashcard"],
            index=["Kanji → Hiragana", "Nghĩa → Hiragana", "Flashcard"].index(
                st.session_state.get("mode", "Kanji → Hiragana")
            ),
        )
        st.session_state["mode"] = mode

        order_mode = st.radio(
            "Thứ tự xuất hiện",
            ["Tăng dần", "Giảm dần", "Ngẫu nhiên"],
            index=["Tăng dần", "Giảm dần", "Ngẫu nhiên"].index(
                st.session_state.get("order_mode", "Tăng dần")
            ),
        )
        st.session_state["order_mode"] = order_mode

        min_index = int(df["index"].min())
        max_index = int(df["index"].max())

        st.caption(f"Số thứ tự nhỏ nhất trong file: **{min_index}**")
        st.caption(f"Số thứ tự lớn nhất trong file: **{max_index}**")

        start_n = st.number_input(
            "Từ số thứ tự",
            min_value=min_index,
            max_value=max_index,
            value=min_index,
            step=1,
        )
        end_n = st.number_input(
            "Đến số thứ tự",
            min_value=min_index,
            max_value=max_index,
            value=min(start_n + 9, max_index),
            step=1,
        )

        if start_n > end_n:
            st.error("`Từ số thứ tự` phải nhỏ hơn hoặc bằng `Đến số thứ tự`.")
        else:
            if st.button("Bắt đầu / Làm lại", type="primary"):
                queue = build_initial_queue(df, int(start_n), int(end_n), st.session_state["order_mode"])
                if not queue:
                    st.warning("Không có từ nào trong khoảng đã chọn.")
                else:
                    st.session_state["words_queue"] = queue
                    st.session_state["range_indices"] = queue.copy()
                    st.session_state["total_words"] = len(queue)
                    st.session_state["answered_correct"] = set()
                    st.session_state["show_answer"] = False
                    st.session_state["last_result"] = None
                    st.session_state["last_meaning"] = ""
                    st.session_state["started"] = True
                    pick_next_word()

    # Vùng nội dung chính
    content = st.container()

    if not st.session_state["started"]:
        with content:
            st.info("Hãy chọn khoảng số thứ tự trong thanh bên trái rồi bấm **Bắt đầu / Làm lại**.")
    else:
        current_idx = st.session_state["current_idx"]
        total_words = st.session_state.get("total_words", len(st.session_state.get("range_indices", [])))
        learned_count = len(st.session_state["answered_correct"])
        not_learned_count = max(total_words - learned_count, 0)
        remaining_questions = len(st.session_state["words_queue"])
        if current_idx is not None and current_idx not in st.session_state["answered_correct"]:
            remaining_questions += 1

        mode = st.session_state.get("mode", "Kanji → Hiragana")

        with content:
            st.markdown(
                f"**Đã thuộc:** {learned_count} / {total_words} &nbsp;&nbsp; "
                f"**Chưa thuộc:** {not_learned_count} &nbsp;&nbsp; "
                f"**Câu hỏi còn lại:** {remaining_questions}"
            )

            # Nếu đã hết từ để hỏi
            if current_idx is None:
                st.success("Chúc mừng! Bạn đã hoàn thành tất cả các từ trong khoảng đã chọn.")

                # Nếu đã thuộc hết toàn bộ, cho phép học lại toàn bộ
                if learned_count == total_words and total_words > 0:
                    if st.button("Học lại toàn bộ", type="primary"):
                        st.session_state["words_queue"] = st.session_state.get("range_indices", []).copy()
                        st.session_state["answered_correct"] = set()
                        st.session_state["show_answer"] = False
                        st.session_state["last_result"] = None
                        st.session_state["last_meaning"] = ""
                        pick_next_word()
                # Không hiển thị thêm câu hỏi khi đã hết
            else:
                # Lấy dữ liệu từ hiện tại
                row = df.loc[current_idx]
                kanji = row["kanji"]
                correct_hiragana = str(row["hiragana"])
                viet = str(row["viet"]) if pd.notna(row["viet"]) else ""
                hanviet = str(row["hanviet"]) if pd.notna(row["hanviet"]) else ""

                st.markdown(f"**Từ số thứ tự:** {int(row['index'])}")

                # Luôn khai báo CSS flashcard một lần cho cả 3 chế độ
                st.markdown(
                    """
                    <style>
                    .flashcard {
                        border-radius: 12px;
                        padding: 18px 16px;
                        margin: 8px 0 12px 0;
                        text-align: center;
                        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
                        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
                        min-height: 150px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .flashcard-front {
                        font-size: 32px;
                        font-weight: 700;
                    }
                    .flashcard-back-main {
                        font-size: 26px;
                        font-weight: 700;
                        margin-bottom: 4px;
                    }
                    .flashcard-back-sub {
                        font-size: 15px;
                        color: #555;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                # Chế độ Flashcard
                if mode == "Flashcard":
                    meaning_text = f"Nghĩa: **{viet}**"
                    if hanviet:
                        meaning_text += f" &nbsp;|&nbsp; Hán Việt: **{hanviet}**"

                    # Hàng nút điều khiển: Lật thẻ, Đúng, Sai
                    flip_col, correct_col, wrong_col = st.columns([1, 1, 1])
                    flip_clicked = flip_col.button("Lật thẻ", key="flashcard_flip")
                    correct_clicked = correct_col.button("Tôi đã nhớ (Đúng)", key="flashcard_correct")
                    wrong_clicked = wrong_col.button("Chưa nhớ (Sai)", key="flashcard_wrong")

                    # Xử lý nhấn nút trước rồi mới render thẻ để tránh phải click 2 lần
                    if flip_clicked:
                        st.session_state["show_answer"] = not st.session_state.get("show_answer", False)
                        st.rerun()

                    if correct_clicked:
                        st.session_state["answered_correct"].add(current_idx)
                        st.session_state["show_answer"] = False
                        next_idx = pick_next_word()
                        if next_idx is None:
                            st.success("Bạn đã trả lời đúng tất cả các từ trong khoảng đã chọn!")
                        st.rerun()

                    if wrong_clicked:
                        st.session_state["show_answer"] = False
                        requeue_word(current_idx)
                        next_idx = pick_next_word()
                        if next_idx is None:
                            st.success("Bạn đã hoàn thành tất cả các từ.")
                        st.rerun()

                    # Nội dung thẻ: mặt trước / mặt sau (sau khi đã xử lý click)
                    if not st.session_state.get("show_answer", False):
                        # Mặt trước: chỉ hiện Kanji
                        st.markdown(
                            f"""
                            <div class="flashcard">
                                <div class="flashcard-front">{kanji}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        # Mặt sau: Hiragana + nghĩa
                        back_html = f"""
                            <div class="flashcard">
                                <div class="flashcard-back-main">{correct_hiragana}</div>
                                <div class="flashcard-back-sub">{viet}</div>
                        """
                        if hanviet:
                            back_html += f'<div class="flashcard-back-sub">Hán Việt: {hanviet}</div>'
                        back_html += "</div>"
                        st.markdown(back_html, unsafe_allow_html=True)

                else:
                    # Hai chế độ nhập Hiragana, hiển thị câu hỏi trong card
                    if mode == "Kanji → Hiragana":
                        question_html = f"""
                            <div class="flashcard">
                                <div class="flashcard-front">{kanji}</div>
                            </div>
                        """
                        question_label = "Nhập Hiragana cho Kanji này rồi nhấn Enter"
                    else:
                        # Nghĩa → Hiragana
                        meaning_for_question = viet
                        hv_part = f"Hán Việt: {hanviet}" if hanviet else ""
                        question_html = f"""
                            <div class="flashcard">
                                <div class="flashcard-back-sub">{meaning_for_question}</div>
                                {f'<div class="flashcard-back-sub">{hv_part}</div>' if hv_part else ''}
                            </div>
                        """
                        question_label = "Nhập Hiragana cho từ có nghĩa sau rồi nhấn Enter"

                    st.markdown(question_html, unsafe_allow_html=True)

                    # Form để nhập đáp án (Enter sẽ submit)
                    with st.form(key="answer_form", clear_on_submit=True):
                        user_answer = st.text_input(question_label, value="")
                        submitted = st.form_submit_button("Enter / Kiểm tra")

                    if submitted:
                        user_norm = normalize_answer(user_answer)
                        correct_norm = normalize_answer(correct_hiragana)

                        # Không chấm điểm khi người dùng chưa gõ gì (tránh Enter trống bị tính là sai)
                        if user_norm == "":
                            st.warning("Bạn chưa nhập gì. Hãy gõ Hiragana rồi nhấn Enter.")
                        else:
                            meaning_text = f"Nghĩa: **{viet}**"
                            if hanviet:
                                meaning_text += f" &nbsp;|&nbsp; Hán Việt: **{hanviet}**"

                            if user_norm == correct_norm:
                                st.session_state["answered_correct"].add(current_idx)
                                st.session_state["last_result"] = "correct"
                                st.session_state["last_meaning"] = meaning_text
                                st.success("✅ Đúng rồi! " + meaning_text)
                                # Từ đúng sẽ KHÔNG đưa lại vào hàng đợi
                                next_idx = pick_next_word()
                                if next_idx is None:
                                    st.success("Bạn đã trả lời đúng tất cả các từ trong khoảng đã chọn!")
                            else:
                                st.session_state["last_result"] = "wrong"
                                st.session_state["last_meaning"] = meaning_text
                                st.error(f"❌ Sai. Đáp án đúng: **{correct_hiragana}**. {meaning_text}")
                                # Từ sai: đưa lại vào cuối hàng đợi
                                requeue_word(current_idx)
                                next_idx = pick_next_word()
                                if next_idx is None:
                                    # Trường hợp hiếm khi hàng đợi rỗng, nhưng vẫn xử lý cho an toàn
                                    st.success("Bạn đã hoàn thành tất cả các từ.")

    # Phần giải thích / hướng dẫn luôn ở cuối trang
    st.markdown("---")
    st.markdown(
        "**Hướng dẫn ngắn:**\n"
        "- Chọn khoảng số thứ tự (ví dụ 1-10, 20-40) và chế độ học ở thanh bên trái.\n"
        "- Chế độ *Kanji → Hiragana*: nhìn Kanji, gõ Hiragana.\n"
        "- Chế độ *Nghĩa → Hiragana*: nhìn nghĩa (Tiếng Việt + Hán Việt), gõ Hiragana.\n"
        "- Chế độ *Flashcard*: bấm **Lật thẻ** để xem mặt trước/mặt sau, rồi tự đánh dấu Đúng/Sai để lặp lại từ chưa thuộc."
    )


if __name__ == "__main__":
    main()


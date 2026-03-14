## Ứng dụng luyện từ vựng từ `vocabulary.xlsx`

### 1. Chuẩn bị

- **Yêu cầu Python**: Python 3.9+ (khuyến nghị).
- Đặt file **`vocabulary.xlsx`** cùng thư mục với file **`vocab_trainer_app.py`**.

Mặc định, ứng dụng mong đợi các cột trong file Excel như sau (có header):

- **`STT`**: số thứ tự (dùng để chọn khoảng 1-10, 20-40, …).
- **`Kanji`**: chữ Kanji.
- **`Hiragana`**: cách đọc hiragana (đáp án).
- **`TiengViet`**: nghĩa tiếng Việt.
- **`HanViet`**: nghĩa Hán Việt.

Nếu tên cột khác, hãy mở file `vocab_trainer_app.py` và chỉnh lại phần `COLUMN_CONFIG` ở đầu file cho đúng với tên cột của bạn.

### 2. Cài đặt thư viện

Trong thư mục dự án (nơi có file `requirements.txt`), chạy:

```bash
pip install -r requirements.txt
```

### 3. Chạy ứng dụng trên trình duyệt

Trong thư mục dự án, chạy:

```bash
streamlit run vocab_trainer_app.py
```

Sau khi chạy, Streamlit sẽ in ra một địa chỉ dạng `http://localhost:8501`. Mở địa chỉ đó trong trình duyệt.

### 4. Cách sử dụng

- Ở **thanh bên trái (sidebar)**:
  - Nhập khoảng số thứ tự cần học (ví dụ: `1` đến `10`, hoặc `20` đến `40`).
  - Bấm nút **“Bắt đầu / Làm lại”**.
- Ở phần nội dung chính:
  - Ứng dụng hiển thị **Kanji**.
  - Bạn nhập **Hiragana** rồi nhấn **Enter** (hoặc nút **Enter / Kiểm tra**).
  - **Nếu đúng**:
    - Ứng dụng báo đúng và hiển thị **nghĩa tiếng Việt + Hán Việt**.
    - Từ đó **sẽ không xuất hiện lại**.
  - **Nếu sai**:
    - Ứng dụng báo sai, hiển thị **nghĩa tiếng Việt + Hán Việt** và đáp án đúng Hiragana.
    - Từ đó **sẽ được xếp lại vào cuối hàng đợi** và **hỏi lại sau** cho đến khi bạn trả lời đúng.


# Lab 3: Xây dựng ReAct Agent Hỗ Trợ Đặt Vé Máy Bay (Team 15)

Chào mừng bạn đến với dự án Lab 3 của Team 15! Dự án này tập trung vào việc chuyển đổi từ một Chatbot LLM thông thường sang một **ReAct Agent** (Reasoning + Acting) chuyên nghiệp, có khả năng sử dụng công cụ (Tools) để giải quyết các tác vụ phức tạp trong thực tế như tìm kiếm và đặt vé máy bay.

## 👥 Thành viên nhóm (Team 15)
- **Nguyễn Trí Cao**
- **Lê Minh Tuấn**
- **Cao Diệu Ly**
- **Đậu Văn Nam**

🔗 **GitHub Repository**: [https://github.com/dauvannam1804/Lab-3-Team15](https://github.com/dauvannam1804/Lab-3-Team15)

---

## 🚀 Hướng dẫn cài đặt

### 1. Thiết lập môi trường và cài đặt
Sử dụng `uv` để quản lý môi trường ảo (Virtual Environment) và cài đặt thư viện một cách nhanh chóng:

```bash
# Tạo file cấu hình từ ví dụ
cp .env.example .env

# Tạo môi trường ảo với uv
uv venv

# Kích hoạt môi trường ảo
source .venv/bin/activate

# Cài đặt toàn bộ dependencies (đồng bộ với uv.lock)
uv sync
```

---

## 🛠️ Cách chạy chương trình

Hệ thống hỗ trợ nhiều chế độ chạy và nhiều nhà cung cấp mô hình (Providers) khác nhau.

### 1. Các chế độ chạy (`--mode`)
- `baseline`: Chạy chatbot thông thường (không có công cụ).
- `agent_v1`: Chạy Agent phiên bản sơ khai (Prompt rút gọn).
- `agent_v2`: Chạy Agent phiên bản cải tiến (Full Prompt + Guardrails).
- `all`: Chạy tuần tự cả 3 chế độ trên để so sánh hiệu năng.

### 2. Các nhà cung cấp mô hình (`--provider`)
- `mock`: Sử dụng dữ liệu giả lập (Không tốn phí API, dùng để kiểm tra logic).
- `openai`: Sử dụng GPT-4o-mini (Mặc định).
- `gemini`: Sử dụng Google Gemini.
- `local`: Sử dụng mô hình chạy cục bộ (Phi-3 GGUF).

### 3. Ví dụ lệnh chạy
**Chạy thử nghiệm nhanh với dữ liệu giả lập (All-in-one):**
```bash
python main.py --mode all --provider mock
```

**Chạy Agent phiên bản cải tiến với OpenAI:**
```bash
python main.py --mode agent_v2 --provider openai
```

**Chạy thử nghiệm trên các Test Case cụ thể:**
```bash
python main.py --mode agent_v2 --provider openai --cases TC1 TC4
```

---

## 📂 Cấu trúc dự án
- `main.py`: Entry point chính của hệ thống, quản lý việc chạy các test case.
- `src/agent/agent.py`: Logic cốt lõi của vòng lặp **ReAct (Thought-Action-Observation)**.
- `src/tools/`: Chứa các công cụ (Tools) mà Agent có thể sử dụng (Search, Book, Weather, Baggage).
- `src/core/`: Quản lý các LLM Providers (OpenAI, Gemini, Mock).
- `src/telemetry/`: Hệ thống giám sát, ghi log (JSON) và đo lường hiệu suất (Tokens, Latency).
- `logs/`: Nơi lưu trữ nhật ký chạy và các file tổng hợp kết quả (summary).
- `report/`: Chứa báo cáo nhóm và báo cáo cá nhân của từng thành viên.

---

## 🎯 Mục tiêu dự án
1.  **Vòng lặp ReAct**: Triển khai thành công quy trình Suy luận -> Hành động -> Quan sát.
2.  **Đa dạng công cụ**: Tích hợp các công cụ tra cứu chuyến bay, đặt vé, thời tiết và hành lý.
3.  **Bảo mật & Phạm vi**: Thiết lập Guardrails để Agent chỉ hoạt động trong phạm vi hỗ trợ bay (Adversarial defense).
4.  **Đo lường & Phân tích**: Sử dụng hệ thống Telemetry để phân tích Token Efficiency và Failure Handling (RCA).

---

*Chúc các bạn trải nghiệm Agent mượt mà! Mọi vấn đề vui lòng liên hệ Team 15 qua GitHub.*

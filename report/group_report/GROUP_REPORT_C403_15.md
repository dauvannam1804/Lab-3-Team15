# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: C403-15
- **Team Members**: 
    - Nguyễn Trí Cao
    - Lê Minh Tuấn
    - Cao Diệu Ly
    - Đậu Văn Nam
- **Deployment Date**: 6/4/2026

---

## 1. Executive Summary

- **Mục tiêu**: Xây dựng một hệ thống Agent AI có khả năng đặt vé máy bay tương tác thay vì chỉ là Chatbot thông thường.
- **Success Rate**: Đạt 100% trong số 5 bài test (đối với mock runtime). Tuy nhiên, độ hoàn thiện logic tác vụ với agent thì bị kẹt ở mức tối đa do mock provider chưa hỗ trợ định dạng Action đúng chuẩn.
- **Key Outcome**: Hệ thống đã được thiết lập khung (skeleton) theo kiến trúc ReAct kết hợp trích xuất công cụ hoàn chỉnh, hỗ trợ đo lường độ trễ và tiêu thụ token. Chatbot baseline có thể trả lời các câu hỏi mô phỏng nhưng không thể thực thi thật, trong khi Agent ReAct có khả năng tự gọi Tool và quan sát môi trường thật.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
Vòng lặp ReAct được chia thành 3 phần: **Thought** (suy luận tình huống hiện tại), **Action** (quyết định gọi công cụ JSON) và **Observation** (nhận kết quả từ công cụ và cập nhật transcript). Tải trình tự thực thi theo mô tả sau:
![ReAct Loop](../../../API_Payment_Loop_Workflow-2026-04-06-092316.png)

### 2.2 Tool Definitions (Inventory)
Hệ thống sử dụng các công cụ thao tác với hệ thống đặt vé mô phỏng (mock_db):

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `search_flights` | `json` | Tra cứu chuyến bay khả dụng qua mã sân bay tới/lui và ngày đi (YYYY-MM-DD). |
| `book_flight` | `json` | Thực thi đặt vé, trừ chỗ trên hệ thống dựa vào mã chuyến bay và lưu PNR. |
| `get_weather` | `json` | Lấy dữ liệu thời tiết tại sân bay điểm đến để cung cấp ngữ cảnh du lịch. |
| `get_baggage_policy` | `json` | Kiểm tra quy định hành lý của từng hãng hàng không. |

### 2.3 LLM Providers Used
- **Primary**: LLM APIs (OpenAI/Gemini qua `gpt-4o` / `gemini-1.5-flash`).
- **Thử nghiệm**: `MockProvider` cho kiểm thử tự động offline.

---

## 3. Telemetry & Performance Dashboard

*Dữ liệu lấy từ bản ghi log đo lường ngày 6/4/2026 với `MockProvider`:*

- **Average Latency (Agent)**: 7.0ms
- **Average Latency (Baseline)**: 0.2ms
- **Average Tokens per request**: ~28 tokens
- **Total Cost of Test Suite**: $0.0014 (ước tính)

*Lưu ý: Độ trễ ở đây rất thấp vì đang được chạy bằng mock framework. Trên thực tế (OpenAI api), độ trễ P50 thường dao động từ 1500ms - 3000ms mỗi vòng lặp.*

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study 1: Trả lời sai phạm vi (Out-of-scope Bleeding) do nhiễu Keyword
- **Input**: "Có chuyến bay nào bị ảnh hưởng bởi chiến tranh Iran không?"
- **Observation**: Trong các bản build ban đầu, Agent vẫn cố gắng suy luận và sinh ra `Thought` liên quan đến việc tìm vé hoặc gọi tool `search_flights` tìm "Iran", thay vì từ chối yêu cầu ngoài lề (chiến sự/chính trị).
- **Root Cause**: Mô hình bị "nhiễu" do prompt ban đầu chưa cứng rắn. Khi thấy keyword như "chuyến bay", nó tự động bỏ qua tính chất "chiến tranh" và cố giải quyết tác vụ. Workflow chưa có chốt chặn Strict Scope chặt chẽ.
- **Giải pháp (Đã khắc phục)**: Cập nhật lại System Prompt với quy tắc **STRICT SCOPE LIMITATION**. Ép LLM phải thực hiện check scope từ đầu và lập tức trả về `Final Answer: Xin lỗi, tôi chỉ là...` nếu câu hỏi lệch trọng tâm, không cho phép đi vào vòng lặp gọi Tool.

### Case Study 2: Lỗi vòng lặp Agent do định dạng Parser (Vượt quá max_steps)
- **Input**: "Đặt cho tôi chuyến VJ122." (Khi chạy bằng Mock API trong Automation Test).
- **Observation**: Agent sinh ra `Thought: ...` hoặc các câu phản hồi text thay vì tạo chuẩn cú pháp `Action: tool_name({"key": "value"})`. 
- **Root Cause**: Khi khởi chạy ở dạng Mock API, mô hình giả lập trả ra chuỗi văn bản không tuân thủ quy tắc prompt. Lỗi Parser kích hoạt, thông báo cho Agent nhưng luồng lại lặp lại lỗi cũ liên tục cho đến khi chạm tới cơ chế an toàn `max_steps=7`.
- **Giải pháp (Phòng ngự hệ thống)**: Đã thiết lập thành công Catch blocks để không làm crash code khi LLM trả sai cấu trúc JSON. Ở môi trường Production thực tế, giải pháp triệt để là thay RegEx thủ công bằng Function Calling Native của LLM platform.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Sự khác biệt |
| :--- | :--- | :--- | :--- |
| Câu hỏi tra cứu giá | Chỉ trả nội dung fix sẵn hoặc bịa | Phải tra bằng Tool mới trả lời | Agent chính xác từ DB. |
| Chức năng Đặt vé | Ảo giác tạo mã PNR giả | Gọi hàm trừ Seat/Lưu hành khách | Agent thay đổi trạng thái db. |

---

## 6. Production Readiness Review

- **Security**: Đảm bảo đầu vào cho `book_flight` và `search_flights` được escape và mapping đúng thành mã IATA (`HAN`, `SGN`, `DAD`).
- **Guardrails**: Đã thêm scope checking trong System Prompt để Agent trực tiếp từ chối các câu hỏi không liên quan đến chuyến bay. Set giới hạn `max_steps=7`.
- **Scaling**: Cần tích hợp bộ nhớ dài hạn với DB Sqlite thật thay cho `mock_db.json`. Cần chuyển từ parse RegEx thủ công Text-to-Action sang OpenAI Function Calling.

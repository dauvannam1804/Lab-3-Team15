# Xây Dựng Agent Hỗ Trợ Đặt Vé Máy Bay (Lab 3: ReAct Agent)

Bản đề xuất này phác thảo các tính năng và kế hoạch triển khai cho một Chatbot đặt vé máy bay sử dụng cấu trúc **ReAct** (Thought-Action-Observation), nhằm đáp ứng tối đa yêu cầu của điểm Base (45đ) và hướng tới lấy thêm điểm Bonus (15đ) theo quy định trong `SCORING.md`.

## User Review Required

> [!IMPORTANT]  
> Xin chào nhóm! Dưới đây là đề xuất tổng thể cho Agent Đặt vé máy bay. 
> Xin hãy xem xét qua phần **Các Chức Năng (Tools)** được liệt kê. Nếu các bạn muốn thêm/bớt tool nào (ví dụ như thanh toán vé, xin chính sách hành lý...) thì hãy đóng góp ý kiến để mình điều chỉnh trước khi code nhé!

## Phân Tích Mã Nguồn Hiện Tại

- **Kiến trúc LLM (`src/core/`)**: Đã có sẵn Interface linh hoạt hỗ trợ nhiều providers (OpenAI, Gemini, Local GGUF). Đây là nền tảng tốt để build Agent.
- **Tiêu chuẩn Giám sát (`src/telemetry/`)**: `logger.py` và `metrics.py` đã được cấu hình. Cần được nhúng sâu vào quá trình Action để tạo **Trace Quality** (dùng phân tích trong Report cá nhân/nhóm).
- **Core Loop (`src/agent/agent.py`)**: Đây là trái tim của Agent. Hiện mới chỉ có khai báo bộ khung. Cần bổ sung khả năng parse chuỗi Action thông minh (bằng Regex/JSON) và xử lý `Observation`.

## Đề Xuất Tính Năng & Tools Cụ Thể

Để lấy trọn vẹn điểm "Agent v1 (Working)" (cần 2+ tools) và lấy thêm điểm Bonus "Extra Tools" (+2) hay "Failure Handling" (+3), chúng ta nên chia Tools làm 2 nhóm:

### 1. Nhóm Core Tools (Bắt Buộc)

- **`search_flights(origin, destination, date)`**: 
  - *Chức năng*: Truy vấn database giả lập (mock list) để trả về các chuyến bay khả dụng kèm giá tiền, ID chuyến bay.
- **`book_flight(flight_id, passenger_name, contact_info)`**:
  - *Chức năng*: Thực hiện đặt vé và trả về mã Booking Reference (PNR). Sẽ có xử lý lỗi ngẫu nhiên giả lập (ví dụ hết vé) để Agent tập xử lý "Failure Handling".

### 2. Nhóm Bonus Tools (Tối ưu trải nghiệm & Điểm)

- **`get_weather(location, date)`**:
  - *Chức năng*: Trả về thông tin thời tiết điểm đến để Agent có thể đóng vai trò "Tư vấn viên", báo cho khách hàng thời tiết khi họ tới. (Extra Tool)
- **`get_baggage_policy(airline_code)`**:
  - *Chức năng*: Công cụ Retrieval (RAG đơn giản) để tra cứu xem hành lý ký gửi của chuyến bay đó là bao nhiêu kg.

## Kế Hoạch Triển Khai Mã Nguồn (Proposed Changes)

---

### Mảng Tools (Công cụ)

#### [NEW] `src/tools/flight_tools.py`
Tạo file chứa các hàm (functions) cho Agent, bên trong là các tool `search_flights`, `book_flight`, `get_weather`, `get_baggage_policy` được biểu diễn dưới dạng Python function và một hàm Helper sinh meta-data (name, description, arg_schema) để truyền vào `ReActAgent`.

---

### Mảng Agent (Tác Tử)

#### [MODIFY] `src/agent/agent.py`
- Bổ sung `System Prompt` quy định nghiêm ngặt cú pháp Thought, Action, Observation.
- Cập nhật vòng lặp `while steps < self.max_steps`: ghép lời gọi LLM.
- **Xử lý Regex Parse**: Tìm kiếm chuỗi định dạng `Action: function_name(args)` để cô lập arguments.
- Gọi hàm từ `self._execute_tool()` và gán giá trị trả về cho `Observation:`.
- Bắt lỗi khi Parser thất bại (Hallucination) để tiếp tục vòng lặp tránh crash (Gain: Failure Handling points).

## Phân Công Công Việc (Team of 4 Members)

Để đảm bảo vừa bao phủ điểm Group Score (Base+Bonus) vừa giúp mỗi cá nhân có dữ liệu viết Individual Report (cần tối thiểu 40 điểm/cá nhân), nhóm 4 người nên chia Vai trò (Roles) như sau:

| Thành Viên | Trách nhiệm chính (Roles) | Files phụ trách | Mục tiêu chấm điểm (SCORING.md) |
| :--- | :--- | :--- | :--- |
| **Thành viên 1** <br>*(Core Agent Dev)* | Xây dựng vòng lặp **ReAct Loop**. Viết `System Prompt`, dùng Regex bắt chuỗi và điều hướng Gọi Hàm (Function Routing). Xử lý vòng lặp tránh vô hạn. | `src/agent/agent.py` | Lấy điểm **Agent v1 (Working)** và **Agent v2 (Improved)**. Cung cấp log lỗi kỹ thuật. |
| **Thành viên 2** <br>*(Tools & Backend Dev)* | Thiết kế **Mock JSON Database** và lập trình các hàm (Tools) như tìm vé, đặt vé, thời tiết, hành lý. Mớm lỗi giả lập vào tool để test. | `src/tools/flight_tools.py`, `src/tools/mock_db.json` | Lấy điểm **Extra Tools** và **Tool Design Evolution**. |
| **Thành viên 3** <br>*(QA & Telemetry)* | Viết `main.py` chạy Chatbot Baseline và Agent trên 5 Test Cases. Thu thập Log JSON, phân tích *Token Efficiency*, *Latency* và *Failures*. | `main.py`, `logs/`, `src/telemetry/` | Lấy điểm **Chatbot Baseline**, **Evaluation & Analysis**, và **Trace Quality**. |
| **Thành viên 4** <br>*(Scrum Master / Analyst)* | Tổng hợp Group Report. Thiết kế sơ đồ kiến trúc (Flowchart). Tối ưu hóa Error Handling (Guardrails). Chuẩn bị Slide/Kịch bản Live Demo. | `report/group_report/`, Markdown files | Lấy điểm **Flowchart & Insight**, **Failure Handling** và **Live System Demo**. |

> **Mẹo Report Cá Nhân**: Thành V iên 1, 2 có thể viết report sâu về "Kỹ thuật Prompt/Xử lý Code", trong khi Thành viên 3, 4 có thể viết mạnh về "Phân tích Dữ liệu / Phân tích Lỗi Hallucination".

---

### Mảng Nguồn Dữ Liệu (Data Sources)

#### [NEW] `src/tools/mock_db.json`
Thay vì hard-code trong hàm, ta sẽ thiết kế một file JSON để giả lập Database. Thiết kế Schema dự kiến:

```json
{
  "flights": [
    {
      "flight_id": "VN213",
      "airline": "Vietnam Airlines",
      "origin": "HAN",
      "destination": "SGN",
      "departure_time": "2026-04-10T08:00:00",
      "price_usd": 120,
      "available_seats": 5
    },
    {
      "flight_id": "VJ122",
      "airline": "Vietjet Air",
      "origin": "HAN",
      "destination": "SGN",
      "departure_time": "2026-04-10T10:30:00",
      "price_usd": 75,
      "available_seats": 0
    }
  ],
  "weather": {
    "SGN": { "condition": "Sunny", "temperature_c": 32 },
    "HAN": { "condition": "Rainy", "temperature_c": 22 }
  },
  "policies": {
    "Vietnam Airlines": "Hành lý xách tay 12kg, ký gửi 23kg.",
    "Vietjet Air": "Hành lý xách tay 7kg, không bao gồm ký gửi."
  },
  "bookings": {}
}
```
*Lưu ý: `bookings` sẽ là object dictionary rỗng để lưu trữ các PNR (Booking Reference) sinh ra khi chạy runtime.*

### Mảng Entrypoint (Kịch bản Test & Trace)

#### [NEW] `main.py`
Tạo file chạy thử nghiệm để chứng minh năng lực của hệ thống (phục vụ việc Demo & Viết Report):
1. Khởi chạy 1 Standard Chatbot với câu hỏi: *"Tìm chuyến bay từ Hà Nội đi Sài Gòn ngày mai và đặt giúp mình"*. Chatbot sẽ fail/hallucinate.
2. Khởi chạy ReAct Agent vào luồng trên. Lấy file log kết quả sinh ra trong mục `logs/` cho nhóm phân tích.

## Tiêu Chí Đánh Giá & So Sánh (Evaluation Plan)

Để so sánh **Baseline Chatbot** bình thường với **ReAct Agent**, chúng ta sẽ dựa vào các số liệu theo chuẩn `EVALUATION.md` sinh ra từ thư mục `logs/`:

| Tiêu Chí Đánh Giá (Metrics) | Baseline Chatbot | ReAct Agent | Mô tả Kì Vọng |
| :--- | :--- | :--- | :--- |
| **Tính chính xác (Accuracy / Capability)** | Dễ bị Hallucinate (bịa ra tên chuyến bay/mã PNR) do không có tools. | Chính xác, gọi `book_flight` và lấy mã PNR thật. | Agent phải vượt trội hoàn toàn về mặt logic giải quyết vấn đề. |
| **Hiệu suất Token (Token Efficiency)** | Dùng ít Token hơn (chỉ 1 vòng lặp). | Dùng nhiều Token hơn (nhiều vòng Thought-Action-Observation) | Đổi token lấy sự chính xác. Cần đo lường ở mức nào là quá tốn kém (chatter). |
| **Độ trễ trung bình (Latency / Duration)** | Nhanh (~1-2s). | Chậm hơn (Mất thời gian xử lý nhiều loop + gọi tool). | Cần phân tích thời gian chạy các tool để tìm nút thắt tốc độ. |
| **Số vòng lặp (Loop Count)** | 0 vòng lặp, trả lời trực tiếp. | > 1 (Ít nhất là tìm chuyến bay -> Quan sát -> Đặt vé -> Quan sát -> Báo cáo). | Agent v2 cần tối ưu prompt để nó đi thẳng vào vấn đề thay vì chạy loop vô ích. |
| **Tỉ lệ lỗi kĩ thuật (Failure Analysis)** | Ít dính lỗi parser. | Dễ dính lỗi định dạng JSON/Regex, Hallucinate tool không tồn tại. | Ghi log vào file để có **Trace Quality** đưa vào báo cáo nhóm chứng minh Error Handling. |

## Open Questions

> [!WARNING]  
> 1. Bạn muốn chạy thử nghiệm trên Model nào là chính? (OpenAI, Gemini hay Phi-3 Local)? Việc biết Model sẽ giúp ích cho việc tinh chỉnh System Prompt sao cho tỷ lệ Parse lỗi thấp nhất.
> 2. Có muốn tôi viết một "Database ảo" dưới dạng file `.json` để lưu thông tin chuyến bay cho nó thực tế một chút không, hay chỉ cần hard-code vài chuyến bay mẫu vào list là được?

## Verification Plan

### Automated Tests
- Chạy hệ thống đo lường được quy định trong `src/telemetry/metrics.py` (nếu có automation tests).

### Manual Verification (5 Test Cases Sinh Log)
Để lấy đủ điểm **Trace Quality** và **Evaluation**, tiến hành chạy `main.py` với 5 câu prompt/kịch bản giả lập sau:

1. **Test Case 1 (Truy vấn cơ bản):** 
   - *Prompt*: "Bạn có tuyến bay nào từ Hà Nội đi Sài Gòn vào ngày 10/04/2026 không?"
   - *Kỳ vọng*: Agent gọi tool `search_flights` và báo cáo chính xác thông tin (hãng, giá tiền, thời gian cất cánh) theo `mock_db.json`.
2. **Test Case 2 (Liên kết đa tool - Multi-step):** 
   - *Prompt*: "Tôi chọn chuyến bay VN213. Bạn hãy đặt vé giúp tôi cho hành khách 'Nguyen Van A' nhé."
   - *Kỳ vọng*: Agent trích xuất mã 'VN213', gọi tool `book_flight` và trả về mã Booking (PNR) cấp phát ngẫu nhiên, lưu vào DB.
3. **Test Case 3 (Failure Handling - Xử lý ngoại lệ hạn chế Hallucinate):** 
   - *Prompt*: "Đặt cho tôi chuyến VJ122."
   - *Kỳ vọng*: Trong DB chuyến bay VJ122 có `available_seats: 0`. Hàm tool báo lỗi "Hết vé". ReAct Agent nhận Observation lỗi và phải thông báo lại cho người dùng "Chuyến bay đã hết chỗ", thay vì bịa ra một mã PNR giả.
4. **Test Case 4 (Hỏi đáp quy định chuyến bay):** 
   - *Prompt*: "Bay của Vietnam Airlines được mang bao nhiêu kg hành lý?"
   - *Kỳ vọng*: Agent gọi `get_baggage_policy` và truyền biến 'Vietnam Airlines' lấy cấu hình từ JSON.
5. **Test Case 5 (Kết hợp ngữ cảnh phụ - Weather Bonus Tool):** 
   - *Prompt*: "Tôi chuẩn bị bay vào Sài Gòn, thời tiết ở đó ra sao?"
   - *Kỳ vọng*: Agent tự gọi `get_weather` với thông số địa điểm SGN/Sài Gòn và chèn vào câu trả lời để tạo thiện cảm.
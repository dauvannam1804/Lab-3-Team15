# Báo Cáo Nhóm: Lab 3 - Hệ Thống Agent Cấp Sản Xuất

- **Tên Nhóm**: Team 15
- **Thành Viên**: Nguyễn Trí Cao, Lê Minh Tuấn, Cao Diệu Ly, Đậu Văn Nam
- **Ngày Triển Khai**: 2026-04-06
- **Mã Nguồn**: https://github.com/dauvannam1804/Lab-3-Team15

---

## 1. Tóm Tắt

Báo cáo này ghi lại quá trình phát triển và đánh giá hệ thống agent cấp sản xuất được thiết kế để hỗ trợ đặt vé máy bay. Agent triển khai kiến trúc vòng lặp ReAct (Reasoning + Acting) với các công cụ chuyên biệt cho tìm kiếm chuyến bay, đặt vé, tra cứu chính sách hành lý và lấy thông tin thởi tiết.

- **Tỷ Lệ Thành Công**: 
  - Baseline (Chatbot): 100% thành công kỹ thuật nhưng 0% đáp ứng hành vi mong đợi (không sử dụng công cụ)
  - Agent v1: 100% (6/6 test case)
  - Agent v2: 83.3% (5/6 test case, 1 lỗi do đạt giới hạn số bước)
- **Kết Quả Chính**: Agent của chúng tôi đã sử dụng thành công các công cụ bên ngoài để xử lý các truy vấn đa bước, tra cứu chính sách và phát hiện câu hỏi ngoài domain, trong khi chatbot baseline không đáp ứng được bất kỳ hành vi mong đợi nào do thiếu tích hợp công cụ.

---

## 2. Kiến Trúc Hệ Thống & Công Cụ

### 2.1 Triển Khai Vòng Lặp ReAct

Agent tuân theo mẫu ReAct (Reasoning + Acting) cổ điển:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Người    │────▶│   Suy Luận  │────▶│    Hành     │────▶│   Quan Sát  │
│    Dùng     │     │   (LLM)     │     │   Động      │     │   (Kết Quả) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                              │
                                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Phản     │◀────│  Câu Trả    │◀────│   Suy Luận  │◀────│   Xử Lý     │
│    Hồi      │     │   Lờii      │     │   (LLM)     │     │   Kết Quả   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Mô Tả Luồng Xử Lý:**
1. **Suy Luận (Thought)**: LLM phân tích truy vấn của ngườii dùng và quyết định hành động tiếp theo
2. **Hành Động (Action)**: Agent gọi công cụ phù hợp với các tham số đã trích xuất
3. **Quan Sát (Observation)**: Công cụ trả về dữ liệu (thông tin chuyến bay, xác nhận đặt vé, chi tiết chính sách, dữ liệu thởi tiết)
4. **Câu Trả Lờii Cuối (Final Answer)**: LLM tổng hợp quan sát thành phản hồi ngôn ngữ tự nhiên

### 2.2 Định Nghĩa Công Cụ (Danh Sách)

| Tên Công Cụ | Định Dạng Đầu Vào | Trường Hợp Sử Dụng |
| :--- | :--- | :--- |
| `search_flights` | `{"origin": string, "destination": string, "date": string}` | Tìm kiếm các chuyến bay khả dụng giữa hai thành phố vào ngày cụ thể. |
| `book_flight` | `{"flight_id": string, "passenger_info": object}` | Đặt vé máy bay cho hành khách và trả về mã xác nhận PNR. |
| `get_baggage_policy` | `{"airline_name": string}` | Truy xuất chính sách hành lý cho một hãng hàng không cụ thể. |
| `get_weather` | `string` (mã thành phố/sân bay) | Lấy thông tin thởi tiết hiện tại cho thành phố đích. |

### 2.3 Nhà Cung Cấp LLM Sử Dụng

- **Chính**: OpenAI GPT-4o-mini
- **Dự Phòng (Backup)**: Không (chỉ sử dụng một nhà cung cấp cho đánh giá này)

---

## 3. Bảng Điều Khiển Hiệu Suất & Telemetry

Phân tích các chỉ số thu thập được trong lần chạy thử cuối cùng (run_id: lab3-8fc08881):

### Thống Kê Tổng Quan

| Chỉ Số | Giá Trị | Cách Tính |
| :--- | :--- | :--- |
| **Tổng Số Request** | 27 | Tổng số lần gọi API LLM: 6 (baseline) + 7 (agent_v1) + 14 (agent_v2) |
| **Độ Trễ Trung Bình (P50)** | 3,676 ms | Tổng độ trễ LLM (99,245 ms) ÷ 27 request |
| **Tổng Prompt Tokens** | 9,948 | Tổng token đầu vào: 168 + 1,762 + 8,018 |
| **Tổng Completion Tokens** | 3,617 | Tổng token đầu ra: 1,464 + 1,231 + 922 |
| **Tổng Tokens** | 13,565 | Prompt (9,948) + Completion (3,617) |
| **Ước Tính Chi Phí** | $0.136 | Tổng tokens × $0.00001/token |

#### Phân Tích Chi Tiết Cách Tính

**1. Tổng Số Request = 27 (Lần Gọi API LLM, KHÔNG Phải Test Case)**

| Runner | Số Test Case | Số Request LLM | Giải Thích |
| :--- | :---: | :---: | :--- |
| Baseline | 6 | 6 | Chat completion đơn giản, 1 request/case |
| Agent v1 | 6 | 7 | Một số case cần nhiều bước suy luận |
| Agent v2 | 6 | 14 | TC5 một mình đã dùng 7 bước trước khi `max_steps_reached` |
| **Tổng** | **18** | **27** | |

**2. Độ Trễ Trung Bình (3,676 ms) = Trên Mỗi Request LLM, KHÔNG Phải Mỗi Test Case**

```
Độ Trễ Trung Bình = Tổng Độ Trễ LLM / Số Request LLM
                  = 99,245 ms / 27
                  = 3,675.74 ms ≈ 3,676 ms
```

> ⚠️ **Quan Trọng**: Đây là trung bình trên mỗi lần gọi API LLM. Độ trễ theo test case khác:
> - Baseline: 5,269 ms | Agent v1: 6,698 ms | Agent v2: 4,579 ms

**3. Tính Toán Tokens**

| Loại Token | Baseline | Agent v1 | Agent v2 | Tổng |
| :--- | :---: | :---: | :---: | :---: |
| Prompt (Đầu Vào) | 168 | 1,762 | 8,018 | **9,948** |
| Completion (Đầu Ra) | 1,464 | 1,231 | 922 | **3,617** |
| **Tổng** | 1,632 | 2,993 | 8,940 | **13,565** |

**4. Ước Tính Chi Phí ($0.136)**

```
Công Thức: Tổng Tokens × $0.00001/token
          = 13,565 × 0.00001
          = $0.13565 ≈ $0.136
```

> ⚠️ **Lưu Ý**: Sử dụng mức giá GIẢ LẬP $10/1M tokens, KHÔNG phải giá thật của GPT-4o-mini!
> Giá thật GPT-4o-mini: Input $0.15/1M, Output $0.60/1M (chi phí thực ~$0.0037)

### So Sánh Theo Runner

| Runner | Số Case | Thành Công | Thất Bại | Độ Trễ TB | Tổng Tokens | Số Request LLM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Baseline | 6 | 6 | 0 | 5,269 ms | 1,632 | 6 |
| Agent v1 | 6 | 6 | 0 | 6,698 ms | 2,993 | 7 |
| Agent v2 | 6 | 5 | 1 | 4,579 ms | 8,940 | 14 |

### Nhận Xét Chính
- Agent v2 có mức tiêu thụ token cao hơn do suy luận đa bước và các vòng lặp thực thi công cụ
- Lỗi ở Agent v2 (TC5) tiêu tốn đáng kể tokens (7 bước trước khi max_steps_reached)
- Độ trễ trung bình cho các lần chạy agent cao hơn do chi phí thực thi công cụ

---

## 4. Phân Tích Nguyên Nhân Gốc Rễ (RCA) - Các Lỗi

### Case Study 1: TC5 - Lỗi Truy Vấn Thởi Tiết (Agent v2)

- **Đầu Vào**: "Tôi chuẩn bị bay vào Sài Gòn, thởi tiết ở đó ra sao?"
- **Hành Vi Mong Đợi**: Sử dụng `get_weather` và chèn thông tin thởi tiết phù hợp ngữ cảnh
- **Hành Vi Thực Tế**: Agent rơi vào vòng lặp vô hạn các lần gọi công cụ sai, cuối cùng đạt `max_steps_reached` (7 bước)
- **Loại Lỗi**: `max_steps_reached`

**Schema Công Cụ (từ mã nguồn):**
```python
{
    "name": "get_weather",
    "description": "Look up destination weather by airport code or city name.",
    "function": get_weather,
    "arg_schema": {
        "location": "str",
        "date": "Optional[YYYY-MM-DD]",
    },
}
```

**Chữ Ký Hàm:**
```python
def get_weather(location: str, date: Optional[str] = None) -> Dict[str, Any]:
```

**Dấu Vết Lỗi (Phân Tích Từng Bước Chi Tiết):**

| Bước | Hành Động Thử | Kết Quả | Phân Tích |
| :--- | :--- | :--- | :--- |
| 0 | `get_weather({"arg1": "SGN"})` | ❌ Lỗi: unexpected keyword argument 'arg1' | Agent tự tạo tên tham số "arg1" thay vì dùng "location" từ schema |
| 1 | `get_weather("Sài Gòn")` | ❌ PARSER_ERROR | Agent thử định dạng string đơn giản, nhưng parser từ chối - framework yêu cầu định dạng JSON |
| 2 | `get_weather({"arg1": "SGN"})` | ❌ Lỗi: unexpected keyword argument 'arg1' | **Agent lặp lại lỗi giống hệt** - không học được từ lỗi trước |
| 3 | `get_weather({"city": "Sài Gòn"})` | ❌ Lỗi: unexpected keyword argument 'city' | Agent đoán "city" - vẫn chưa dùng tên tham số đúng "location" |
| 4 | `get_weather("SGN")` | ❌ PARSER_ERROR | Thử string đơn giản lại - parser vẫn từ chối định dạng non-JSON |
| 5 | `get_weather({"airport": "SGN"})` | ❌ Lỗi: unexpected keyword argument 'airport' | Agent đoán "airport" - vẫn sai |
| 6 | `get_weather({"arg1": "Sài Gòn"})` | ❌ Lỗi: unexpected keyword argument 'arg1' | **Agent quay lại "arg1"** - kẹt trong vòng lặp mà không bao giờ thử "location" |

**Quan Sát Quan Trọng:**
1. **Không bao giờ thử tham số đúng**: Agent thử `arg1`, `city`, `airport` nhưng **KHÔNG BAO GIỜ thử `location`** - tên tham số thực tế từ schema
2. **Ràng buộc parser**: Parser của framework BẮT BUỘC định dạng JSON (`{"key": "value"}`) - các đối số string đơn giản như `get_weather("SGN")` bị từ chối với PARSER_ERROR
3. **Không học từ lỗi**: Mặc dù nhận được thông báo lỗi rõ ràng (`unexpected keyword argument 'xxx'`), agent không suy luận được rằng nên dùng tên tham số từ schema (`location`)
4. **Hành vi lặp lại**: Agent lặp lại giữa các tên tham số sai mà không khám phá có hệ thống tùy chọn đúng

**Phân Tích Nguyên Nhân Gốc Rễ (5 Whys):**

1. **Tại sao agent thất bại?** → Không thể gọi thành công công cụ `get_weather`
2. **Tại sao không gọi được công cụ?** → Sử dụng tên tham số sai trong đối số JSON
3. **Tại sao dùng tên tham số sai?** → Schema `"location": "str"` không đủ rõ ràng để LLM hiểu đây là tên tham số BẮT BUỘC
4. **Tại sao schema không rõ ràng?** → Mô tả "Look up destination weather by airport code or city name" không nói rõ tham số PHẢI tên là "location"
5. **Tại sao agent không học từ lỗi?** → Thông báo lỗi chỉ hiển thị tên tham số sai nhưng không hướng dẫn agent đến tên đúng; không có ví dụ few-shot

**Các Yếu Tố Đóng Góp:**

| Yếu Tố | Mức Độ Ảnh Hưởng | Bằng Chứng |
| :--- | :--- | :--- |
| Schema mơ hồ | Cao | Agent không bao giờ xác định "location" là key đúng dù nó có trong schema |
| Parser quá nghiêm ngặt | Trung bình | Định dạng string đơn giản bị từ chối, buộc phải dùng JSON mà agent gặp khó khăn |
| Thiếu ví dụ few-shot | Cao | Agent v1 thành công có lẽ vì có ví dụ; Agent v2 thiếu |
| Vòng lặp phản hồi lỗi kém | Trung bình | Thông báo lỗi không giúp agent hội tụ về tên tham số đúng |

**So Sánh Với Các Lần Gọi Công Cụ Thành Công:**

Các công cụ khác hoạt động vì schema của chúng dễ hiểu hơn:
- `search_flights({"origin": "Hà Nội", "destination": "Sài Gòn", "date": "2026-04-10"})` - tên tham số rõ ràng khớp ngôn ngữ tự nhiên
- `get_baggage_policy({"airline_name": "Vietnam Airlines"})` - "airline_name" trực quan
- `get_weather` - "location" kém rõ ràng hơn; agent có thể mong đợi "city" hoặc "airport" dựa trên mô tả

**Các Khuyến Nghị Sửa Lỗi (theo thứ tự ưu tiên):**

1. **Thêm mô tả tham số rõ ràng trong schema:**
   ```python
   "arg_schema": {
       "location": "str (BẮT BUỘC) - Mã sân bay (vd: 'SGN') hoặc tên thành phố (vd: 'Sài Gòn')",
       "date": "Optional[YYYY-MM-DD]",
   }
   ```

2. **Thêm ví dụ few-shot trong system prompt:**
   ```
   Ví dụ: Với truy vấn thởi tiết "Thởi tiết Sài Gòn thế nào?"
   Thought: Tôi cần tra cứu thởi tiết Sài Gòn dùng tham số location.
   Action: get_weather({"location": "SGN"})
   ```

3. **Cải thiện parser để chấp nhận đối số string đơn giản** khi hàm có một tham số bắt buộc duy nhất:
   Cho phép `get_weather("SGN")` được hiểu là `get_weather({"location": "SGN"})`

4. **Thêm xác thực tham số với thông báo lỗi hữu ích:**
   Thay vì `unexpected keyword argument 'arg1'`, trả về: `Tham số không hợp lệ 'arg1'. Cần 'location'. Ví dụ: {"location": "SGN"}`

### Case Study 2: TC6 - Phát Hiện Câu Hỏi Ngoài Domain (Agent v1)

- **Đầu Vào**: "So sánh giúp tôi triết lý của chủ nghĩa khắc kỷ với Phật giáo..."
- **Hành Vi Mong Đợi**: Nhận diện câu hỏi ngoài domain (không liên quan đến flight/booking/weather/baggage)
- **Hành Vi Thực Tế (Agent v1)**: Agent cung cấp bài so sánh triết học chi tiết
- **Hành Vi Thực Tế (Agent v2)**: Từ chối đúng cách với thông báo giới hạn domain

**Nguyên Nhân Gốc Rễ:**
- Agent v1 thiếu các rào chắn domain rõ ràng trong system prompt
- Agent không được hướng dẫn để từ chối các truy vấn ngoài domain
- Agent v2 đã thêm hướng dẫn rõ ràng: "The user is asking an out-of-scope question. I must refuse to save tokens."

**Khuyến Nghị Sửa Lỗi:**
- Bao gồm các hướng dẫn giới hạn domain rõ ràng trong system prompt
- Thêm các ví dụ về truy vấn ngoài domain và phản hồi từ chối phù hợp

---

## 5. Các Thử Nghiệm & Nghiên Cứu Ablation

### Thử Nghiệm 1: So Sánh Baseline Chatbot vs Agent (v1 & v2)

| Test Case | Hành Vi Mong Đợi | Baseline | Agent v1 | Agent v2 |
| :--- | :--- | :--- | :--- | :--- |
| TC1: Tìm chuyến bay | Trả về các chuyến bay khả dụng từ mock_db.json | ❌ Từ chối (không có công cụ) | ✅ Dùng search_flights | ✅ Dùng search_flights |
| TC2: Đặt vé đa bước | Trích xuất mã chuyến bay, gọi book_flight, trả về PNR | ❌ Từ chối (không có công cụ) | ✅ Đặt thành công | ⚠️ Hỏi thêm thông tin |
| TC3: Xử lý hết chỗ | Phát hiện hết chỗ, báo lại (không tạo PNR giả) | ❌ Từ chối (không có công cụ) | ✅ Báo không tìm thấy | ⚠️ Hỏi thông tin hành khách |
| TC4: Tra cứu chính sách hành lý | Dùng get_baggage_policy theo JSON policy | ❌ Kiến thức chung | ✅ Dùng get_baggage_policy | ✅ Dùng get_baggage_policy |
| TC5: Ngữ cảnh thởi tiết | Dùng get_weather với phản hồi phù hợp ngữ cảnh | ❌ Kiến thức chung | ✅ Dùng get_weather | ❌ Max steps reached |
| TC6: Ngoài domain | Từ chối truy vấn không thuộc domain | ❌ Vẫn trả lờii | ❌ Vẫn trả lờii | ✅ Từ chối đúng |

**Phân Tích:**
- **Baseline**: Thất bại tất cả các yêu cầu chức năng do thiếu truy cập công cụ. Các phản hồi là từ chối chung chung hoặc kiến thức chung ảo giác.
- **Agent v1**: Sử dụng thành công công cụ cho TC1-TC5 nhưng thất bại phát hiện domain cho TC6.
- **Agent v2**: Cải thiện phát hiện domain (TC6) nhưng gây regression trong việc sử dụng công cụ thởi tiết (TC5).

### Thử Nghiệm 2: Hiệu Quả Sử Dụng Công Cụ

| Công Cụ | Số Lần Gọi Thành Công | Số Lần Gọi Thất Bại | Tỷ Lệ Thành Công |
| :--- | :---: | :---: | :---: |
| search_flights | 3 | 0 | 100% |
| book_flight | 1 | 0 | 100% |
| get_baggage_policy | 2 | 0 | 100% |
| get_weather | 1 | 6 | 14.3% |

**Phát Hiện Chính**: Công cụ `get_weather` có tỷ lệ thành công thấp nhất do nhầm lẫn định dạng tham số. Tất cả các công cụ khác được sử dụng đúng khi được gọi.

---

## 6. Đánh Giá Sẵn Sàng Sản Xuất

### 6.1 Các Vấn Đề Bảo Mật
- **Làm Sạch Đầu Vào**: Các đối số công cụ nên được xác thực trước khi thực thi để ngăn chặn tấn công injection
- **Giới Hạn Tốc Độ**: Triển khai giới hạn tốc độ cho mỗi ngườii dùng để ngăn chặn lạm dụng API
- **Xử Lý PII**: Thông tin hành khách trong yêu cầu đặt vé nên được mã hóa và ghi log an toàn

### 6.2 Các Rào Chắn (Guardrails)
- **Giới Hạn Số Bước**: Hiện đặt là 7 bước - phù hợp để ngăn chặn vòng lặp vô hạn
- **Giới Hạn Domain**: Agent v2 triển khai thành công từ chối domain, tiết kiệm tokens cho truy vấn ngoài phạm vi
- **Xử Lý Lỗi**: Các lỗi thực thi công cụ nên được xử lý gracefully với thông báo thân thiện với ngườii dùng

### 6.3 Khuyến Nghị Mở Rộng
- **Caching**: Triển khai caching phản hồi cho dữ liệu được truy cập thường xuyên (chính sách hành lý, thởi tiết)
- **Xử Lý Bất Đồng Bộ**: Cho các thao tác đặt vé, xem xét xử lý bất đồng bộ với webhook callbacks
- **Giám Sát**: Thêm ghi log có cấu trúc và thu thập metrics cho khả năng quan sát sản xuất
- **Dự Phòng LLM**: Triển khai dự phòng nhà cung cấp (vd: Gemini, Claude) cho tính sẵn sàng cao

### 6.4 Các Hạn Chế Đã Biết
1. **Khám Phá Tham Số Công Cụ**: Agent gặp khó khăn trong việc xác định định dạng tham số đúng nếu không có ví dụ rõ ràng
2. **Giữ Ngữ Cảnh**: Các cuộc hội thoại đa lượt có thể mất ngữ cảnh giữa các lần gọi agent riêng biệt
3. **Phục Hồi Lỗi**: Khả năng phục hồi hạn chế từ các lần gọi công cụ thất bại lặp lại

---

## Phụ Lục: Định Nghĩa Các Test Case

```python
TEST_CASES = [
    TestCase(
        case_id="TC1",
        name="Tìm kiếm chuyến bay",
        prompt="Bạn có tuyến bay nào từ Hà Nội đi Sài Gòn vào ngày 10/04/2026 không?",
        expected_behavior="Trả đúng các chuyến bay khả dụng theo mock_db.json.",
    ),
    TestCase(
        case_id="TC2",
        name="Đặt vé đa bước",
        prompt="Tôi chọn chuyến bay VN213. Bạn hãy đặt vé giúp tôi cho hành khách 'Nguyen Van A' nhé.",
        expected_behavior="Trích xuất mã chuyến bay, gọi book_flight và trả về PNR.",
    ),
    TestCase(
        case_id="TC3",
        name="Xử lý lỗi hết chỗ",
        prompt="Đặt cho tôi chuyến VJ122.",
        expected_behavior="Phát hiện hết chỗ và báo lại thay vì bịa PNR.",
    ),
    TestCase(
        case_id="TC4",
        name="Tra cứu chính sách hành lý",
        prompt="Bay của Vietnam Airlines được mang bao nhiêu kg hành lý?",
        expected_behavior="Dùng get_baggage_policy để trả lờii đúng theo JSON policy.",
    ),
    TestCase(
        case_id="TC5",
        name="Ngữ cảnh thởi tiết",
        prompt="Tôi chuẩn bị bay vào Sài Gòn, thởi tiết ở đó ra sao?",
        expected_behavior="Dùng get_weather và chèn thông tin thởi tiết hợp ngữ cảnh.",
    ),
    TestCase(
        case_id="TC6",
        name="Truy vấn ngoài domain",
        prompt="So sánh giúp tôi triết lý của chủ nghĩa khắc kỷ với Phật giáo...",
        expected_behavior="Nhận diện đây là câu hỏi ngoài domain (không liên quan đến flight/booking/weather/baggage).",
    ),
]
```

---

> [!NOTE]
> Báo cáo này được tạo dựa trên lần chạy thử `lab3-8fc08881` thực hiện ngày 2026-04-06.
> Log đầy đủ có tại: `logs/2026-04-06.log`

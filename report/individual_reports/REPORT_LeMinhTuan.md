# Báo Cáo Cá Nhân: Lab 3 - Chatbot vs ReAct Agent

- **Họ tên**: Lê Minh Tuấn
- **MSSV**: 2AS202600379
- **Ngày**: 06-04-2026

---

## I. Đóng Góp Kỹ Thuật (15 Điểm)

### Modules đã triển khai

Vai trò: **Tools & Backend Dev** — Thiết kế Mock Database và lập trình toàn bộ các hàm công cụ (Tools) cho ReAct Agent.

| File | Mô tả |
|------|--------|
| `src/tools/flight_tools.py` | Toàn bộ 4 tools + helper functions |
| `src/tools/mock_db.json` | Mock JSON database cho chuyến bay, thời tiết, chính sách hành lý |

### Code Highlights

#### 1. Normalize Location — Xử lý đa dạng đầu vào tiếng Việt

LLM thường trả về tên địa điểm dưới nhiều dạng khác nhau ("Hà Nội", "HAN", "ha noi", "hn"...). Hàm `_normalize_location()` chuyển tất cả về mã sân bay chuẩn IATA:

```python
def _normalize_location(value: str) -> str:
    text = value.strip()
    aliases = {
        "ha noi": "HAN", "hanoi": "HAN", "hn": "HAN", "han": "HAN",
        "sai gon": "SGN", "saigon": "SGN", "sg": "SGN",
        "ho chi minh": "SGN", "ho chi minh city": "SGN",
        "hcm": "SGN", "tphcm": "SGN", "tp hcm": "SGN", "sgn": "SGN",
        "da nang": "DAD", "danang": "DAD", "dad": "DAD",
    }
    return aliases.get(text.lower(), text.upper())
```

#### 2. Book Flight — Xử lý lỗi giả lập (Failure Handling)

Tool `book_flight` có cơ chế kiểm tra ghế trống trước khi đặt vé, giúp Agent phải xử lý ngoại lệ thay vì bịa PNR:

```python
def book_flight(flight_id, passenger_name, contact_info=None):
    # ...
    if flight["available_seats"] <= 0:
        raise ValueError(f"Flight '{flight['flight_id']}' is sold out.")
    # Trừ ghế, sinh PNR, lưu vào state
    flight["available_seats"] -= 1
    pnr = _generate_pnr()
    booking = {"pnr": pnr, "flight_id": ..., "status": "confirmed"}
    state["bookings"][pnr] = booking
    return copy.deepcopy(booking)
```

#### 3. Tool Registry — Metadata chuẩn cho Agent

Hàm `get_tools()` cung cấp danh sách tools kèm metadata (name, description, arg_schema, function reference) để Agent tự động biết cách gọi:

```python
def get_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "search_flights",
            "description": "Search available flights by origin, destination, and travel date.",
            "function": search_flights,
            "arg_schema": {"origin": "str", "destination": "str", "date": "YYYY-MM-DD"},
        },
        # ... book_flight, get_weather, get_baggage_policy
    ]
```

### Tương tác với ReAct Loop

Các tools được đăng ký vào Agent thông qua `get_tools()`. Khi `agent.py` parse được chuỗi `Action: tool_name({"arg": "value"})`, nó gọi `_execute_tool()` để tìm tool theo tên, parse JSON arguments, và gọi hàm Python tương ứng. Kết quả trả về (hoặc thông báo lỗi) được nối vào transcript dưới dạng `Observation:` cho LLM xử lý ở vòng lặp tiếp theo.

---

## II. Debugging Case Study (10 Điểm)

### Vấn đề: Agent không tìm được đúng tên argument cho `get_baggage_policy`

**Mô tả vấn đề:**
Khi người dùng hỏi "Bay Vietnam Airlines thì được mang bao nhiêu kg hành lý ký gửi?", Agent liên tục gọi `get_baggage_policy` với sai tên argument (thử `airline_name` → `airline` → `name`) và cuối cùng **từ chối trả lời**, nói rằng không có công cụ phù hợp.

**Nguồn Log:** `logs/2026-04-06.log`, dòng 27–32 và 50–56

```json
// Step 0: LLM thử airline_name
{"event": "TOOL_EXECUTED", "data": {
  "tool": "get_baggage_policy",
  "args": "{\"airline_name\": \"Vietnam Airlines\"}",
  "observation": "[Error] Wrong arguments for 'get_baggage_policy': get_baggage_policy() got an unexpected keyword argument 'airline_name'"
}}

// Step 1: LLM đoán thử "airline"
{"event": "TOOL_EXECUTED", "data": {
  "tool": "get_baggage_policy",
  "args": "{\"airline\": \"Vietnam Airlines\"}",
  "observation": "[Error] Wrong arguments for 'get_baggage_policy': get_baggage_policy() got an unexpected keyword argument 'airline'"
}}

// Step 2: LLM đoán thử "name" → vẫn sai
// Cuối cùng Agent bỏ cuộc sau 3 lần thử
```

**Chẩn đoán:**
Nguyên nhân gốc rễ là **sự bất đồng bộ giữa tool spec (arg_schema) và implementation thực tế**:
- Trong `arg_schema` khi đăng ký tool, tôi ghi `"airline_name": "str"`
- Nhưng hàm Python thực tế ban đầu lại dùng parameter tên `airline_code`
- LLM đọc description "by airline name" → đoán `airline_name` → sai
- LLM tự sửa thử `airline` → vẫn sai → `name` → vẫn sai

Đây là lỗi **hallucination do tool spec không khớp code**, không phải lỗi của model. Model đã cố gắng tự sửa (self-correct) rất logic, nhưng không thể đoán đúng khi tên parameter thật sự lại là `airline_code`.

**Giải pháp:**
1. **Sửa tên parameter** trong hàm Python từ `airline_code` thành `airline_name` cho khớp với mô tả ngữ nghĩa
2. **Cập nhật `arg_schema`** cho khớp 1:1 với tên parameter thực tế trong function signature
3. **Thêm tên argument vào tool description** để LLM không phải đoán:
   ```python
   "description": "Retrieve baggage allowance policy. Args: airline_name (str)",
   ```
4. Tương tự, bug với `get_weather` cũng xảy ra (LLM thử `airport_code`, `code`, `airport` — đều sai vì tên thật là `location`). Đã sửa bằng cách thống nhất arg_schema.

---

## III. Nhận Xét Cá Nhân: Chatbot vs ReAct (10 Điểm)

### 1. Suy luận (Reasoning)

Khối `Thought` trong ReAct Agent mang lại lợi ích rất rõ ràng so với Chatbot thông thường. Khi đối mặt với yêu cầu multi-step như "Tìm chuyến bay rẻ nhất còn chỗ rồi đặt vé", Chatbot baseline chỉ có thể **bịa ra một câu trả lời** dựa trên kiến thức đã huấn luyện (hallucinate mã PNR giả). Trong khi đó, Agent sử dụng Thought để phân tích: "Cần search trước → lọc chuyến có chỗ → chọn rẻ nhất → book" — mỗi bước đều được kiểm chứng bằng Observation thực tế.

Ví dụ từ log (TC3), Agent suy luận:
> *"Chuyến VJ122 giá 75 USD nhưng hết chỗ (available_seats: 0). Chuyến QH501 giá 95 USD còn 8 chỗ → đây là chuyến rẻ nhất CÒN CHỖ."*

Đây là chuỗi suy luận logic mà baseline chatbot không thể thực hiện được.

### 2. Độ tin cậy (Reliability)

Agent thực sự hoạt động **kém hơn** Chatbot ở hai trường hợp:
- **Câu hỏi đơn giản, chỉ cần kiến thức chung**: Ví dụ hỏi thời tiết mà tool spec bị sai → Agent thử 3 lần rồi bỏ cuộc, trong khi Chatbot có thể trả lời ngay (dù dựa trên kiến thức cũ).
- **Tool spec bị lỗi/không khớp**: Khi argument name không đúng, Agent rơi vào vòng lặp thử-sai tốn nhiều token, cuối cùng vẫn thất bại. Baseline chatbot ít nhất vẫn đưa ra câu trả lời (dù có thể không chính xác).

→ **Bài học**: Chất lượng của Agent phụ thuộc hoàn toàn vào chất lượng tool definitions. Tool spec sai = Agent tệ hơn Chatbot.

### 3. Quan sát (Observation)

Feedback từ môi trường (Observation) đóng vai trò then chốt trong việc tự điều chỉnh hành vi của Agent:
- Khi `search_flights` trả về danh sách chuyến bay với `available_seats: 0`, Agent biết bỏ qua chuyến đó thay vì đặt vé.
- Khi `book_flight` trả về lỗi "sold out", Agent dừng lại và thông báo cho người dùng thay vì bịa PNR.
- Khi tool trả về `[Error] Wrong arguments`, Agent cố gắng tự sửa argument name ở bước tiếp theo.

Tuy nhiên, Observation cũng có mặt trái: nếu lỗi message không đủ thông tin (ví dụ không gợi ý tên argument đúng), Agent sẽ đoán mù và tốn thêm nhiều vòng lặp + token.

---

## IV. Cải Tiến Trong Tương Lai (5 Điểm)

### Scalability
- **Asynchronous tool execution**: Khi có nhiều tools, sử dụng `asyncio` hoặc message queue (RabbitMQ/Celery) để gọi tools song song thay vì tuần tự. Ví dụ: gọi đồng thời `search_flights` + `get_weather` khi user cần cả hai.
- **Tool registry API**: Thay vì hard-code danh sách tools, xây dựng một REST API hoặc module dynamic import để đăng ký/gỡ tools khi runtime, phục vụ hệ thống multi-agent.

### Safety
- **Supervisor LLM**: Triển khai một LLM "giám sát" (ví dụ model nhỏ, rẻ) để audit Action trước khi thực thi — đặc biệt với các tool có side-effect như `book_flight` (mất tiền thật trong production).
- **Rate limiting per user**: Giới hạn số lần gọi tool/phút cho mỗi user để tránh lạm dụng hoặc vòng lặp vô hạn do hallucination.
- **Input sanitization**: Validate arguments trước khi gọi tool → trả lỗi rõ ràng sớm hơn, thay vì để exception tự phát.

### Performance
- **Vector DB cho Tool Retrieval**: Khi hệ thống có 50+ tools, không nên đưa toàn bộ tool descriptions vào system prompt (tốn token). Thay vào đó, dùng Embedding + Vector DB (FAISS/Qdrant) để retrieve chỉ 3–5 tools liên quan dựa trên câu hỏi user.
- **Caching**: Cache kết quả `search_flights` trong 5 phút (TTL) để giảm latency khi user hỏi lại cùng tuyến bay.
- **Prompt compression**: Sau 3+ vòng lặp, tóm tắt các Observation cũ thay vì giữ nguyên toàn bộ transcript → giảm prompt tokens đáng kể.

---

> [!NOTE]
> File này đã được đặt tên theo quy định và đặt trong thư mục `report/individual_reports/`.

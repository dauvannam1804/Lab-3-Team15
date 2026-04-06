# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đậu Văn Nam
- **Student ID**: [Student ID]
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

Trong dự án Lab 3, tôi đảm nhiệm vai trò **Member 2 (Tools & Backend Dev)** theo kế hoạch tại `plan.md`. Tôi chịu trách nhiệm xây dựng nền tảng dữ liệu và các công cụ bổ trợ cho Agent. Bên cạnh đó, tôi cũng thực hiện các nhiệm vụ quản lý dự án (Scrum Master phụ trợ).

- **Modules Implementated**: 
    - `src/tools/flight_tools.py`: Triển khai các hàm tìm kiếm, đặt vé, thời tiết và hành lý.
    - `src/tools/mock_db.json`: Thiết kế cấu trúc cơ sở dữ liệu giả lập để Agent truy vấn.
- **Code Highlights**:
    ```python
    def search_flights(origin: str, destination: str, date: str) -> List[Dict[str, Any]]:
        # Trích xuất dữ liệu từ mock_db.json và lọc theo tiêu chí
        with open("src/tools/mock_db.json", "r") as f:
            db = json.load(f)
        return [f for f in db["flights"] if f["origin"] == origin ...]
    ```
- **Documentation**: 
    Tôi đã sử dụng **Antigravity** để lên kế hoạch chi tiết (`plan.md`) và phân chia công việc cho các thành viên. Tôi cũng khởi tạo Repository, quản lý các lượt Commit và dùng Antigravity hỗ trợ **Merge Conflict** khi kết hợp code của các thành viên trước khi đẩy lên nhánh `main`. Điều này giúp hệ thống hoạt động thống nhất và tránh bị lỗi do xung đột code.

---

## II. Debugging Case Study (10 Points)

Trong quá trình chạy thực tế với Agent v2 (Run ID: lab3-8fc08881), tôi đã gặp một lỗi nghiêm trọng ở Test Case 5.

- **Problem Description**: Agent rơi vào vòng lặp vô tận (Infinite Loop) và đạt ngưỡng `max_steps_reached` khi hỏi về thời tiết Sài Gòn.
- **Log Source**: `logs/2026-04-06.log`
    ```json
    {"step": 0, "tool": "get_weather", "args": "{\"arg1\": \"SGN\"}", "observation": "[Error] unexpected keyword argument 'arg1'"}
    {"step": 3, "tool": "get_weather", "args": "{\"city\": \"Sài Gòn\"}", "observation": "[Error] ..."}
    ```
- **Diagnosis**: Agent v2 đã thực hiện **Argument Hallucination**. Thay vì sử dụng đúng tên tham số `location`, nó tự bịa ra các key như `arg1` hoặc `city`. Lỗi này không phải do code của Tool mà là do Prompt chưa cung cấp đủ ví dụ định dạng tham số chính xác.
- **Solution**: Tôi đã cập nhật Docstring của hàm `get_weather` để rõ ràng hơn và gợi ý cho Thành viên 1 bổ sung `Few-shot Examples` vào System Prompt để Agent biết cách gọi đúng tham số `location`.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

Dựa trên dữ liệu log thực tế:

1.  **Reasoning**: Khối `Thought` giúp Agent v2 biết "dừng lại" để gọi tool `get_baggage_policy` (TC4) lấy dữ liệu thực từ JSON, thay vì trả lời theo cảm tính như Baseline. Baseline chỉ đưa ra quy định chung chung của VNA, không chính xác theo chính sách cụ thể mà nhóm đã thiết lập.
2.  **Reliability**: Agent v2 đôi khi kém ổn định hơn Chatbot khi gặp lỗi tham số (TC5). Chatbot trả lời rất nhanh và không bao giờ bị "treo", trong khi Agent khi không hiểu Tool sẽ bị "loạn" và tiêu tốn rất nhiều token. (Ví dụ Agent v2 dùng ~1490 tokens vs 158 tokens của Baseline).
3.  **Observation**: Kết quả trả về từ môi trường (`Observation`) đóng vai trò là "mỏ neo" sự thật. Khi Tool trả về lỗi `unexpected keyword argument`, Agent đã cố gắng tự sửa (Self-Correct) bằng cách đổi key khác. Dù chưa thành công ở TC5 nhưng nó cho thấy tiềm năng tự xử lý lỗi của ReAct.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Thay thế `mock_db.json` bằng một Vector Database (như ChromaDB) để Agent có thể tra cứu hàng ngàn chính sách hành lý khác nhau mà không làm quá tải Context window.
- **Safety**: Xây dựng một lớp **Schema Validator** (sử dụng Pydantic) nằm giữa Agent và Tool. Nếu Agent gọi sai tham số, validator sẽ trả về một gợi ý sửa lỗi cực kỳ chi tiết cho Agent thay vì chỉ trả về Python traceback.
- **Performance**: Chuyển các lượt gọi LLM bên trong ReAct loop sang chế độ **Streaming** để người dùng có thể thấy "luồng suy nghĩ" (Thoughts) ngay lập tức, giảm cảm giác chờ đợi do Latency (hiện tại trung bình là ~4.5s).

---

> [!NOTE]
> Báo cáo hoàn thiện bởi Đậu Văn Nam với sự hỗ trợ của Antigravity Agent.

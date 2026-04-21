# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Cao Diệu Ly
- **Student ID**: 2A202600356
- **Date**: 6/4/2026

---

## I. Technical Contribution (15 Points)

Trong tiến trình xây dựng hệ thống ReAct Agent, trách nhiệm chính của tôi tập trung vào việc kiến trúc luồng, theo dõi chất lượng, và chốt chặn an toàn (Guardrails) cho hệ thống:

- **Modules Phụ Trách**: `report/group_report`, Markdown files, thiết lập cấu trúc Diagram.
- **Tổng hợp & Báo cáo**: Chịu trách nhiệm phân tích Log thu thập từ đợt chạy Automation Test, tổng hợp metric (P50 Latency, Tokens dùng, Success Rate) và đúc kết thành **Group Report**.
- **Thiết kế sơ đồ kiến trúc (Flowchart)**: Sơ đồ hóa luồng hoạt động Thought-Action-Observation của hệ thống (`API_Payment_Loop_Workflow`), giúp nhóm phát triển (Dev) dễ dàng bám sát quy trình gọi Tool và xử lý Observation.
- **Tối ưu hóa Error Handling (Guardrails)**: Lập tài liệu hóa quá trình bắt lỗi. Đóng góp trực tiếp vào thiết kế **System Prompt Constraints** nhằm rào chặt "scope bleeding" (hiện tượng LLM bị thoát khỏi miền dữ liệu khi gặp keyword nhiễu).
- **Chuẩn bị Kịch bản Live Demo**: Soạn thảo trước danh sách kịch bản test mang tính đối nghịch nhằm chứng minh sức mạnh của Agent so với Baseline Chatbot.

---

## II. Debugging Case Study (10 Points)

Để bảo vệ ngân sách Token và tăng UX, tôi đã phân tích sự cố rò rỉ ngữ cảnh (Bleeding Intent) trong kiểm thử nội bộ:

- **Problem Description**: Khi người dùng nhập "Có chuyến bay nào bị ảnh hưởng bởi chiến tranh Iran không?", Agent thay vì từ chối các câu hỏi về chính trị/sự kiện ngoài lề, lại sinh ra `Thought` liên quan đến nghiệp vụ tìm kiếm vé do bị kích hoạt (trigger) bởi cụm từ "chuyến bay". Mặc dù không có hệ quả nghiêm trọng, nhưng vòng lặp tốn kém token và phản hồi sai mục đích.
- **Log Source**: `logs/summary-lab3-da562271.json` kết hợp quá trình chạy debug tay. Trạng thái hiển thị Agent bị kẹt ở "blocked" hoặc mất nhiều bước để nhận ra không có tool phù hợp.
- **Diagnosis**: Do LLM mang trọng số thiên vị hữu ích (helpfulness bias). Khi gặp keyword nghiệp vụ, nó bỏ qua chỉ thị chung chung là "chỉ trả lời đặt vé máy bay". Phễu sàng lọc (Guardrail) bằng văn bản lỏng lẻo không hoạt động.
- **Solution**: Đã khắc phục ở cấp độ quản trị rủi ro bằng cách đưa bộ quy tắc **STRICT SCOPE LIMITATION** (Luật tuyệt đối) vào thẳng System Prompt. Ép buộc tác tử (Agent) trong vòng `Thought` khởi tạo phải quét ngữ nghĩa thực sự, nếu vi phạm, trả ngay format cứng `Final Answer: Xin lỗi, tôi chỉ là trợ lý ảo hỗ trợ đặt vé...`. Kết quả: Agent ngắt luồng ngay bước đầu, không chạy Action calls.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

Từ góc nhìn của một Analyst và Scrum Master, kiến trúc ReAct đem đến sự khác biệt cốt lõi:

1. **Reasoning (Lập luận)**: Khối `Thought` hoạt động như một "biên bản nháp", giúp kiểm soát khả năng ảo giác (Hallucination) triệt để. Tuy nhiên, nó yêu cầu thiết kế System Prompt chặt chẽ, nếu không mô hình sẽ sa đà vòng vo.
2. **Reliability (Độ tin cậy) - Nơi Agent thua Chatbot**: Trong các truy vấn quá căn bản (Ví dụ: "Xin chào", "Cảm ơn"), Agent tốn nhiều độ trễ hơn (latency cao) và Token lãng phí hơn Baseline Chatbot vì nó vẫn cố thiết lập khung `Thought` và tìm Tool.
3. **Observation (Giám sát Môi trường)**: Tính linh hoạt tuyệt vời nhất. Khi kết quả DB trả về rỗng (Hết vé VJ122), Observation phản ánh trực tiếp sự thật, buộc LLM phải diễn đạt lại sự kiện đó cho user, thay vì như Chatbot - sẽ nỗ lực sinh ra data ảo (Mã PNR giả mạo) để chiều lòng user.

---

## IV. Future Improvements (5 Points)

Để mở rộng hệ thống này lên chuẩn Production (chịu tải thực tế), tôi đề xuất:

- **Scalability (Cấu trúc Semantic Router)**: Không nhồi quá nhiều Tool vào System Prompt của Agent làm phình Token. Cần chia tầng bằng **Supervisor Agent** (Semantic Routing). Nếu hỏi thời tiết -> Push cho Agent Thời Tiết. Hỏi Đặt Vé -> Push cho Booking Agent.
- **Safety (Kiểm toán - Audit Logging)**: Lưu log PNR booking kèm `Trace_ID` để mapping mọi `Tool_call` với Session của User, đề phòng các giao dịch sai lệch trên DB cần rollback.
- **Performance**: Nhanh chóng loại bỏ manual Regex/JSON parsing hiện tại và chuyển dứt điểm sang sử dụng **Native Function Calling** API (Ví dụ: OpenAI Structured Outputs) để loại trừ 100% rủi ro vòng lặp do lỗi cú pháp Parser.

# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyen Tri Cao
- **Student ID**: 2A202600223
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

Trong bài lab này, phần việc tôi làm nghiêng nhiều về hướng QA và telemetry hơn là phát triển lõi ReAct loop. Mục tiêu của tôi là biến quá trình chạy thử từ chỗ làm thủ công thành một quy trình có thể lặp lại, có log, có summary và đủ rõ để dùng trực tiếp cho phần phân tích trong báo cáo nhóm.

Việc đầu tiên tôi xây là [main.py](c:/Users/ASUS/Lab-3-Team15/main.py), đóng vai trò như một runner chung cho cả baseline chatbot lẫn ReAct agent. File này chứa sẵn 5 test case theo đúng hướng đã đề ra trong plan, cho phép chạy từng mode riêng hoặc chạy cả hai để đối chiếu. Tôi không muốn mỗi lần demo lại phải nhập tay từng prompt và tự nhìn log bằng mắt, nên runner được thiết kế để tự ghi `run_id`, tự log `CASE_START`, `CASE_RESULT`, `RUN_START`, `RUN_END`, và cuối cùng sinh ra một file summary trong thư mục `logs/`. Cách làm này giúp việc so sánh giữa hai hệ thống nhất quán hơn, đặc biệt khi cần quay lại xem một lần chạy cũ.

Song song với runner, tôi chỉnh lại phần telemetry ở [src/telemetry/logger.py](c:/Users/ASUS/Lab-3-Team15/src/telemetry/logger.py) và [src/telemetry/metrics.py](c:/Users/ASUS/Lab-3-Team15/src/telemetry/metrics.py). Logger được sửa để ghi UTF-8 cho ổn định, tránh việc thêm handler lặp khi import nhiều lần, và cung cấp sẵn đường dẫn log hiện tại để runner có thể đọc lại sau khi chạy. Với `PerformanceTracker`, tôi bổ sung phần `context` cho từng metric, ví dụ như `run_id`, `runner`, `test_case_id`. Điều này nghe có vẻ nhỏ, nhưng thực tế rất quan trọng: nếu không có context thì log metric chỉ là một loạt con số rời rạc, rất khó biết metric nào thuộc baseline, metric nào thuộc agent, và thuộc test case nào.

Từ đó, tôi thêm [src/telemetry/log_analysis.py](c:/Users/ASUS/Lab-3-Team15/src/telemetry/log_analysis.py) để đọc log JSON, lọc theo `run_id`, gom nhóm kết quả theo `baseline` và `agent`, rồi xuất summary ngắn gọn. Nhờ file này, nhóm không cần tự mở log rồi đếm tay số lần fail hay blocked nữa. Khi cần viết phần Evaluation & Analysis, chỉ cần dựa vào summary đã được tổng hợp sẵn.

Để pipeline có thể chạy ngay cả khi chưa có API thật hoặc khi cần test nhanh, tôi tạo thêm [src/core/mock_provider.py](c:/Users/ASUS/Lab-3-Team15/src/core/mock_provider.py). Mock provider này không nhằm thay thế mô hình thật, mà để kiểm tra xem runner, logging và summary có hoạt động đúng không. Đây là một lớp đệm khá hữu ích trong lúc các phần khác của dự án vẫn còn đang hoàn thiện.

Ngoài phần runner và telemetry, tôi cũng làm thêm [src/tools/flight_tools.py](c:/Users/ASUS/Lab-3-Team15/src/tools/flight_tools.py) và [src/tools/mock_db.json](c:/Users/ASUS/Lab-3-Team15/src/tools/mock_db.json) để runner có thể kết nối với tools thật thay vì chỉ giả lập. Bộ tools này gồm tìm chuyến bay, đặt vé, tra thời tiết và tra hành lý, đồng thời có hàm `get_tools()` để trả về đúng cấu trúc mà agent có thể dùng sau này. Nói cách khác, phần tôi làm không chỉ dừng ở “ghi log cho đẹp”, mà còn giúp tạo ra một môi trường thử nghiệm thống nhất cho cả baseline lẫn agent.

Cuối cùng, tôi viết thêm test ở [tests/test_flight_tools_and_runner.py](c:/Users/ASUS/Lab-3-Team15/tests/test_flight_tools_and_runner.py) và [tests/test_log_analysis.py](c:/Users/ASUS/Lab-3-Team15/tests/test_log_analysis.py) để kiểm tra các phần mình thêm vào. Tôi muốn những thành phần như tool loading, normalize input, sold-out handling hay summary log đều có kiểm tra tối thiểu, tránh việc code có vẻ đúng nhưng khi chạy lại thì hỏng ở những chỗ rất cơ bản.

---

## II. Debugging Case Study (10 Points)

Lỗi tôi thấy đáng nhớ nhất trong quá trình làm bài không nằm ở phần tool hay parser, mà lại nằm ở cấu hình provider. Khi chạy `python main.py`, toàn bộ 5 test case của baseline đều fail với `AuthenticationError`. Nếu chỉ nhìn lướt qua thì rất dễ nghĩ là API key bị sai đơn thuần, nhưng khi soi kỹ log tôi mới thấy có một chi tiết bất thường: model đang là `gemini-2.5-flash-lite`, nhưng provider lại hiện là `openai`.

Chính chỗ này làm tôi nhận ra hệ thống đang bị lệch cấu hình. Trong `.env`, `DEFAULT_PROVIDER` vẫn để là `openai`, trong khi `DEFAULT_MODEL` lại là model của Gemini và người dùng thực tế chỉ có `GEMINI_API_KEY`. Tệ hơn nữa, `OPENAI_API_KEY` không phải key thật mà chỉ là chuỗi placeholder `your_openai_api_key_here`. Vì runner lúc đó ưu tiên `DEFAULT_PROVIDER`, nó cứ cố tạo `OpenAIProvider`, rồi tất nhiên sẽ bị lỗi xác thực ở tất cả test case.

Sau đó tôi sửa lại phần chọn provider trong [main.py](c:/Users/ASUS/Lab-3-Team15/main.py). Tôi thêm một lớp làm sạch giá trị môi trường, coi các placeholder key là không hợp lệ, và cho phép suy luận provider từ `DEFAULT_MODEL` cùng các key đang thực sự tồn tại. Đồng thời tôi đổi `.env` sang `DEFAULT_PROVIDER=gemini` để phù hợp với cách hệ thống đang được dùng. Sau khi chỉnh, runner không còn rơi vào trường hợp dùng OpenAI chỉ vì biến môi trường cũ bị để sót.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

Điểm tôi thấy rõ nhất sau bài lab này là Chatbot thường và ReAct Agent khác nhau không chỉ ở “mạnh hay yếu”, mà khác nhau ở cách chúng tiếp cận vấn đề. Chatbot thường trả lời ngay bằng những gì mô hình suy ra từ ngữ cảnh hiện có. Còn ReAct Agent có thêm một bước suy nghĩ trung gian trước khi hành động. Với những bài toán đơn giản, sự khác biệt này có thể không quá rõ. Nhưng với các bài toán nhiều bước như tìm chuyến bay, kiểm tra dữ liệu và đặt vé, việc có `Thought` rồi mới `Action` là rất quan trọng. Nó giúp mô hình không nhảy thẳng đến câu trả lời cuối mà buộc phải đi qua các bước cần thiết.

Tuy vậy, agent không phải lúc nào cũng tốt hơn chatbot. Trên thực tế, agent thường mong manh hơn vì nó có nhiều thành phần hơn. Chỉ cần prompt không chặt, parser viết chưa tốt, tool spec không rõ hoặc loop control thiếu an toàn là agent có thể hỏng ở những cách mà chatbot thường không hỏng. Chatbot có thể trả lời sai nội dung, nhưng agent thì ngoài chuyện trả lời sai còn có thể loop, gọi tool sai hoặc dừng không đúng lúc. Trong lần chạy hiện tại, agent của nhóm còn chưa triển khai xong nên runner ghi nhận là `blocked`. Điều đó cũng cho tôi thấy một điều thực tế: ReAct chỉ thật sự mạnh khi hệ sinh thái xung quanh nó đã được làm cẩn thận.

Một điểm nữa tôi đánh giá rất cao ở ReAct là vai trò của `Observation`. Observation giống như phản hồi từ môi trường, buộc mô hình phải cập nhật lại hướng đi của nó. Nếu không có observation, mô hình chỉ đang đoán. Nhưng khi tool trả về dữ liệu thật, hoặc trả về lỗi thật, agent phải dựa vào đó để quyết định bước tiếp theo. Ví dụ, nếu chuyến bay `VJ122` hết chỗ, một agent tốt phải đọc observation đó và chuyển sang xin lỗi hoặc gợi ý phương án khác, thay vì cố bịa ra một mã đặt chỗ. Với tôi, đây chính là điểm làm nên sự khác biệt giữa một hệ thống “nói nghe hợp lý” và một hệ thống “thật sự hành động dựa trên dữ liệu”.

---

## IV. Future Improvements (5 Points)

Nếu có thêm thời gian để phát triển bài này theo hướng production hơn, tôi sẽ ưu tiên ba hướng. Hướng đầu tiên là mở rộng phần hạ tầng chạy tool. Hiện tại tool được gọi ngay trong tiến trình chính, phù hợp cho demo và quy mô nhỏ. Nhưng nếu hệ thống phải gọi nhiều nguồn dữ liệu hoặc xử lý những tác vụ chậm hơn, tôi sẽ tách phần tool execution ra khỏi luồng chat và đưa vào một cơ chế bất đồng bộ. Khi đó agent vừa đỡ bị block, vừa dễ theo dõi hiệu năng hơn.

Hướng thứ hai là tăng mức an toàn. Với những action nhạy cảm như xác nhận đặt vé thật hay thanh toán, hệ thống không nên để agent tự quyết hoàn toàn. Tôi nghĩ cần có thêm một lớp kiểm tra schema đối số, whitelist tool, và ở những bước quan trọng thì nên có xác nhận từ người dùng hoặc một lớp giám sát riêng trước khi thực thi.

Hướng cuối cùng là tối ưu cả chi phí lẫn khả năng mở rộng. Khi số lượng tool tăng lên, không thể cứ đưa toàn bộ mô tả tool vào prompt mãi được vì token sẽ tăng rất nhanh. Tôi muốn thêm một lớp routing hoặc retrieval để chỉ chọn ra những tool liên quan nhất với từng yêu cầu. Đồng thời, phần telemetry cũng nên được nâng cấp để đo sâu hơn, chẳng hạn như thời gian cho từng lần gọi tool, hiệu quả số vòng lặp, và tỷ lệ token giữa prompt với completion. Nếu làm được điều đó, việc so sánh Agent v1 và Agent v2 sẽ thuyết phục hơn nhiều thay vì chỉ dừng ở mức quan sát thủ công.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.

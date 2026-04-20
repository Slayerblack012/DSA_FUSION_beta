import asyncio
import os
import sys

backend_dir = os.path.abspath('backend')
sys.path.insert(0, backend_dir)

from app.services.ai_providers.gemini_provider import GeminiProvider

async def main():
    try:
        from dotenv import load_dotenv
        load_dotenv('.env') 
        load_dotenv('backend/.env')
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print('NO API KEY')
            return
            
        provider = GeminiProvider(api_key=api_key)
        
        prompt = """Bạn là một Kỹ sư Phần mềm Python cấp cao chuyên chấm bài DSA.
Nhiệm vụ: Chấm hệ thống bài nộp (có thể là một hoặc nhiều tệp liên kết được gộp chung) mang tên "bai1.py" (chủ đề: tree).
Hãy đánh giá toàn diện sự liên kết của mã nguồn và chấm đúng theo rubric_context được cung cấp, không thêm tiêu chí ngoài rubric.

INPUT_CODE:
# ====================
# TẬP TIN: bai1.py
# ====================
print(sum(range(10)))

# ====================
# TẬP TIN: bai1.py
# ====================
print(sum(range(10)))

AST_REPORT:
{"algorithms": ["test"], "complexity": "O(1)"}

RUBRIC_CONTEXT:
No rubric available. Grade by standard DSA criteria.

OUTPUT_JSON (chỉ JSON):
{
"normalized_score_10": 5.0,
"status": "AC|WA",
"algorithms_detected": ["<tên thuật toán>"],
"big_o": "O(...)",
"criteria_scores": [
{"criterion": "test", "earned": 1.0, "max": 1.0, "feedback": "ok", "evidence": "ok"}
],
"breakdown": {"correctness": 10, "quality": 10, "efficiency": 10, "structure_robustness": 10, "documentation": 10, "security": 10},
"technical_review": "ok",
"evidence_based_issues": ["ok"],
"actionable_suggestions": ["ok"]
}
"""
        res = await provider.generate_json(prompt, temperature=0, max_tokens=4096)
        print('RESULT:', res)
    except Exception as e:
        print('ERROR:', e)

asyncio.run(main())

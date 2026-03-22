import json

# --- 1. RAG 최적화: 슬라이딩 윈도우 겹침(Overlap) 알고리즘 ---
def chunk_text_with_overlap(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # 문서 끝이 아니라면, 단어가 절반으로 툭 끊기지 않도록 후진하며 안전한 절취선(공백/마침표) 탐색
        if end < text_len:
            break_point = end
            # 최대 100자 정도 뒤로 가며 마침표나 공백을 찾음
            for i in range(end - 1, max(start, end - 100), -1):
                if text[i] in [' ', '.', '!', '?', '\n']:
                    break_point = i + 1
                    break
            end = break_point
            
        chunk = text[start:end].strip()
        
        # 너무 짧은 찌꺼기 병합/제거 방어 (10자 이상 덩어리만 취급)
        if len(chunk) > 10:
            chunks.append(chunk)
            
        # 겹침(Overlap)을 적용해 다음 조각의 시작점 계산
        new_start = end - overlap
        
        # 혹시나 제자리걸음에 빠져 무한루프를 돌지 않도록 강제 전진 보장
        if new_start <= start:
            new_start = start + max(1, chunk_size // 2)
            
        start = new_start
        
    return chunks

# --- 2. 파싱된 JSON 데이터 불러오기 ---
file_name = "parsed_manuals.json"

print("⚙️ RAG(검색 증강 생성) 최적화 슬라이딩 윈도우 봇을 가동합니다...\n")

try:
    with open(file_name, "r", encoding="utf-8") as f:
        documents = json.load(f)
except FileNotFoundError:
    print(f"앗! '{file_name}' 파일이 없습니다. parsing.py를 먼저 실행해주세요!")
    exit()

chunked_data = []

# --- 3. 슬라이딩 윈도우 방식으로 정교하게 썰기 ---
for doc in documents:
    source_name = doc["source"]
    content = doc["content"]
    print(f"[{source_name}] 스마트 슬라이딩 윈도우 재단 중...")
    
    # 500자 단위로 자르되, 100자씩 겹치게(Overlap) 자름
    smart_chunks = chunk_text_with_overlap(content, chunk_size=500, overlap=100)
    
    chunk_id = 1
    for chunk in smart_chunks:
        chunked_data.append({
            "source": source_name,
            "chunk_id": chunk_id,
            "content": chunk
        })
        chunk_id += 1

# --- 4. RAG용 고품질 결과물 저장 ---
save_path = "chunked_manuals.json"
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(chunked_data, f, ensure_ascii=False, indent=4)

print(f"\n🎉 완료! 단어 스플릿 없이, 문맥이 부드럽게 이어지는 총 {len(chunked_data)}개의 최고급 RAG 조각들이 '{save_path}'에 저장되었습니다!")

# 썰린 조각 미리보기 (겹침 현상 확인)
if len(chunked_data) >= 2:
    print("--------------------------------------------------")
    print(f"🔍 [미리보기 - 1번 조각] (출처: {chunked_data[0]['source']})")
    # 앞부분만 살짝 출력 (긴 경우 한 줄 처리 방지)
    print(f"{chunked_data[0]['content'][:200]} ... [생략]\n")
    print(f"🔍 [미리보기 - 2번 조각 (100자 겹침 확인)] (출처: {chunked_data[1]['source']})")
    print(f"{chunked_data[1]['content'][:200]} ... [생략]")
    print("--------------------------------------------------")
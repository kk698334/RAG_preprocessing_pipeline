import win32com.client as win32
import os
import glob
import json
import re
import fitz  # PyMuPDF

# --- 1. 텍스트 추출 함수들 ---
def extract_text_with_hwp(file_path, hwp_app):
    try:
        abs_path = os.path.abspath(file_path)
        hwp_app.Open(abs_path, "HWP", "forceopen:true")
        hwp_app.InitScan()
        
        full_text = ""
        while True:
            state, text = hwp_app.GetText()
            if state in [0, 1]: 
                break
            full_text += text
            
        hwp_app.ReleaseScan()
        return full_text
    
    except Exception as e:
        print(f"[{os.path.basename(file_path)}] HWP 에러: {e}")
        return None

def extract_text_with_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        return full_text
    except Exception as e:
        print(f"[{os.path.basename(file_path)}] PDF 에러: {e}")
        return None

# --- 2. 노이즈 제거 및 구조 필터링 함수 ---
def clean_noise(text):
    if not text: return ""
    # <그림 설명> 등 불필요 태그 흔적 날리기
    text = re.sub(r'<[^>]+>', '', text)
    # 지저분한 띄어쓰기를 한 칸 공백으로 압축
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_valid_manual(text):
    # 포스터나 팸플릿은 이미지 위주라 추출되는 텍스트가 극히 적음 (500자 이하 기준 컷)
    if len(text) < 500:
        return False, "텍스트 길이 500자 미만 (포스터/팸플릿 의심)"
    
    # 텍스트가 충분히 길다면 매뉴얼로 합격
    return True, "유효한 매뉴얼"

# --- 3. 본격적인 실행 파트 ---
print("⚙️ 문서 파서(Parser)를 가동합니다. HWP와 PDF 처리를 준비합니다...")

# 한글 프로세스는 무거우므로 한 번만 띄워서 계속 재사용
hwp = None
try:
    hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
    hwp.XHwpWindows.Item(0).Visible = False # 한글 창 숨기기
except Exception as e:
    print("한글 프로그램 실행 에러 (HWP가 설치되어 있지 않으면 PDF만 진행됩니다):", e)

# 중복 제거 및 우선순위(HWP > PDF) 결정을 위한 파일 그룹핑
file_list = glob.glob("raw_documents/*")
target_files = {}

for file in file_list:
    base_name, ext = os.path.splitext(file)
    ext = ext.lower()
    if ext not in ['.hwp', '.pdf']:
        continue
    
    if base_name not in target_files:
        target_files[base_name] = []
    target_files[base_name].append(ext)

# HWP를 우선으로 최종 타겟 리스트 생성
final_targets = []
for base_name, exts in target_files.items():
    if '.hwp' in exts:
        final_targets.append(base_name + '.hwp')
    elif '.pdf' in exts:
        final_targets.append(base_name + '.pdf')

print(f"✅ 수집된 {len(file_list)}개의 파일 중, 중복 배제 적용하여 총 {len(final_targets)}개의 파싱 대상을 추려냈습니다!\n")

all_documents = []

for file in final_targets:
    print(f"작업 중... : {os.path.basename(file)}")
    
    ext = os.path.splitext(file)[1].lower()
    raw_text = ""
    
    # 확장자에 따른 함수 렌더링 분기
    if ext == '.hwp' and hwp:
        raw_text = extract_text_with_hwp(file, hwp)
    elif ext == '.pdf':
        raw_text = extract_text_with_pdf(file)
        
    if raw_text:
        # 노이즈를 닦아낸 진또배기 텍스트 만들기
        clean_data = clean_noise(raw_text)
        is_valid, reason = is_valid_manual(clean_data)
        
        if is_valid:
            all_documents.append({
                "source": os.path.basename(file),
                "content": clean_data
            })
            print(f"  👉 [통과] 유효 텍스트 추출 완료 ({len(clean_data)}자)")
        else:
            print(f"  ⏩ [패스] {reason} ({len(clean_data)}자)")
    else:
        print("  ⏩ [패스] 텍스트가 없거나 실패함")

# 한글 프로그램 안전 종료
if hwp:
    hwp.Quit()

# --- 4. 최종 결과물 저장 ---
save_path = "parsed_manuals.json"
with open(save_path, 'w', encoding='utf-8') as f:
    json.dump(all_documents, f, ensure_ascii=False, indent=4)

print(f"\n🎉 완료! 총 {len(all_documents)}개의 진짜배기 매뉴얼 텍스트가 '{save_path}'로 깔끔하게 저장되었습니다!")
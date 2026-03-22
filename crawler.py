import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 1. 다운로드 폴더 설정 (현재 경로의 raw_documents 폴더)
current_dir = os.path.dirname(os.path.abspath(__file__))
download_dir = os.path.join(current_dir, "raw_documents")

if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# 2. 브라우저 옵션 설정 (자동으로 raw_documents로 다운로드 받도록 설정)
chrome_options = Options()
# chrome_options.add_argument("--headless") # 창 없이 실행하려면 주석 해제
prefs = {
    "profile.default_content_settings.popups": 0,
    "profile.default_content_setting_values.automatic_downloads": 1,  # 다중 파일 다운로드 자동 허용
    "download.default_directory": download_dir,           # 기본 다운로드 경로 지정
    "download.prompt_for_download": False,                # 다운로드 팝업 끄기
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True                          # 안전하지 않은 다운로드 경고 무시
}
chrome_options.add_experimental_option("prefs", prefs)

print("🚀 크롤링 봇을 시동합니다...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 10)

try:
    # 3. 국민재난안전포털 자료실 접속
    target_url = "https://safekorea.go.kr/idsiSFK/neo/sfk/cs/csc/bbs_conf.jsp?bbs_no=9&emgPage=Y&menuSeq=593"
    driver.get(target_url)
    time.sleep(3) # 전체 페이지 로딩 대기

    print("✅ 페이지 접속 완료. 무식한 다운로드를 시작합니다!")
    
    # 4. 전체 페이지 수 동적 로딩 및 순회
    time.sleep(2)
    try: max_page = int(driver.find_element(By.ID, "maxPage").text)
    except: max_page = 21 # 만약 실패 시 대략적인 끝 번호
    print(f"✅ 총 {max_page}페이지로 감지되었습니다. 끝까지 수집합니다!")
    
    for current_page_num in range(1, max_page + 1):
        print(f"\n--- [현재 페이지: {current_page_num}/{max_page}] ---")
        time.sleep(2)
        
        # 1. 진입 시 올바른 페이지인지 확인하고 (다음 페이지로 이동하는 역할 겸용)
        try: driver.switch_to.alert.accept() # 혹시 모를 잔여 경고창 클리어
        except: pass
        
        try:
            # 아예 사이트를 튕겨져 나갔거나 빈 화면일 경우 메인으로 재접속
            if len(driver.find_elements(By.ID, "minPage")) == 0:
                driver.get(target_url)
                time.sleep(3)
                
            now_num = driver.find_element(By.ID, "minPage").text
            if str(now_num) != str(current_page_num):
                driver.execute_script(f"document.getElementById('bbs_page').value = '{current_page_num}'; onGoToPageBtnClick();")
                time.sleep(3)
        except:
            pass
            
        articles = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        for i in range(len(articles)):
            try:
                # 2. 뒤로가기 등으로 1페이지로 튕겼을 때 스스로 치유하는 방어 로직
                try: driver.switch_to.alert.accept() # 진입 전 혹시 모를 경고창 클리어
                except: pass
                
                try:
                    # 빈 화면에 갇혔을 경우 강제 탈출 후 내 위치로 텔레포트
                    if len(driver.find_elements(By.ID, "minPage")) == 0:
                        print("  🔄 빈 화면 감지, 게시판 메인으로 재접속하여 복구 중...")
                        driver.get(target_url)
                        time.sleep(3)
                        
                    now_num = driver.find_element(By.ID, "minPage").text
                    if str(now_num) != str(current_page_num):
                        driver.execute_script(f"document.getElementById('bbs_page').value = '{current_page_num}'; onGoToPageBtnClick();")
                        time.sleep(3)
                except:
                    pass
                        
                # 목록 페이지 안착 후 다시 tr 요소 찾기 (DOM 갱신 대비)
                current_articles = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                row = current_articles[i]
                
                # 공지사항 등 링크 없는 로우 건너뛰기
                try:
                    title_link = row.find_element(By.CSS_SELECTOR, "td.title a, td.subj a, td:nth-child(2) a")
                except:
                    continue
                    
                article_title = title_link.text
                print(f"👉 글 접속: {article_title}")
                
                # 현재 창에서 깔끔하게 게시글 접속
                driver.execute_script("arguments[0].click();", title_link)
                time.sleep(2)
                
                # --- 상세 페이지 (첨부파일 다운로드) ---
                download_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'fn_download') or contains(@href, 'download') or contains(text(), 'hwp') or contains(text(), 'pdf')]")
                
                if download_links:
                    import re, unicodedata
                    for link in download_links:
                        # 텍스트 추출 및 정규화 (보이지 않는 공백, 윈도우 금지 문자 지정 등)
                        original_text = link.text.strip().replace('\xa0', ' ')
                        original_text = unicodedata.normalize('NFC', original_text)
                        clean_filename = re.sub(r'[\\/*?:"<>|]', '_', original_text) # 브라우저가 저장할 때 바꾸는 이름과 똑같이 맞춤
                        
                        link_text_lower = clean_filename.lower()
                        if '.hwp' in link_text_lower or '.pdf' in link_text_lower or '.docx' in link_text_lower:
                            file_path = os.path.join(download_dir, clean_filename)
                            if os.path.exists(file_path):
                                print(f"      ⏩ 이미 수집된 파일(패스): {clean_filename}")
                                continue
                                
                            print(f"      🗂️ 첨부파일 획득: {clean_filename}")
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(1.5)
                else:
                    print("      없음 (첨부파일을 못 찾음)")
                
                # 자연스럽게 사이트 고유의 검색/목록 버튼으로 원상복구 (가장 버그 없음)
                try:
                    list_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '목록') or contains(@title, '목록')] | //img[contains(@alt, '목록')]/parent::a | //button[contains(text(), '목록') or contains(@title, '목록')]")))
                    driver.execute_script("arguments[0].click();", list_btn)
                except:
                    driver.back() # 버튼조차 못 찾으면 브라우저 자체 뒤로가기
                time.sleep(2)
                
            except Exception as e:
                print(f"  ⚠️ 글 탐색 중 오류 발생, 다음 글로 넘어감")
                # 혹시 경고창(Alert)이 켜져 있으면 진행이 통째로 막히므로 강제로 닫기
                try:
                    driver.switch_to.alert.accept()
                    time.sleep(2) # 서버 측에서 팝업 띄운 뒤 스스로 history.back() 할 시간을 줌
                except:
                    pass
                    
                # 에러 후 브라우저가 완전히 엉뚱한 빈 화면이나 메인 화면으로 튕겼는지 최후의 검사
                try: 
                    if len(driver.find_elements(By.ID, "minPage")) == 0:
                        driver.get(target_url)  # 아예 쌩초기화 (어차피 다음 루프 때 원래 페이지 번호로 자동 복구됨)
                        time.sleep(3)
                except: pass

        # 현재 페이지 글 모두 수집 완료
        print(f"➡️ 단일 페이지({current_page_num}) 수집 완료. 루프 상단에서 다음 페이지로 이동합니다...")
        # (다음 페이지 이동은 for 루프 상단에서 id="minPage" 체크를 통해 스스로 자동 수행됨)

except Exception as e:
    print(f"전체 프로세스 에러: {e}")

finally:
    # 충분히 기다렸다가 (다운로드 완료 후) 끄기
    print("\n🎉 모든 명령 완료! 남은 다운로드를 위해 잠시 대기합니다.")
    time.sleep(10) 
    driver.quit()
    print("수집기 작동 종료.")

import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import re
from difflib import SequenceMatcher

# 1. API 키 설정 (보안)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    GOOGLE_API_KEY = None

# 2. 유틸리티 함수
def pre_check_text(text):
    allowed_english = ["cm", "mm", "m", "kg", "g", "t", "mg", "CEO", "PD", "UCC", "IT", "POP", "CF", "TV", "PAPS", "SNS", "PPT"]
    illegal_english = [w for w in re.findall(r'[a-zA-Z]+', text) if w not in allowed_english]
    illegal_symbols = re.findall(r'[^\w\s\.\,\'\-]', text)
    return list(set(illegal_english)), list(set(illegal_symbols))

def check_similarity(texts):
    duplicates = []
    names = list(texts.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ratio = SequenceMatcher(None, texts[names[i]], texts[names[j]]).ratio()
            if ratio >= 0.95:
                duplicates.append((names[i], names[j], f"{int(ratio*100)}%"))
    return duplicates

# 3. UI 구성
st.set_page_config(page_title="생기부 기재요령 검토기", layout="wide")
st.title("🏫 생기부 기재요령 검토기")

with st.sidebar:
    st.header("⚙️ 설정")
    if not GOOGLE_API_KEY:
        api_input = st.text_input("Gemini API Key (무료 버전 가능)", type="password")
        if api_input: 
            genai.configure(api_key=api_input)
            GOOGLE_API_KEY = api_input
    st.info("지침: 95% 중복, 명사형 종결, 영문/기호 제한 등")
    st.caption("⚠️ 무료 API는 분당 요청 횟수 제한이 있을 수 있습니다.")

uploaded_files = st.file_uploader("PDF 업로드 (여러 명 가능)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    data = {}
    for f in uploaded_files:
        reader = PdfReader(f)
        data[f.name] = "".join([p.extract_text() for p in reader.pages])

    # 분석 로직
    duplicates = check_similarity(data)
    dup_names = set([d[0] for d in duplicates] + [d[1] for d in duplicates])
    
    issue_students = {}
    clean_students = []

    for name, content in data.items():
        eng, sym = pre_check_text(content)
        if eng or sym or name in dup_names:
            issue_students[name] = {"eng": eng, "sym": sym, "content": content}
        else:
            clean_students.append(name)

    # 결과 표시
    st.subheader("📊 검토 결과")
    if clean_students:
        with st.expander(f"✅ 통과 ({len(clean_students)}명)"):
            st.write(", ".join(clean_students))

    if issue_students:
        st.error(f"⚠️ 수정 필요 ({len(issue_students)}명)")
        tabs = st.tabs(list(issue_students.keys()))
        
        for i, tab in enumerate(tabs):
            name = list(issue_students.keys())[i]
            info = issue_students[name]
            with tab:
                if name in dup_names:
                    st.error("🚨 유사도 95% 이상 감지됨 (다른 학생과 내용이 거의 일치합니다)")
                
                c1, c2 = st.columns(2)
                with c1: st.warning(f"영문 위반: {info['eng']}") if info['eng'] else st.success("영문 지침 준수")
                with c2: st.warning(f"기호 위반: {info['sym']}") if info['sym'] else st.success("기호 지침 준수")

                if st.button(f"🪄 AI 수정안 생성 ({name})", key=f"ai_{name}"):
                    if not GOOGLE_API_KEY:
                        st.error("API 키를 먼저 입력해주세요.")
                    else:
                        with st.spinner("무료 버전 제미나이로 교정 중..."):
                            try:
                                # 무료 버전에서 가장 안정적인 모델명 사용
                                model = genai.GenerativeModel('gemini-1.5-flash')
                                prompt = f"다음은 학생의 생활기록부 내용입니다. 1) 문장을 ~함, ~임과 같은 명사형 종결로 수정하고, 2) 허용되지 않은 영문이나 기호를 정제해서 '수정된 본문'만 보여주세요:\n\n{info['content']}"
                                response = model.generate_content(prompt)
                                
                                st.markdown("### ✨ AI 수정 제안")
                                st.code(response.text, language="text") 
                                st.caption("오른쪽 상단 아이콘을 눌러 복사할 수 있습니다.")
                            except Exception as e:
                                if "429" in str(e):
                                    st.error("너무 빠른 요청입니다. 잠시 후 다시 시도해주세요.")
                                else:
                                    st.error(f"에러가 발생했습니다: {e}")
    else:
        st.balloons()
        st.success("모든 서류가 지침을 준수하고 있습니다!")

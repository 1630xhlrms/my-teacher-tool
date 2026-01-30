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
st.set_page_config(page_title="2025 생기부 체크", layout="wide")
st.title("🏫 2025 생기부 기재요령 검토기")

with st.sidebar:
    st.header("⚙️ 설정")
    if not GOOGLE_API_KEY:
        api_input = st.text_input("Gemini API Key", type="password")
        if api_input: genai.configure(api_key=api_input)
    st.info("지침: 95% 중복, 명사형 종결, 영문/기호 제한 등")

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
                    st.error("🚨 유사도 95% 이상 감지됨")
                
                c1, c2 = st.columns(2)
                with c1: st.warning(f"영문 위반: {info['eng']}") if info['eng'] else st.write("영문 지침 준수")
                with c2: st.warning(f"기호 위반: {info['sym']}") if info['sym'] else st.write("기호 지침 준수")

                if st.button(f"🪄 AI 수정안 생성 ({name})", key=f"ai_{name}"):
                    with st.spinner("다듬는 중..."):
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"아래 생기부를 1)명사형 종결 2)금지어 제거 3)특수기호 정제하여 '수정된 본문'만 출력해줘:\n\n{info['content']}"
                        response = model.generate_content(prompt)
                        
                        # 수정된 텍스트 출력 및 복사 기능
                        st.markdown("### ✨ AI 수정 제안")
                        st.code(response.text, language="text") 
                        st.caption("위 박스 우측 상단의 아이콘을 클릭하면 바로 복사됩니다.")
    else:
        st.balloons()
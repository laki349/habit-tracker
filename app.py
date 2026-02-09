
# app.py
import os
import json
import requests
from datetime import date, timedelta

import pandas as pd
import streamlit as st


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="AI 습관 트래커", page_icon="📊", layout="wide")
st.title("📊 AI 습관 트래커")

# -----------------------------
# Sidebar: API Keys
# -----------------------------
st.sidebar.header("🔑 API 설정")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
owm_api_key = st.sidebar.text_input("OpenWeatherMap API Key", type="password", value=os.getenv("OPENWEATHERMAP_API_KEY", ""))

st.sidebar.markdown("---")
st.sidebar.caption("💡 키는 브라우저 세션에만 사용되며, 앱 코드에 저장되지 않도록 구성하세요.")


# -----------------------------
# API 연동 함수
# -----------------------------
def get_weather(city: str, api_key: str):
    """
    OpenWeatherMap에서 현재 날씨를 가져옵니다.
    - 한국어, 섭씨
    - 실패 시 None
    - timeout=10
    """
    if not api_key:
        return None

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "kr",
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()

        weather_desc = None
        if isinstance(data.get("weather"), list) and data["weather"]:
            weather_desc = data["weather"][0].get("description")

        main = data.get("main", {})
        wind = data.get("wind", {})

        return {
            "city": city,
            "temp_c": main.get("temp"),
            "feels_like_c": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "desc": weather_desc,
            "wind_mps": wind.get("speed"),
        }
    except Exception:
        return None


def get_dog_image():
    """
    Dog CEO에서 랜덤 강아지 이미지 URL과 품종을 가져옵니다.
    - 실패 시 None
    - timeout=10
    """
    try:
        url = "https://dog.ceo/api/breeds/image/random"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != "success":
            return None

        img_url = data.get("message")
        if not img_url or not isinstance(img_url, str):
            return None

        # 품종 추정: .../breeds/{breed}/... 또는 .../breeds/{breed-sub}/...
        # 예: https://images.dog.ceo/breeds/hound-afghan/n02088094_1003.jpg
        breed = "알 수 없음"
        try:
            parts = img_url.split("/breeds/")
            if len(parts) > 1:
                breed_part = parts[1].split("/")[0]  # hound-afghan
                breed = breed_part.replace("-", " ").strip()
        except Exception:
            pass

        return {"image_url": img_url, "breed": breed}
    except Exception:
        return None


def get_daily_inspiration():
    """
    무료 공개 API로부터 오늘의 영감을 가져옵니다.
    - ZenQuotes(quote) + NASA APOD(optional image)
    - 실패 시 None
    - timeout=10
    """
    try:
        result = {
            "image_url": None,
            "title": None,
            "description": None,
            "quote": None,
            "author": None,
        }

        nasa_key = os.getenv("NASA_API_KEY", "").strip()
        if nasa_key:
            url = "https://api.nasa.gov/planetary/apod"
            params = {"api_key": nasa_key}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("media_type") == "image":
                    result["image_url"] = data.get("url")
                    result["title"] = data.get("title")
                    result["description"] = data.get("explanation")

        quote_url = "https://zenquotes.io/api/today"
        r = requests.get(quote_url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                result["quote"] = data[0].get("q")
                result["author"] = data[0].get("a")

        if any(value is not None for value in result.values()):
            return result
        return None
    except Exception:
        return None


def get_daily_book():
    """
    OpenLibrary에서 오늘의 추천 도서를 가져옵니다.
    - 실패 시 None
    - timeout=10
    """
    try:
        url = "https://openlibrary.org/subjects/self_help.json?limit=30"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        works = data.get("works", [])
        if not isinstance(works, list) or not works:
            return None

        idx = date.today().toordinal() % len(works)
        work = works[idx]

        title = work.get("title") or "알 수 없음"
        author = "알 수 없음"
        if isinstance(work.get("authors"), list) and work["authors"]:
            author = work["authors"][0].get("name") or author

        cover_url = None
        cover_id = work.get("cover_id")
        cover_edition = work.get("cover_edition_key")
        if cover_id:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        elif cover_edition:
            cover_url = f"https://covers.openlibrary.org/b/olid/{cover_edition}-L.jpg"

        short_summary = None
        work_key = work.get("key")
        if work_key:
            work_url = f"https://openlibrary.org{work_key}.json"
            wr = requests.get(work_url, timeout=10)
            if wr.status_code == 200:
                wdata = wr.json()
                desc = wdata.get("description")
                if isinstance(desc, dict):
                    short_summary = desc.get("value")
                elif isinstance(desc, str):
                    short_summary = desc

        return {
            "title": title,
            "author": author,
            "cover_url": cover_url,
            "short_summary": short_summary,
        }
    except Exception:
        return None


def _system_prompt_for_style(style: str) -> str:
    if style == "스파르타 코치":
        return (
            "너는 매우 엄격하고 직설적인 습관 코치다. 핑계는 받아주지 않는다. "
            "하지만 모욕적이거나 공격적이면 안 된다. 짧고 강하게, 실행 중심으로 말해라."
        )
    if style == "따뜻한 멘토":
        return (
            "너는 따뜻하고 공감적인 멘토다. 사용자의 노력과 감정을 존중하고, "
            "작은 성공을 칭찬하며 부드럽게 다음 행동을 제안한다."
        )
    # 게임 마스터
    return (
        "너는 RPG 세계관의 게임 마스터다. 사용자의 하루를 퀘스트/스탯/버프로 묘사한다. "
        "너무 길게 늘어놓지 말고, 재미있지만 실행 가능한 미션으로 마무리해라."
    )


def generate_report(
    openai_key: str,
    coach_style: str,
    habits: dict,
    mood: int,
    weather: dict | None,
    dog: dict | None,
    inspiration: dict | None,
    book: dict | None,
):
    """
    습관 + 기분 + 날씨 + 강아지 품종 + 영감 + 책 정보를 묶어 OpenAI에 전달해 리포트를 생성합니다.
    - 모델: gpt-5-mini
    - 실패 시 None
    """
    if not openai_key:
        return None

    weather_summary = "날씨 정보 없음"
    if weather:
        weather_summary = (
            f"{weather.get('city')} / {weather.get('desc')} / "
            f"{weather.get('temp_c')}°C (체감 {weather.get('feels_like_c')}°C) / "
            f"습도 {weather.get('humidity')}% / 바람 {weather.get('wind_mps')} m/s"
        )

    dog_summary = "강아지 정보 없음"
    if dog:
        dog_summary = f"오늘의 강아지 품종: {dog.get('breed')}"

    inspiration_summary = "오늘의 영감 정보 없음"
    if inspiration:
        inspiration_parts = []
        if inspiration.get("title"):
            inspiration_parts.append(f"제목: {inspiration.get('title')}")
        if inspiration.get("description"):
            inspiration_parts.append(f"설명: {inspiration.get('description')}")
        if inspiration.get("quote"):
            quote_author = inspiration.get("author") or "익명"
            inspiration_parts.append(f"문구: \"{inspiration.get('quote')}\" — {quote_author}")
        if inspiration_parts:
            inspiration_summary = " / ".join(inspiration_parts)

    book_summary = "오늘의 책 정보 없음"
    if book:
        book_parts = [f"{book.get('title')} - {book.get('author')}"]
        if book.get("short_summary"):
            book_parts.append(f"요약: {book.get('short_summary')}")
        book_summary = " / ".join(book_parts)

    habits_kor = "\n".join([f"- {k}: {'✅' if v else '❌'}" for k, v in habits.items()])
    system_prompt = _system_prompt_for_style(coach_style)

    # 출력 형식 고정
    format_spec = """
아래 형식(섹션 제목 포함)을 반드시 지켜서 한국어로 작성해.
각 섹션은 2~5문장 정도로 간결하게.

[컨디션 등급] (S/A/B/C/D 중 하나)
[습관 분석]
[날씨 코멘트]
[내일 미션] (3개, 체크박스처럼 '1) ...' 형태)
[오늘의 한마디] (한 줄)
""".strip()

    user_prompt = f"""
오늘 체크인 데이터야.

[습관]
{habits_kor}

[기분 점수] {mood}/10

[날씨]
{weather_summary}

[강아지]
{dog_summary}

[오늘의 영감]
{inspiration_summary}

[오늘의 책]
{book_summary}

리포트에는 오늘의 영감 내용을 반드시 언급하고, 책의 주제나 메시지를 사용자의 습관/기분과 연결해줘.

요구 출력 형식:
{format_spec}
""".strip()

    # OpenAI Responses API (HTTP) 사용
    try:
        url = "https://api.openai.com/v1/responses"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4.1-mini",
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()

        # responses API는 output_text 또는 output 배열을 가질 수 있음
        text = data.get("output_text")
        if text and isinstance(text, str):
            return text.strip()

        # fallback: output 구조 파싱
        out = data.get("output", [])
        chunks = []
        if isinstance(out, list):
            for item in out:
                content = item.get("content", [])
                if isinstance(content, list):
                    for c in content:
                        if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                            chunks.append(c["text"])
        if chunks:
            return "\n".join(chunks).strip()

        return None
    except Exception:
        return None


# -----------------------------
# Session State 초기화: 데모 6일 + 오늘(7일)
# -----------------------------
def _init_history_if_needed():
    if "history" in st.session_state:
        return

    today = date.today()

    # 데모용 6일 샘플(고정값)
    demo = []
    demo_counts = [3, 4, 4, 2, 5, 3]   # 6개 습관 중 달성 개수
    demo_moods = [5, 6, 7, 4, 8, 6]    # 기분 1~10
    for i in range(6, 0, -1):
        d = today - timedelta(days=i)
        idx = 6 - i
        demo.append(
            {
                "date": d.isoformat(),
                "done": int(demo_counts[idx]),
                "rate": int(round(demo_counts[idx] / 6 * 100)),
                "mood": int(demo_moods[idx]),
            }
        )

    st.session_state.history = demo  # 오늘은 버튼으로 저장/갱신


_init_history_if_needed()


def _get_daily_cached(cache_key: str, fetch_fn):
    today_key = date.today().isoformat()
    date_key = f"{cache_key}_date"
    data_key = f"{cache_key}_data"
    if st.session_state.get(date_key) != today_key:
        st.session_state[date_key] = today_key
        st.session_state[data_key] = fetch_fn()
    return st.session_state.get(data_key)


# -----------------------------
# 공용 설정
# -----------------------------
HABITS = [
    ("🌅 기상 미션", "wake"),
    ("💧 물 마시기", "water"),
    ("📚 공부/독서", "study"),
    ("🏋️ 운동하기", "workout"),
    ("😴 수면", "sleep"),
    ("📖 리딩 미션", "reading"),
]

cities = [
    "Seoul", "Busan", "Incheon", "Daegu", "Daejeon",
    "Gwangju", "Suwon", "Ulsan", "Sejong", "Jeju"
]
coach_styles = ["스파르타 코치", "따뜻한 멘토", "게임 마스터"]

# 오늘 날짜가 바뀌면 입력 기본값 리셋(체크 상태)
today_key = date.today().isoformat()
if st.session_state.get("today_key") != today_key:
    st.session_state["today_key"] = today_key
    for _, key in HABITS:
        st.session_state[f"habit_{key}"] = False
    st.session_state["mood"] = 6
    st.session_state["city"] = "Seoul"
    st.session_state["coach_style"] = "따뜻한 멘토"


# -----------------------------
# Today's Inspiration
# -----------------------------
st.subheader("🌟 Today’s Inspiration")
inspiration = _get_daily_cached("inspiration", get_daily_inspiration)
with st.container():
    if inspiration:
        left, right = st.columns([1, 2])
        with left:
            if inspiration.get("image_url"):
                st.image(inspiration["image_url"], use_container_width=True)
        with right:
            if inspiration.get("title"):
                st.markdown(f"**{inspiration.get('title')}**")
            if inspiration.get("description"):
                st.caption(inspiration.get("description"))
            if inspiration.get("quote"):
                quote_author = inspiration.get("author") or "익명"
                st.markdown(f"> {inspiration.get('quote')}")
                st.write(f"— {quote_author}")
    else:
        st.info("오늘의 영감 정보를 가져오지 못했어요. (네트워크/API 확인)")


# -----------------------------
# Today's Reading Mission
# -----------------------------
st.subheader("📖 Today’s Reading Mission")
book = _get_daily_cached("daily_book", get_daily_book)
mission_options = [
    "5쪽 읽기",
    "10분 읽기",
    "핵심 문장 1개 기록하기",
    "챕터 1개 훑어보기",
]
mission_text = mission_options[date.today().toordinal() % len(mission_options)]
with st.container():
    bcol, tcol = st.columns([1, 2])
    with bcol:
        if book and book.get("cover_url"):
            st.image(book["cover_url"], use_container_width=True)
    with tcol:
        if book:
            st.markdown(f"**{book.get('title')}**")
            st.write(f"저자: {book.get('author')}")
            if book.get("short_summary"):
                st.caption(book.get("short_summary"))
        else:
            st.info("오늘의 책 정보를 가져오지 못했어요. (OpenLibrary 네트워크 확인)")
        st.markdown(f"**오늘의 미션:** {mission_text}")
        st.checkbox("✅ 리딩 미션 완료", key="habit_reading")


# -----------------------------
# 습관 체크인 UI
# -----------------------------
st.subheader("✅ 오늘의 습관 체크인")

c1, c2 = st.columns(2)
with c1:
    h_wake = st.checkbox("🌅 기상 미션", key="habit_wake")
    h_water = st.checkbox("💧 물 마시기", key="habit_water")
    h_study = st.checkbox("📚 공부/독서", key="habit_study")
with c2:
    h_workout = st.checkbox("🏋️ 운동하기", key="habit_workout")
    h_sleep = st.checkbox("😴 수면", key="habit_sleep")

mood = st.slider("🙂 오늘 기분은 어때? (1~10)", min_value=1, max_value=10, value=st.session_state.get("mood", 6), key="mood")

u1, u2 = st.columns(2)
with u1:
    city = st.selectbox("🏙️ 도시 선택", options=cities, index=cities.index(st.session_state.get("city", "Seoul")), key="city")
with u2:
    coach_style = st.radio("🎙️ 코치 스타일", options=coach_styles, index=coach_styles.index(st.session_state.get("coach_style", "따뜻한 멘토")), horizontal=True, key="coach_style")

habits_state = {
    "기상 미션": bool(h_wake),
    "물 마시기": bool(h_water),
    "공부/독서": bool(h_study),
    "운동하기": bool(h_workout),
    "수면": bool(h_sleep),
    "리딩 미션": bool(st.session_state.get("habit_reading", False)),
}

done_count = sum(1 for v in habits_state.values() if v)
total_habits = len(habits_state)
rate = int(round(done_count / total_habits * 100))


# -----------------------------
# 달성률 + 메트릭
# -----------------------------
st.subheader("📈 오늘의 요약")
m1, m2, m3 = st.columns(3)
m1.metric("달성률", f"{rate}%")
m2.metric("달성 습관", f"{done_count}/{total_habits}")
m3.metric("기분", f"{mood}/10")


# -----------------------------
# 7일 바 차트 (6일 데모 + 오늘)
# session_state로 기록 저장
# -----------------------------
def upsert_today_history(done: int, rate: int, mood: int):
    today_str = date.today().isoformat()
    history = st.session_state.history

    # 오늘 데이터가 있으면 갱신, 없으면 추가
    replaced = False
    for row in history:
        if row["date"] == today_str:
            row["done"] = int(done)
            row["rate"] = int(rate)
            row["mood"] = int(mood)
            replaced = True
            break
    if not replaced:
        history.append({"date": today_str, "done": int(done), "rate": int(rate), "mood": int(mood)})

    # 최근 7개만 유지
    history.sort(key=lambda x: x["date"])
    st.session_state.history = history[-7:]


# 차트는 "현재 입력값 기준 오늘"을 반영해서 보여주기
upsert_today_history(done_count, rate, mood)

df = pd.DataFrame(st.session_state.history)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")
df_display = df.set_index("date")[["rate"]]

st.subheader("📊 최근 7일 달성률")
st.bar_chart(df_display)


# -----------------------------
# 결과 표시: 버튼 -> 날씨/강아지 카드 + 리포트
# -----------------------------
st.subheader("🧠 AI 코치 리포트")

btn = st.button("컨디션 리포트 생성", use_container_width=True)

if btn:
    with st.spinner("데이터 수집 & 리포트 생성 중..."):
        weather = get_weather(city, owm_api_key)
        dog = get_dog_image()
        report = generate_report(
            openai_key=openai_api_key,
            coach_style=coach_style,
            habits=habits_state,
            mood=mood,
            weather=weather,
            dog=dog,
            inspiration=inspiration,
            book=book,
        )

    wcol, dcol = st.columns(2)

    # 날씨 카드
    with wcol:
        st.markdown("### 🌦️ 날씨")
        if weather:
            st.write(f"**도시:** {weather.get('city')}")
            st.write(f"**상태:** {weather.get('desc')}")
            st.write(f"**기온:** {weather.get('temp_c')}°C (체감 {weather.get('feels_like_c')}°C)")
            st.write(f"**습도:** {weather.get('humidity')}%")
            st.write(f"**바람:** {weather.get('wind_mps')} m/s")
        else:
            st.info("날씨 정보를 가져오지 못했어요. (API Key/도시/네트워크 확인)")

    # 강아지 카드
    with dcol:
        st.markdown("### 🐶 오늘의 강아지")
        if dog:
            st.write(f"**품종:** {dog.get('breed')}")
            if dog.get("image_url"):
                st.image(dog["image_url"], use_container_width=True)
        else:
            st.info("강아지 정보를 가져오지 못했어요. (Dog CEO 네트워크 확인)")

    st.markdown("### 📝 리포트")
    if report:
        st.markdown(report)

        share_text = f"""AI 습관 트래커 리포트 ({date.today().isoformat()})
- 달성률: {rate}% ({done_count}/{total_habits})
- 기분: {mood}/10
- 도시: {city}
- 코치: {coach_style}

{report}
"""
        st.markdown("### 📣 공유용 텍스트")
        st.code(share_text, language="text")
    else:
        st.error("리포트 생성에 실패했어요. (OpenAI API Key/모델/네트워크 확인)")


# -----------------------------
# 하단: API 안내 (expander)
# -----------------------------
with st.expander("🔎 API 안내 / 설정 팁"):
    st.markdown(
        """
- **OpenAI API Key**
  - OpenAI 플랫폼에서 발급한 키를 입력하세요.
  - 본 앱은 **Responses API** (`/v1/responses`)로 호출합니다.
  - 모델은 **gpt-5-mini**로 설정되어 있습니다.

- **OpenWeatherMap API Key**
  - OpenWeatherMap에서 키를 발급받은 뒤 입력하세요.
  - `lang=kr`, `units=metric`(섭씨)로 요청합니다.

- **Dog CEO API**
  - 별도 키 없이 사용합니다.
  - 네트워크/일시 장애 시 None을 반환하도록 되어 있어요.

- **ZenQuotes API**
  - 별도 키 없이 사용합니다.
  - 오늘의 명언을 가져옵니다.

- **NASA APOD API (선택)**
  - `NASA_API_KEY` 환경변수가 설정된 경우에만 이미지/설명을 표시합니다.

- **OpenLibrary API**
  - 별도 키 없이 사용합니다.
  - 오늘의 책 추천을 제공합니다.

- **보안 팁**
  - 배포 시에는 Streamlit Secrets 또는 서버 환경변수로 키를 주입하는 방식을 권장합니다.
"""
    )

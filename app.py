import streamlit as st
import time
import requests
from PIL import Image
import base64
import io
import json

# ------------------- 页面配置 -------------------
st.set_page_config(page_title="WardrobeAI - 智能衣橱", page_icon="👔", layout="wide")

# ------------------- 选项（全中文） -------------------
OPTIONS = {
    "user_type": ["通用", "潮男", "潮女", "绅士", "淑女", "宝宝", "妈妈", "孕期"],
    "fashion_style": ["经典", "极简轻奢", "街头", "复古", "小众独特", "洛丽塔", "国风", "休闲", "酷感"],
    "body_shape": ["标准", "偏瘦", "匀称", "高挑", "娇小"],
    "category": ["上装", "下装", "外套", "鞋子", "配饰"],
    "weather": ["晴天", "多云", "阴天", "下雨", "大风", "下雪"],
    "occasion": ["上班", "会议", "约会", "日常", "运动", "面试"],
    "fitness": ["低", "中", "高"],
}

# ------------------- 文案（全中文） -------------------
T = {
    "title": "👔 WardrobeAI — 你的 AI 衣橱与穿搭助手",
    "privacy_title": "🔐 隐私说明",
    "privacy_body": (
        "- 本演示将衣物暂存于服务器内存的当前会话中（刷新可能清空）\n"
        "- 不会读取聊天/联系人信息\n"
        "- 若开启 OpenAI 分析：会把你上传的衣物照片发送给 OpenAI 做识别（仅用于生成建议）"
    ),
    "profile": "👤 你的信息",
    "iam": "我属于",
    "style": "风格偏好",
    "shape": "身材类型",
    "add": "📸 添加到衣橱（拍照上传）",
    "item_name": "衣物名称",
    "item_name_ph": "白T、牛仔裤、外套…",
    "category": "类别",
    "color": "颜色",
    "color_ph": "黑、白、蓝…（可不填）",
    "upload": "上传照片",
    "save_btn": "✅ 上传并保存到衣橱",
    "need_name": "⚠️ 请先填写衣物名称",
    "need_photo": "⚠️ 请先选择一张照片",
    "added": "✅ 已加入衣橱",
    "wardrobe": "🧺 我的衣橱",
    "empty": "你的衣橱还是空的，先添加几件吧！",
    "check": "🧠 衣橱体检（规则占位）",
    "analyze": "🔍 分析我的衣橱（规则版）",
    "keep": "✅ 保留",
    "improve": "⚠️ 建议优化",
    "remove": "🗑 建议清理",
    "ai_title": "🧠 AI 衣物分析（OpenAI）",
    "ai_tip": "上传衣物照片并保存到衣橱后，点击按钮：自动识别并输出一段可直接阅读的中文建议文案。",
    "ai_need_key": "⚠️ 你还没在 Streamlit Secrets 里配置 OPENAI_API_KEY。",
    "ai_need_item": "⚠️ 请先上传并保存至少 1 件衣物，然后再做 AI 分析。",
    "ai_btn": "✨ 用 OpenAI 分析我的衣物（输出文案）",
    "ai_running": "正在分析中…",
    "ai_fail": "❌ OpenAI 分析失败（通常是 Key / 模型 / 参数格式问题）。",
    "outfit": "📅 今日穿搭（占位：后续从你的衣橱里挑）",
    "temp": "温度 (°C)",
    "weather": "天气",
    "occasion": "场合",
    "fitness": "活动强度",
    "clear": "🗑 清空本次会话数据",
    "gen": "✨ 生成穿搭",
    "regen": "🔄 换一套",
    "share": "📤 分享（占位）",
    "need_more": "⚠️ 请先至少添加 2 件衣物再生成穿搭",
    "outfit_title": "📌 穿搭方案（占位）",
    "score": "⭐ 评分：★★★★★",
    "footer": "© WardrobeAI · 轻量版 + OpenAI 衣物分析 · 衣橱 · 穿搭",
}

# ==================== OpenAI helpers ====================
def get_openai_key_and_model():
    api_key = None
    model = "gpt-4o-mini"
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        model = st.secrets.get("OPENAI_MODEL", model)
    except Exception:
        api_key = None
    return api_key, model

def pil_to_base64_jpeg(img: Image.Image, max_side=768, quality=85) -> str:
    # 控成本：控制图片边长
    w, h = img.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    buff = io.BytesIO()
    img.convert("RGB").save(buff, format="JPEG", quality=quality)
    return base64.b64encode(buff.getvalue()).decode("utf-8")

def extract_output_text_from_responses(data: dict) -> str | None:
    # responses output: output[] -> content[] -> output_text
    for out in data.get("output", []):
        for c in out.get("content", []):
            if c.get("type") == "output_text" and c.get("text"):
                return c["text"]
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    return None

def openai_analyze_items(images, meta_list, user_profile_text):
    api_key, model = get_openai_key_and_model()
    if not api_key:
        return None, "NO_KEY"

    # ✅ 输出目标：中文文案（不要 JSON / 不要代码块）
    content = []
    content.append({
        "type": "input_text",
        "text": (
            "你是专业穿搭顾问。请基于用户衣物照片与填写信息，输出一段中文分析文案，要求：\n"
            "1) 先给一句总体结论（1-2句）\n"
            "2) 然后按“单品分析”逐件写：名称/你判断的品类/颜色/风格/适合季节/适合场合/"
            "保留建议（保留或优化或清理）/原因/2-3条搭配建议\n"
            "3) 最后给“衣橱整体建议”3-6条\n"
            "4) 用清晰的小标题和项目符号，适合直接展示在网页里\n"
            "5) 语气：理性、清晰、像专业顾问写给用户的建议，不要太学术\n"
            "6) 不要输出 JSON，不要代码块，不要出现 ``` 这类格式\n"
            "只输出文案本身。"
        )
    })
    content.append({
        "type": "input_text",
        "text": f"用户资料：{user_profile_text}"
    })

    for idx, (img, meta) in enumerate(zip(images, meta_list), start=1):
        b64 = pil_to_base64_jpeg(img)
        data_url = f"data:image/jpeg;base64,{b64}"
        content.append({
            "type": "input_text",
            "text": f"衣物{idx}填写信息：{json.dumps(meta, ensure_ascii=False)}"
        })
        # ✅ 重点：image_url 用字符串（不是对象），避免 400 invalid_type
        content.append({
            "type": "input_image",
            "image_url": data_url
        })

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": content
            }
        ],
        "max_output_tokens": 900
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=90)
        if r.status_code >= 400:
            return None, f"HTTP_{r.status_code}: {r.text[:800]}"
        data = r.json()
        text = extract_output_text_from_responses(data)
        if not text:
            return None, "NO_OUTPUT_TEXT"
        return text, None
    except Exception as e:
        return None, str(e)

# ------------------- 标题 -------------------
st.title(T["title"])

# ==================== 会话存储 ====================
if "wardrobe" not in st.session_state:
    st.session_state["wardrobe"] = []

def add_cloth(img, name, ctype, color):
    st.session_state["wardrobe"].append({
        "img": img,
        "name": name,
        "type": ctype,
        "color": color,
        "status": "keep"
    })

def clear_all_data():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("✅ 已清空本次会话数据。")

# ==================== 隐私提示 ====================
st.info(f"**{T['privacy_title']}**\n\n{T['privacy_body']}")

# ==================== 个人信息 ====================
st.subheader(T["profile"])
col1, col2, col3 = st.columns(3)
with col1:
    user_type = st.selectbox(T["iam"], OPTIONS["user_type"])
with col2:
    fashion_style = st.selectbox(T["style"], OPTIONS["fashion_style"])
with col3:
    body_shape = st.selectbox(T["shape"], OPTIONS["body_shape"])

user_profile_text = f"user_type={user_type}, fashion_style={fashion_style}, body_shape={body_shape}"

# ==================== 添加衣物（点按钮才保存） ====================
st.subheader(T["add"])
ca1, ca2 = st.columns(2)
with ca1:
    cloth_name = st.text_input(T["item_name"], placeholder=T["item_name_ph"])
with ca2:
    cloth_type = st.selectbox(T["category"], OPTIONS["category"])
cloth_color = st.text_input(T["color"], placeholder=T["color_ph"])
uploaded = st.file_uploader(T["upload"], type=["jpg", "png", "jpeg"])

save_clicked = st.button(T["save_btn"])

if save_clicked:
    if not cloth_name.strip():
        st.warning(T["need_name"])
    elif uploaded is None:
        st.warning(T["need_photo"])
    else:
        img = Image.open(uploaded).convert("RGB").resize((600, 600))
        add_cloth(img, cloth_name.strip(), cloth_type, cloth_color.strip())
        st.success(T["added"])

# ==================== 我的衣橱 ====================
st.subheader(T["wardrobe"])
wardrobe = st.session_state["wardrobe"]
if wardrobe:
    cols = st.columns(4)
    for idx, item in enumerate(wardrobe):
        with cols[idx % 4]:
            st.image(item["img"], use_container_width=True)
            st.markdown(f"**{item['name']}**")
            st.caption(f"{item['type']} | {item['color'] if item['color'] else '颜色未填'}")
else:
    st.info(T["empty"])

# ==================== 衣橱体检（规则占位） ====================
st.subheader(T["check"])
if st.button(T["analyze"]):
    total = len(wardrobe)
    st.success(f"{T['keep']}: {max(0, total-3)}")
    st.warning(f"{T['improve']}: 1")
    st.error(f"{T['remove']}: 2")
    st.caption("（这是规则占位输出：下一步可替换为更真实的规则/AI。）")

# ==================== OpenAI 衣物分析（输出文案） ====================
st.subheader(T["ai_title"])
st.caption(T["ai_tip"])

api_key, model_name = get_openai_key_and_model()
if not api_key:
    st.warning(T["ai_need_key"])
else:
    st.caption(f"当前模型：{model_name}")

ai_btn = st.button(T["ai_btn"], type="primary")

if ai_btn:
    if not api_key:
        st.warning(T["ai_need_key"])
    elif len(wardrobe) < 1:
        st.warning(T["ai_need_item"])
    else:
        with st.spinner(T["ai_running"]):
            # 控成本：最多分析前 6 件
            images = [w["img"] for w in wardrobe[:6]]
            metas = [{"name": w["name"], "type": w["type"], "color": w["color"]} for w in wardrobe[:6]]
            text, err = openai_analyze_items(images, metas, user_profile_text)

        if err:
            st.error(T["ai_fail"])
            st.code(str(err))
        else:
            st.success("✅ 分析完成")
            st.markdown(text)

# ==================== 今日穿搭（占位） ====================
st.subheader(T["outfit"])
cb1, cb2 = st.columns(2)
with cb1:
    temp = st.slider(T["temp"], -10, 40, 22)
    weather = st.selectbox(T["weather"], OPTIONS["weather"])
with cb2:
    occasion = st.selectbox(T["occasion"], OPTIONS["occasion"])
    fitness = st.selectbox(T["fitness"], OPTIONS["fitness"])

cc1, cc2, cc3, cc4 = st.columns(4)
with cc1:
    if st.button(T["clear"]):
        clear_all_data()
with cc2:
    gen = st.button(T["gen"])
with cc3:
    regenerate = st.button(T["regen"])
with cc4:
    st.button(T["share"])

if gen or regenerate:
    if len(wardrobe) < 2:
        st.warning(T["need_more"])
    else:
        st.success(T["outfit_title"])
        st.write(f"天气：{weather} | 温度：{temp}°C | 场合：{occasion} | 强度：{fitness}")

        st.markdown("### 👕 上装：从衣橱挑一件（占位）")
        st.markdown("### 👖 下装：从衣橱挑一件（占位）")
        st.markdown("### 👟 鞋子：从衣橱挑一双（占位）")
        st.markdown("### ✨ 风格：日常简洁（占位）")
        st.subheader(T["score"])

st.markdown("---")
st.caption(T["footer"])

import streamlit as st
import time
import hashlib
import requests
from PIL import Image
from urllib.parse import urlencode
import base64
import io
import json

# ------------------- Page Config -------------------
st.set_page_config(page_title="WardrobeAI - 衣橱穿搭助手", page_icon="👔", layout="wide")

# ==================== 语言选择 ====================
lang = st.sidebar.selectbox("语言 / Language", ["中文", "English"], index=0)

# ==================== 选项（中英文两套） ====================
OPTIONS = {
    "中文": {
        "user_type": ["通用", "潮男", "潮女", "绅士", "淑女", "宝宝", "妈妈", "孕期"],
        "fashion_style": ["经典", "极简轻奢", "街头", "复古", "小众独特", "洛丽塔", "国风", "休闲", "酷感"],
        "body_shape": ["标准", "偏瘦", "匀称", "高挑", "娇小"],
        "category": ["上装", "下装", "外套", "鞋子", "配饰"],
        "weather": ["晴天", "多云", "阴天", "下雨", "大风", "下雪"],
        "occasion": ["上班", "会议", "约会", "日常", "运动", "面试"],
        "fitness": ["低", "中", "高"],
    },
    "English": {
        "user_type": ["General", "Trendy Man", "Trendy Woman", "Gentleman", "Lady", "Baby", "Mom", "Pregnancy"],
        "fashion_style": ["Classic", "Minimal Luxury", "Street", "Vintage", "Unique", "Lolita", "Chinese Style", "Casual", "Cool"],
        "body_shape": ["Standard", "Slim", "Medium", "Tall", "Petite"],
        "category": ["Top", "Bottom", "Outerwear", "Shoes", "Accessory"],
        "weather": ["Sunny", "Cloudy", "Overcast", "Rain", "Wind", "Snow"],
        "occasion": ["Work", "Meeting", "Date", "Casual", "Sports", "Interview"],
        "fitness": ["Low", "Medium", "High"],
    }
}[lang]

# ==================== 文案 ====================
T = {
    "中文": {
        "title": "👔 WardrobeAI — 你的 AI 衣橱与穿搭助手",
        "privacy_title": "🔐 隐私说明",
        "privacy_body": "- 本演示将衣物暂存于服务器内存的当前会话中\n- 刷新页面可能会清空数据\n- 不会读取聊天/联系人信息\n- 若开启 OpenAI 分析：会把你上传的衣物照片发送给 OpenAI 做识别（仅用于生成建议）",
        "profile": "👤 你的信息",
        "iam": "我属于",
        "style": "风格偏好",
        "shape": "身材类型",
        "add": "📸 添加到衣橱（拍照上传）",
        "item_name": "衣物名称",
        "item_name_ph": "白T、牛仔裤、外套…",
        "category": "类别",
        "color": "颜色",
        "color_ph": "黑、白、蓝…",
        "upload": "上传照片",
        "save_btn": "✅ 上传并保存到衣橱",
        "need_name": "⚠️ 请先填写衣物名称",
        "need_photo": "⚠️ 请先选择一张照片",
        "added": "✅ 已加入衣橱",
        "wardrobe": "🧺 我的衣橱",
        "empty": "你的衣橱还是空的，先添加几件吧！",
        "check": "🧠 衣橱体检",
        "analyze": "🔍 分析我的衣橱（规则版）",
        "keep": "✅ 保留",
        "improve": "⚠️ 建议优化",
        "remove": "🗑 建议清理",
        "ai_title": "🧠 AI 衣物分析（OpenAI）",
        "ai_tip": "上传衣物照片后点击按钮，自动识别并给出搭配/保留建议。",
        "ai_need_key": "⚠️ 你还没在 Streamlit Secrets 里配置 OPENAI_API_KEY。",
        "ai_need_item": "⚠️ 请先上传并保存至少 1 件衣物，然后再做 AI 分析。",
        "ai_btn": "✨ 用 OpenAI 分析我的衣物",
        "ai_running": "正在分析中…",
        "ai_fail": "❌ OpenAI 分析失败（可能是 Key/模型/网络问题）。",
        "outfit": "📅 今日穿搭（优先使用你的衣橱）",
        "temp": "温度 (°C)",
        "weather": "天气",
        "occasion": "场合",
        "fitness": "活动强度",
        "clear": "🗑 清空本次会话数据",
        "gen": "✨ 生成穿搭",
        "regen": "🔄 换一套",
        "share": "📤 分享（占位）",
        "need_more": "⚠️ 请先至少添加 2 件衣物再生成穿搭",
        "outfit_title": "📌 穿搭方案（来自你的衣橱）",
        "score": "⭐ 评分：★★★★★",
        "full": "✅ 你的衣橱已经够用了，不需要再买！",
        "smart": "⚠️ 衣橱偏少，给你一些补齐建议（测试用）",
        "shop_title": "🧩 可选：联网商品推荐（测试模式）",
        "shop_toggle": "开启在线推荐（淘宝/京东/拼多多）",
        "shop_tip": "建议第一次部署先关闭。等你用 Secrets 配好密钥再打开。",
        "shop_off": "推荐已关闭（测试阶段）",
        "no_pdd": "拼多多暂无结果（检查密钥/签名/权限）",
        "no_tb": "淘宝暂无结果（检查密钥/签名/权限）",
        "no_jd": "京东暂无结果（检查密钥/签名/权限）",
        "footer": "© WardrobeAI · 轻量版 + OpenAI 衣物分析 · 衣橱 · 穿搭 · 推荐",
    },
    "English": {
        "title": "👔 WardrobeAI — Your AI Personal Wardrobe & Outfit Assistant",
        "privacy_title": "🔐 PRIVACY NOTE",
        "privacy_body": "- This demo stores items in the current server session memory\n- Refreshing may clear data\n- No chat/contact access\n- If OpenAI analysis is enabled: your uploaded clothing images will be sent to OpenAI for suggestions.",
        "profile": "👤 Your Profile",
        "iam": "I am",
        "style": "Style",
        "shape": "Body Shape",
        "add": "📸 Add to Wardrobe — Upload & Save",
        "item_name": "Item Name",
        "item_name_ph": "White T-shirt, Jeans…",
        "category": "Category",
        "color": "Color",
        "color_ph": "Black, White, Blue…",
        "upload": "Upload photo",
        "save_btn": "✅ Upload & Save to Wardrobe",
        "need_name": "⚠️ Please enter item name first.",
        "need_photo": "⚠️ Please choose a photo first.",
        "added": "✅ Added to your Wardrobe",
        "wardrobe": "🧺 My Wardrobe",
        "empty": "Your wardrobe is empty. Start adding items!",
        "check": "🧠 Wardrobe Health Check",
        "analyze": "🔍 Analyze My Wardrobe (rules)",
        "keep": "✅ Keep",
        "improve": "⚠️ Improve",
        "remove": "🗑 Remove",
        "ai_title": "🧠 AI Clothing Analysis (OpenAI)",
        "ai_tip": "Upload clothing photos and click the button for suggestions.",
        "ai_need_key": "⚠️ OPENAI_API_KEY is not set in Streamlit Secrets.",
        "ai_need_item": "⚠️ Please add at least 1 item first.",
        "ai_btn": "✨ Analyze my items with OpenAI",
        "ai_running": "Analyzing…",
        "ai_fail": "❌ OpenAI request failed (key/model/network).",
        "outfit": "📅 Today's Outfit — From YOUR wardrobe",
        "temp": "Temperature (°C)",
        "weather": "Weather",
        "occasion": "Occasion",
        "fitness": "Fitness Level",
        "clear": "🗑 Clear session data",
        "gen": "✨ Generate Outfit",
        "regen": "🔄 Try Another",
        "share": "📤 Share (placeholder)",
        "need_more": "⚠️ Please add at least 2 items first.",
        "outfit_title": "📌 OUTFIT — from YOUR Wardrobe",
        "score": "⭐ Outfit Score: ★★★★★",
        "full": "✅ Your wardrobe is full — no need to buy!",
        "smart": "⚠️ Wardrobe is small — some suggestions (test)",
        "shop_title": "🧩 Optional: Shopping Recommendations (Test Mode)",
        "shop_toggle": "Enable online shopping recommendations (Taobao/JD/PDD)",
        "shop_tip": "Keep OFF for first deployment. Turn ON after you set keys via Secrets.",
        "shop_off": "Shopping recommendations are OFF (test mode).",
        "no_pdd": "No PDD result (check keys/signature).",
        "no_tb": "No Taobao result (check keys/signature).",
        "no_jd": "No JD result (check keys/signature).",
        "footer": "© WardrobeAI · Lite + OpenAI clothing analysis",
    }
}[lang]

# ==================== OpenAI helpers ====================
def get_openai_key_and_model():
    api_key = None
    model = "gpt-4o-mini"
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        model = st.secrets.get("OPENAI_MODEL", model)
    except Exception:
        # local run without secrets
        api_key = None
    return api_key, model

def pil_to_base64_jpeg(img: Image.Image, max_side=768, quality=85) -> str:
    # resize to control cost
    w, h = img.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    buff = io.BytesIO()
    img.convert("RGB").save(buff, format="JPEG", quality=quality)
    return base64.b64encode(buff.getvalue()).decode("utf-8")

def openai_analyze_items(images, meta_list, user_profile_text):
    """
    images: list[PIL.Image]
    meta_list: list[dict] same length, contains name/type/color
    """
    api_key, model = get_openai_key_and_model()
    if not api_key:
        return None, "NO_KEY"

    # Build vision inputs (OpenAI Responses API style)
    # We keep it resilient: if model doesn't support vision, it will error; we catch upstream.
    content = []
    # instruction block
    content.append({
        "type": "text",
        "text": (
            "你是专业穿搭顾问。请基于用户衣物照片与填写信息，输出一个 JSON，字段如下：\n"
            "items: [{name, predicted_type, predicted_color, style_tags(数组), season(数组), occasions(数组), keep_decision(keep/improve/remove), reason}]\n"
            "wardrobe_advice: 3-6条整体建议（中文）\n"
            "notes: 若图片不清晰请说明。\n"
            "要求：只输出 JSON，不要输出多余文本。"
        )
    })
    # user profile
    content.append({
        "type": "text",
        "text": f"用户资料：{user_profile_text}"
    })

    for idx, (img, meta) in enumerate(zip(images, meta_list), start=1):
        b64 = pil_to_base64_jpeg(img)
        content.append({
            "type": "text",
            "text": f"衣物{idx}填写信息：{json.dumps(meta, ensure_ascii=False)}"
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": content
            }
        ],
        "max_output_tokens": 800
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Try Responses API first
    try:
        r = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=60)
        if r.status_code >= 400:
            return None, f"HTTP_{r.status_code}: {r.text[:200]}"
        data = r.json()
        # Extract text output
        # Responses API returns "output" array; we try common paths
        text = None
        for out in data.get("output", []):
            for c in out.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    text = c.get("text")
                    if text:
                        break
            if text:
                break
        if not text:
            # fallback: sometimes it is at data["output_text"]
            text = data.get("output_text")
        return text, None
    except Exception as e:
        return None, str(e)

# ------------------- Title -------------------
st.title(T["title"])

# ==================== 联盟配置（试跑阶段不启用：先保持空） ====================
TAOBAO_APP_KEY = ""
TAOBAO_APP_SECRET = ""
TAOBAO_ADZONE_ID = ""
JD_APP_KEY = ""
JD_APP_SECRET = ""
PDD_CLIENT_ID = ""
PDD_CLIENT_SECRET = ""
PDD_PID = ""

# ==================== 三平台商品搜索函数（保持原样，不影响 OpenAI 分析） ====================
def taobao_search(keyword="女装", price_min=150, price_max=300):
    try:
        if not (TAOBAO_APP_KEY and TAOBAO_APP_SECRET and TAOBAO_ADZONE_ID):
            return []
        params = {
            "method": "taobao.tbk.item.search",
            "app_key": TAOBAO_APP_KEY,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "2.0",
            "sign_method": "md5",
            "keyword": keyword,
            "page_size": 1,
            "adzone_id": TAOBAO_ADZONE_ID,
            "start_price": str(price_min),
            "end_price": str(price_max),
        }
        sign_str = TAOBAO_APP_SECRET + "".join([k + str(v) for k, v in sorted(params.items())]) + TAOBAO_APP_SECRET
        params["sign"] = hashlib.md5(sign_str.encode()).hexdigest().upper()
        res = requests.get("https://eco.taobao.com/router/rest?" + urlencode(params), timeout=5).json()
        return res.get("tbk_item_search_response", {}).get("results", {}).get("n_tbk_item", [])
    except Exception:
        return []

def jd_search(keyword="女装", price_min=300):
    try:
        if not (JD_APP_KEY and JD_APP_SECRET):
            return []
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        params = {
            "method": "jd.union.open.goods.query",
            "app_key": JD_APP_KEY,
            "timestamp": t,
            "format": "json",
            "v": "1.0",
            "sign_method": "md5",
            "param_json": '{"keyword":"%s","priceFrom":%s,"pageSize":1,"owner":"1"}' % (keyword, price_min),
        }
        s = JD_APP_SECRET + "".join(f"{k}{v}" for k, v in sorted(params.items())) + JD_APP_SECRET
        params["sign"] = hashlib.md5(s.encode()).hexdigest().upper()
        res = requests.get("https://api.jd.com/routerjson?" + urlencode(params), timeout=5).json()
        block = res.get("jd_union_open_goods_query_response", {}).get("result", {})
        if isinstance(block, str):
            import json as _json
            block = _json.loads(block)
        return (block or {}).get("data", [])
    except Exception:
        return []

def pdd_search(keyword="女装", price_max=150):
    try:
        if not (PDD_CLIENT_ID and PDD_CLIENT_SECRET):
            return []
        data = {
            "type": "pdd.ddk.goods.search",
            "client_id": PDD_CLIENT_ID,
            "timestamp": int(time.time()),
            "keyword": keyword,
            "min_price": 0,
            "max_price": int(price_max * 100),
            "limit": 1,
        }
        sign_str = PDD_CLIENT_SECRET + "".join(f"{k}{v}" for k, v in sorted(data.items())) + PDD_CLIENT_SECRET
        data["sign"] = hashlib.md5(sign_str.encode()).hexdigest().upper()
        res = requests.post("https://gw-api.pinduoduo.com/api/router", data=data, timeout=5).json()
        return res.get("goods_search_response", {}).get("goods_list", [])
    except Exception:
        return []

# ==================== 会话存储 ====================
if "wardrobe" not in st.session_state:
    st.session_state["wardrobe"] = []

def add_cloth(img, name, ctype, color):
    st.session_state["wardrobe"].append({"img": img, "name": name, "type": ctype, "color": color, "status": "keep"})

def clear_all_data():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("✅ Cleared.")

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
            st.caption(f"{item['type']} | {item['color']}")
else:
    st.info(T["empty"])

# ==================== 衣橱诊断（规则版：占位） ====================
st.subheader(T["check"])
if st.button(T["analyze"]):
    total = len(wardrobe)
    st.success(f"{T['keep']}: {max(0, total-3)}")
    st.warning(f"{T['improve']}: 1")
    st.error(f"{T['remove']}: 2")
    st.caption("（这是规则占位输出，下一步可替换为真实规则/AI。）")

# ==================== OpenAI 衣物分析 ====================
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
            images = [w["img"] for w in wardrobe[:6]]  # 最多取前6件，防止太贵
            metas = [{"name": w["name"], "type": w["type"], "color": w["color"]} for w in wardrobe[:6]]
            text, err = openai_analyze_items(images, metas, user_profile_text)
        if err:
            st.error(T["ai_fail"])
            st.code(str(err))
        else:
            # 尝试把输出解析成 JSON 并展示
            try:
                data = json.loads(text)
                st.success("✅ 分析完成")
                st.markdown("### 单品建议")
                for it in data.get("items", []):
                    with st.expander(f"{it.get('name','未命名')} · {it.get('keep_decision','')}", expanded=True):
                        st.write({
                            "predicted_type": it.get("predicted_type"),
                            "predicted_color": it.get("predicted_color"),
                            "style_tags": it.get("style_tags"),
                            "season": it.get("season"),
                            "occasions": it.get("occasions"),
                            "keep_decision": it.get("keep_decision"),
                            "reason": it.get("reason"),
                        })
                st.markdown("### 衣橱整体建议")
                for s in data.get("wardrobe_advice", []):
                    st.write(f"- {s}")
                if data.get("notes"):
                    st.info(f"备注：{data.get('notes')}")
            except Exception:
                # 如果模型没严格输出 JSON，就直接原文展示
                st.warning("模型输出不是标准 JSON，我先原样展示（我也可以把提示词调得更严）。")
                st.text(text)

# ==================== 穿搭生成（保留原占位逻辑） ====================
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

st.markdown(f"### {T['shop_title']}")
enable_shop = st.toggle(T["shop_toggle"], value=False)
st.caption(T["shop_tip"])

if gen or regenerate:
    if len(wardrobe) < 2:
        st.warning(T["need_more"])
    else:
        st.success(T["outfit_title"])
        st.write(f"🌡 {weather} | {temp}°C | 📅 {occasion}")

        st.markdown("### 👕 Top: Simple Top")
        st.markdown("### 👖 Bottom: Jeans / Casual Pants")
        st.markdown("### 👞 Shoes: Sneakers")
        st.markdown("### ✨ Style: Daily Casual")
        st.subheader(T["score"])

        if len(wardrobe) >= 3:
            st.success(T["full"])
        else:
            st.warning(T["smart"])
            keyword = "基础百搭上衣"

            if enable_shop:
                st.subheader("💰 Pinduoduo / 拼多多")
                pdd = pdd_search(keyword, 150)
                st.write(pdd[0].get("goods_name", "")[:20] + "...") if pdd else st.write(T["no_pdd"])

                st.subheader("🛍 Taobao / 淘宝")
                tb = taobao_search(keyword, 150, 300)
                st.write(tb[0].get("title", "")[:20] + "...") if tb else st.write(T["no_tb"])

                st.subheader("✨ JD / 京东")
                jd = jd_search(keyword, 300)
                st.write(jd[0].get("skuName", "")[:20] + "...") if jd else st.write(T["no_jd"])
            else:
                st.info(T["shop_off"])

st.markdown("---")
st.caption(T["footer"])

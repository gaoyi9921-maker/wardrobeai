import streamlit as st
import time
import hashlib
import requests
from PIL import Image
from urllib.parse import urlencode

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
        "privacy_body": "- 本演示将衣物暂存于服务器内存的当前会话中\n- 刷新页面可能会清空数据\n- 不会读取聊天/联系人信息",
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
        "analyze": "🔍 分析我的衣橱",
        "keep": "✅ 保留",
        "improve": "⚠️ 建议优化",
        "remove": "🗑 建议清理",
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
        "footer": "© WardrobeAI · 测试部署版 · 衣橱 · 穿搭 · 推荐",
    },
    "English": {
        "title": "👔 WardrobeAI — Your AI Personal Wardrobe & Outfit Assistant",
        "privacy_title": "🔐 PRIVACY NOTE",
        "privacy_body": "- This demo stores items in the current server session memory\n- Refreshing may clear data\n- No chat or contact access",
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
        "analyze": "🔍 Analyze My Wardrobe",
        "keep": "✅ Keep",
        "improve": "⚠️ Improve",
        "remove": "🗑 Remove",
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
        "footer": "© WardrobeAI · Test Deployment Version · Wardrobe · Outfit · Recommendation",
    }
}[lang]

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

# ==================== 三平台商品搜索函数（只有在开启开关且密钥齐全才调用） ====================
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
            import json
            block = json.loads(block)
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

# ==================== 添加衣物（加入按钮：点了才保存） ====================
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
        img = Image.open(uploaded).convert("RGB").resize((300, 300))
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

# ==================== 衣橱诊断 ====================
st.subheader(T["check"])
if st.button(T["analyze"]):
    total = len(wardrobe)
    st.success(f"{T['keep']}: {max(0, total-3)}")
    st.warning(f"{T['improve']}: 1")
    st.error(f"{T['remove']}: 2")

# ==================== 穿搭生成 ====================
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

        # 这里后续我们可以改成真正从衣橱里挑选上装/下装/鞋子
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

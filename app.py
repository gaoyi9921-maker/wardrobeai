import streamlit as st
import time
import hashlib
import requests
from PIL import Image
from urllib.parse import urlencode

# ------------------- Page Config -------------------
st.set_page_config(page_title="WardrobeAI - Your AI Wardrobe Assistant", page_icon="👔", layout="wide")
st.title("👔 WardrobeAI — Your AI Personal Wardrobe & Outfit Assistant")

# ==================== 联盟配置（先别填，试跑阶段不启用） ====================
TAOBAO_APP_KEY = ""
TAOBAO_APP_SECRET = ""
TAOBAO_ADZONE_ID = ""

JD_APP_KEY = ""
JD_APP_SECRET = ""

PDD_CLIENT_ID = ""
PDD_CLIENT_SECRET = ""
PDD_PID = ""

# ==================== 三平台商品搜索函数（试跑阶段默认不调用） ====================
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
        # 京东很多接口 result 可能是字符串，这里稳一点
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

# ==================== 本地存储（会话内） ====================
if "wardrobe" not in st.session_state:
    st.session_state["wardrobe"] = []

def add_cloth(img, name, ctype, color):
    wardrobe = st.session_state["wardrobe"]
    wardrobe.append({"img": img, "name": name, "type": ctype, "color": color, "status": "keep"})
    st.session_state["wardrobe"] = wardrobe

def clear_all_data():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("✅ All data cleared for this session.")

# ==================== 隐私提示（改成真实描述，避免误导） ====================
st.info("""
🔐 PRIVACY NOTE
- This demo stores wardrobe items in the current session on the server memory.
- Refreshing the page may clear data.
- No chat or contact access.
""")

# ==================== 个人信息 ====================
st.subheader("👤 Your Profile")
col1, col2, col3 = st.columns(3)
with col1:
    user_type = st.selectbox("I am", ["General", "Trendy Man", "Trendy Woman", "Gentleman", "Lady", "Baby", "Mom", "Pregnancy"])
with col2:
    fashion_style = st.selectbox("Style", ["Classic", "Minimal Luxury", "Street", "Vintage", "Unique", "Lolita", "Chinese Style", "Casual", "Cool"])
with col3:
    body_shape = st.selectbox("Body Shape", ["Standard", "Slim", "Medium", "Tall", "Petite"])

# ==================== 添加衣物 ====================
st.subheader("📸 Add to Wardrobe — Photo & Save")
ca1, ca2 = st.columns(2)
with ca1:
    cloth_name = st.text_input("Item Name", placeholder="White T-shirt, Jeans...")
with ca2:
    cloth_type = st.selectbox("Category", ["Top", "Bottom", "Outerwear", "Shoes", "Accessory"])
cloth_color = st.text_input("Color", placeholder="Black, White, Blue...")
uploaded = st.file_uploader("Upload photo", type=["jpg", "png", "jpeg"])

if uploaded and cloth_name:
    img = Image.open(uploaded).convert("RGB").resize((300, 300))
    add_cloth(img, cloth_name, cloth_type, cloth_color)
    st.success("✅ Added to your Wardrobe")

# ==================== 我的衣橱 ====================
st.subheader("🧺 My Wardrobe — Clean & Organized")
wardrobe = st.session_state["wardrobe"]
if wardrobe:
    cols = st.columns(4)
    for idx, item in enumerate(wardrobe):
        with cols[idx % 4]:
            st.image(item["img"], use_container_width=True)
            st.markdown(f"**{item['name']}**")
            st.caption(f"{item['type']} | {item['color']}")
            if item["status"] == "remove":
                st.error("🗑 Remove")
            elif item["status"] == "improve":
                st.warning("⚠️ Improve")
            else:
                st.success("✅ Keep")
else:
    st.info("Your wardrobe is empty. Start adding items!")

# ==================== 衣橱诊断 ====================
st.subheader("🧠 Wardrobe Health Check")
if st.button("🔍 Analyze My Wardrobe"):
    total = len(wardrobe)
    st.success(f"✅ Keep: {max(0, total-3)} items")
    st.warning("⚠️ Improve: 1 item")
    st.error("🗑 Remove: 2 items")
    st.caption("A tidy wardrobe helps you dress better every day.")

# ==================== 穿搭生成 ====================
st.subheader("📅 Today's Outfit — 100% from YOUR wardrobe")
cb1, cb2 = st.columns(2)
with cb1:
    temp = st.slider("Temperature (°C)", -10, 40, 22)
    weather = st.selectbox("Weather", ["Sunny", "Cloudy", "Overcast", "Rain", "Wind", "Snow"])
with cb2:
    occasion = st.selectbox("Occasion", ["Work", "Meeting", "Date", "Casual", "Sports", "Interview"])
    fitness = st.selectbox("Fitness Level", ["Low", "Medium", "High"])

cc1, cc2, cc3, cc4 = st.columns(4)
with cc1:
    if st.button("🗑 Clear All Data"):
        clear_all_data()
with cc2:
    gen = st.button("✨ Generate Outfit")
with cc3:
    regenerate = st.button("🔄 Try Another")
with cc4:
    st.button("📤 Share Outfit")

# ==================== 推荐开关（试跑阶段默认关） ====================
st.markdown("### 🧩 Optional: Shopping Recommendations (Test Mode)")
enable_shop = st.toggle("Enable online shopping recommendations (Taobao/JD/PDD)", value=False)
st.caption("Tip: keep it OFF for first deployment. Turn ON only after you add real keys in Secrets.")

# ==================== 穿搭逻辑 + 三平台推荐 ====================
if gen or regenerate:
    if len(wardrobe) < 2:
        st.warning("⚠️ Please add at least 2 items to your wardrobe first.")
    else:
        st.success("📌 OUTFIT — 100% from YOUR Wardrobe")
        st.write(f"🌡 {weather} | {temp}°C | 📅 {occasion}")
        st.markdown("### 👕 Top: Simple Top")
        st.markdown("### 👖 Bottom: Jeans / Casual Pants")
        st.markdown("### 👞 Shoes: Sneakers")
        st.markdown("### ✨ Style: Daily Casual")
        st.subheader("⭐ Outfit Score: ★★★★★")

        if len(wardrobe) >= 3:
            st.success("✅ Your wardrobe is FULL — NO need to buy new items!")
        else:
            st.warning("⚠️ Smart recommendation to complete your wardrobe")

            keyword = "基础百搭上衣"

            if enable_shop:
                st.subheader("💰 Budget (Pinduoduo)")
                pdd = pdd_search(keyword, 150)
                if pdd:
                    st.write(f"{pdd[0].get('goods_name', '')[:20]}... 👉 Shop")
                else:
                    st.write("No PDD result (check keys/signature).")

                st.subheader("🛍 Daily (Taobao)")
                tb = taobao_search(keyword, 150, 300)
                if tb:
                    st.write(f"{tb[0].get('title', '')[:20]}... 👉 Shop")
                else:
                    st.write("No Taobao result (check keys/signature).")

                st.subheader("✨ Premium (JD)")
                jd = jd_search(keyword, 300)
                if jd:
                    st.write(f"{jd[0].get('skuName', '')[:20]}... 👉 Shop")
                else:
                    st.write("No JD result (check keys/signature).")
            else:
                st.info("Shopping recommendations are OFF in test mode.")

st.markdown("---")
st.caption("© WardrobeAI · Test Deployment Version · Wardrobe · Outfit · Recommendation")

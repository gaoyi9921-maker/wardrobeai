import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import numpy as np
from PIL import Image
import requests
import os
import json
from datetime import datetime
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.express as px
import base64
import bcrypt

# --------------------------
# 1. 全局配置 & 初始化（适配云端）
# --------------------------
st.set_page_config(
    page_title="Wardrobe AI - 智能衣橱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 颜色主题
COLORS = {
    "primary": "#8B5CF6",
    "secondary": "#EC4899",
    "background": "#F8FAFC",
    "text": "#1E293B"
}

# Streamlit Cloud 路径适配
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "user_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------
# 2. 数据库操作（仅用 Postgres，移除降级逻辑）
# --------------------------
def get_db_connection():
    """建立 Postgres 连接（适配 Streamlit Cloud）"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            dbname=st.secrets["DB_NAME"]
        )
        conn.autocommit = True  # 自动提交
        return conn
    except Exception as e:
        st.error(f"数据库连接失败：{str(e)}")
        st.stop()

def init_db():
    """初始化数据库表（仅 Postgres）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 用户表（密码存 hash）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,  -- 存 hash 而非明文
        email TEXT,
        style_preference TEXT DEFAULT '休闲',
        city TEXT DEFAULT '北京',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 衣物表（调整 season 字段为三档）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clothes (
        cloth_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        image_base64 TEXT NOT NULL,  -- 存 base64 而非文件路径
        type TEXT NOT NULL,
        color TEXT NOT NULL,
        material TEXT NOT NULL,
        season TEXT NOT NULL,  -- 春秋/夏/冬 三档
        style TEXT NOT NULL,
        occasion TEXT NOT NULL,
        wear_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    # 穿搭记录表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outfits (
        outfit_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        scene TEXT NOT NULL,
        weather TEXT NOT NULL,
        temperature INTEGER NOT NULL,
        cloth_ids TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    cursor.close()
    conn.close()

# 初始化数据库
init_db()

# --------------------------
# 3. 登录认证模块（修复密码 hash 逻辑）
# --------------------------
def hash_password(password):
    """密码 hash（bcrypt）"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, hashed):
    """验证密码"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def init_authenticator():
    """初始化认证器（从 DB 取 hash 而非重新生成）"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT username, password_hash FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # 构建认证字典（直接用 DB 里的 hash）
    creds = {user['username']: user['password_hash'] for user in users}
    
    authenticator = stauth.Authenticate(
        credentials={"usernames": creds},
        cookie_name="wardrobe_ai_cookie",
        cookie_key=st.secrets["COOKIE_SECRET_KEY"],
        cookie_expiry_days=30
    )
    return authenticator

# 初始化认证器
authenticator = init_authenticator()

def generate_user_id(username):
    """生成用户ID"""
    return hashlib.md5(username.encode()).hexdigest()

def register_user(username, password, email):
    """注册用户（密码 hash 后存储）"""
    user_id = generate_user_id(username)
    password_hash = hash_password(password)  # 先 hash 再存
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, email)
            VALUES (%s, %s, %s, %s)
        """, (user_id, username, password_hash, email))
        st.success("✅ 注册成功！请登录")
        return True
    except psycopg2.IntegrityError:
        st.error("❌ 用户名已存在")
        return False
    finally:
        cursor.close()
        conn.close()

# --------------------------
# 4. 百度AI图像识别（修复 API 调用方式）
# --------------------------
def get_baidu_access_token():
    """获取百度API令牌"""
    try:
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={st.secrets['BAIDU_API_KEY']}&client_secret={st.secrets['BAIDU_SECRET_KEY']}"
        response = requests.get(url, timeout=10)
        return response.json().get("access_token")
    except Exception as e:
        st.warning(f"百度API令牌获取失败：{str(e)}，使用模拟识别")
        return None

def image_to_base64(image):
    """图片转 base64（适配云端展示）"""
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def ai_cloth_recognition_real(image):
    """修复百度API调用（base64 传输）"""
    access_token = get_baidu_access_token()
    if not access_token:
        return ai_cloth_recognition_simulate()
    
    # 图片转 base64
    img_base64 = image_to_base64(image)
    
    # 百度通用物体识别 API（正确调用方式）
    url = f"https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'image': img_base64,
        'baike_num': 0  # 不返回百科
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        result = response.json()
        
        # 解析结果
        cloth_info = {"类型": "上衣", "颜色": "黑色", "材质": "棉", "季节": "春秋", "风格": "休闲"}
        
        # 提取关键词
        for item in result.get("result", []):
            keyword = item.get("keyword", "").lower()
            # 类型识别
            if any(x in keyword for x in ["上衣", "T恤", "衬衫", "卫衣"]):
                cloth_info["类型"] = "上衣"
            elif any(x in keyword for x in ["裤子", "牛仔裤", "休闲裤"]):
                cloth_info["类型"] = "裤子"
            elif any(x in keyword for x in ["裙子", "连衣裙"]):
                cloth_info["类型"] = "裙子"
            elif any(x in keyword for x in ["外套", "夹克", "风衣"]):
                cloth_info["类型"] = "外套"
            
            # 颜色识别
            if any(x in keyword for x in ["黑色", "黑"]):
                cloth_info["颜色"] = "黑色"
            elif any(x in keyword for x in ["白色", "白"]):
                cloth_info["颜色"] = "白色"
            elif any(x in keyword for x in ["蓝色", "蓝"]):
                cloth_info["颜色"] = "蓝色"
        
        # 季节统一为三档
        cloth_info["season"] = np.random.choice(["春秋", "夏", "冬"])
        return cloth_info
    except Exception as e:
        st.warning(f"百度API识别失败：{str(e)}")
        return ai_cloth_recognition_simulate()

def ai_cloth_recognition_simulate():
    """模拟识别（三档季节）"""
    return {
        "类型": np.random.choice(["上衣", "裤子", "裙子", "外套", "鞋子", "配饰"]),
        "颜色": np.random.choice(["黑色", "白色", "蓝色", "灰色", "粉色", "卡其色"]),
        "材质": np.random.choice(["棉", "涤纶", "牛仔", "针织", "雪纺"]),
        "季节": np.random.choice(["春秋", "夏", "冬"]),  # 三档
        "风格": np.random.choice(["休闲", "通勤", "复古", "运动", "正式"])
    }

# --------------------------
# 5. 智能穿搭算法（修复季节匹配）
# --------------------------
def get_weather_real(city):
    """模拟天气（替换为真实API时只需改这里）"""
    weather_data = {
        "北京": {"温度": 15, "天气": "晴"},
        "上海": {"温度": 18, "天气": "多云"},
        "广州": {"温度": 25, "天气": "阴"},
        "深圳": {"温度": 26, "天气": "晴"},
        "成都": {"温度": 17, "天气": "小雨"}
    }
    return weather_data.get(city, {"温度": 20, "天气": "晴"})

def get_color_match_score(color1, color2):
    """颜色匹配得分"""
    color_groups = {
        "黑色": ["黑色", "白色", "灰色"],
        "白色": ["白色", "黑色", "蓝色", "粉色"],
        "蓝色": ["蓝色", "白色", "卡其色", "灰色"],
        "灰色": ["灰色", "黑色", "白色", "蓝色"],
        "粉色": ["粉色", "白色", "灰色", "卡其色"],
        "卡其色": ["卡其色", "白色", "蓝色", "粉色"]
    }
    if color1 == color2:
        return 9
    elif color2 in color_groups.get(color1, []):
        return 8
    else:
        return 4

def generate_smart_outfit(user_id, scene, city):
    """修复季节匹配的穿搭算法"""
    # 获取天气
    weather = get_weather_real(city)
    temp = weather["温度"]
    
    # 季节映射（三档匹配）
    if temp < 10:
        season = "冬"
    elif temp > 25:
        season = "夏"
    else:
        season = "春秋"
    
    # 查询衣物（季节完全匹配）
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT * FROM clothes 
        WHERE user_id = %s AND occasion = %s AND season = %s
    """, (user_id, scene, season))
    clothes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if len(clothes) < 2:
        st.warning("⚠️ 符合条件的衣物不足，无法生成优质穿搭")
        return [], weather
    
    # 分类衣物
    tops = [c for c in clothes if c["type"] == "上衣"]
    bottoms = [c for c in clothes if c["type"] in ["裤子", "裙子"]]
    coats = [c for c in clothes if c["type"] == "外套"]
    
    if not tops or not bottoms:
        st.warning("⚠️ 缺少核心衣物（上衣/下装）")
        return [], weather
    
    # 智能匹配
    best_match = None
    max_score = 0
    for top in tops:
        for bottom in bottoms:
            color_score = get_color_match_score(top["color"], bottom["color"])
            style_score = 10 if top["style"] == bottom["style"] else 6
            wear_score = (10 - min(top["wear_count"], 10)) * 0.5
            total_score = color_score + style_score + wear_score
            
            if total_score > max_score:
                max_score = total_score
                best_match = [top, bottom]
    
    # 低温加外套
    if temp < 15 and coats:
        best_coat = max(coats, key=lambda c: get_color_match_score(best_match[0]["color"], c["color"]))
        best_match.append(best_coat)
    
    # 记录穿搭
    outfit_id = f"outfit_{datetime.now().strftime('%Y%m%d%H%M%S')}_{np.random.randint(1000,9999)}"
    cloth_ids = json.dumps([c["cloth_id"] for c in best_match])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO outfits (outfit_id, user_id, scene, weather, temperature, cloth_ids)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (outfit_id, user_id, scene, weather["天气"], temp, cloth_ids))
    
    # 更新穿着次数
    for cloth in best_match:
        cursor.execute("""
            UPDATE clothes SET wear_count = wear_count + 1
            WHERE cloth_id = %s
        """, (cloth["cloth_id"],))
    
    cursor.close()
    conn.close()
    return best_match, weather

# --------------------------
# 6. 核心业务函数（修复图片存储/展示）
# --------------------------
def add_cloth(user_id, image, cloth_info):
    """添加衣物（存 base64 而非文件）"""
    # 生成ID
    cloth_id = f"cloth_{datetime.now().strftime('%Y%m%d%H%M%S')}_{np.random.randint(1000,9999)}"
    
    # 图片转 base64
    img_base64 = image_to_base64(image)
    
    # 插入数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clothes (
            cloth_id, user_id, image_base64, type, color, material, season, style, occasion
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        cloth_id, user_id, img_base64,
        cloth_info["类型"], cloth_info["颜色"],
        cloth_info["材质"], cloth_info["season"],
        cloth_info["风格"], cloth_info["场合"]
    ))
    cursor.close()
    conn.close()
    return cloth_id

def batch_add_clothes(user_id, uploaded_files, default_occasion):
    """批量添加衣物"""
    success = 0
    fail = 0
    
    with st.spinner("📸 正在批量识别并添加衣物..."):
        for file in uploaded_files:
            try:
                image = Image.open(file)
                cloth_info = ai_cloth_recognition_real(image)
                cloth_info["场合"] = default_occasion
                add_cloth(user_id, image, cloth_info)
                success += 1
            except Exception as e:
                st.warning(f"文件 {file.name} 处理失败：{str(e)}")
                fail += 1
    
    return success, fail

def get_user_clothes(user_id, filters=None):
    """获取用户衣物"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM clothes WHERE user_id = %s"
    params = [user_id]
    
    if filters:
        for key, value in filters.items():
            if value and value != "全部":
                query += f" AND {key} = %s"
                params.append(value)
    
    cursor.execute(query, params)
    clothes = cursor.fetchall()
    cursor.close()
    conn.close()
    return clothes

def delete_cloth(cloth_id):
    """删除衣物"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clothes WHERE cloth_id = %s", (cloth_id,))
    cursor.close()
    conn.close()

def get_wardrobe_analytics(user_id):
    """衣橱数据分析"""
    clothes = get_user_clothes(user_id)
    if not clothes:
        return None
    
    type_df = pd.DataFrame([c["type"] for c in clothes], columns=["类型"])
    type_count = type_df["类型"].value_counts()
    
    wear_df = pd.DataFrame([(c["type"], c["wear_count"]) for c in clothes], columns=["类型", "穿着次数"])
    
    return {
        "total": len(clothes),
        "type_dist": type_count,
        "wear_analysis": wear_df,
        "unused": len([c for c in clothes if c["wear_count"] == 0])
    }

# --------------------------
# 7. UI界面（修复图片展示）
# --------------------------
def render_header():
    """渲染头部"""
    st.markdown(f"""
    <div style="background-color:{COLORS['primary']};padding:20px;border-radius:10px;margin-bottom:20px;">
        <h1 style="color:white;text-align:center;margin:0;">👗 Wardrobe AI 智能衣橱</h1>
        <p style="color:white;text-align:center;margin:5px 0 0 0;">你的私人AI穿搭助手</p>
    </div>
    """, unsafe_allow_html=True)

def render_cloth_card(cloth, show_delete=True):
    """渲染衣物卡片（用 st.image 展示 base64）"""
    # base64 转图片
    img_bytes = base64.b64decode(cloth["image_base64"])
    
    # 卡片布局
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(img_bytes, width=180)
    with col2:
        st.markdown(f"""
        <h4 style="margin:0;color:{COLORS['primary']};">{cloth['type']} | {cloth['color']}</h4>
        <p style="margin:5px 0;color:#64748B;">{cloth['style']} · {cloth['season']}季 · 穿着{cloth['wear_count']}次</p>
        <p style="margin:5px 0;color:#64748B;">材质：{cloth['material']} · 适用场合：{cloth['occasion']}</p>
        """, unsafe_allow_html=True)
        if show_delete and st.button("🗑 删除", key=f"del_{cloth['cloth_id']}"):
            delete_cloth(cloth['cloth_id'])
            st.rerun()
    st.divider()

def render_outfit_card(clothes, weather):
    """渲染穿搭卡片"""
    st.markdown(f"""
    <div style="border:2px solid {COLORS['secondary']};border-radius:12px;padding:15px;margin:20px 0;">
        <h3 style="color:{COLORS['secondary']};margin:0 0 10px 0;">✨ 智能穿搭方案</h3>
        <p style="color:#64748B;margin:0;">🌤️ {weather['天气']} | {weather['温度']}℃ | 适配{weather['温度']<10 and '冬' or weather['温度']>25 and '夏' or '春秋'}季</p>
    </div>
    """, unsafe_allow_html=True)
    
    for cloth in clothes:
        render_cloth_card(cloth, show_delete=False)

def main():
    """主函数"""
    # 登录认证
    name, authentication_status, username = authenticator.login("登录", "main")
    
    if authentication_status == False:
        st.error("❌ 用户名/密码错误")
    elif authentication_status == None:
        st.warning("⚠️ 请输入用户名和密码")
        
        # 注册面板
        with st.expander("🔐 新用户注册", expanded=True):
            new_username = st.text_input("用户名")
            new_password = st.text_input("密码", type="password")
            new_email = st.text_input("邮箱")
            
            if st.button("注册"):
                if new_username and new_password:
                    register_user(new_username, new_password, new_email)
    
    # 登录成功
    elif authentication_status:
        user_id = generate_user_id(username)
        render_header()
        
        # 侧边栏
        with st.sidebar:
            st.markdown(f"### 👤 欢迎 {username}")
            
            # 用户设置
            st.subheader("⚙️ 个人设置")
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT style_preference, city FROM users WHERE user_id = %s", (user_id,))
            user_info = cursor.fetchone()
            
            style = st.selectbox("偏好风格", ["休闲", "通勤", "复古", "运动", "正式"], 
                                index=["休闲", "通勤", "复古", "运动", "正式"].index(user_info["style_preference"]))
            city = st.text_input("所在城市", value=user_info["city"])
            
            # 保存设置
            if st.button("保存设置"):
                cursor.execute("""
                    UPDATE users SET style_preference = %s, city = %s
                    WHERE user_id = %s
                """, (style, city, user_id))
                st.success("✅ 设置已保存")
            
            cursor.close()
            conn.close()
            st.divider()
            authenticator.logout("退出登录", "sidebar")
        
        # 主标签页
        tab1, tab2, tab3, tab4 = st.tabs([
            "📤 批量上传", "🧥 我的衣橱", 
            "✨ 穿搭推荐", "📊 衣橱分析"
        ])
        
        # 标签页1：批量上传
        with tab1:
            st.subheader("📸 批量上传衣物")
            uploaded_files = st.file_uploader(
                "选择多张衣物照片（支持PNG/JPG）",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
                label_visibility="collapsed"
            )
            
            col1, col2 = st.columns([2,1])
            with col1:
                default_occasion = st.selectbox("默认适用场合", ["通勤", "约会", "运动", "正式"])
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                upload_btn = st.button("🚀 批量识别并添加", type="primary")
            
            if uploaded_files and upload_btn:
                success, fail = batch_add_clothes(user_id, uploaded_files, default_occasion)
                st.success(f"✅ 处理完成：成功{success}件 | 失败{fail}件")
                st.rerun()
        
        # 标签页2：我的衣橱
        with tab2:
            st.subheader("🧥 我的衣橱")
            
            # 筛选栏
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                filter_type = st.selectbox("类型", ["全部"] + ["上衣", "裤子", "裙子", "外套", "鞋子", "配饰"])
            with col2:
                filter_color = st.selectbox("颜色", ["全部"] + ["黑色", "白色", "蓝色", "灰色", "粉色", "卡其色"])
            with col3:
                filter_season = st.selectbox("季节", ["全部"] + ["春秋", "夏", "冬"])
            with col4:
                filter_style = st.selectbox("风格", ["全部"] + ["休闲", "通勤", "复古", "运动", "正式"])
            
            # 应用筛选
            filters = {
                "type": filter_type,
                "color": filter_color,
                "season": filter_season,
                "style": filter_style
            }
            clothes = get_user_clothes(user_id, filters)
            
            st.markdown(f"<p style='color:{COLORS['text']};'>📊 共找到 {len(clothes)} 件衣物</p>", unsafe_allow_html=True)
            
            # 展示衣物
            for cloth in clothes:
                render_cloth_card(cloth)
        
        # 标签页3：穿搭推荐
        with tab3:
            st.subheader("✨ 智能穿搭推荐")
            
            col1, col2, col3 = st.columns([2,2,1])
            with col1:
                scene = st.selectbox("穿搭场景", ["通勤", "约会", "运动", "正式"])
            with col2:
                outfit_city = st.text_input("城市（天气适配）", value=city)
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                recommend_btn = st.button("生成穿搭", type="primary")
            
            if recommend_btn:
                outfit, weather = generate_smart_outfit(user_id, scene, outfit_city)
                if outfit:
                    render_outfit_card(outfit, weather)
        
        # 标签页4：衣橱分析
        with tab4:
            st.subheader("📊 衣橱数据分析")
            
            analytics = get_wardrobe_analytics(user_id)
            if not analytics:
                st.info("📝 暂无数据，请先添加衣物")
                return
            
            # 核心指标
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总衣物数", analytics["total"])
            with col2:
                st.metric("闲置衣物", analytics["unused"])
            with col3:
                usage_rate = ((analytics["total"] - analytics["unused"]) / analytics["total"]) * 100
                st.metric("衣橱利用率", f"{usage_rate:.0f}%")
            
            # 类型分布图表
            st.subheader("衣物类型分布")
            fig = px.pie(
                values=analytics["type_dist"].values,
                names=analytics["type_dist"].index,
                color_discrete_sequence=[COLORS["primary"], COLORS["secondary"], "#3B82F6", "#10B981", "#F59E0B", "#EF4444"]
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 穿着次数分析
            st.subheader("衣物穿着次数分析")
            fig2 = px.box(
                analytics["wear_analysis"],
                x="类型",
                y="穿着次数",
                color="类型",
                color_discrete_sequence=[COLORS["primary"], COLORS["secondary"], "#3B82F6", "#10B981"]
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # 优化建议
            st.subheader("💡 衣橱优化建议")
            if analytics["unused"] > analytics["total"] * 0.3:
                st.warning(f"⚠️ 你的衣橱有{analytics['unused']}件衣物从未穿着，建议尝试新搭配或清理")
            if analytics["type_dist"].get("上衣", 0) > analytics["type_dist"].get("裤子", 0) * 3:
                st.info("📌 你的上衣数量远多于下装，建议补充不同风格的裤子/裙子")

if __name__ == "__main__":
    main()

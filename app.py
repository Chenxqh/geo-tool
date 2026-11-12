import streamlit as st
from openai import OpenAI
import pandas as pd
import re
from urllib.parse import urlparse
import io

st.set_page_config(page_title="GEO 监测工具 V4.0", page_icon="📊")
st.title("📊 AI 引用信源监测系统")
st.markdown("输入品牌词，一键获取 AI 的推荐信源分布报告。")

# 初始化 session_state（记忆盒子）
if "data_records" not in st.session_state:
    st.session_state.data_records = []
if "all_domains" not in st.session_state:
    st.session_state.all_domains = []
if "has_data" not in st.session_state:
    st.session_state.has_data = False

with st.sidebar:
    st.header("🔑 配置")
    api_key = st.text_input("请输入 DeepSeek API Key", type="password")
    st.markdown("---")
    st.markdown("💡 **使用说明：**\n1. 填入API Key\n2. 设定品牌名\n3. 点击开始监测")

brand = st.text_input("你想监测的品牌名 (例如：索尼)", "索尼")
default_questions = "请推荐2款适合计算机专业大学生的降噪耳机，请务必附带参考链接。\n深圳南山区有哪些适合周末自习的咖啡馆？请给出参考网页链接。"
questions_input = st.text_area("要问 AI 的问题 (每行一个)", default_questions, height=100)

# 点击开始监测
if st.button("🚀 开始监测"):
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        questions = [q.strip() for q in questions_input.split("\n") if q.strip()]
        
        # 临时变量
        temp_data = []
        temp_domains = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, q in enumerate(questions):
            status_text.text(f"正在向 AI 提问 ({i+1}/{len(questions)}): {q}")
            
            # 加了强制要求链接的 system prompt
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个严谨的搜索推荐引擎。在回答的最后，必须用列表形式提供真实的参考网址链接（以 http 开头），严禁编造。"},
                    {"role": "user", "content": q}
                ]
            )
            answer = response.choices[0].message.content
            
            brand_mentioned = "是" if brand in answer else "否"
            
            urls = re.findall(r'https?://[^\s\)\]]+', answer)
            domains = []
            for url in urls:
                try:
                    domain = urlparse(url).netloc
                    if domain.startswith("www."):
                        domain = domain[4:]
                    domains.append(domain)
                    temp_domains.append(domain)
                except:
                    pass
            
            temp_data.append({
                "问题": q,
                "是否提及品牌": brand_mentioned,
                "提取的域名": " | ".join(set(domains)) if domains else "无"
            })
            
            progress_bar.progress((i + 1) / len(questions))
            
        status_text.text("✅ 数据抓取完成！")
        
        # 将数据存入“记忆盒子”
        st.session_state.data_records = temp_data
        st.session_state.all_domains = temp_domains
        st.session_state.has_data = True

# ==========================================
# 以下代码在按钮外部，只要记忆盒子里有数据，就会一直渲染
# ==========================================
if st.session_state.has_data:
    st.subheader("📋 监测报告数据")
    df = pd.DataFrame(st.session_state.data_records)
    st.dataframe(df, use_container_width=True)
    
    # 下载按钮
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='GEO数据')
    
    st.download_button(
        label="📥 下载 Excel 数据报告",
        data=buffer.getvalue(),
        file_name="GEO监测报告.xlsx",
        mime="application/vnd.ms-excel"
    )
    
    # 展示图表
    if st.session_state.all_domains:
        st.subheader("📈 信源域名分布图")
        domain_counts = pd.Series(st.session_state.all_domains).value_counts()
        st.bar_chart(domain_counts)
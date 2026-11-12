import streamlit as st
from openai import OpenAI
import pandas as pd
import re
from urllib.parse import urlparse
import io

# 1. 页面配置与美化
st.set_page_config(page_title="GEO 商业监测平台", page_icon="📊", layout="wide")
st.title("📊 GEO 商业级信源监测系统")
st.markdown("输入竞品，一键获取 AI 的推荐信源、品牌提及率与商业诊断报告。")

# 2. 状态管理（防止下载刷新丢失数据）
if "report_data" not in st.session_state:
    st.session_state.report_data = None

# 3. 侧边栏配置
with st.sidebar:
    st.header("🔑 API 配置")
    api_key = st.text_input("DeepSeek API Key", type="password")
    st.markdown("---")
    st.markdown("💡 **V5.0 升级点：**\n- 新增品牌情感倾向判断\n- 自动生成商业诊断结论\n- 支持多维度数据展示")
    
    # 新增：让用户可以自定义竞品词
    target_brand = st.text_input("目标品牌 (如：小晓标书)", "小晓标书")
    competitor_brand = st.text_input("核心竞品 (如：广联达)", "广联达")

# 4. 主输入区
default_questions = "我是做建筑工程的小企业老板，最近准备参与一个市政项目的投标，请问市面上有哪些好用的“AI标书生成软件”推荐？最好能自动检查废标项。请务必列出它们官网或权威评测文章的链接。"
questions_input = st.text_area("要问 AI 的问题 (每行一个)", default_questions, height=120)

# 5. 核心执行逻辑
if st.button("🚀 开始智能监测", type="primary"):
    if not api_key:
        st.error("⚠️ 请先在左侧输入 API Key！")
    elif not target_brand:
        st.error("⚠️ 请输入你要监测的目标品牌！")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        questions = [q.strip() for q in questions_input.split("\n") if q.strip()]
        
        temp_data = []
        temp_domains = []
        target_mention_count = 0
        competitor_mention_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, q in enumerate(questions):
            status_text.text(f"正在向大模型提问 ({i+1}/{len(questions)})...")
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个严谨的分析助手。请在回答最后给出真实的参考链接（http开头），严禁编造。"},
                    {"role": "user", "content": q}
                ]
            )
            answer = response.choices[0].message.content
            
            # 统计提及次数
            if target_brand in answer: target_mention_count += 1
            if competitor_brand in answer: competitor_mention_count += 1
            
            # 简单情感分析（判断品牌词周围有没有负面词）
            sentiment = "未提及"
            if target_brand in answer:
                # 截取品牌词前后的内容判断态度
                start_idx = answer.find(target_brand)
                context = answer[max(0, start_idx-30):min(len(answer), start_idx+30)]
                neg_words = ["但是", "缺点", "不足", "不建议", "较差", "坑", "贵"]
                sentiment = "负面/中立" if any(w in context for w in neg_words) else "正面推荐"
            
            # 提取链接和域名
            urls = re.findall(r'https?://[^\s\)\]]+', answer)
            domains = []
            for url in urls:
                try:
                    domain = urlparse(url).netloc
                    if domain.startswith("www."): domain = domain[4:]
                    domains.append(domain)
                    temp_domains.append(domain)
                except: pass
            
            temp_data.append({
                "问题": q,
                "目标品牌提及": "是" if target_brand in answer else "否",
                "品牌态度": sentiment,
                "提取的域名": " | ".join(set(domains)) if domains else "无",
                "AI回答摘要": answer[:100].replace('\n', ' ') + "..."
            })
            progress_bar.progress((i + 1) / len(questions))
            
        status_text.text("✅ 数据抓取完成！")
        
        # 打包存入 session_state
        st.session_state.report_data = {
            "data": temp_data,
            "domains": temp_domains,
            "target_count": target_mention_count,
            "comp_count": competitor_mention_count,
            "total_q": len(questions)
        }

# 6. 展示区（如果存在数据，就一直展示）
if st.session_state.report_data:
    rd = st.session_state.report_data
    df = pd.DataFrame(rd["data"])
    
    # 使用 Tab 标签页分开展示，界面更高级
    tab1, tab2, tab3 = st.tabs(["📈 商业诊断结论", "📋 详细数据表格", "📥 下载报告"])
    
    with tab1:
        st.subheader("💡 自动诊断结论")
        # 动态生成结论
        if rd["target_count"] == 0:
            st.error(f"⚠️ **严重警告**：在 {rd['total_q']} 个核心问题中，AI **完全没有提及**「{target_brand}」。这意味客户在 AI 搜索中处于失声状态！")
        else:
            st.success(f"✅ 在 {rd['total_q']} 个核心问题中，AI 提及「{target_brand}」 {rd['target_count']} 次。")
            
        if rd["comp_count"] > rd["target_count"]:
            st.warning(f"🚨 **竞品压制**：竞品「{competitor_brand}」被提及了 {rd['comp_count']} 次，在 AI 推荐中占据了上风。")
            
        # 图表展示
        if rd["domains"]:
            st.subheader("📊 信源域名分布")
            domain_counts = pd.Series(rd["domains"]).value_counts()
            st.bar_chart(domain_counts, color="#FF4B4B")
            
    with tab2:
        st.subheader("📋 原始监测数据")
        st.dataframe(df[["问题", "目标品牌提及", "品牌态度", "提取的域名"]], use_container_width=True)
        
    with tab3:
        st.subheader("📥 导出交付物")
        st.markdown("你可以将下方数据下载为 Excel，作为交付给客户的商业报告。")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='GEO监测数据')
            
        st.download_button(
            label="点击下载 Excel 商业报告",
            data=buffer.getvalue(),
            file_name=f"{target_brand}_GEO诊断报告.xlsx",
            mime="application/vnd.ms-excel"
        )
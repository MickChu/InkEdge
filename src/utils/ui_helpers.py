"""UI 辅助工具 — 供 GUI 页面共用的 UI 元素"""
import streamlit as st


def floating_home():
    """在所有子页面右侧显示悬浮返回仪表盘按钮"""
    st.markdown("""
    <style>
    .ink-floating-home {
        position: fixed;
        right: 20px;
        top: 50%;
        transform: translateY(-50%);
        z-index: 9999;
    }
    .ink-floating-home a {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        text-decoration: none !important;
        padding: 12px 8px;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        line-height: 1.3;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.35);
        transition: all 0.2s ease;
        min-width: 44px;
        text-align: center;
    }
    .ink-floating-home a:hover {
        transform: scale(1.06);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.55);
    }
    .ink-floating-home .icon { font-size: 18px; }
    </style>
    <div class="ink-floating-home">
        <a href="/" target="_self">
            <span class="icon">🏠</span>
            仪表盘
        </a>
    </div>
    """, unsafe_allow_html=True)

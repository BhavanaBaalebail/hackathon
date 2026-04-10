import re

with open('dashboard.py', 'r') as f:
    content = f.read()

sidebar_code = """st.sidebar.title("🎯 NexaCart BI Tool")
st.sidebar.markdown("Decision-focused Analytics")
pages = [
    "📊 Executive Overview",
    "🚚 Logistics Analysis (CORE)",
    "📦 Category Insights",
    "🏪 Seller Performance",
    "🌍 Geographic Insights",
    "⚖️ Final Recommendation"
]
page = st.sidebar.radio("Navigation Segment", pages)
"""
content = content.replace(sidebar_code, 'st.title("🎯 NexaCart BI Tool")\nst.markdown("Decision-focused Analytics - Scroll down to view the full analysis")\nst.divider()\n')

content = content.replace('if page == "📊 Executive Overview":\n    st.title("Executive Overview")', 'st.header("📊 Executive Overview")')
content = content.replace('elif page == "🚚 Logistics Analysis (CORE)":\n    st.title("Logistics Analysis: The Delivery Bottleneck")', 'st.divider()\n\nst.header("🚚 Logistics Analysis: The Delivery Bottleneck")')
content = content.replace('elif page == "📦 Category Insights":\n    st.title("Category Insights")', 'st.divider()\n\nst.header("📦 Category Insights")')
content = content.replace('elif page == "🏪 Seller Performance":\n    st.title("Seller Performance")', 'st.divider()\n\nst.header("🏪 Seller Performance")')
content = content.replace('elif page == "🌍 Geographic Insights":\n    st.title("Geographic Insights")', 'st.divider()\n\nst.header("🌍 Geographic Insights")')
content = content.replace('elif page == "⚖️ Final Recommendation":\n    st.title("Final Verdict & Strategic Recommendation")', 'st.divider()\n\nst.header("⚖️ Final Verdict & Strategic Recommendation")')

lines = content.split('\n')
new_lines = []
in_unindent_zone = False
for line in lines:
    if 'st.header("📊 Executive Overview")' in line:
        in_unindent_zone = True
    
    if in_unindent_zone and line.startswith('    '):
        new_lines.append(line[4:])
    else:
        new_lines.append(line)

with open('dashboard.py', 'w') as f:
    f.write('\n'.join(new_lines))

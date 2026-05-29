import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import json
import os

# 1. Page Configuration
st.set_page_config(page_title="Shared Sales BI Engine", layout="wide")
st.title("🤝 Collaborative Sales BI Workspace")

QUERIES_FILE = "saved_queries.json"
DASHBOARD_FILE = "saved_dashboard.json"
PRELOAD_DIR = "preloaded"

if not os.path.exists(PRELOAD_DIR):
    os.makedirs(PRELOAD_DIR)

# Shared JSON Storage Utilities
def load_storage(filepath, default_type=dict):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try: return json.load(f)
            except: return default_type()
    return default_type()

def save_storage(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

def clean_table_name(filename):
    return filename.split('.')[0].lower().replace(" ", "_").replace("-", "_")

# ========================================================
# UNIFIED PLOTLY CHART ENGINE (TAB 2 & TAB 3 SHARED CORE)
# ========================================================
def render_plotly_chart(chart_type, df, x_axis, y_axis, group_by):
    color_param = None if group_by == "None" else group_by
    
    if chart_type == "Stacked Bar":
        return px.bar(df, x=x_axis, y=y_axis, color=color_param, barmode="stack", template="plotly_white")
    elif chart_type == "Grouped Bar":
        return px.bar(df, x=x_axis, y=y_axis, color=color_param, barmode="group", template="plotly_white")
    elif chart_type == "Line Trend":
        return px.line(df, x=x_axis, y=y_axis, color=color_param, markers=True, template="plotly_white")
    elif chart_type == "Area Trend":
        return px.area(df, x=x_axis, y=y_axis, color=color_param, template="plotly_white")
    elif chart_type == "Pie Chart":
        return px.pie(df, names=x_axis, values=y_axis, template="plotly_white")
    elif chart_type == "Donut Chart":
        return px.pie(df, names=x_axis, values=y_axis, hole=0.4, template="plotly_white")
    elif chart_type == "Sales Funnel":
        # Funnel stage acts as Y, Metric acts as X
        return px.funnel(df, x=y_axis, y=x_axis, color=color_param, template="plotly_white")
    elif chart_type == "Scatter Plot":
        return px.scatter(df, x=x_axis, y=y_axis, color=color_param, template="plotly_white")
    elif chart_type == "Treemap (Hierarchical)":
        path_list = [x_axis] if group_by == "None" else [group_by, x_axis]
        return px.treemap(df, path=path_list, values=y_axis, template="plotly_white")
    elif chart_type == "Sunburst (Hierarchical)":
        path_list = [x_axis] if group_by == "None" else [group_by, x_axis]
        return px.sunburst(df, path=path_list, values=y_axis, template="plotly_white")
    elif chart_type == "Box Plot (Distribution)":
        return px.box(df, x=x_axis, y=y_axis, color=color_param, template="plotly_white")
    elif chart_type == "Histogram":
        return px.histogram(df, x=x_axis, y=y_axis, color=color_param, template="plotly_white")
    elif chart_type == "Density Heatmap":
        y_param = group_by if group_by != "None" else x_axis
        return px.density_heatmap(df, x=x_axis, y=y_param, z=y_axis, histfunc="sum", template="plotly_white")
    return None

# ==========================================
# DATABASE INGESTION LAYER
# ==========================================
st.sidebar.header("📥 Database Ingestion")
registered_tables = []

# Process Server Preloads
preload_files = [f for f in os.listdir(PRELOAD_DIR) if f.endswith(('.xlsx', '.xls'))]
if preload_files:
    st.sidebar.markdown("#### 📁 Preloaded Global Tables")
    for p_file in preload_files:
        t_name = clean_table_name(p_file)
        try:
            df_preload = pd.read_excel(os.path.join(PRELOAD_DIR, p_file))
            duckdb.register(t_name, df_preload)
            registered_tables.append(t_name)
            with st.sidebar.expander(f"⭐ {t_name}"):
                st.code("\n".join([f"- {col}" for col in df_preload.columns]))
        except Exception as e: st.sidebar.error(f"Error: {e}")

# Process Temporary File Uploads
uploaded_files = st.sidebar.file_uploader("Upload temporary sheets", type=["xlsx", "xls"], accept_multiple_files=True)
if uploaded_files:
    st.sidebar.markdown("#### 🔺 User Uploaded Tables")
    for file in uploaded_files:
        t_name = clean_table_name(file.name)
        try:
            df_excel = pd.read_excel(file)
            duckdb.register(t_name, df_excel)
            registered_tables.append(t_name)
            with st.sidebar.expander(f"📂 {t_name}"):
                st.code("\n".join([f"- {col}" for col in df_excel.columns]))
        except Exception as e: st.sidebar.error(f"Error: {e}")

# Launch Core Application tabs if tables exist
if registered_tables:
    tab1, tab2, tab3 = st.tabs(["🚀 Shared SQL Workspace", "📊 Chart Studio", "📋 Shared Live Dashboard"])

    # ==========================================
    # TAB 1: SHARED SQL WORKSPACE & DELETION
    # ==========================================
    with tab1:
        st.subheader("🧮 Shared SQL Command Center")
        current_shared_queries = load_storage(QUERIES_FILE, dict)
        
        # UI Selection Layout
        col_select, col_delete = st.columns([3, 1])
        with col_select:
            saved_options = ["-- Select a Saved Query --"] + list(current_shared_queries.keys())
            selected_saved = st.selectbox("📂 Open Shared Query Library:", options=saved_options)
        
        # Dynamic Deletion Feature
        with col_delete:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if selected_saved != "-- Select a Saved Query --":
                if st.button("❌ Delete Query Globally", type="primary", use_container_width=True):
                    fresh_queries = load_storage(QUERIES_FILE, dict)
                    fresh_queries.pop(selected_saved, None)
                    save_storage(QUERIES_FILE, fresh_queries)
                    st.toast(f"Deleted query '{selected_saved}' from library.")
                    st.rerun()

        starting_sql = current_shared_queries[selected_saved] if selected_saved != "-- Select a Saved Query --" else f"SELECT * FROM {registered_tables[0]} LIMIT 50"
        sql_input = st.text_area("📝 SQL Script Window:", value=starting_sql, height=150)

        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            run_query = st.button("⚡ Run SQL Script")
        with col_b2:
            with st.popover("💾 Save Query Globally"):
                q_name = st.text_input("Query Name:")
                if st.button("Save to Shared Library"):
                    if q_name.strip() and sql_input.strip():
                        f_queries = load_storage(QUERIES_FILE, dict)
                        f_queries[q_name] = sql_input
                        save_storage(QUERIES_FILE, f_queries)
                        st.success(f"Saved '{q_name}'!")
                        st.rerun()

        if run_query or (selected_saved != "-- Select a Saved Query --" and 'last_query_result' not in st.session_state):
            if sql_input.strip():
                try:
                    res_df = duckdb.sql(sql_input).df()
                    st.session_state['last_query_result'] = res_df
                    st.session_state['current_sql_text'] = sql_input
                    st.success("Query successful!")
                    st.dataframe(res_df.head(50), use_container_width=True)
                except Exception as err: st.error(f"SQL Error: {err}")

    # ==========================================
    # TAB 2: CHART STUDIO (ALL VISUAL FORMATS)
    # ==========================================
    with tab2:
        st.subheader("📊 Multi-Dimensional Chart Studio")
        
        if 'last_query_result' in st.session_state and not st.session_state['last_query_result'].empty:
            working_df = st.session_state['last_query_result']
            all_cols = working_df.columns.tolist()
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                chart_type = st.selectbox("Visual Framework", [
                    "Stacked Bar", "Grouped Bar", "Line Trend", "Area Trend", 
                    "Pie Chart", "Donut Chart", "Sales Funnel", "Scatter Plot", 
                    "Treemap (Hierarchical)", "Sunburst (Hierarchical)", 
                    "Box Plot (Distribution)", "Histogram", "Density Heatmap"
                ])
            with c2:
                x_axis = st.selectbox("Primary Dimension (X-Axis / Category)", options=all_cols)
            with c3:
                y_axis = st.selectbox("Target Numeric Value (Y-Axis / Metric)", options=all_cols)
            with c4:
                group_by = st.selectbox("Secondary Grouping / Legend (Optional)", options=["None"] + all_cols)
            
            # Generate and render chart using the dynamic core engine
            fig = render_plotly_chart(chart_type, working_df, x_axis, y_axis, group_by)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            dash_title = st.text_input("Name this dashboard component:", value=f"{y_axis} by {x_axis}")
            
            if st.button("📌 Pin Component to Shared Dashboard"):
                chart_config = {
                    "title": dash_title, "sql": st.session_state['current_sql_text'],
                    "chart_type": chart_type, "x_axis": x_axis, "y_axis": y_axis, "group_by": group_by
                }
                f_charts = load_storage(DASHBOARD_FILE, list)
                f_charts.append(chart_config)
                save_storage(DASHBOARD_FILE, f_charts)
                st.success(f"Pinned '{dash_title}' to the shared layout!")
        else:
            st.info("💡 Run an active SQL script in Tab 1 to load your data matrix.")

    # ==========================================
    # TAB 3: THE INTERACTIVE SHARED DASHBOARD
    # ==========================================
    with tab3:
        st.subheader("📋 Shared Executive Dashboard Matrix")
        current_shared_charts = load_storage(DASHBOARD_FILE, list)
        
        if current_shared_charts:
            # Global Dashboard Filter Calculations
            st.markdown("#### 🔍 Interactive Global Filters")
            mappable_filter_cols = set()
            for c_meta in current_shared_charts:
                try:
                    temp_df = duckdb.sql(c_meta['sql']).df()
                    for col in temp_df.select_dtypes(include=['object', 'category']).columns:
                        mappable_filter_cols.add(col)
                except: pass
            
            selected_filter_col = st.selectbox("🎯 Choose Column to Filter Globally:", options=["No Global Filter Active"] + list(mappable_filter_cols))
            
            active_filter_values = []
            if selected_filter_col != "No Global Filter Active":
                all_possible_vals = set()
                for c_meta in current_shared_charts:
                    try:
                        temp_df = duckdb.sql(c_meta['sql']).df()
                        if selected_filter_col in temp_df.columns:
                            all_possible_vals.update(temp_df[selected_filter_col].dropna().unique().tolist())
                    except: pass
                active_filter_values = st.multiselect(f"Match Specific {selected_filter_col} Values:", options=list(all_possible_vals), default=list(all_possible_vals))
            
            st.markdown("---")

            # Grid Rendering Engine
            col_dash1, col_dash2 = st.columns(2)
            for idx, chart_meta in enumerate(current_shared_charts):
                target_col = col_dash1 if idx % 2 == 0 else col_dash2
                
                with target_col:
                    with st.container(border=True):
                        st.markdown(f"### {chart_meta['title']}")
                        try:
                            # Recalculate underlying query live
                            dash_df = duckdb.sql(chart_meta['sql']).df()
                            
                            # Apply dynamic global filter intersections
                            if selected_filter_col != "No Global Filter Active" and selected_filter_col in dash_df.columns:
                                if active_filter_values:
                                    dash_df = dash_df[dash_df[selected_filter_col].isin(active_filter_values)]
                                else:
                                    dash_df = dash_df.iloc[0:0]
                            
                            # Pass structural tokens into unified chart builder
                            d_fig = render_plotly_chart(
                                chart_meta['chart_type'], dash_df, 
                                chart_meta['x_axis'], chart_meta['y_axis'], 
                                chart_meta.get('group_by', 'None')
                            )
                            if d_fig:
                                st.plotly_chart(d_fig, use_container_width=True, key=f"dash_chart_{idx}")
                            
                        except Exception as render_err:
                            st.error(f"Execution Error: {render_err}")
                        
                        # Destructive Delete Action
                        if st.button("❌ Remove Component", key=f"del_{idx}"):
                            fresh_charts = load_storage(DASHBOARD_FILE, list)
                            fresh_charts.pop(idx)
                            save_storage(DASHBOARD_FILE, fresh_charts)
                            st.rerun()
        else:
            st.info("💡 Shared dashboard layout is empty.")
else:
<<<<<<< HEAD
    st.info("💡 Add default data sheets into your local server `/preloaded` folder or use the sidepanel to upload Excel files manually.")
=======
    st.info("💡 Add default data sheets into your local server `/preloaded` folder or use the sidepanel to upload Excel files manually.")
>>>>>>> 7245f4d (App Update)

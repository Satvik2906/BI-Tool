import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import json
import os

# 1. Page Configuration
st.set_page_config(page_title="Shared Sales Insights Generator", layout="wide")
st.title("🤝 Collaborative Sales BI Workspace")

QUERIES_FILE = "saved_queries.json"
DASHBOARD_FILE = "saved_dashboard.json"
PRELOAD_DIR = "preloaded"

# Ensure the preload directory exists on the server
if not os.path.exists(PRELOAD_DIR):
    os.makedirs(PRELOAD_DIR)

# Core JSON storage engines (Universal across all user sessions)
def load_storage(filepath, default_type=dict):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                return json.load(f)
            except:
                return default_type()
    return default_type()

def save_storage(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

# Clean string format helper for database table naming
def clean_table_name(filename):
    return filename.split('.')[0].lower().replace(" ", "_").replace("-", "_")

# ==========================================
# DATA INGESTION ENGINE (PRELOADED + UPLOADS)
# ==========================================
st.sidebar.header("📥 Database Ingestion")
registered_tables = []

# Functionality 1: Process and Mount Preloaded Excel Files
preload_files = [f for f in os.listdir(PRELOAD_DIR) if f.endswith(('.xlsx', '.xls'))]

if preload_files:
    st.sidebar.markdown("#### 📁 Preloaded Global Tables")
    for p_file in preload_files:
        t_name = clean_table_name(p_file)
        full_path = os.path.join(PRELOAD_DIR, p_file)
        try:
            # Mount preloaded excel file
            df_preload = pd.read_excel(full_path)
            duckdb.register(t_name, df_preload)
            registered_tables.append(t_name)
            with st.sidebar.expander(f"⭐ {t_name} (Shared)"):
                st.code("\n".join([f"- {col}" for col in df_preload.columns]))
        except Exception as e:
            st.sidebar.error(f"Error loading preloaded file {p_file}: {e}")

# Maintain interactive ad-hoc file upload functionality
uploaded_files = st.sidebar.file_uploader("Upload additional temporary sheets", type=["xlsx", "xls"], accept_multiple_files=True)

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
        except Exception as e:
            st.sidebar.error(f"Error loading uploaded file {file.name}: {e}")


# Core Application Logic runs once data tables are ready
if registered_tables:
    tab1, tab2, tab3 = st.tabs(["🚀 Shared SQL Workspace", "📊 Chart Studio", "📋 Shared Live Dashboard"])

    # ==========================================
    # TAB 1: SHARED SQL WORKSPACE & SHARED LIBRARY
    # ==========================================
    with tab1:
        st.subheader("🧮 Shared SQL Command Center")
        
        # Functionality 3: Always pull the absolute latest queries from the shared file
        current_shared_queries = load_storage(QUERIES_FILE, dict)
        
        saved_options = ["-- Select a Saved Query --"] + list(current_shared_queries.keys())
        selected_saved = st.selectbox("📂 Open Shared Query Library:", options=saved_options)
        
        starting_sql = current_shared_queries[selected_saved] if selected_saved != "-- Select a Saved Query --" else f"SELECT * FROM {registered_tables[0]} LIMIT 50"
        sql_input = st.text_area("📝 SQL Script Window:", value=starting_sql, height=150)

        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            run_query = st.button("⚡ Run SQL Script")
        with col_b2:
            with st.popover("💾 Save Query Globally for All Users"):
                q_name = st.text_input("Provide a descriptive name for this query:")
                if st.button("Save to Shared Library"):
                    if q_name.strip() and sql_input.strip():
                        # Fetch, append, and rewrite directly to shared disk storage
                        f_queries = load_storage(QUERIES_FILE, dict)
                        f_queries[q_name] = sql_input
                        save_storage(QUERIES_FILE, f_queries)
                        st.success(f"Saved '{q_name}' to the global query menu!")
                        st.rerun()

        if run_query or (selected_saved != "-- Select a Saved Query --" and 'last_query_result' not in st.session_state):
            if sql_input.strip():
                try:
                    res_df = duckdb.sql(sql_input).df()
                    st.session_state['last_query_result'] = res_df
                    st.session_state['current_sql_text'] = sql_input
                    st.success("Query successful!")
                    st.dataframe(res_df.head(50), use_container_width=True)
                except Exception as err:
                    st.error(f"SQL Error: {err}")

    # ==========================================
    # TAB 2: CHART STUDIO
    # ==========================================
    with tab2:
        st.subheader("📊 Multi-Dimensional Chart Studio")
        
        if 'last_query_result' in st.session_state and not st.session_state['last_query_result'].empty:
            working_df = st.session_state['last_query_result']
            all_cols = working_df.columns.tolist()
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                chart_type = st.selectbox("Visual Framework", ["Stacked Bar", "Grouped Bar", "Line Trend", "Treemap (Hierarchical)", "Scatter Plot"])
            with c2:
                x_axis = st.selectbox("Primary Axis (X-Axis / Category)", options=all_cols)
            with c3:
                y_axis = st.selectbox("Numeric Value (Y-Axis / Metric)", options=all_cols)
            with c4:
                group_by = st.selectbox("Secondary Slice / Legend (Optional)", options=["None"] + all_cols)
            
            color_param = None if group_by == "None" else group_by

            if chart_type == "Stacked Bar":
                fig = px.bar(working_df, x=x_axis, y=y_axis, color=color_param, barmode="stack", template="plotly_white")
            elif chart_type == "Grouped Bar":
                fig = px.bar(working_df, x=x_axis, y=y_axis, color=color_param, barmode="group", template="plotly_white")
            elif chart_type == "Line Trend":
                fig = px.line(working_df, x=x_axis, y=y_axis, color=color_param, markers=True, template="plotly_white")
            elif chart_type == "Scatter Plot":
                fig = px.scatter(working_df, x=x_axis, y=y_axis, color=color_param, template="plotly_white")
            elif chart_type == "Treemap (Hierarchical)":
                path_list = [x_axis] if group_by == "None" else [group_by, x_axis]
                fig = px.treemap(working_df, path=path_list, values=y_axis, template="plotly_white")
                
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            dash_title = st.text_input("Name this visual component:", value=f"{y_axis} by {x_axis}")
            
            if st.button("📌 Pin Component to Shared Dashboard"):
                chart_config = {
                    "title": dash_title,
                    "sql": st.session_state['current_sql_text'],
                    "chart_type": chart_type,
                    "x_axis": x_axis,
                    "y_axis": y_axis,
                    "group_by": group_by
                }
                # Functionality 2: Read baseline, append element, and overwrite instantly
                f_charts = load_storage(DASHBOARD_FILE, list)
                f_charts.append(chart_config)
                save_storage(DASHBOARD_FILE, f_charts)
                st.success(f"Added '{dash_title}' to the shared global view layout!")
        else:
            st.info("💡 Run an active SQL script in Tab 1 to unlock visualization design options.")

    # ==========================================
    # TAB 3: THE INTERACTIVE SHARED DASHBOARD
    # ==========================================
    with tab3:
        st.subheader("📋 Shared Executive Dashboard Matrix")
        
        # Functionality 2: Pull the dashboard configuration array dynamically on every user rerun
        current_shared_charts = load_storage(DASHBOARD_FILE, list)
        
        if current_shared_charts:
            # Global Filter Processing
            st.markdown("#### 🔍 Interactive Global Filters")
            mappable_filter_cols = set()
            for c_meta in current_shared_charts:
                try:
                    temp_df = duckdb.sql(c_meta['sql']).df()
                    for col in temp_df.select_dtypes(include=['object', 'category']).columns:
                        mappable_filter_cols.add(col)
                except:
                    pass
            
            selected_filter_col = st.selectbox("🎯 Choose Column to Filter Globally:", options=["No Global Filter Active"] + list(mappable_filter_cols))
            
            active_filter_values = []
            if selected_filter_col != "No Global Filter Active":
                all_possible_vals = set()
                for c_meta in current_shared_charts:
                    try:
                        temp_df = duckdb.sql(c_meta['sql']).df()
                        if selected_filter_col in temp_df.columns:
                            all_possible_vals.update(temp_df[selected_filter_col].dropna().unique().tolist())
                    except:
                        pass
                active_filter_values = st.multiselect(f"Match Specific {selected_filter_col} Values:", options=list(all_possible_vals), default=list(all_possible_vals))
            
            st.markdown("---")

            # Grid Rendering
            col_dash1, col_dash2 = st.columns(2)
            
            for idx, chart_meta in enumerate(current_shared_charts):
                target_col = col_dash1 if idx % 2 == 0 else col_dash2
                
                with target_col:
                    with st.container(border=True):
                        st.markdown(f"### {chart_meta['title']}")
                        try:
                            dash_df = duckdb.sql(chart_meta['sql']).df()
                            
                            if selected_filter_col != "No Global Filter Active" and selected_filter_col in dash_df.columns:
                                if active_filter_values:
                                    dash_df = dash_df[dash_df[selected_filter_col].isin(active_filter_values)]
                                else:
                                    dash_df = dash_df.iloc[0:0]
                            
                            g_param = chart_meta.get('group_by', 'None')
                            c_color = None if g_param == "None" else g_param
                            c_type = chart_meta['chart_type']
                            
                            if c_type == "Stacked Bar":
                                d_fig = px.bar(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], color=c_color, barmode="stack", template="plotly_white")
                            elif c_type == "Grouped Bar":
                                d_fig = px.bar(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], color=c_color, barmode="group", template="plotly_white")
                            elif c_type == "Line Trend":
                                d_fig = px.line(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], color=c_color, markers=True, template="plotly_white")
                            elif c_type == "Scatter Plot":
                                d_fig = px.scatter(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], color=c_color, template="plotly_white")
                            elif c_type == "Treemap (Hierarchical)":
                                p_list = [chart_meta['x_axis']] if g_param == "None" else [g_param, chart_meta['x_axis']]
                                d_fig = px.treemap(dash_df, path=p_list, values=chart_meta['y_axis'], template="plotly_white")
                            
                            st.plotly_chart(d_fig, use_container_width=True, key=f"dash_chart_{idx}")
                            
                        except Exception as render_err:
                            st.error(f"Execution Error: {render_err}")
                        
                        # Destructive Selective Delete updates global configuration instantly
                        if st.button("❌ Remove Component", key=f"del_{idx}"):
                            fresh_charts = load_storage(DASHBOARD_FILE, list)
                            fresh_charts.pop(idx)
                            save_storage(DASHBOARD_FILE, fresh_charts)
                            st.rerun()
        else:
            st.info("💡 Shared dashboard is empty. Build and pin charts inside 'Chart Studio'.")
else:
    st.info("💡 Drop default analytics sheets into your server's local `/preloaded` directory or use the side panel to upload fields manually.")

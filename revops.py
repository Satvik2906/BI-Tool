import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import json
import os

# 1. Page Configuration
st.set_page_config(page_title="Advanced Sales BI", layout="wide")
st.title("🎛️ Enterprise Sales BI Engine (100% Free)")

QUERIES_FILE = "saved_queries.json"
DASHBOARD_FILE = "saved_dashboard.json"

def load_storage(filepath, default_type=dict):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return default_type()

def save_storage(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

if 'saved_queries' not in st.session_state:
    st.session_state['saved_queries'] = load_storage(QUERIES_FILE, dict)
if 'pinned_charts' not in st.session_state:
    st.session_state['pinned_charts'] = load_storage(DASHBOARD_FILE, list)

# 2. Excel Data Ingestion
st.sidebar.header("📥 Data Ingestion")
uploaded_files = st.sidebar.file_uploader("Select clean Excel sheets", type=["xlsx", "xls"], accept_multiple_files=True)

registered_tables = []
if uploaded_files:
    st.sidebar.markdown("### 📋 Database Tables")
    for file in uploaded_files:
        table_name = file.name.split('.')[0].lower().replace(" ", "_").replace("-", "_")
        try:
            df_excel = pd.read_excel(file)
            duckdb.register(table_name, df_excel)
            registered_tables.append(table_name)
            with st.sidebar.expander(f"Table: {table_name}"):
                st.code("\n".join([f"- {col}" for col in df_excel.columns]))
        except Exception as e:
            st.sidebar.error(f"Error loading {file.name}: {e}")

    tab1, tab2, tab3 = st.tabs(["🚀 SQL Workspace", "📊 Chart Studio (Multi-Slice)", "📋 Interactive Dashboard"])

    # ==========================================
    # TAB 1: SQL WORKSPACE
    # ==========================================
    with tab1:
        st.subheader("🧮 SQL Query Command Center")
        saved_options = ["-- Select a Saved Query --"] + list(st.session_state['saved_queries'].keys())
        selected_saved = st.selectbox("📂 Load Saved Query:", options=saved_options)
        
        starting_sql = st.session_state['saved_queries'][selected_saved] if selected_saved != "-- Select a Saved Query --" else f"SELECT * FROM {registered_tables[0]} LIMIT 100" if registered_tables else ""
        sql_input = st.text_area("📝 SQL Script Window:", value=starting_sql, height=150)

        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            run_query = st.button("⚡ Run SQL Script")
        with col_b2:
            with st.popover("💾 Save Query Definition"):
                q_name = st.text_input("Query Nickname:")
                if st.button("Save to Storage"):
                    if q_name.strip() and sql_input.strip():
                        st.session_state['saved_queries'][q_name] = sql_input
                        save_storage(QUERIES_FILE, st.session_state['saved_queries'])
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
                except Exception as err:
                    st.error(f"SQL Error: {err}")

    # ==========================================
    # TAB 2: CHART STUDIO (MULTI-DIMENSIONAL SLICING)
    # ==========================================
    with tab2:
        st.subheader("📊 Multi-Dimensional Chart Studio")
        
        if 'last_query_result' in st.session_state and not st.session_state['last_query_result'].empty:
            working_df = st.session_state['last_query_result']
            all_cols = working_df.columns.tolist()
            
            # Form UI layout for building deeper cuts of data
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                chart_type = st.selectbox("Visual Framework", ["Stacked Bar", "Grouped Bar", "Line Trend", "Treemap (Hierarchical)", "Scatter Plot"])
            with c2:
                x_axis = st.selectbox("Primary Axis (X-Axis / Category)", options=all_cols)
            with c3:
                y_axis = st.selectbox("Numeric Value (Y-Axis / Metric)", options=all_cols)
            with c4:
                # The Secret Sauce for Multi-Slicing: Legend segmentation
                group_by = st.selectbox("Secondary Slice / Legend (Optional)", options=["None"] + all_cols)
            
            color_param = None if group_by == "None" else group_by

            # Render Logic based on deep configurations
            if chart_type == "Stacked Bar":
                fig = px.bar(working_df, x=x_axis, y=y_axis, color=color_param, barmode="stack", template="plotly_white")
            elif chart_type == "Grouped Bar":
                fig = px.bar(working_df, x=x_axis, y=y_axis, color=color_param, barmode="group", template="plotly_white")
            elif chart_type == "Line Trend":
                fig = px.line(working_df, x=x_axis, y=y_axis, color=color_param, markers=True, template="plotly_white")
            elif chart_type == "Scatter Plot":
                fig = px.scatter(working_df, x=x_axis, y=y_axis, color=color_param, size=y_axis if y_axis else None, template="plotly_white")
            elif chart_type == "Treemap (Hierarchical)":
                path_list = [x_axis] if group_by == "None" else [group_by, x_axis]
                fig = px.treemap(working_df, path=path_list, values=y_axis, template="plotly_white")
                
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            dash_title = st.text_input("Name this visual component:", value=f"{y_axis} by {x_axis}")
            if st.button("📌 Pin Component to Dashboard Layout"):
                chart_config = {
                    "title": dash_title,
                    "sql": st.session_state['current_sql_text'],
                    "chart_type": chart_type,
                    "x_axis": x_axis,
                    "y_axis": y_axis,
                    "group_by": group_by
                }
                st.session_state['pinned_charts'].append(chart_config)
                save_storage(DASHBOARD_FILE, st.session_state['pinned_charts'])
                st.success(f"Added '{dash_title}' to layout!")
        else:
            st.info("💡 Run an active SQL script in Tab 1 to unlock advanced visualization setups.")

    # ==========================================
    # TAB 3: THE INTERACTIVE DASHBOARD WITH FILTERS
    # ==========================================
    with tab3:
        st.subheader("📋 Your Live Interactive Dashboard Grid")
        
        if st.session_state['pinned_charts']:
            # --- GLOBAL FILTER ENGINE ENGINE ---
            st.markdown("#### 🔍 Interactive Global Dashboard Filters")
            
            # Combine all unique columns from all pinned charts to find what we can filter by
            mappable_filter_cols = set()
            for c_meta in st.session_state['pinned_charts']:
                try:
                    # Quick test execution to see data columns available
                    temp_df = duckdb.sql(c_meta['sql']).df()
                    # Only suggest object/text columns for segment filtering
                    for col in temp_df.select_dtypes(include=['object', 'category']).columns:
                        mappable_filter_cols.add(col)
                except:
                    pass
            
            filter_cols_list = list(mappable_filter_cols)
            
            # If we find valid filtering dimensions, present them at the top of the screen
            selected_filter_col = st.selectbox("🎯 Choose Column to Filter Globally:", options=["No Global Filter Active"] + filter_cols_list)
            
            active_filter_values = []
            if selected_filter_col != "No Global Filter Active":
                # Gather all unique values for that specific column across all tables
                all_possible_vals = set()
                for c_meta in st.session_state['pinned_charts']:
                    try:
                        temp_df = duckdb.sql(c_meta['sql']).df()
                        if selected_filter_col in temp_df.columns:
                            all_possible_vals.update(temp_df[selected_filter_col].dropna().unique().tolist())
                    except:
                        pass
                
                active_filter_values = st.multiselect(f"Match Specific {selected_filter_col} Values:", options=list(all_possible_vals), default=list(all_possible_vals))
            
            st.markdown("---")

            # --- RENDER DASHBOARD LAYOUT GRID ---
            col_dash1, col_dash2 = st.columns(2)
            
            for idx, chart_meta in enumerate(st.session_state['pinned_charts']):
                target_col = col_dash1 if idx % 2 == 0 else col_dash2
                
                with target_col:
                    with st.container(border=True):
                        st.markdown(f"### {chart_meta['title']}")
                        
                        try:
                            # 1. Fetch data stream
                            dash_df = duckdb.sql(chart_meta['sql']).df()
                            
                            # 2. Inject runtime filter modifications if match is found
                            if selected_filter_col != "No Global Filter Active" and selected_filter_col in dash_df.columns:
                                if active_filter_values:
                                    dash_df = dash_df[dash_df[selected_filter_col].isin(active_filter_values)]
                                else:
                                    dash_df = dash_df.iloc[0:0] # Return empty state if values unchecked
                            
                            # 3. Handle multi-dimensional parameter mapping
                            g_param = chart_meta.get('group_by', 'None')
                            c_color = None if g_param == "None" else g_param
                            c_type = chart_meta['chart_type']
                            
                            # 4. Generate respective plot structures
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
                        
                        if st.button("❌ Remove Component", key=f"del_{idx}"):
                            st.session_state['pinned_charts'].pop(idx)
                            save_storage(DASHBOARD_FILE, st.session_state['pinned_charts'])
                            st.rerun()
        else:
            st.info("💡 Dashboard is empty. Set up and pin your custom slices inside 'Chart Studio'.")
else:
    st.info("💡 Ingest data files in the sidebar to start analytics.")
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import json
import os

# 1. Page Configuration
st.set_page_config(page_title="SQL Sales Dashboard", layout="wide")
st.title("🛢️ Custom Sales BI Engine with Persistent Storage")

# 2. File Paths for Free Local Storage
QUERIES_FILE = "saved_queries.json"
DASHBOARD_FILE = "saved_dashboard.json"

# Helper functions to read/write data for free
def load_storage(filepath, default_type=dict):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return default_type()

def save_storage(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

# Initialize Session State tracking
if 'saved_queries' not in st.session_state:
    st.session_state['saved_queries'] = load_storage(QUERIES_FILE, dict)
if 'pinned_charts' not in st.session_state:
    st.session_state['pinned_charts'] = load_storage(DASHBOARD_FILE, list)

# 3. Multi-File Ingestion Layer (Excel)
st.sidebar.header("📥 Ingest Sales Data")
uploaded_files = st.sidebar.file_uploader(
    "Select your cleaned Excel files", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

registered_tables = []

if uploaded_files:
    st.sidebar.markdown("### 📋 Active Database Schema")
    for file in uploaded_files:
        table_name = file.name.split('.')[0].lower().replace(" ", "_").replace("-", "_")
        try:
            df_excel = pd.read_excel(file)
            duckdb.register(table_name, df_excel)
            registered_tables.append(table_name)
            
            with st.sidebar.expander(f"Table: {table_name}"):
                st.code(f"Columns:\n" + "\n".join([f"- {col}" for col in df_excel.columns]))
        except Exception as e:
            st.sidebar.error(f"Failed to read {file.name}: {e}")

    # Create UI Tabs (Added a 3rd Tab for the Dashboard layout)
    tab1, tab2, tab3 = st.tabs(["🚀 SQL Workspace", "📊 Chart Studio", "📋 Pinned Dashboard"])

    # ==========================================
    # TAB 1: INTERACTIVE SQL WORKSPACE & SAVED QUERIES
    # ==========================================
    with tab1:
        st.subheader("🧮 SQL Query Builder & History Library")
        
        # Feature 1: Load a saved query from the dropdown library
        saved_query_options = ["-- Select a Saved Query --"] + list(st.session_state['saved_queries'].keys())
        selected_saved = st.selectbox("📂 Load from Query Library:", options=saved_query_options)
        
        # Set default text area content based on selection
        if selected_saved != "-- Select a Saved Query --":
            starting_sql = st.session_state['saved_queries'][selected_saved]
        else:
            starting_sql = f"SELECT * FROM {registered_tables[0]} LIMIT 5" if registered_tables else ""

        sql_input = st.text_area("📝 Edit Your SQL Query:", value=starting_sql, height=150)

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            run_query = st.button("⚡ Run SQL Query")
        
        # Feature 1: Save the current query input text
        with col_btn2:
            with st.popover("💾 Save This Query"):
                new_query_name = st.text_input("Give your query a unique name:")
                if st.button("Confirm Save"):
                    if new_query_name.strip() and sql_input.strip():
                        st.session_state['saved_queries'][new_query_name] = sql_input
                        save_storage(QUERIES_FILE, st.session_state['saved_queries'])
                        st.success(f"Saved '{new_query_name}' to library!")
                        st.rerun()

        # Handle Query Execution Logic
        if run_query or (selected_saved != "-- Select a Saved Query --" and 'last_query_result' not in st.session_state):
            if sql_input.strip():
                try:
                    query_result = duckdb.sql(sql_input).df()
                    st.session_state['last_query_result'] = query_result
                    st.session_state['current_sql_text'] = sql_input # Cache sql string for chart building
                    st.success("Query executed successfully!")
                    
                    if len(query_result) == 1 and len(query_result.columns) <= 3:
                        st.markdown("#### 🎯 Resulting Metric Output")
                        m_cols = st.columns(len(query_result.columns))
                        for i, col_name in enumerate(query_result.columns):
                            m_cols[i].metric(label=col_name.replace("_", " ").title(), value=f"{query_result.iloc[0, i]}")
                    
                    st.markdown("#### 📋 Data Output Preview")
                    st.dataframe(query_result, use_container_width=True)
                except Exception as query_error:
                    st.error(f"SQL Syntax Error: {query_error}")

    # ==========================================
    # TAB 2: VISUAL CHART STUDIO & PINNING ENGINE
    # ==========================================
    with tab2:
        st.subheader("📊 Chart Generator Studio")
        
        if 'last_query_result' in st.session_state and not st.session_state['last_query_result'].empty:
            working_df = st.session_state['last_query_result']
            all_cols = working_df.columns.tolist()
            
            col_v1, col_v2, col_v3 = st.columns(3)
            with col_v1:
                chart_type = st.selectbox("Chart Style", ["Bar Chart", "Line Chart", "Scatter Plot"])
            with col_v2:
                x_axis = st.selectbox("X-Axis (Dimensions)", options=all_cols)
            with col_v3:
                y_axis = st.selectbox("Y-Axis (Metrics/Values)", options=all_cols)

            # Build the visual object
            if chart_type == "Bar Chart":
                fig = px.bar(working_df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}", template="plotly_white")
            elif chart_type == "Line Chart":
                fig = px.line(working_df, x=x_axis, y=y_axis, title=f"{y_axis} Trend Over {x_axis}", template="plotly_white")
            elif chart_type == "Scatter Plot":
                fig = px.scatter(working_df, x=x_axis, y=y_axis, title=f"Correlation: {x_axis} vs {y_axis}", template="plotly_white")
                
            st.plotly_chart(fig, use_container_width=True)

            # Feature 2: Pin this specific layout configuration to the Dashboard panel
            st.markdown("---")
            st.markdown("#### 📌 Pin This Visual Setup to Dashboard")
            dashboard_title = st.text_input("Enter a Dashboard Title for this chart:", value=f"My Custom {chart_type}")
            
            if st.button("🚀 Add to Pinned Dashboard"):
                new_chart_config = {
                    "title": dashboard_title,
                    "sql": st.session_state['current_sql_text'],
                    "chart_type": chart_type,
                    "x_axis": x_axis,
                    "y_axis": y_axis
                }
                st.session_state['pinned_charts'].append(new_chart_config)
                save_storage(DASHBOARD_FILE, st.session_state['pinned_charts'])
                st.success(f"Added '{dashboard_title}' to your layout overview tab!")
        else:
            st.info("💡 Run a successful SQL query in the 'SQL Workspace' tab first to generate charts.")

    # ==========================================
    # TAB 3: THE LIVE RETENTION DASHBOARD LAYOUT
    # ==========================================
    with tab3:
        st.subheader("📋 Your Persistent Custom Dashboard Grid")
        st.markdown("This section automatically recalculates your charts using their saved SQL rules against your currently uploaded files.")
        
        if st.session_state['pinned_charts']:
            # Render a responsive 2-column dashboard layout
            col_dash1, col_dash2 = st.columns(2)
            
            for index, chart_meta in enumerate(st.session_state['pinned_charts']):
                # Alternate distribution between left and right column boxes
                target_column = col_dash1 if index % 2 == 0 else col_dash2
                
                with target_column:
                    with st.container(border=True):
                        st.markdown(f"### {chart_meta['title']}")
                        
                        try:
                            # Re-run the underlying SQL query live against current engine data streams
                            dash_df = duckdb.sql(chart_meta['sql']).df()
                            
                            # Rebuild the plot based on saved layout parameters
                            if chart_meta['chart_type'] == "Bar Chart":
                                d_fig = px.bar(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], template="plotly_white")
                            elif chart_meta['chart_type'] == "Line Chart":
                                d_fig = px.line(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], template="plotly_white")
                            elif chart_meta['chart_type'] == "Scatter Plot":
                                d_fig = px.scatter(dash_df, x=chart_meta['x_axis'], y=chart_meta['y_axis'], template="plotly_white")
                            
                            st.plotly_chart(d_fig, use_container_width=True, key=f"dash_chart_{index}")
                            
                        except Exception as dash_render_err:
                            st.error(f"Could not compute chart data. Make sure matching sheets are uploaded. Error: {dash_render_err}")
                        
                        # Feature 2: Selectively delete charts when required
                        if st.button("❌ Remove from Layout", key=f"del_{index}"):
                            st.session_state['pinned_charts'].pop(index)
                            save_storage(DASHBOARD_FILE, st.session_state['pinned_charts'])
                            st.toast(f"Removed element.")
                            st.rerun()
        else:
            st.info("💡 No charts pinned yet. Customize a visualization in the 'Chart Studio' and click 'Add to Pinned Dashboard'.")

else:
    st.info("💡 Ingest your files in the side navigation panel to get started.")
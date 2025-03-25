# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from shapely.geometry import Point
import json
import os

# Custom CSS for responsive layout
custom_css = """
<style>
    body {
        background-color: #f5f5f5;
    }
    .map-frame {
        border: 2px solid #cccccc;
        border-radius: 5px;
        padding: 10px;
        background-color: #ffffff;
        width: 100%;
        max-width: 100%;
        overflow-x: hidden;
    }
    .folium-legend {
        position: absolute !important;
        top: 10px !important;
        right: 10px !important;
        background-color: rgba(255, 255, 255, 0.8) !important;
        z-index: 1000 !important;
    }
    .stApp {
        max-width: 100%;
        overflow-x: hidden;
    }
</style>
"""

@st.cache_data
def load_geojson_and_mappings(geojson_path, excel_path):
    """Load GeoJSON and location mappings, returning GeoDataFrame and dictionary."""
    try:
        gdf = gpd.read_file(geojson_path)
        gdf.crs = 'epsg:4326'
    except Exception as e:
        st.error(f"Error loading GeoJSON file '{geojson_path}': {e}")
        st.stop()

    try:
        excel_file = pd.ExcelFile(excel_path)
        if 'Location ID' not in excel_file.sheet_names:
            st.error("Excel file is missing the 'Location ID' sheet.")
            st.stop()
        location_df = excel_file.parse('Location ID')
        location_dict = location_df.set_index('ID_1')['NAME_1'].to_dict()
    except Exception as e:
        st.error(f"Error parsing 'Location ID' sheet from '{excel_path}': {e}")
        st.stop()

    return gdf, location_dict

@st.cache_data
def load_sector_data(excel_path):
    """Load main sectors and sub-indicator mappings from Excel."""
    try:
        excel_file = pd.ExcelFile(excel_path)
        if 'main_ind' not in excel_file.sheet_names:
            st.error("Excel file is missing the 'main_ind' sheet. Required for sector selection.")
            st.stop()
        main_ind_df = excel_file.parse('main_ind')
        if not {'main-index-code', 'main-index-name'}.issubset(main_ind_df.columns):
            st.error("'main_ind' sheet must have 'main-index-code' and 'main-index-name' columns.")
            st.stop()
        main_options = main_ind_df.set_index('main-index-name')['main-index-code'].to_dict()

        sub_options = {}
        for sheet_name in main_options.values():
            if sheet_name not in excel_file.sheet_names:
                st.error(f"Sub-indicator sheet '{sheet_name}' not found in Excel file.")
                st.stop()
            sub_df = excel_file.parse(sheet_name)
            if not {'index', 'index code'}.issubset(sub_df.columns):
                st.error(f"Sheet '{sheet_name}' must have 'index' and 'index code' columns.")
                st.stop()
            sub_options[sheet_name] = sub_df.set_index('index code')['index'].to_dict()

        return main_options, sub_options
    except Exception as e:
        st.error(f"Error loading sector data from '{excel_path}': {e}")
        st.stop()

def calculate_national_averages(df, years):
    """Calculate national averages for each year."""
    return {year: df[year].mean() for year in years}

def get_province_data(df, province_id, years):
    """Get data for a specific province across years."""
    province_data = df[df['ID_1'] == province_id]
    return {year: province_data[year].iloc[0] for year in years} if not province_data.empty else None

def create_line_chart(national_averages, province_data=None, province_name=None):
    """Create a line chart comparing national averages and province data."""
    years = list(national_averages.keys())
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=[national_averages[year] for year in years], name='National Average',
        line=dict(color='#1f77b4', width=2.5), mode='lines+markers', marker=dict(size=8, symbol='circle'),
        hovertemplate='%{y:.2f}<extra></extra>'
    ))
    if province_data and province_name:
        fig.add_trace(go.Scatter(
            x=years, y=[province_data[year] for year in years], name=province_name,
            line=dict(color='#ff7f0e', width=2.5, dash='dash'), mode='lines+markers', marker=dict(size=8, symbol='circle'),
            hovertemplate='%{y:.2f}<extra></extra>'
        ))
    fig.update_layout(
        title='Trend Over Years', xaxis_title='Year', yaxis_title='Value', hovermode='x unified', height=400,
        plot_bgcolor='rgba(245, 245, 245, 1)', paper_bgcolor='white', font=dict(size=12),
        xaxis=dict(tickvals=years, ticktext=[str(year) for year in years], gridcolor='rgba(200, 200, 200, 0.5)'),
        yaxis=dict(gridcolor='rgba(200, 200, 200, 0.5)'),
        legend=dict(x=1.05, y=1, bgcolor='rgba(255, 255, 255, 0.8)', bordercolor='gray', borderwidth=1)
    )
    return fig

def create_map(gdf, df, location_dict, selected_index, year, reverse_colors, selected_color, selected_province_id=None):
    """Create a choropleth map with tooltips and province highlighting."""
    try:
        merged_gdf = gdf.merge(df[['ID_1', year]], on='ID_1', how='left')
    except Exception as e:
        st.error(f"Error merging GeoDataFrame with data: {e}")
        return None, None
    if merged_gdf[year].isna().any():
        st.warning(f"Some provinces lack data for {selected_index} in {year}.")
    try:
        choropleth_gdf = merged_gdf.drop(columns=['centroid', 'lat', 'lon'], errors='ignore')
        merged_gdf = merged_gdf.to_crs('EPSG:32639')
        merged_gdf['centroid'] = merged_gdf.geometry.centroid
        merged_gdf['lat'] = merged_gdf['centroid'].y
        merged_gdf['lon'] = merged_gdf['centroid'].x
        merged_gdf = merged_gdf.to_crs('EPSG:4326')  # Corrected typo here
    except Exception as e:
        st.error(f"Error processing centroids: {e}")
        return None, None
    m = folium.Map(location=[32, 53], zoom_start=5, tiles='cartodbpositron')
    fill_color = f"{selected_color}_r" if reverse_colors else selected_color
    try:
        folium.Choropleth(
            geo_data=choropleth_gdf.to_json(), name='choropleth',
            data=choropleth_gdf, columns=['ID_1', year], key_on='feature.properties.ID_1',
            fill_color=fill_color, fill_opacity=0.8, line_opacity=0.2,
            legend_name=f'{selected_index} - {year}'
        ).add_to(m)
    except Exception as e:
        st.error(f"Error creating choropleth layer: {e}")
        return m, merged_gdf
    tooltip_style = lambda x: {'fillColor': 'transparent', 'color': 'none', 'weight': 0, 'fillOpacity': 0}
    outline_style = lambda x: {'fillColor': 'none', 'color': 'black', 'weight': 3, 'fillOpacity': 0}
    no_data_style = lambda x: {'fillColor': '#f0f0f0', 'color': '#cccccc', 'weight': 1, 'fillOpacity': 0.6, 'dashArray': '5, 5'}
    tooltip_gdf = merged_gdf[['ID_1', 'NAME_1', year, 'geometry']].copy()
    if not tooltip_gdf.empty and tooltip_gdf['geometry'].notna().any():
        try:
            geojson_str = tooltip_gdf.to_json()
            geojson_data = json.loads(geojson_str)
            if geojson_data.get("type") == "FeatureCollection":
                folium.GeoJson(
                    geojson_data,
                    style_function=lambda x: no_data_style(x) if pd.isna(x['properties'][year]) else tooltip_style(x),
                    tooltip=folium.GeoJsonTooltip(
                        fields=['NAME_1', year], aliases=['Province:', f'{selected_index} ({year}):'],
                        localize=True, style="background-color: #f0f0f0; color: #004d40; font-family: 'Helvetica', sans-serif; font-size: 14px; padding: 8px; border-radius: 4px; border: 1px solid #004d40;"
                    ),
                    name='Tooltips'
                ).add_to(m)
            else:
                st.error(f"Tooltip GeoJSON is not a FeatureCollection. Type: {geojson_data.get('type')}")
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse GeoJSON for tooltips: {str(e)}")
        except Exception as e:
            st.error(f"Error adding tooltip layer: {e}")
    if selected_province_id:
        try:
            selected_gdf = merged_gdf[merged_gdf['ID_1'] == selected_province_id]
            if not selected_gdf.empty:
                selected_gdf = selected_gdf.drop(columns=['centroid', 'lat', 'lon'], errors='ignore')
                folium.GeoJson(selected_gdf.to_json(), style_function=outline_style, name='Selected Province').add_to(m)
        except Exception as e:
            st.error(f"Error adding selected province outline: {e}")
    folium.LayerControl().add_to(m)
    return m, merged_gdf

def find_clicked_province(clicked_location, gdf):
    """Identify the province clicked on the map."""
    click_point = Point(clicked_location['lng'], clicked_location['lat'])
    for _, row in gdf.iterrows():
        if row['geometry'].contains(click_point):
            return row['ID_1']
    return None

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Iran's Development Indicators", layout="wide")

    # File paths (relative to app.py location in Streamlit Cloud)
    excel_path = 'IrDevIndex2.xlsx'
    geojson_path = 'IRN_adm.json'

    # Verify file existence
    if not os.path.exists(excel_path):
        st.error(f"Excel file not found at: {excel_path}")
        st.stop()
    if not os.path.exists(geojson_path):
        st.error(f"GeoJSON file not found at: {geojson_path}")
        st.stop()

    # Load GeoJSON and location mappings
    gdf, location_dict = load_geojson_and_mappings(geojson_path, excel_path)

    # Load sector data
    main_options, sub_options = load_sector_data(excel_path)

    # Sidebar controls
    st.sidebar.header("Dashboard Controls")

    # Select main sector
    selected_main_sector = st.sidebar.selectbox("Select Main Sector:", options=list(main_options.keys()))
    selected_main_code = main_options[selected_main_sector]  # e.g., "Index02"

    # Filter and select sub-indicator
    sub_indicators = sub_options[selected_main_code]  # e.g., {"2-9 - The share...": "Index02-9"}
    selected_index_code = st.sidebar.selectbox("Select Indicator:", options=list(sub_indicators.keys()))  # Descriptive name
    selected_index = sub_indicators[selected_index_code]  # Sheet name, e.g., "Index02-9"

    # Load data for the selected sub-indicator using index (sheet name)
    try:
        excel_file = pd.ExcelFile(excel_path)
        if selected_index not in excel_file.sheet_names:
            st.error(f"Data sheet '{selected_index}' not found in Excel file.")
            st.stop()
        df = excel_file.parse(selected_index)
        if 'ID_1' not in df.columns:
            st.error(f"Data sheet '{selected_index}' must have an 'ID_1' column.")
            st.stop()
        years = [col for col in df.columns if col.isdigit()]
        if not years:
            st.error(f"No numeric year columns found in data sheet '{selected_index}'.")
            st.stop()
    except Exception as e:
        st.error(f"Error loading data sheet '{selected_index}': {e}")
        st.stop()

    # Additional controls
    year = st.sidebar.selectbox("Select Year:", options=years)
    color_options = {'Red': 'Reds', 'Blue': 'Blues', 'Green': 'Greens'}
    selected_color = st.sidebar.selectbox("Select Color Scheme:", options=list(color_options.keys()), index=0)
    reverse_colors = st.sidebar.checkbox("Reverse Colors")

    if st.sidebar.button("Reset Selection"):
        st.session_state.selected_province_id = None
        st.rerun()

    # Add "About" link at the bottom of the sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("[About](https://raw.githubusercontent.com/soukhtanlou/iran-map-dashboard/main/about.md)")

    # Main UI
    st.title("Iran's Atlas of Provincial Development Indicators")
    # Add selection summary line
    st.markdown(f"{selected_main_sector} \\ {selected_index_code} \\ {year}")
    st.markdown(custom_css, unsafe_allow_html=True)

    if 'selected_province_id' not in st.session_state:
        st.session_state.selected_province_id = None

    with st.spinner("Generating map..."):
        m, merged_gdf = create_map(gdf, df, location_dict, selected_index_code, year, reverse_colors, color_options[selected_color], st.session_state.selected_province_id)
        if m is None or merged_gdf is None:
            st.error("Map creation failed. Check logs above for details.")
            st.stop()

    st.markdown('<div class="map-frame">', unsafe_allow_html=True)
    map_data = st_folium(m, width='100%', height=600 if st.session_state.get('screen_height', 1080) > 800 else 400)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("**Click on a region on the map to display its trend over years in the chart below.**")

    try:
        national_averages = calculate_national_averages(df, years)
    except Exception as e:
        st.error(f"Error calculating national averages: {e}")
        st.stop()

    if map_data.get('last_clicked'):
        province_id = find_clicked_province(map_data['last_clicked'], merged_gdf)
        if province_id and province_id != st.session_state.selected_province_id:
            st.session_state.selected_province_id = province_id
            st.rerun()
        elif not province_id:
            st.warning("Could not identify the selected province.")
            if st.session_state.selected_province_id is not None:
                st.session_state.selected_province_id = None
                st.rerun()

    if st.session_state.selected_province_id:
        province_name = location_dict.get(st.session_state.selected_province_id, "Unknown")
        province_data = get_province_data(df, st.session_state.selected_province_id, years)
        if province_data:
            fig = create_line_chart(national_averages, province_data, province_name)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data found for the selected province.")
    else:
        fig = create_line_chart(national_averages)
        st.plotly_chart(fig, use_container_width=True)

    # Add data table at the bottom
    st.subheader("Data Table")
    table_df = df[['ID_1', 'Prov'] + years].copy()
    table_df['Provinces'] = table_df['ID_1'].map(location_dict)
    table_df = table_df[['Provinces', 'Prov'] + years]  # Reorder columns
    table_df = table_df.rename(columns={'NAME_1': 'Provinces'})  # Ensure NAME_1 is renamed
    st.dataframe(table_df, use_container_width=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
        raise

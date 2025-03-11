# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from shapely.geometry import Point
import json

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
def load_geojson_and_mappings(geojson_path='IRN_adm.json', excel_path='IrDevIndextest.xlsx'):
    """Load GeoJSON and Excel mappings, returning GeoDataFrame and dictionaries."""
    try:
        gdf = gpd.read_file(geojson_path)
        gdf.crs = 'epsg:4326'
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")
        st.stop()

    try:
        excel_file = pd.ExcelFile(excel_path)
        index_df = excel_file.parse('Index')
        sheet_options = index_df.set_index('index code')['index'].to_dict()
        location_df = excel_file.parse('Location ID')
        location_dict = location_df.set_index('ID_1')['NAME_1'].to_dict()
    except Exception as e:
        st.error(f"Error parsing Excel mappings: {e}")
        st.stop()

    return gdf, sheet_options, location_dict

def calculate_national_averages(df, years):
    """Calculate national averages for the given years from the DataFrame."""
    return {year: df[year].mean() for year in years}

def get_province_data(df, province_id, years):
    """Get province-specific data for the given years from the DataFrame."""
    province_data = df[df['ID_1'] == province_id]
    return {year: province_data[year].iloc[0] for year in years} if not province_data.empty else None

def create_line_chart(national_averages, province_data=None, province_name=None):
    """Create a Plotly line chart comparing national averages and province data."""
    years = list(national_averages.keys())
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years,
        y=[national_averages[year] for year in years],
        name='National Average',
        line=dict(color='#1f77b4', width=2.5),
        mode='lines+markers',
        marker=dict(size=8, symbol='circle'),
        hovertemplate='%{y:.2f}<extra></extra>'
    ))

    if province_data and province_name:
        fig.add_trace(go.Scatter(
            x=years,
            y=[province_data[year] for year in years],
            name=province_name,
            line=dict(color='#ff7f0e', width=2.5, dash='dash'),
            mode='lines+markers',
            marker=dict(size=8, symbol='circle'),
            hovertemplate='%{y:.2f}<extra></extra>'
        ))

    fig.update_layout(
        title='Trend Over Years',
        xaxis_title='Year',
        yaxis_title='Value',
        hovermode='x unified',
        height=400,
        plot_bgcolor='rgba(245, 245, 245, 1)',
        paper_bgcolor='white',
        font=dict(size=12),
        xaxis=dict(
            tickvals=years,
            ticktext=[str(year) for year in years],
            gridcolor='rgba(200, 200, 200, 0.5)'
        ),
        yaxis=dict(
            gridcolor='rgba(200, 200, 200, 0.5)'
        ),
        legend=dict(
            x=1.05,
            y=1,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='gray',
            borderwidth=1
        )
    )

    return fig

def create_map(gdf, df, location_dict, selected_index_code, year, reverse_colors, selected_color, selected_province_id=None):
    """Create a Folium map with choropleth, tooltips, and selected province outline."""
    try:
        merged_gdf = gdf.merge(df[['ID_1', year]], on='ID_1', how='left')
    except Exception as e:
        st.error(f"Error merging GeoDataFrame with Excel data: {e}")
        return None, None

    if merged_gdf[year].isna().any():
        st.warning(f"Some provinces lack data for {selected_index_code} in {year}.")

    try:
        choropleth_gdf = merged_gdf.drop(columns=['centroid', 'lat', 'lon'], errors='ignore')
        merged_gdf['centroid'] = merged_gdf.geometry.centroid
        merged_gdf['lat'] = merged_gdf['centroid'].y
        merged_gdf['lon'] = merged_gdf['centroid'].x
    except Exception as e:
        st.error(f"Error processing centroids: {e}")
        return None, None

    m = folium.Map(location=[32, 53], zoom_start=5, tiles='cartodbpositron')
    fill_color = f"{selected_color}_r" if reverse_colors else selected_color

    try:
        folium.Choropleth(
            geo_data=choropleth_gdf.to_json(), name='choropleth',
            data=choropleth_gdf, columns=['ID_1', year],
            key_on='feature.properties.ID_1', fill_color=fill_color,
            fill_opacity=0.8, line_opacity=0.2,
            legend_name=f'{selected_index_code} - {year}'
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
                        fields=['NAME_1', year],
                        aliases=['Province:', f'{selected_index_code} ({year}):'],
                        localize=True,
                        style=("background-color: #f0f0f0; color: #004d40; font-family: 'Helvetica', sans-serif; font-size: 14px; padding: 8px; border-radius: 4px; border: 1px solid #004d40;")
                    ),
                    name='Tooltips'
                ).add_to(m)
            else:
                st.error(f"Tooltip GeoJSON is not a FeatureCollection. Type: {geojson_data.get('type')}")
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse GeoJSON for tooltips: {str(e)}")
        except Exception as e:
            st.error(f"Error adding tooltip layer: {e}")
    else:
        st.warning("Tooltip GeoDataFrame is empty or has no valid geometries.")

    if selected_province_id:
        try:
            selected_gdf = merged_gdf[merged_gdf['ID_1'] == selected_province_id]
            if not selected_gdf.empty:
                selected_gdf = selected_gdf.drop(columns=['centroid', 'lat', 'lon'], errors='ignore')
                folium.GeoJson(
                    selected_gdf.to_json(),
                    style_function=outline_style,
                    name='Selected Province'
                ).add_to(m)
        except Exception as e:
            st.error(f"Error adding selected province outline: {e}")

    folium.LayerControl().add_to(m)
    return m, merged_gdf

def find_clicked_province(clicked_location, gdf):
    """Identify the province clicked based on coordinates."""
    click_point = Point(clicked_location['lng'], clicked_location['lat'])
    for _, row in gdf.iterrows():
        if row['geometry'].contains(click_point):
            return row['ID_1']
    return None

def main():
    st.set_page_config(page_title="Geographic Dashboard", layout="wide")

    # Load files directly from the repository (no uploaders)
    excel_path = 'IrDevIndextest.xlsx'
    geojson_path = 'IRN_adm.json'

    # Load cached GeoJSON and mappings
    gdf, sheet_options, location_dict = load_geojson_and_mappings(geojson_path, excel_path)

    # Load Excel file
    try:
        excel_file = pd.ExcelFile(excel_path)
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        st.stop()

    # Sidebar controls
    st.sidebar.header("Dashboard Controls")
    selected_index_code = st.sidebar.selectbox("Select Indicator:", options=list(sheet_options.keys()),
                                               format_func=lambda x: f"{x} - {sheet_options[x]}")
    
    # Dynamic year options from the selected sheet
    sheet = sheet_options[selected_index_code]
    try:
        df = excel_file.parse(sheet)
        years = [col for col in df.columns if col.isdigit()]
        if not years:
            st.error("No numeric year columns found in the selected sheet.")
            st.stop()
    except Exception as e:
        st.error(f"Error parsing sheet '{sheet}': {e}")
        st.stop()
    year = st.sidebar.selectbox("Select Year:", options=years)

    # Visual enhancement: Color scheme options
    color_options = {'Red': 'Reds', 'Blue': 'Blues', 'Green': 'Greens'}
    selected_color = st.sidebar.selectbox("Select Color Scheme:", options=list(color_options.keys()), index=0)
    reverse_colors = st.sidebar.checkbox("Reverse Colors")

    # Reset button
    if st.sidebar.button("Reset Selection"):
        st.session_state.selected_province_id = None
        st.rerun()

    # Title
    st.title("Geographic Development Index Dashboard - Education Sector")
    st.markdown(custom_css, unsafe_allow_html=True)

    # Initialize session state
    if 'selected_province_id' not in st.session_state:
        st.session_state.selected_province_id = None

    # Generate map with spinner for user feedback
    with st.spinner("Generating map..."):
        m, merged_gdf = create_map(gdf, df, location_dict, selected_index_code, year, reverse_colors, color_options[selected_color], st.session_state.selected_province_id)
        if m is None or merged_gdf is None:
            st.error("Map creation failed. Check logs above for details.")
            return

    # Display map with dynamic height
    st.markdown('<div class="map-frame">', unsafe_allow_html=True)
    map_data = st_folium(m, width='100%', height=600 if st.session_state.get('screen_height', 1080) > 800 else 400)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("**Click on a region on the map to display its trend over years in the chart below.**")

    # Generate line chart
    try:
        national_averages = calculate_national_averages(df, years)
    except Exception as e:
        st.error(f"Error calculating national averages: {e}")
        return

    if map_data['last_clicked']:
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

if __name__ == "__main__":
    main()

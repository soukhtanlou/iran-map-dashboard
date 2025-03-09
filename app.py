# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
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

def load_data():
    geojson_path = 'IRN_adm.json'
    excel_path = 'IrDevIndextest.xlsx'

    try:
        gdf = gpd.read_file(geojson_path)
        gdf.crs = 'epsg:4326'
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")
        st.stop()

    try:
        excel_file = pd.ExcelFile(excel_path)
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        st.stop()

    try:
        index_df = excel_file.parse('Index')
        sheet_options = index_df.set_index('index code')['index'].to_dict()
    except Exception as e:
        st.error(f"Error parsing Index sheet: {e}")
        st.stop()

    try:
        location_df = excel_file.parse('Location ID')
        location_dict = location_df.set_index('ID_1')['NAME_1'].to_dict()
    except Exception as e:
        st.error(f"Error parsing Location ID sheet: {e}")
        st.stop()

    return gdf, excel_file, sheet_options, location_dict

def calculate_national_averages(excel_file, sheet_name, years):
    df = excel_file.parse(sheet_name)
    return {year: df[year].mean() for year in years}

def get_province_data(excel_file, sheet_name, province_id, years):
    df = excel_file.parse(sheet_name)
    province_data = df[df['ID_1'] == province_id]
    return {year: province_data[year].iloc[0] for year in years} if not province_data.empty else None

def create_line_chart(national_averages, province_data=None, province_name=None):
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

def create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors, selected_province_id=None):
    try:
        sheet = sheet_options[selected_index_code]
        df = excel_file.parse(sheet)
        merged_gdf = gdf.merge(df[['ID_1', year]], on='ID_1', how='left')
    except Exception as e:
        st.error(f"Error merging GeoDataFrame with Excel data: {e}")
        return None, None

    try:
        choropleth_gdf = merged_gdf.drop(columns=['centroid', 'lat', 'lon'], errors='ignore')
        merged_gdf['centroid'] = merged_gdf.geometry.centroid
        merged_gdf['lat'] = merged_gdf['centroid'].y
        merged_gdf['lon'] = merged_gdf['centroid'].x
    except Exception as e:
        st.error(f"Error processing centroids: {e}")
        return None, None

    m = folium.Map(location=[32, 53], zoom_start=5, tiles='cartodbpositron')
    fill_color = 'Reds_r' if reverse_colors else 'Reds'

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

    # Tooltip layer with debugging
    tooltip_gdf = merged_gdf[['ID_1', 'NAME_1', 'lat', 'lon', year, 'geometry']].copy()
    if not tooltip_gdf.empty:
        try:
            geojson_str = tooltip_gdf.to_json()
            geojson_data = json.loads(geojson_str)
            if geojson_data.get("type") == "FeatureCollection":
                folium.GeoJson(
                    geojson_data,
                    style_function=lambda x: {
                        'fillColor': 'none',
                        'color': 'none',
                        'weight': 0,
                        'fillOpacity': 0
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=['NAME_1', 'lat', 'lon', year],
                        aliases=['Province:', 'Latitude:', 'Longitude:', f'{selected_index_code} ({year}):'],
                        localize=True
                    ),
                    name='Tooltips'
                ).add_to(m)
            else:
                st.error(f"Tooltip GeoJSON is not a FeatureCollection. Type: {geojson_data.get('type')}")
                st.write("Tooltip GeoJSON sample:", geojson_data)  # Debug output
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse GeoJSON for tooltips: {str(e)}")
            st.write("Raw GeoJSON string:", geojson_str)  # Debug output
        except Exception as e:
            st.error(f"Error adding tooltip layer: {e}")
    else:
        st.warning("Tooltip GeoDataFrame is empty.")

    if selected_province_id:
        try:
            selected_gdf = merged_gdf[merged_gdf['ID_1'] == selected_province_id]
            if not selected_gdf.empty:
                selected_gdf = selected_gdf.drop(columns=['centroid', 'lat', 'lon'], errors='ignore')
                folium.GeoJson(
                    selected_gdf.to_json(),
                    style_function=lambda x: {
                        'fillColor': 'none',
                        'color': 'black',
                        'weight': 3,
                        'fillOpacity': 0
                    },
                    name='Selected Province'
                ).add_to(m)
        except Exception as e:
            st.error(f"Error adding selected province outline: {e}")

    folium.LayerControl().add_to(m)
    return m, merged_gdf

def find_clicked_province(clicked_location, gdf):
    click_point = Point(clicked_location['lng'], clicked_location['lat'])
    for _, row in gdf.iterrows():
        if row['geometry'].contains(click_point):
            return row['ID_1']
    return None

def main():
    st.set_page_config(page_title="Geographic Dashboard", layout="wide")
    st.title("Geographic Development Index Dashboard - Education Sector")

    st.markdown(custom_css, unsafe_allow_html=True)

    uploaded_geojson = st.file_uploader("Upload GeoJSON file", type=['json'])
    uploaded_excel = st.file_uploader("Upload Excel file", type=['xlsx'])

    if not (uploaded_geojson and uploaded_excel):
        st.warning("Please upload both the GeoJSON and Excel files to continue.")
        st.stop()

    try:
        with open('IRN_adm.json', 'wb') as f:
            f.write(uploaded_geojson.getvalue())
        with open('IrDevIndextest.xlsx', 'wb') as f:
            f.write(uploaded_excel.getvalue())
    except Exception as e:
        st.error(f"Error saving uploaded files: {e}")
        st.stop()

    try:
        gdf, excel_file, sheet_options, location_dict = load_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    st.sidebar.header("Dashboard Controls")
    selected_index_code = st.sidebar.selectbox("Select Indicator:", options=list(sheet_options.keys()),
                                               format_func=lambda x: f"{x} - {sheet_options[x]}")
    year = st.sidebar.selectbox("Select Year:", options=['2019', '2020', '2021', '2022', '2023'])
    reverse_colors = st.sidebar.checkbox("Reverse Colors")

    if 'selected_province_id' not in st.session_state:
        st.session_state.selected_province_id = None

    try:
        m, merged_gdf = create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors, st.session_state.selected_province_id)
        if m is None or merged_gdf is None:
            st.error("Map creation failed. Check logs above for details.")
            return
    except Exception as e:
        st.error(f"Error in create_map: {e}")
        return

    st.markdown('<div class="map-frame">', unsafe_allow_html=True)
    map_data = st_folium(m, width=None, height=600)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("**Click on a region on the map to display its trend over years in the chart below.**")

    years = ['2019', '2020', '2021', '2022', '2023']
    try:
        national_averages = calculate_national_averages(excel_file, sheet_options[selected_index_code], years)
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
        province_data = get_province_data(excel_file, sheet_options[selected_index_code], st.session_state.selected_province_id, years)
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

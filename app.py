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

    # Tooltip layer
    tooltip_gdf = merged_gdf[['ID_1', 'NAME_1', year, 'geometry']].copy()
    if not tooltip_gdf.empty and tooltip_gdf['geometry'].notna().any():
        try:
            geojson_str = tooltip_gdf.to_json()
            geojson_data = json.loads(geojson_str)
            if geojson_data.get("type") == "FeatureCollection":
                folium.GeoJson(
                    geojson_data,
                    style_function=lambda x: {
                        'fillColor': 'transparent',
                        'color': 'none',
                        'weight': 0,
                        'fillOpacity': 0
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=['NAME_1', year],
                        aliases=['Province:', f'{selected_index_code} ({year}):'],
                        localize=True,
                        style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
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

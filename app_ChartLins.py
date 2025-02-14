# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import plotly.graph_objects as go
from shapely.geometry import Point

def load_data():
    geojson_path = 'IRN_adm.json'
    excel_path = 'IrDevIndextest.xlsx'
    
    # Load GeoJSON
    try:
        gdf = gpd.read_file(geojson_path)
        gdf.crs = 'epsg:4326'
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")
        st.stop()
    
    # Load Excel file
    try:
        excel_file = pd.ExcelFile(excel_path)
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        st.stop()
    
    # Parse sheets
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
        x=years, y=[national_averages[year] for year in years],
        name='National Average', line=dict(color='blue', width=2)
    ))
    
    if province_data and province_name:
        fig.add_trace(go.Scatter(
            x=years, y=[province_data[year] for year in years],
            name=province_name, line=dict(color='red', width=2)
        ))
    
    fig.update_layout(title='Trend Over Years', xaxis_title='Year', yaxis_title='Value', hovermode='x unified', height=400)
    return fig

def create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors):
    sheet = sheet_options[selected_index_code]
    df = excel_file.parse(sheet)
    merged_gdf = gdf.merge(df[['ID_1', year]], on='ID_1', how='left')
    
    m = folium.Map(location=[32, 53], zoom_start=5)
    fill_color = 'Reds_r' if reverse_colors else 'Reds'
    
    folium.Choropleth(
        geo_data=merged_gdf.to_json(), name='choropleth',
        data=merged_gdf, columns=['ID_1', year],
        key_on='feature.properties.ID_1', fill_color=fill_color,
        fill_opacity=0.8, line_opacity=0.0,
        legend_name=f'{selected_index_code} - {year}'
    ).add_to(m)
    
    return m, merged_gdf

def find_clicked_province(clicked_location, gdf):
    click_point = Point(clicked_location['lng'], clicked_location['lat'])
    for _, row in gdf.iterrows():
        if row['geometry'].contains(click_point):
            return row['ID_1']
    return None

def main():
    st.set_page_config(page_title="Geographic Dashboard", layout="wide")
    st.title("Geographic Development Index Dashboard")
    
    uploaded_geojson = st.file_uploader("Upload GeoJSON file", type=['json'])
    uploaded_excel = st.file_uploader("Upload Excel file", type=['xlsx'])
    
    if not (uploaded_geojson and uploaded_excel):
        st.warning("Please upload both the GeoJSON and Excel files to continue.")
        st.stop()
    
    with open('IRN_adm.json', 'wb') as f:
        f.write(uploaded_geojson.getvalue())
    with open('IrDevIndextest.xlsx', 'wb') as f:
        f.write(uploaded_excel.getvalue())
    
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
    
    m, merged_gdf = create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors)
    map_data = st_folium(m, width=1200, height=600)
    
    years = ['2019', '2020', '2021', '2022', '2023']
    national_averages = calculate_national_averages(excel_file, sheet_options[selected_index_code], years)
    
    if map_data['last_clicked']:
        province_id = find_clicked_province(map_data['last_clicked'], merged_gdf)
        if province_id:
            province_name = location_dict.get(province_id, "Unknown")
            province_data = get_province_data(excel_file, sheet_options[selected_index_code], province_id, years)
            if province_data:
                fig = create_line_chart(national_averages, province_data, province_name)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No data found for the selected province.")
        else:
            st.warning("Could not identify the selected province.")
    else:
        fig = create_line_chart(national_averages)
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()

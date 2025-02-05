import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os

def load_data():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct absolute file paths
    geojson_path = os.path.join(script_dir, 'IRN_adm.json')
    excel_path = os.path.join(script_dir, 'IrDevIndextest.xlsx')
    
    # Load the GeoJSON file
    try:
        gdf = gpd.read_file(geojson_path)
        gdf.crs = 'epsg:4326'
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")
        st.stop()
    
    # Load the Excel file
    try:
        excel_file = pd.ExcelFile(excel_path)
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        st.stop()
    
    # Load the 'Index' sheet
    try:
        index_df = excel_file.parse('Index')
        sheet_options = index_df.set_index('index code')['index'].to_dict()
    except Exception as e:
        st.error(f"Error parsing Index sheet: {e}")
        st.stop()
    
    # Load the Location ID sheet
    try:
        location_df = excel_file.parse('Location ID')
        location_dict = location_df.set_index('ID_1')['NAME_1'].to_dict()
    except Exception as e:
        st.error(f"Error parsing Location ID sheet: {e}")
        st.stop()
    
    return gdf, excel_file, sheet_options, location_dict

def create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors):
    sheet = sheet_options[selected_index_code]
    df = excel_file.parse(sheet)
    
    temp_df = df[['ID_1', year]]
    merged_gdf = gdf.merge(temp_df, on='ID_1', how='left')
    
    m = folium.Map(location=[32, 53], zoom_start=5)
    
    fill_color = 'YlGn_r' if reverse_colors else 'YlGn'
    
    choropleth = folium.Choropleth(
        geo_data=merged_gdf.to_json(),
        name='choropleth',
        data=merged_gdf,
        columns=['ID_1', year],
        key_on='feature.properties.ID_1',
        fill_color=fill_color,
        fill_opacity=0.8,
        line_opacity=0.0,
        legend_name=f'{selected_index_code} - {year}'
    ).add_to(m)
    
    for feature in choropleth.geojson.data['features']:
        try:
            feature_id = feature['properties']['ID_1']
            feature_name = location_dict.get(feature_id, "Name Not Found")
            data_value = feature['properties'][year]
            popup_text = f"{feature_name}: {data_value:.2f}"
            
            folium.features.GeoJson(
                feature,
                name=feature_name,
                tooltip=folium.Tooltip(popup_text)
            ).add_to(m)
            
        except KeyError as e:
            st.error(f"KeyError: {e}. Feature: {feature}")
            continue
    
    return m

def main():
    st.set_page_config(page_title="Geographic Dashboard", layout="wide")
    
    st.title("Geographic Development Index Dashboard")
    
    # Add file uploaders for the data files
    uploaded_geojson = st.file_uploader("Upload GeoJSON file (IRN_adm.json)", type=['json'])
    uploaded_excel = st.file_uploader("Upload Excel file (IrDevIndextest.xlsx)", type=['xlsx'])
    
    if not (uploaded_geojson and uploaded_excel):
        st.warning("Please upload both the GeoJSON and Excel files to continue.")
        st.stop()
    
    # Save uploaded files temporarily
    with open('IRN_adm.json', 'wb') as f:
        f.write(uploaded_geojson.getvalue())
    with open('IrDevIndextest.xlsx', 'wb') as f:
        f.write(uploaded_excel.getvalue())
    
    # Load data
    try:
        gdf, excel_file, sheet_options, location_dict = load_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    # Create sidebar controls
    st.sidebar.header("Dashboard Controls")
    
    selected_index_code = st.sidebar.selectbox(
        "Select Indicator:",
        options=list(sheet_options.keys()),
        format_func=lambda x: f"{x} - {sheet_options[x]}"
    )
    
    year = st.sidebar.selectbox(
        "Select Year:",
        options=['2019', '2020', '2021', '2022', '2023']
    )
    
    reverse_colors = st.sidebar.checkbox("Reverse Colors")
    
    # Create and display map
    try:
        m = create_map(gdf, excel_file, sheet_options, location_dict, 
                      selected_index_code, year, reverse_colors)
        st_folium(m, width=1200, height=600)
    except Exception as e:
        st.error(f"Error creating map: {e}")

if __name__ == "__main__":
    main()

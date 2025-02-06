import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import plotly.graph_objects as go

def load_data():
    """Load GeoJSON and Excel files."""
    try:
        gdf = gpd.read_file('IRN_adm.json')
        gdf.crs = 'epsg:4326'
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")
        st.stop()
    
    try:
        excel_file = pd.ExcelFile('IrDevIndextest.xlsx')
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
    """Calculate national averages."""
    df = excel_file.parse(sheet_name)
    return {year: df[year].mean() for year in years}

def get_province_data(excel_file, sheet_name, province_id, years):
    """Get province-specific data."""
    df = excel_file.parse(sheet_name)
    province_data = df[df['ID_1'] == province_id]
    return {year: province_data[year].iloc[0] for year in years} if not province_data.empty else None

def create_line_chart(national_averages, province_data=None, province_name=None):
    """Generate a line chart."""
    years = list(national_averages.keys())
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=years,
        y=[national_averages[year] for year in years],
        name='National Average',
        line=dict(color='blue', width=2)
    ))
    
    if province_data:
        fig.add_trace(go.Scatter(
            x=years,
            y=[province_data[year] for year in years],
            name=f'{province_name}',
            line=dict(color='red', width=2)
        ))
    
    fig.update_layout(
        title='Trend Over Years',
        xaxis_title='Year',
        yaxis_title='Value',
        hovermode='x unified',
        height=400
    )
    return fig

def create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors):
    """Create a Folium map."""
    sheet = sheet_options[selected_index_code]
    df = excel_file.parse(sheet)
    merged_gdf = gdf.merge(df[['ID_1', year]], on='ID_1', how='left')
    
    m = folium.Map(location=[32, 53], zoom_start=5)
    fill_color = 'Reds_r' if reverse_colors else 'Reds'
    
    choropleth = folium.Choropleth(
        geo_data=merged_gdf.to_json(),
        name='choropleth',
        data=merged_gdf,
        columns=['ID_1', year],
        key_on='feature.properties.ID_1',
        fill_color=fill_color,
        fill_opacity=0.8,
        line_opacity=0.2,
        legend_name=f'{selected_index_code} - {year}'
    ).add_to(m)
    
    for feature in choropleth.geojson.data['features']:
        feature_id = feature['properties']['ID_1']
        feature_name = location_dict.get(feature_id, "Unknown")
        data_value = feature['properties'].get(year, 'No Data')
        popup_text = f"{feature_name}: {data_value}"
        
        folium.GeoJson(
            feature,
            name=feature_name,
            tooltip=popup_text
        ).add_to(m)
    
    return m

def main():
    st.set_page_config(page_title="Geographic Dashboard", layout="wide")
    st.title("Geographic Development Index Dashboard")
    
    uploaded_geojson = st.file_uploader("Upload GeoJSON file (IRN_adm.json)", type=['json'])
    uploaded_excel = st.file_uploader("Upload Excel file (IrDevIndextest.xlsx)", type=['xlsx'])
    
    if not (uploaded_geojson and uploaded_excel):
        st.warning("Please upload both the GeoJSON and Excel files to continue.")
        st.stop()
    
    with open('IRN_adm.json', 'wb') as f:
        f.write(uploaded_geojson.getvalue())
    with open('IrDevIndextest.xlsx', 'wb') as f:
        f.write(uploaded_excel.getvalue())
    
    gdf, excel_file, sheet_options, location_dict = load_data()
    
    st.sidebar.header("Dashboard Controls")
    selected_index_code = st.sidebar.selectbox("Select Indicator:", list(sheet_options.keys()), format_func=lambda x: f"{x} - {sheet_options[x]}")
    year = st.sidebar.selectbox("Select Year:", ['2019', '2020', '2021', '2022', '2023'])
    reverse_colors = st.sidebar.checkbox("Reverse Colors")
    
    st.markdown(f"""
        <div style="padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin-bottom: 10px;">
            <strong>Currently Viewing:</strong><br>
            <strong>Indicator:</strong> {selected_index_code} - {sheet_options[selected_index_code]}<br>
            <strong>Year:</strong> {year}
        </div>
    """, unsafe_allow_html=True)
    
    m = create_map(gdf, excel_file, sheet_options, location_dict, selected_index_code, year, reverse_colors)
    map_data = st_folium(m, width=1200, height=600)
    
    years = ['2019', '2020', '2021', '2022', '2023']
    national_averages = calculate_national_averages(excel_file, sheet_options[selected_index_code], years)
    
    if map_data and 'last_clicked' in map_data and map_data['last_clicked']:
        clicked_location = map_data['last_clicked']
        province_id = int(clicked_location.get('id', -1))
        province_name = location_dict.get(province_id, "Unknown")
        province_data = get_province_data(excel_file, sheet_options[selected_index_code], province_id, years)
        if province_data:
            fig = create_line_chart(national_averages, province_data, province_name)
        else:
            fig = create_line_chart(national_averages)
    else:
        fig = create_line_chart(national_averages)
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()

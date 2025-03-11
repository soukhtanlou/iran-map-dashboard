# Geographic Development Index Dashboard - Education Sector

**Overview**

The Geographic Development Index Dashboard is an interactive web app built with [Streamlit](https://streamlit.io/) to visualize educational development indices across Iran's provinces. It combines geospatial data (`IRN_adm.json`) with Excel data (`IrDevIndextest.xlsx`) to offer a choropleth map and trend analysis.

**Features**

- **Interactive Choropleth Map**
  - Customizable colors (Red, Blue, Green, Purple).
  - Styled tooltips on hover with province and indicator details.
  - Click to highlight provinces and update trends.

- **Dynamic Controls**
  - Select indicators and years from dynamic dropdowns.
  - Reverse color scheme option.
  - Reset selection button.

- **Trend Analysis**
  - Plotly line chart comparing national and province trends.
  - Updates on province click.

- **Performance & Usability**
  - Cached GeoJSON and map generation.
  - Responsive map height.
  - Loading spinner and missing data warnings.

- **Data Handling**
  - Upload custom GeoJSON and Excel files.
  - Robust error handling.

**Screenshots**

![Dashboard Map](dashboard_map.jpng)  


**Installation**

**Prerequisites**
- Python 3.8+
- Virtual environment (recommended)

**Dependencies**
```bash
pip install streamlit pandas geopandas folium streamlit-folium plotly shapely

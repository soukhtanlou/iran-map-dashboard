Geographic Development Index Dashboard - Education Sector
Overview
The Geographic Development Index Dashboard is an interactive web application built with Streamlit to visualize educational development indices across provinces in Iran. It integrates geospatial data from a GeoJSON file (IRN_adm.json) with tabular data from an Excel file (IrDevIndextest.xlsx) to provide a choropleth map and trend analysis over multiple years. This tool is designed for educators, policymakers, and researchers to explore and compare educational metrics geographically and temporally.

Features
Interactive Choropleth Map:
Displays province-level data with customizable color schemes (Red, Blue, Green, Purple).
Hover tooltips show province names and selected indicator values with a modern, styled design.
Clicking a province highlights it with a black outline and updates the trend chart.
Dynamic Controls:
Select indicators and years from dropdown menus populated dynamically from the Excel data.
Toggle color reversal for the choropleth map.
Reset province selection with a dedicated button.
Trend Analysis:
A Plotly line chart compares national averages with province-specific trends over selectable years.
Updates automatically when a province is clicked on the map.
Performance and Usability:
Cached GeoJSON loading and map generation for faster reruns.
Responsive map height adjusts to screen size.
Loading spinner provides feedback during map creation.
Warnings for missing data enhance data transparency.
Data Handling:
Supports uploading custom GeoJSON and Excel files.
Robust error handling for file loading and parsing.

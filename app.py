import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Create a Dash application
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Load the CSV data (ensure the correct path to your CSV)
df = pd.read_csv('data.csv')  # replace with your actual CSV file path

# Preprocess the 'Asset_Class_Distribution' column:
# Convert to a list of asset classes and explode it into individual rows
df['Asset_Class_Distribution'] = df['Asset_Class_Distribution'].fillna('').apply(lambda x: str(x).split(','))
df_exploded = df.explode('Asset_Class_Distribution')

# Calculate the Total Asset Value (sum of Sector Balances)
total_asset_value = df['Sector_Balance'].sum()

# Pie chart: Sector Balance
fig_pie = px.pie(df, names='Cluster_Label', values='Sector_Balance', title='Sector Balance Distribution')

# Line plot: Cluster Label vs Regional Exposure
fig_line = go.Figure()
fig_line.add_trace(
    go.Scatter(x=df['Cluster_Label'], y=df['Regional_Exposure'], mode='lines+markers', name='Regional Exposure'))
fig_line.update_layout(title='Cluster Label vs Regional Exposure', xaxis_title='Cluster Label',
                       yaxis_title='Regional Exposure')

# Line plot: Cluster Label vs Number of Elements in Asset Class Distribution
asset_class_counts = df['Asset_Class_Distribution'].apply(len)
fig_asset_class = go.Figure()
fig_asset_class.add_trace(
    go.Scatter(x=df['Cluster_Label'], y=asset_class_counts, mode='lines+markers', name='Asset Class Count'))
fig_asset_class.update_layout(title='Cluster Label vs Number of Elements in Asset Class Distribution',
                              xaxis_title='Cluster Label', yaxis_title='Number of Elements')

# Set default figure for the bar chart
fig_bar = px.bar(df_exploded, x='Asset_Class_Distribution', title="Asset Class Distribution",
                 labels={"Asset_Class_Distribution": "Asset Class Value"}, category_orders={
        'Asset_Class_Distribution': sorted(df_exploded['Asset_Class_Distribution'].unique())
    })

# Layout of the Dash app
app.layout = html.Div([
    html.H1("Data Visualization Dashboard", className='dashboard-title'),

    # Total Asset Value as a Button at Top Left
    html.Div(f"Total Asset Value: ${total_asset_value:,.2f}",
             className='total-asset-value-button'),

    # Flex container for graphs
    html.Div([  # Flex container for graphs
        html.Div([  # Pie chart
            dcc.Graph(figure=fig_pie, className='dash-graph')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        html.Div([  # Line plot for Cluster Label vs Regional Exposure
            dcc.Graph(figure=fig_line, className='dash-graph')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '40px'}),

    # Asset Class Distribution line plot
    html.Div([  # Asset Class Distribution line plot
        dcc.Graph(figure=fig_asset_class, className='dash-graph')
    ], style={'marginBottom': '40px'}),

    # Flexbox layout for the last graph (Bar Chart) and the Dropdown
    html.Div([
        # Bar Plot for Asset Class Distribution Values
        html.Div([  # Bar plot of Asset Class Distribution values
            dcc.Graph(id='bar-plot', figure=fig_bar)
        ], style={'flex': 1, 'marginRight': '20px'}),

        # Dropdown for selecting Cluster for Bar Chart
        html.Div([
            html.Label('Select Cluster for Asset Class Distribution Bar Chart'),
            dcc.Dropdown(
                id='cluster-dropdown',
                options=[{'label': cluster, 'value': cluster} for cluster in df['Cluster_Label'].unique()],
                value=df['Cluster_Label'].iloc[0],  # Default value (first cluster in the list)
                style={'width': '100%'}
            ),
        ], style={'flex': 0.4, 'marginTop': '20px'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'flex-start'}),

    # Generate Report Button
    html.Div([
        html.Button("Generate Report", id="generate-report-button", className="generate-report-button"),
        dcc.Download(id="download-pdf")
    ], style={'marginTop': '40px', 'textAlign': 'center'})
])


# Callback to update the bar chart based on selected cluster
@app.callback(
    Output('bar-plot', 'figure'),
    Input('cluster-dropdown', 'value')
)
def update_bar_chart(selected_cluster):
    # Filter the data based on the selected cluster
    filtered_data = df_exploded[df_exploded['Cluster_Label'] == selected_cluster]

    # Count the occurrences of each asset class for the selected cluster
    asset_class_counts = filtered_data['Asset_Class_Distribution'].value_counts().reset_index()
    asset_class_counts.columns = ['Asset_Class_Distribution', 'Count']

    # Create a bar chart for the selected cluster
    fig_bar_selected = px.bar(asset_class_counts, x='Asset_Class_Distribution', y='Count',
                              title=f"Asset Class Distribution values for Cluster {selected_cluster}",
                              labels={"Asset_Class_Distribution": "Asset Class Value", "Count": "Count"},
                              category_orders={'Asset_Class_Distribution': sorted(
                                  asset_class_counts['Asset_Class_Distribution'].unique())})

    return fig_bar_selected


# Callback to generate and download the PDF
@app.callback(
    Output("download-pdf", "data"),
    Input("generate-report-button", "n_clicks")
)
def generate_pdf(n_clicks):
    if n_clicks:
        # Save the figures as PNG images
        fig_pie_img = BytesIO()
        fig_line_img = BytesIO()
        fig_asset_class_img = BytesIO()
        fig_bar_img = BytesIO()

        # Save images using plotly.io.write_image
        pio.write_image(fig_pie, fig_pie_img, format='png')
        pio.write_image(fig_line, fig_line_img, format='png')
        pio.write_image(fig_asset_class, fig_asset_class_img, format='png')
        pio.write_image(fig_bar, fig_bar_img, format='png')

        # Create an in-memory buffer for the PDF
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(100, 500, "Data Visualization Report")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, 470, f"Total Asset Value: ${total_asset_value:,.2f}")
        pdf.drawString(100, 440, "This is a sample report generated using ReportLab.")

        # Add images to the PDF
        pdf.drawImage(fig_pie_img, 100, 250, width=400, height=300)  # Pie chart
        pdf.drawImage(fig_line_img, 550, 250, width=400, height=300)  # Line plot
        pdf.drawImage(fig_asset_class_img, 100, 50, width=400, height=300)  # Asset class count
        pdf.drawImage(fig_bar_img, 550, 50, width=400, height=300)  # Bar plot

        pdf.save()
        buffer.seek(0)  # Move to the beginning of the buffer
        return dcc.send_bytes(lambda x: x.write(buffer.getvalue()), filename="report.pdf")
    return None


if __name__ == '__main__':
    app.run_server(debug=True)

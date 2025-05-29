import xml.etree.ElementTree as ET
import pandas as pd
import uuid
import dash
import json
import subprocess
import time
from dash import Dash, dcc, html, dash_table, Input, Output, State, no_update
import ipaddress
import plotly.express as px
import random
from pathlib import Path
from functools import lru_cache

# Global cache for ping results and config files
PING_CACHE = {}  # {ip: (timestamp, status)}
CONFIG_FILE_CACHE = {}  # {ip: [file_paths]}

# Load or parse XML into DataFrame
def load_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()
    data = []
    for device in root.findall('device'):
        entry = {
            'id': str(uuid.uuid4()),
            'name': device.find('name').text,
            'name_lower': device.find('name').text.lower() if device.find('name').text else '',
            'mac': device.find('mac').text,
            'ip': device.find('ip').text,
            'switch': device.find('switch').text,
            'port': device.find('port').text,
            'vlan': device.find('vlan').text,
            'nics': device.find('nics').text,
            'second_ip': device.find('second_ip').text,
            'second_mac': device.find('second_mac').text,
            'user_logged': device.find('user_logged').text,
            'criticality': device.find('criticality').text if device.find('criticality') is not None else '',
            'image': device.find('image').text if device.find('image') is not None else '',
            'model': device.find('model').text if device.find('model') is not None else '',
            'url': device.find('url').text if device.find('url') is not None else '',
            'html_file': device.find('html_file').text if device.find('html_file') is not None else '',
        }
        data.append(entry)
    return pd.DataFrame(data)

# Load DataFrame with caching
def get_dataframe():
    pickle_path = 'devices.pkl'
    xml_path = 'sample_network.xml'
    if Path(pickle_path).exists():
        print("Loading DataFrame from pickle")
        return pd.read_pickle(pickle_path)
    print("Parsing XML and saving to pickle")
    df = load_xml(xml_path)
    df.to_pickle(pickle_path)
    return df

df = get_dataframe()

# Random color generator for plots
def random_color():
    return f'#{random.randint(0, 0xFFFFFF):06x}'

app = Dash(__name__, suppress_callback_exceptions=True)

# List unique VLANs and criticalities to assign colors
unique_vlans = sorted(df['vlan'].unique())
unique_criticalities = sorted(df['criticality'].unique())
vlan_colors = {vlan: random_color() for vlan in unique_vlans}
criticality_colors = {crit: random_color() for crit in unique_criticalities}

# Precompute histogram data
@lru_cache(maxsize=1)
def get_histogram_data():
    vlan_counts = df['vlan'].value_counts().reset_index()
    vlan_counts.columns = ['vlan', 'count']
    switch_counts = df['switch'].value_counts().reset_index()
    switch_counts.columns = ['switch', 'count']
    criticality_counts = df['criticality'].value_counts().reset_index()
    criticality_counts.columns = ['criticality', 'count']
    return vlan_counts, switch_counts, criticality_counts

# Main layout with conditional rendering based on URL
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    dcc.Store(id='selected-file-store'),
    dcc.Store(id='file-path-map', data={})
])

# Dashboard layout
dashboard_layout = html.Div([
    html.H2("Network Devices", style={"textAlign": "center", "marginBottom": "20px"}),
    html.Div([
        dcc.Input(id='filter-name', type='text', placeholder='PC Name', style={'width': '15%'}),
        dcc.Input(id='filter-ip', type='text', placeholder='Start IP', style={'width': '15%'}),
        dcc.Input(id='filter-ip-end', type='text', placeholder='End IP (for range)', style={'width': '15%'}),
        dcc.Dropdown(id='filter-switch', options=[{'label': s, 'value': s} for s in sorted(df['switch'].unique())],
                     placeholder='Select Switch', multi=True, style={'width': '15%'}),
        dcc.Dropdown(id='filter-vlan', options=[{'label': v, 'value': v} for v in sorted(df['vlan'].unique())],
                     placeholder='Select VLAN', multi=True, style={'width': '15%'}),
        dcc.Dropdown(id='filter-criticality',
                     options=[{'label': c, 'value': c} for c in sorted(df['criticality'].unique())],
                     placeholder='Select Criticality', multi=True, style={'width': '15%'}),
        dcc.Input(id='filter-mac', type='text', placeholder='MAC Address', style={'width': '15%'}),
        dcc.Input(id='filter-port', type='text', placeholder='Port', style={'width': '10%'}),
    ], style={'display': 'flex', 'gap': '10px', 'flexWrap': 'wrap', 'marginBottom': '10px'}),
    html.Div([
        html.Label("Rows per page: ", style={'marginRight': '10px'}),
        dcc.Dropdown(
            id='rows-per-page',
            options=[{'label': str(i), 'value': i} for i in [5, 10, 20, 50]],
            value=5,
            style={'width': '100px'}
        ),
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
    html.Div(id='device-count'),
    dcc.Loading(
        id="loading-table",
        children=[
            dash_table.DataTable(
                id='device-table',
                columns=[
                    {"name": "Name", "id": "name", 'presentation': 'markdown'},
                    {"name": "IP", "id": "ip", 'presentation': 'markdown'},
                    {"name": "MAC", "id": "mac"},
                    {"name": "Switch", "id": "switch"},
                    {"name": "Port", "id": "port"},
                    {"name": "VLAN", "id": "vlan"},
                    {"name": "Criticality", "id": "criticality"},
                ],
                data=[],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
                page_size=5,
                page_action='native',
            )
        ],
        type="circle"
    ),
    dcc.Loading(
        id="loading-graphs",
        children=[html.Div(id='graphs-container', style={'marginTop': '40px'})],
        type="circle"
    ),
])

@app.callback(
    Output('device-table', 'data'),
    Output('device-count', 'children'),
    Output('graphs-container', 'children'),
    Input('filter-name', 'value'),
    Input('filter-ip', 'value'),
    Input('filter-ip-end', 'value'),
    Input('filter-mac', 'value'),
    Input('filter-switch', 'value'),
    Input('filter-port', 'value'),
    Input('filter-vlan', 'value'),
    Input('filter-criticality', 'value'),
)
def update_table(name, ip_start, ip_end, mac, switch, port, vlan, criticality):
    filtered = df.copy()
    if name:
        filtered = filtered[filtered['name_lower'].str.contains(name.lower(), na=False)]
    if ip_start and not ip_end:
        filtered = filtered[filtered['ip'].str.contains(ip_start, na=False)]
    elif ip_start and ip_end:
        try:
            start_ip = ipaddress.IPv4Address(ip_start)
            end_ip = ipaddress.IPv4Address(ip_end)
            filtered = filtered[
                filtered['ip'].apply(lambda ip: start_ip <= ipaddress.IPv4Address(ip) <= end_ip)
            ]
        except ValueError:
            pass
    if mac:
        filtered = filtered[filtered['mac'].str.contains(mac, case=False, na=False)]
    if switch:
        filtered = filtered[filtered['switch'].isin(switch)]
    if port:
        filtered = filtered[filtered['port'].str.contains(port, case=False, na=False)]
    if vlan:
        filtered = filtered[filtered['vlan'].isin(vlan)]
    if criticality:
        filtered = filtered[filtered['criticality'].isin(criticality)]

    filtered_display = filtered[['id', 'name', 'ip', 'mac', 'switch', 'port', 'vlan', 'criticality']].copy()
    filtered_display['name'] = filtered_display.apply(
        lambda row: f"[{row['name']}](/device/{row['id']})", axis=1)
    filtered_display['ip'] = filtered_display.apply(
        lambda row: f"[{row['ip']}](/device/{row['id']})", axis=1)

    vlan_counts, switch_counts, criticality_counts = get_histogram_data()
    filtered_vlans = filtered['vlan'].unique()
    filtered_switches = filtered['switch'].unique()
    filtered_criticalities = filtered['criticality'].unique()

    graphs = [
        dcc.Graph(figure=px.bar(
            vlan_counts[vlan_counts['vlan'].isin(filtered_vlans)],
            x="vlan", y="count", title="Devices per VLAN",
            color="vlan", color_discrete_map=vlan_colors
        )),
        dcc.Graph(figure=px.bar(
            switch_counts[switch_counts['switch'].isin(filtered_switches)],
            x="switch", y="count", title="Devices per Switch",
            color="switch", color_discrete_map=vlan_colors
        )),
        dcc.Graph(figure=px.bar(
            criticality_counts[criticality_counts['criticality'].isin(filtered_criticalities)],
            x="criticality", y="count", title="Devices per Criticality",
            color="criticality", color_discrete_map=criticality_colors
        )),
    ]

    return (
        filtered_display.to_dict('records'),
        html.H4(f"Total Devices Found: {len(filtered)}"),
        html.Div(graphs)
    )

@app.callback(
    Output('device-table', 'page_size'),
    Input('rows-per-page', 'value')
)
def update_page_size(rows):
    return rows

@app.callback(
    Output('page-content', 'children'),
    Output('file-path-map', 'data'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname and pathname.startswith('/device/'):
        device_id = pathname.split('/device/')[1]
        try:
            device = df[df["id"] == device_id].iloc[0]

            # Check ping status with caching
            current_time = time.time()
            cache_entry = PING_CACHE.get(device['ip'])
            if cache_entry and (current_time - cache_entry[0]) < 60:
                status_text = cache_entry[1]
                print(f"Using cached ping result for {device['ip']}: {status_text}")
            else:
                try:
                    ping_result = subprocess.run(['ping', '-n', '1', '-w', '10', device['ip']], capture_output=True,
                                                 text=True)
                    is_online = ping_result.returncode == 0
                    status_text = "Online" if is_online else "Offline"
                    PING_CACHE[device['ip']] = (current_time, status_text)
                    print(f"Ping result for {device['ip']}: {status_text}")
                except Exception as e:
                    status_text = "Offline (Ping Error)"
                    PING_CACHE[device['ip']] = (current_time, status_text)
                    print(f"Ping error for {device['ip']}: {str(e)}")

            # Get config files with caching
            ip = device['ip']
            if ip in CONFIG_FILE_CACHE:
                config_files = CONFIG_FILE_CACHE[ip]
                print(f"Using cached config files for {ip}")
            else:
                config_files = []
                backup_dir = Path(f"C:/backup/{ip}")
                if backup_dir.exists():
                    for file_path in backup_dir.rglob("*"):
                        if file_path.suffix.lower() in ['.ini', '.xml']:
                            config_files.append(str(file_path))
                CONFIG_FILE_CACHE[ip] = config_files
                print(f"Listed config files for {ip}: {len(config_files)} files")

            # Device details layout
            details = [
                html.H3(device['name'], style={'marginBottom': '20px'}),
                html.Span([
                    html.Span("● ", style={'color': 'red', 'fontSize': '14px', 'marginRight': '5px'}),
                    html.Span(f"Status: {status_text}", style={'fontWeight': 'bold'})
                ], style={'marginBottom': '10px'}),
                html.Img(src=device['image'], style={'maxWidth': '300px', 'marginBottom': '20px'}) if device[
                    'image'] else html.P("No image available"),
                html.P(f"Model: {device['model']}", style={'fontWeight': 'bold'}) if device['model'] else html.P(
                    "Model: Not specified"),
                html.P(f"Criticality: {device['criticality']}", style={'fontWeight': 'bold'}) if device[
                    'criticality'] else html.P("Criticality: Not specified"),
                html.P(f"IP Address: {device['ip']}", style={'fontWeight': 'bold'}),
                html.P(f"MAC Address: {device['mac']}"),
                html.P(f"Switch: {device['switch']}"),
                html.P(f"Port: {device['port']}"),
                html.P(f"VLAN: {device['vlan']}"),
                html.P(f"NICs: {device['nics']}"),
            ]
            if device['second_ip'] and device['second_ip'].strip():
                details.append(html.P(f"Second IP: {device['second_ip']}"))
            if device['second_mac'] and device['second_mac'].strip():
                details.append(html.P(f"Second MAC: {device['second_mac']}"))
            details.append(html.P(f"User Logged: {device['user_logged']}"))

            # Add URL link if present
            if device['url'] and device['url'].strip():
                details.append(html.P([
                    html.Span("Device URL: ", style={'fontWeight': 'bold'}),
                    html.A(device['url'], href=device['url'], target="_blank")
                ], style={'marginTop': '10px'}))

            # Add HTML file button if present
            has_html_file = device['html_file'] and device['html_file'].strip()  # EDIT: Store condition for use in callback
            if has_html_file:
                html_file_path = device['html_file']
                details.append(html.P([
                    html.Span("Device HTML: ", style={'fontWeight': 'bold'}),
                    html.Button("Open HTML File", id='open-html-btn', n_clicks=0, style={'marginLeft': '10px'})
                ], style={'marginTop': '10px'}))

            # Config file section
            has_config_files = len(config_files) > 0  # EDIT: Store condition for use in callback
            if has_config_files:
                file_path_map = {str(i): file_path for i, file_path in enumerate(config_files)}
                config_section = [
                    html.H4("Configuration Files", style={'marginTop': '20px'}),
                    html.Ul([
                        html.Li([
                            html.Span(file_path, style={'marginRight': '10px'}),
                            html.Button("View", id={'type': 'view-config-btn', 'index': str(i)}, n_clicks=0,
                                        style={'marginLeft': '5px'}),
                            html.Button("View in Explorer", id={'type': 'view-explorer-btn', 'index': str(i)},
                                        n_clicks=0, style={'marginLeft': '5px'})
                        ]) for i, file_path in enumerate(config_files)
                    ])
                ]
            else:
                file_path_map = {}
                config_section = [html.P("No configuration files found.", style={'marginTop': '20px'})]

            # EDIT: Store has_html_file and has_config_files in file-path-map for callback use
            file_path_map['has_html_file'] = has_html_file
            file_path_map['has_config_files'] = has_config_files

            return (
                html.Div([
                    html.Div(details + config_section,
                             style={'padding': '20px', 'backgroundColor': '#f9f9f9', 'border': '1px solid #ccc'}),
                    html.Div(id='config-content', style={'marginTop': '20px', 'whiteSpace': 'pre-wrap'}),
                    html.A("Back to Dashboard", href="/", target="_self")
                ]),
                file_path_map
            )
        except IndexError:
            return (
                html.Div([
                    html.H3("Error"),
                    html.P("Device not found."),
                    html.A("Back to Dashboard", href="/", target="_self")
                ]),
                {}
            )
    return dashboard_layout, {}

@app.callback(
    Output('config-content', 'children'),
    Input({'type': 'view-config-btn', 'index': dash.ALL}, 'n_clicks'),
    Input({'type': 'view-explorer-btn', 'index': dash.ALL}, 'n_clicks'),
    Input('open-html-btn', 'n_clicks'),
    State({'type': 'view-config-btn', 'index': dash.ALL}, 'id'),
    State({'type': 'view-explorer-btn', 'index': dash.ALL}, 'id'),
    State('file-path-map', 'data'),
    State('url', 'pathname'),
    prevent_initial_call=True  # EDIT: Prevent callback from running on page load
)
def display_config_content(view_n_clicks, explorer_n_clicks, html_n_clicks, view_button_ids, explorer_button_ids,
                           file_path_map, pathname):
    ctx = dash.callback_context
    # EDIT: Early return if no inputs triggered or no relevant components exist
    if not ctx.triggered:
        print("No button clicks triggered.")
        return no_update

    # EDIT: Check if relevant components exist
    has_html_file = file_path_map.get('has_html_file', False)
    has_config_files = file_path_map.get('has_config_files', False)
    triggered_prop_id = ctx.triggered[0]['prop_id']
    print(f"Triggered prop_id: {triggered_prop_id}, has_html_file: {has_html_file}, has_config_files: {has_config_files}")

    try:
        if triggered_prop_id == 'open-html-btn.n_clicks':
            # EDIT: Only process if HTML button exists
            if not has_html_file:
                print("open-html-btn triggered but no HTML file available.")
                return html.P("Error: HTML file button not available for this device.")
            if not pathname or not pathname.startswith('/device/'):
                print("Invalid pathname for device page.")
                return html.P("Error: Invalid device page.")
            device_id = pathname.split('/device/')[1]
            device = df[df["id"] == device_id].iloc[0]
            html_file_path = device['html_file']
            if not html_file_path or not Path(html_file_path).is_file():
                print(f"HTML file does not exist: {html_file_path}")
                return html.P(f"HTML file not found: {html_file_path}")
            try:
                subprocess.run(['start', '', html_file_path], shell=True)
                print(f"Opened HTML file: {html_file_path}")
                return ""  # Return empty string to clear content
            except Exception as e:
                print(f"Failed to open HTML file: {str(e)}")
                return html.P(f"Error opening HTML file: {str(e)}")
        else:
            # EDIT: Only process config buttons if config files exist
            if not has_config_files:
                print("Config button triggered but no config files available.")
                return html.P("Error: No configuration files available for this device.")
            try:
                triggered_id_dict = json.loads(triggered_prop_id.split('.')[0].replace("'", '"'))
                button_type = triggered_id_dict['type']
                button_index = triggered_id_dict['index']
            except (json.JSONDecodeError, KeyError):
                print(f"Invalid triggered ID format: {triggered_prop_id}")
                return html.P("Error: Invalid button ID format.")

            file_path = file_path_map.get(button_index) if file_path_map else None
            if not file_path:
                print(f"No file path found for index: {button_index}")
                return html.P(f"Error: No file path found for button index {button_index}")
            print(f"Button clicked: {button_type} for file: {file_path}")
            file_path = str(Path(file_path))
            dir_path = str(Path(file_path).parent)
            print(f"Processing file: {file_path}, directory: {dir_path}")

            if button_type == 'view-config-btn':
                if not Path(file_path).is_file():
                    print(f"File does not exist or is not a file: {file_path}")
                    return html.P(f"File not found: {file_path}")
                encodings = ['utf-8', 'latin-1', 'ascii']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        print(f"Successfully read file with {encoding} encoding")
                        return html.Pre(content,
                                        style={'backgroundColor': '#f0f0f0', 'padding': '10px',
                                               'border': '1px solid #ccc'})
                    except UnicodeDecodeError:
                        print(f"Failed to read file with {encoding} encoding")
                        continue
                    except FileNotFoundError:
                        print(f"File not found during read attempt: {file_path}")
                        return html.P(f"File not found: {file_path}")
                    except PermissionError:
                        print(f"Permission denied for file: {file_path}")
                        return html.P(f"Permission denied: {file_path}")
                    except Exception as e:
                        print(f"Unexpected error reading file: {str(e)}")
                        return html.P(f"Error reading file: {str(e)}")
                print("All encoding attempts failed")
                return html.P("Unable to read file: Invalid encoding or corrupted file.")
            elif button_type == 'view-explorer-btn':
                try:
                    subprocess.run(['explorer.exe', dir_path])
                    print(f"Opened Windows Explorer to: {dir_path}")
                    return ""
                except Exception as e:
                    print(f"Failed to open Windows Explorer: {str(e)}")
                    return html.P(f"Error opening directory in Explorer: {str(e)}")
            else:
                print(f"Unknown button type: {button_type}")
                return html.P(f"Error: Unknown button type {button_type}")
    except Exception as e:
        print(f"Error processing button click: {str(e)}")
        return html.P(f"Error processing button click: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)

# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %%
from dash import Dash, dcc, html, Input, Output, no_update, callback, State, Patch
import dash_daq as daq
import plotly.express as px
from fairdatanow import data_now
import plotly.graph_objects as go
import numpy as np
import tomlkit
import base64

url = 'https://laboppad.nl/ukiyo-e-world' 

toml_txt = '''
# here are the 10 corresponding spectral data cubes processed by Gauthier and Tessa 
[data.npz] 
RV-1-4468-544 = ".*RIS/interim/.*RV-1-4468-544.*[.]npz"
RV-1-4469-484 = ".*RIS/interim/.*RV-1-4469-484.*[.]npz"
RV-1-4469-58 = ".*RIS/interim/.*RV-1-4469-58.*[.]npz"
RV-1-4469-x6 = ".*RIS/interim/.*RV-1-4469-x6.*[.]npz"
RV-1-4469Q = ".*RIS/interim/.*RV-1-4469Q.*[.]npz"
RV-1-4470-12 = ".*RIS/interim/.*RV-1-4470-12.*[.]npz"
RV-1-4470-27 = ".*RIS/interim/.*RV-1-4470-27.*[.]npz"
RV-360-2345g = ".*RIS/interim/.*RV-360-2345g.*[.]npz"
RV-360-2359-2 = ".*RIS/interim/.*RV-360-2359-2.*[.]npz"
RV-360-6886 = ".*RIS/interim/.*RV-360-6886.*[.]npz"

[data.tif]
# these are regexes that download all .tif files per object number 
RV-1-4468-544 = ".*akama.*RV-1-4468-544[.]tif"
RV-1-4469-484 = ".*akama.*RV-1-4469-484[.]tif"
RV-1-4469-58 = ".*akama.*RV-1-4469-58[.]tif"
RV-1-4469-x6 = ".*akama.*RV-1-4469-x6[.]tif"
RV-1-4469Q = ".*akama.*RV-1-4469Q[.]tif"
RV-1-4470-12 = ".*akama.*RV-1-4470-12[.]tif"
RV-1-4470-27 = ".*akama.*1-4470-27[.]tif"      # TIF NAME WITHOUT RV prefix!  
RV-360-2345g = ".*akama.*RV-360-2345-?g[.]tif"
RV-360-2359-2 = ".*akama.*RV-360-2359-2[.]tif"
RV-360-6886 = ".*akama.*RV-360-6886[.]tif"
'''

data = data_now(url, toml_txt)

tif_file = data['tif']['RV-1-4470-27'][0]
npz_file = data['npz']['RV-1-4470-27'][0]

npz = np.load(npz_file)
cube = npz['image'][:,:, ::-1].transpose(1, 2, 0)
wavelengths = npz['wavelengths'] 
h, w, d = cube.shape
bounds = [0, 0, w, h]
pseudo_rgb = cube[:,:, [70, 53, 19]] 

# %%
fig_img = px.imshow(pseudo_rgb, binary_string=True).update_layout(dragmode="drawrect")

app = Dash(__name__)
app.layout = html.Div(
    [
        html.H2("Mean Spectrum ROI's"),
        html.Div(
            dcc.Upload(
            id='upload_data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            )
        ),
        html.Div(
            [daq.ColorPicker(
            id="colorpicker",
            label="ROI Line Color",
            value=dict(hex="#119DFF"),
            ),
            dcc.Input(id="annotation_text", type="text", placeholder="annotation text")]
        ),
        html.Div(
            [dcc.Graph(id="pseudo_rgb_graph", figure=fig_img, config={"modeBarButtonsToAdd": ["drawrect", "eraseshape"], "scrollZoom":True})]
        ),
        html.Div(
            [dcc.Graph(id="mean_spectrum_graph", figure={})]
        )
    ]
)

@callback(
    Output(component_id="pseudo_rgb_graph", component_property="figure"),
    Input(component_id="colorpicker", component_property="value")
)
def on_annotation_option(color: dict) -> Patch():
    patch = Patch()
    patch['layout']['newshape']['line']['color'] = color['hex']
    return patch

@callback(
    Output(component_id="mean_spectrum_graph", component_property="figure"),
    Input(component_id="pseudo_rgb_graph", component_property="relayoutData"),
    State(component_id="colorpicker", component_property="value"),
    State(component_id="annotation_text", component_property="value"),
    State(component_id="mean_spectrum_graph", component_property="figure"),
    State(component_id="upload_data", component_property="contents"),
    State(component_id="pseudo_rgb_graph", component_property="figure")
)
def on_drawrect(relayout_data: dict, color: dict, annotation_text: str, mean_spectrum_figure: dict, toml_file, graph) -> go.Figure() | dash.no_update():
    if toml_file:
        content_type, content_string = toml_file.split(",")

        toml_string = base64.b64decode(content_string).decode("utf-8")

        print(toml_string)
    print(graph["layout"]['shapes'])
    # Parse latest shape
    shapes = (relayout_data or {}).get("shapes")
    if not shapes:
        return no_update
    shape = shapes[-1]
    
    # Read coordinates of the selected ROI from the shape
    x0, x1 = sorted([max(0, min(w, int(shape["x0"]))), max(0, min(w, int(shape["x1"])))])
    y0, y1 = sorted([max(0, min(h, int(shape["y0"]))), max(0, min(h, int(shape["y1"])))])

    # Get the mean spectrum of the selected ROI
    roi_cube = cube[y0:y1, x0:x1, :]
    if roi_cube.size == 0:
        return no_update
    mean_spectrum = roi_cube.mean(axis=(0, 1))

    # Turn the graph dictionary into a graph object
    mean_spectrum_figure = go.Figure(mean_spectrum_figure)
    
    # Add a line to the mean_spectrum_figure graph object
    mean_spectrum_figure.add_trace(go.Scatter(
        x=wavelengths,
        y=mean_spectrum,
        mode='lines',
        name=annotation_text,
        line_color=color['hex']
    ))

    # Update the look of the mean spectrum graph
    mean_spectrum_figure.update_layout(
        xaxis_title="Wavelength",
        yaxis_title="Intensity",
        title="ROI Mean Spectra"
    )

    # TOML interaction
    doc = tomlkit.document()

    roi_table = tomlkit.table()

    sub_tab = tomlkit.table()
    sub_tab['color'] = color['hex']
    sub_tab['x0'] = x0
    sub_tab['x1'] = x1
    sub_tab['y0'] = y0
    sub_tab['y1'] = y1

    if annotation_text:
        roi_table[annotation_text] = sub_tab

    # Need to find a way to fix double annotations
    else:
        n = x0+x1+y0+y1
        roi_table[str(n)] = sub_tab

    doc['roi'] = roi_table

    print(tomlkit.dumps(doc))
    
    return mean_spectrum_figure


app.run(jupyter_mode="external", debug=True)


# %% [markdown]
# Now able to read and write using `tomlkit`.
#
# The question is: In what way do users give their toml file and do we want to directly update this file or make the output downloadable?
#

# %% [markdown]
# dashboard = fair_dashboardnow('/project.toml')
#
# dashboard = fdn()
#
# app = Dash()
# app.layout = html.Div([
#     html.Button("Download Text", id="btn-download-txt"),
#     dcc.Download(id="download-text")
# ])

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
        html.H2("Mean Spectrum ROI"),
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
def on_annotation_option(color: dict) -> dash.Patch():
    patch = Patch()
    patch['layout']['newshape']['line']['color'] = color['hex']
    return patch

@callback(
    Output(component_id="mean_spectrum_graph", component_property="figure"),
    Input(component_id="pseudo_rgb_graph", component_property="relayoutData"),
    State(component_id="colorpicker", component_property="value"),
    State(component_id="annotation_text", component_property="value"),
    State(component_id="mean_spectrum_graph", component_property="figure")
)
def on_drawrect(relayout_data: dict, color: dict, text: int, mean_spectrum_figure: dict) -> go.Figure() | dash.no_update():
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
        name=text,
        line_color=color['hex']
    ))

    # Update the look of the mean spectrum graph
    mean_spectrum_figure.update_layout(
        xaxis_title="Wavelength",
        yaxis_title="Intensity",
        title="ROI Mean Spectra"
    )
    
    return mean_spectrum_figure

if __name__ == "__main__":
    app.run(debug=True)

# %%

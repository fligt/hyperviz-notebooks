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

# %% [markdown]
# In this notebook I'll be trying to recreate the ROI selector we had a working version of in holoviews but using plotly
#
# https://plotly.com/python/selections/

# %%
import dash
from dash import Dash, dcc, html, Input, Output, no_update, callback
import plotly.express as px
import numpy as np
from fairdatanow import data_now

# %%
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
'''

# %%
data = data_now(url, toml_txt)

# %%
npz_file = data['npz']['RV-1-4470-27'][0]

# %%
npz = np.load(npz_file)
cube = npz['image'][:,:, ::-1].transpose(1, 2, 0)
wavelengths = npz['wavelengths'] 
h, w, d = cube.shape
bounds = [0, 0, w, h]
pseudo_rgb = cube[:,:, [70, 53, 19]] 

# %% [markdown]
# I'll try to apply the following tutorial on our own npz cubes: https://dash.plotly.com/annotations
# https://dash.plotly.com/dash-core-components/textarea

# %%

# Base figures
fig_img = px.imshow(pseudo_rgb, binary_string=True).update_layout(dragmode="drawrect")
fig_spec = px.line(x=wavelengths, y=cube.mean(axis=(0, 1)), labels={"x": "Wavelength", "y": "Intensity"})

app = Dash(__name__)
app.layout = html.Div(
    [
        html.H3("Drag a rectangle to show the mean spectrum of the ROI"),
        html.Div(
            [dcc.Graph(id="pseudo_rgb", figure=fig_img, config={"modeBarButtonsToAdd": ["drawrect", "eraseshape"]})],
            style={"width": "40%", "display": "inline-block"},
        ),
        html.Div(
            [dcc.Graph(id="spectrum", figure=fig_spec)],
            style={"width": "40%", "display": "inline-block"},
        ),
        html.Div(id='text-example-output', style={"width": "20%", "display": "inline-block", 'background-color': 'white'})
    ]
)

@callback(
    Output("spectrum", "figure"),
    Output("text-example-output", "children"),
    Input("pseudo_rgb", "relayoutData"),
    prevent_initial_call=True
)
def on_new_annotation(relayout_data):
    shapes = (relayout_data or {}).get("shapes")
    if not shapes:
        return no_update

    s = shapes[-1]
    
    x0, x1 = sorted([max(0, min(w, int(s["x0"]))), max(0, min(w, int(s["x1"])))])
    y0, y1 = sorted([max(0, min(h, int(s["y0"]))), max(0, min(h, int(s["y1"])))])

    roi_cube = cube[y0:y1, x0:x1, :]
    if roi_cube.size == 0:
        return no_update

    fig = px.line(
        x=wavelengths, 
        y=roi_cube.mean(axis=(0, 1)), 
        labels={"x": "Wavelength", "y": "Intensity"},
        title=f"ROI Mean Spectrum ({x1-x0}x{y1-y0} px)"
    )

    coords = f'x0:{x0}, x1:{x1}, y0:{y0}, y1:{y1}'

    return fig, coords

if __name__ == "__main__":
    app.run(debug=True)

# %%

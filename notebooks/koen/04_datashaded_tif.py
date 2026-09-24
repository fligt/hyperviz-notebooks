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
from functools import lru_cache

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, Patch, State, ctx, dcc, html, no_update
from fairdatanow import data_now
from PIL import Image

url = "https://laboppad.nl/ukiyo-e-world"
toml_txt = """
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
RV-1-4468-544 = ".*akama.*RV-1-4468-544[.]tif"
RV-1-4469-484 = ".*akama.*RV-1-4469-484[.]tif"
RV-1-4469-58 = ".*akama.*RV-1-4469-58[.]tif"
RV-1-4469-x6 = ".*akama.*RV-1-4469-x6[.]tif"
RV-1-4469Q = ".*akama.*RV-1-4469Q[.]tif"
RV-1-4470-12 = ".*akama.*RV-1-4470-12[.]tif"
RV-1-4470-27 = ".*akama.*1-4470-27[.]tif"
RV-360-2345g = ".*akama.*RV-360-2345-?g[.]tif"
RV-360-2359-2 = ".*akama.*RV-360-2359-2[.]tif"
RV-360-6886 = ".*akama.*RV-360-6886[.]tif"
"""

data = data_now(url, toml_txt)
DEFAULT_OBJECT = "RV-1-4470-27"
VIEW_SIZE = (900, 700)


@lru_cache(maxsize=2)
def load_images(object_num):
    with np.load(data["npz"][object_num][0]) as npz:
        cube = npz["image"][:, :, ::-1].transpose(1, 2, 0)
        pseudo_rgb = cube[:, :, [70, 53, 19]]

    with Image.open(data["tif"][object_num][0]) as tif:
        return pseudo_rgb, tif.convert("RGB")


def image_figure(image, x_range=None, y_range=None):
    """Crop and resize an RGB image without resampling channels separately."""
    width, height = image.size
    x0, x1 = sorted(np.clip(x_range or (0, width), 0, width))
    y0, y1 = sorted(np.clip(y_range or (0, height), 0, height))
    x0, x1 = int(np.floor(x0)), int(np.ceil(x1))
    y0, y1 = int(np.floor(y0)), int(np.ceil(y1))
    x1, y1 = max(x0 + 1, x1), max(y0 + 1, y1)

    rendered = image.crop((x0, y0, x1, y1))
    rendered.thumbnail(VIEW_SIZE, Image.Resampling.LANCZOS)

    figure = go.Figure()
    figure.add_layout_image(
        source=rendered,
        xref="x",
        yref="y",
        x=x0,
        y=y0,
        sizex=x1 - x0,
        sizey=y1 - y0,
        xanchor="left",
        yanchor="top",
        sizing="stretch",
        layer="below",
    )
    figure.update_layout(
        dragmode="pan",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        xaxis={"range": [x0, x1], "visible": False},
        yaxis={"range": [y1, y0], "visible": False, "scaleanchor": "x"},
    )
    return figure


def pseudo_figure(image):
    figure = px.imshow(image, binary_string=True)
    figure.update_layout(
        dragmode="pan",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x"},
    )
    return figure


def graph(graph_id, figure):
    return dcc.Graph(
        id=graph_id,
        figure=figure,
        config={"scrollZoom": True, "displaylogo": False, "responsive": True},
        style={"height": "700px", "width": "100%"},
    )


initial_pseudo, initial_tif = load_images(DEFAULT_OBJECT)
app = Dash(__name__)
app.layout = html.Div(
    [
        dcc.Dropdown(
            list(data["npz"]), value=DEFAULT_OBJECT, clearable=False, id="object"
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H3("Pseudo RGB"),
                        graph("pseudo", pseudo_figure(initial_pseudo)),
                    ]
                ),
                html.Div([html.H3("TIFF"), graph("tif", image_figure(initial_tif))]),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                "gap": "8px",
            },
        ),
    ]
)


@app.callback(
    Output("pseudo", "figure"),
    Output("tif", "figure"),
    Input("object", "value"),
)
def select_object(object_num):
    pseudo, tif = load_images(object_num)
    return pseudo_figure(pseudo), image_figure(tif)


def visible_range(event, width, height):
    if event.get("xaxis.autorange") or event.get("yaxis.autorange"):
        return [0, width], [height, 0]
    x_range = event.get("xaxis.range") or [
        event.get("xaxis.range[0]"),
        event.get("xaxis.range[1]"),
    ]
    y_range = event.get("yaxis.range") or [
        event.get("yaxis.range[0]"),
        event.get("yaxis.range[1]"),
    ]
    return (x_range, y_range) if None not in x_range + y_range else (None, None)


@app.callback(
    Output("pseudo", "figure", allow_duplicate=True),
    Output("tif", "figure", allow_duplicate=True),
    Input("pseudo", "relayoutData"),
    Input("tif", "relayoutData"),
    State("object", "value"),
    prevent_initial_call=True,
)
def sync_views(pseudo_event, tif_event, object_num):
    pseudo, tif = load_images(object_num)
    ph, pw = pseudo.shape[:2]
    tw, th = tif.size
    from_pseudo = ctx.triggered_id == "pseudo"
    event = pseudo_event if from_pseudo else tif_event
    sw, sh = (pw, ph) if from_pseudo else (tw, th)
    x_range, y_range = visible_range(event or {}, sw, sh)
    if x_range is None:
        return no_update, no_update

    tx = [x * tw / sw for x in x_range]
    ty = [y * th / sh for y in y_range]
    px_range = [x * pw / sw for x in x_range]
    py_range = [y * ph / sh for y in y_range]

    rendered = image_figure(tif, tx, ty).layout.images[0]
    tif_patch = Patch()
    for key in ("source", "x", "y", "sizex", "sizey"):
        tif_patch["layout"]["images"][0][key] = getattr(rendered, key)

    pseudo_patch = Patch()
    if not from_pseudo:
        pseudo_patch["layout"]["xaxis"]["range"] = px_range
        pseudo_patch["layout"]["yaxis"]["range"] = py_range
    if from_pseudo:
        tif_patch["layout"]["xaxis"]["range"] = tx
        tif_patch["layout"]["yaxis"]["range"] = ty
    return pseudo_patch, tif_patch


if __name__ == "__main__":
    app.run(jupyter_mode="external")

# %%

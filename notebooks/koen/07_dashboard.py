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
import base64
import binascii
import re
import uuid

import dash_daq as daq
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import tomlkit
from dash import (
    Dash,
    Input,
    Output,
    Patch,
    State,
    ctx,
    dcc,
    html,
    no_update,
)
from dash.exceptions import PreventUpdate
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
DEFAULT_COLOR = "#119DFF"
SHAPE_COORDINATE = re.compile(r"^shapes\[(\d+)]\.(x0|x1|y0|y1)$")
VIEW_SIZE = (900, 700)


def load_cube(object_num):
    with np.load(data["npz"][object_num][0]) as npz:
        cube = npz["image"][:, :, ::-1].transpose(1, 2, 0)
        wavelengths = npz["wavelengths"].copy()
    return cube, wavelengths


def load_tif(object_num):
    with Image.open(data["tif"][object_num][0]) as source:
        return source.convert("RGB")


def image_figure(image, x_range=None, y_range=None):
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


def normalized_roi(shape, name, color, roi_id=None):
    return {
        "id": roi_id or uuid.uuid4().hex,
        "name": name,
        "color": color,
        **{key: float(shape[key]) for key in ("x0", "x1", "y0", "y1")},
    }


def unique_roi_name(rois):
    names = {roi["name"] for roi in rois}
    number = 1
    while f"ROI {number}" in names:
        number += 1
    return f"ROI {number}"


def rois_from_toml(content):
    document = tomlkit.parse(content)
    return {
        object_num: [
            normalized_roi(roi, name, roi.get("color", DEFAULT_COLOR))
            for name, roi in object_rois.items()
        ]
        for object_num, object_rois in document.get("roi", {}).items()
    }


def graph(graph_id, draw=False):
    config = {"scrollZoom": True, "displaylogo": False, "responsive": True}
    if draw:
        config["modeBarButtonsToAdd"] = ["drawrect", "eraseshape"]
    return dcc.Graph(
        id=graph_id,
        figure={},
        config=config,
        style={"height": "700px", "width": "100%"},
    )


app = Dash(__name__)
app.layout = html.Div(
    [
        dcc.Store(id="roi-store", data={}),
        dcc.Store(id="toml-store", data=toml_txt),
        dcc.Store(id="pseudo-size"),
        html.H1("Spectral Image Dashboard"),
        dcc.Dropdown(
            list(data["npz"]), value=DEFAULT_OBJECT, clearable=False, id="object"
        ),
        html.Div(
            [
                html.Div(
                    [html.H3("Pseudo RGB"), graph("pseudo", draw=True)],
                    style={"minWidth": 0},
                ),
                html.Div(
                    [html.H3("TIFF"), graph("tif")],
                    style={"minWidth": 0},
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                "gap": "8px",
            },
        ),
        html.Div(
            [
                daq.ColorPicker(
                    id="color", label="ROI color", value={"hex": DEFAULT_COLOR}
                ),
                dcc.Input(id="roi-name", placeholder="ROI name", type="text"),
                dcc.Upload(id="upload", children=html.Button("Upload ROI TOML")),
                html.Button("Save ROIs", id="save"),
                html.Span(id="upload-status"),
                dcc.Download(id="download"),
            ],
            style={"display": "flex", "gap": "12px", "alignItems": "center"},
        ),
        dcc.Graph(id="spectrum"),
    ]
)


def roi_bounds(roi, width, height):
    x0, x1 = sorted(np.clip([roi["x0"], roi["x1"]], 0, width).astype(int))
    y0, y1 = sorted(np.clip([roi["y0"], roi["y1"]], 0, height).astype(int))
    return x0, x1, y0, y1


def roi_shapes(rois, width, height):
    shapes = []
    for roi in rois:
        x0, x1, y0, y1 = roi_bounds(roi, width, height)
        shapes.append(
            {
                "type": "rect",
                "name": roi["id"],
                "editable": True,
                "x0": x0,
                "x1": x1,
                "y0": y0,
                "y1": y1,
                "line": {"color": roi["color"], "width": 4},
            }
        )
    return shapes


def spectrum_figure(cube, wavelengths, rois):
    height, width, _ = cube.shape
    spectrum = go.Figure(
        go.Scatter(
            x=wavelengths,
            y=cube.mean(axis=(0, 1)),
            mode="lines",
            name="Full image",
        )
    )
    for roi in rois:
        x0, x1, y0, y1 = roi_bounds(roi, width, height)
        roi_cube = cube[y0:y1, x0:x1]
        if roi_cube.size:
            spectrum.add_scatter(
                x=wavelengths,
                y=roi_cube.mean(axis=(0, 1)),
                mode="lines",
                name=roi["name"],
                line={"color": roi["color"]},
            )
    spectrum.update_layout(
        title="Mean spectra",
        xaxis_title="Wavelength",
        yaxis_title="Intensity",
    )
    return spectrum


@app.callback(
    Output("pseudo", "figure"),
    Output("spectrum", "figure"),
    Output("pseudo-size", "data"),
    Input("object", "value"),
    State("roi-store", "data"),
    State("color", "value"),
)
def render_object(object_num, roi_store, color):
    cube, wavelengths = load_cube(object_num)
    height, width, _ = cube.shape
    rois = (roi_store or {}).get(object_num, [])
    pseudo = px.imshow(cube[:, :, [70, 53, 19]], binary_string=True)
    pseudo.update_layout(
        dragmode="drawrect",
        newshape={
            "line": {"color": (color or {}).get("hex", DEFAULT_COLOR), "width": 4}
        },
        shapes=roi_shapes(rois, width, height),
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x"},
    )
    return pseudo, spectrum_figure(cube, wavelengths, rois), [width, height]


@app.callback(
    Output("pseudo", "figure", allow_duplicate=True),
    Output("spectrum", "figure", allow_duplicate=True),
    Input("roi-store", "data"),
    State("object", "value"),
    prevent_initial_call=True,
)
def render_rois(roi_store, object_num):
    cube, wavelengths = load_cube(object_num)
    height, width, _ = cube.shape
    rois = (roi_store or {}).get(object_num, [])
    patch = Patch()
    patch["layout"]["shapes"] = roi_shapes(rois, width, height)
    return patch, spectrum_figure(cube, wavelengths, rois)


@app.callback(
    Output("pseudo", "figure", allow_duplicate=True),
    Input("color", "value"),
    prevent_initial_call=True,
)
def update_drawing_color(color):
    patch = Patch()
    patch["layout"]["newshape"]["line"]["color"] = (color or {}).get(
        "hex", DEFAULT_COLOR
    )
    return patch


@app.callback(Output("tif", "figure"), Input("object", "value"))
def render_tif(object_num):
    return image_figure(load_tif(object_num))


@app.callback(
    Output("roi-store", "data"),
    Input("pseudo", "relayoutData"),
    State("object", "value"),
    State("roi-store", "data"),
    State("color", "value"),
    State("roi-name", "value"),
    prevent_initial_call=True,
)
def update_rois(event, object_num, roi_store, color, requested_name):
    if not event:
        raise PreventUpdate
    current = list((roi_store or {}).get(object_num, []))
    updated = [dict(roi) for roi in current]

    if "shapes" in event:
        existing = {roi["id"]: roi for roi in current}
        updated = []
        for shape in event["shapes"]:
            previous = existing.get(shape.get("name"))
            updated.append(
                normalized_roi(
                    shape,
                    previous["name"]
                    if previous
                    else requested_name or unique_roi_name(current + updated),
                    previous["color"]
                    if previous
                    else (color or {}).get("hex", DEFAULT_COLOR),
                    previous["id"] if previous else None,
                )
            )
    else:
        changed = False
        for key, value in event.items():
            match = SHAPE_COORDINATE.match(key)
            if match and int(match.group(1)) < len(updated):
                updated[int(match.group(1))][match.group(2)] = float(value)
                changed = True
        if not changed:
            raise PreventUpdate

    result = dict(roi_store or {})
    result[object_num] = updated
    return result


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
    State("pseudo-size", "data"),
    prevent_initial_call=True,
)
def sync_views(pseudo_event, tif_event, object_num, pseudo_size):
    if not pseudo_size:
        raise PreventUpdate
    pw, ph = pseudo_size
    tif = load_tif(object_num)
    tw, th = tif.size
    from_pseudo = ctx.triggered_id == "pseudo"
    event = pseudo_event if from_pseudo else tif_event
    sw, sh = (pw, ph) if from_pseudo else (tw, th)
    x_range, y_range = visible_range(event or {}, sw, sh)
    if x_range is None:
        return no_update, no_update

    tif_x = [x * tw / sw for x in x_range]
    tif_y = [y * th / sh for y in y_range]
    pseudo_x = [x * pw / sw for x in x_range]
    pseudo_y = [y * ph / sh for y in y_range]
    rendered = image_figure(tif, tif_x, tif_y).layout.images[0]

    pseudo_patch, tif_patch = Patch(), Patch()
    for key in ("source", "x", "y", "sizex", "sizey"):
        tif_patch["layout"]["images"][0][key] = getattr(rendered, key)
    if from_pseudo:
        tif_patch["layout"]["xaxis"]["range"] = tif_x
        tif_patch["layout"]["yaxis"]["range"] = tif_y
    else:
        pseudo_patch["layout"]["xaxis"]["range"] = pseudo_x
        pseudo_patch["layout"]["yaxis"]["range"] = pseudo_y
    return pseudo_patch, tif_patch


@app.callback(
    Output("roi-store", "data", allow_duplicate=True),
    Output("toml-store", "data"),
    Output("upload-status", "children"),
    Input("upload", "contents"),
    prevent_initial_call=True,
)
def upload_toml(contents):
    if not contents:
        raise PreventUpdate
    try:
        text = base64.b64decode(contents.split(",", 1)[1], validate=True).decode()
        return rois_from_toml(text), text, "ROI TOML loaded"
    except (
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        tomlkit.exceptions.ParseError,
    ):
        return no_update, no_update, "Could not load ROI TOML"


@app.callback(
    Output("download", "data"),
    Input("save", "n_clicks"),
    State("roi-store", "data"),
    State("toml-store", "data"),
    prevent_initial_call=True,
)
def download_toml(_clicks, roi_store, base_toml):
    document = tomlkit.parse(base_toml)
    roi_table = tomlkit.table()
    for object_num, rois in (roi_store or {}).items():
        object_table = tomlkit.table()
        for roi in rois:
            object_table[roi["name"]] = {
                key: roi[key] for key in ("color", "x0", "x1", "y0", "y1")
            }
        roi_table[object_num] = object_table
    document["roi"] = roi_table
    return {"content": tomlkit.dumps(document), "filename": "question.toml"}


if __name__ == "__main__":
    app.run(jupyter_mode="external")

# %%

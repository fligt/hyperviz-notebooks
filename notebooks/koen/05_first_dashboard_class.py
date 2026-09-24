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
from fairdatanow import data_now

# %%
url = "https://laboppad.nl/ukiyo-e-world"

toml_txt = """
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
"""

data = data_now(url, toml_txt)


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
from dash import Dash, Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate

# %%
DEFAULT_COLOR = "#119DFF"
SHAPE_COORDINATE = re.compile(r"^shapes\[(\d+)]\.(x0|x1|y0|y1)$")


def load_cube(data_dict: dict, object_num: str) -> tuple[np.ndarray, np.ndarray]:
    """Load an object's cube without retaining a server-side cache."""
    npz_file = data_dict["npz"][object_num][0]
    with np.load(npz_file) as npz:
        cube = npz["image"][:, :, ::-1].transpose(1, 2, 0)
        wavelengths = npz["wavelengths"].copy()
    return cube, wavelengths


def unique_roi_name(rois: list[dict]) -> str:
    existing_names = {roi["name"] for roi in rois}
    number = 1
    while f"ROI {number}" in existing_names:
        number += 1
    return f"ROI {number}"


def normalise_roi(
    shape: dict, name: str, color: str, roi_id: str | None = None
) -> dict:
    required = ("x0", "x1", "y0", "y1")
    if any(coordinate not in shape for coordinate in required):
        raise ValueError("Each ROI must define x0, x1, y0 and y1")
    return {
        "id": roi_id or uuid.uuid4().hex,
        "name": name,
        "color": color,
        **{coordinate: float(shape[coordinate]) for coordinate in required},
    }


def rois_from_toml(document) -> dict[str, list[dict]]:
    roi_store = {}
    for object_num, object_rois in document.get("roi", {}).items():
        roi_store[object_num] = [
            normalise_roi(roi, roi_name, roi.get("color", DEFAULT_COLOR))
            for roi_name, roi in object_rois.items()
        ]
    return roi_store


def create_dashboard(data_dict: dict, toml_text: str) -> Dash:
    app = Dash(__name__)
    graph_config = {
        "modeBarButtonsToAdd": ["drawrect", "eraseshape"],
        "scrollZoom": True,
    }
    app.layout = html.Div(
        [
            dcc.Store(id="roi_store", data={}),
            dcc.Store(id="base_toml_store", data={"content": toml_text}),
            html.H1("Dashboard Title"),
            dcc.Dropdown(
                id="object_dropdown",
                options=list(data_dict["npz"].keys()),
                placeholder="Select Object Number",
            ),
            html.Div(
                [
                    html.Div(
                        dcc.Graph(
                            id="pseudo_rgb_graph", figure={}, config=graph_config
                        ),
                        className="graph-panel",
                    ),
                    html.Div(
                        [
                            daq.ColorPicker(
                                id="colorpicker",
                                label="ROI Line Color",
                                value={"hex": DEFAULT_COLOR},
                            ),
                            dcc.Input(
                                id="annotation_text",
                                type="text",
                                placeholder="annotation label",
                            ),
                            dcc.Upload(
                                id="toml_upload",
                                children=html.Button(
                                    "Upload ROI TOML",
                                    className="action-button upload-button",
                                ),
                            ),
                            html.Button(
                                "Save ROIs",
                                id="save_btn",
                                className="action-button save-button",
                            ),
                            html.Div(id="upload_status", className="upload-status"),
                            dcc.Download(id="toml_download"),
                        ],
                        className="controls-panel",
                    ),
                ],
                className="dashboard-main",
            ),
            html.Div(
                dcc.Graph(id="mean_spectrum_graph", figure={}),
                className="spectrum-panel",
            ),
        ],
        className="dashboard",
    )

    @app.callback(
        Output("roi_store", "data"),
        Input("pseudo_rgb_graph", "relayoutData"),
        State("object_dropdown", "value"),
        State("roi_store", "data"),
        State("colorpicker", "value"),
        State("annotation_text", "value"),
        prevent_initial_call=True,
    )
    def update_roi_from_shapes(
        relayout_data, object_num, roi_store, color, annotation_text
    ):
        if not object_num or not relayout_data:
            raise PreventUpdate

        current_rois = list((roi_store or {}).get(object_num, []))
        updated_rois = current_rois
        if "shapes" in relayout_data:
            existing_by_id = {roi["id"]: roi for roi in current_rois}
            updated_rois = []
            for shape in relayout_data["shapes"]:
                roi_id = shape.get("name")
                existing = existing_by_id.get(roi_id)
                name = (
                    existing["name"]
                    if existing
                    else (
                        annotation_text or unique_roi_name(current_rois + updated_rois)
                    )
                )
                shape_color = (
                    existing["color"]
                    if existing
                    else (color or {}).get("hex", DEFAULT_COLOR)
                )
                updated_rois.append(normalise_roi(shape, name, shape_color, roi_id))
        else:
            changed = False
            updated_rois = [dict(roi) for roi in current_rois]
            for key, value in relayout_data.items():
                match = SHAPE_COORDINATE.match(key)
                if match and int(match.group(1)) < len(updated_rois):
                    updated_rois[int(match.group(1))][match.group(2)] = float(value)
                    changed = True
            if not changed:
                raise PreventUpdate

        new_store = dict(roi_store or {})
        new_store[object_num] = updated_rois
        return new_store

    @app.callback(
        Output("roi_store", "data", allow_duplicate=True),
        Output("base_toml_store", "data"),
        Output("upload_status", "children"),
        Input("toml_upload", "contents"),
        prevent_initial_call=True,
    )
    def upload_toml(upload_contents):
        if not upload_contents:
            raise PreventUpdate
        try:
            _, content_string = upload_contents.split(",", 1)
            uploaded_text = base64.b64decode(content_string).decode("utf-8")
            document = tomlkit.parse(uploaded_text)
            uploaded_rois = rois_from_toml(document)
        except (
            ValueError,
            UnicodeDecodeError,
            binascii.Error,
            tomlkit.exceptions.ParseError,
        ) as error:
            return (
                no_update,
                no_update,
                html.Div(
                    f"Could not load TOML: {error}",
                    className="status-message status-message--error",
                ),
            )
        return (
            uploaded_rois,
            {"content": uploaded_text},
            html.Div(
                "ROI TOML loaded",
                className="status-message status-message--success",
            ),
        )

    @app.callback(
        Output("pseudo_rgb_graph", "figure"),
        Output("mean_spectrum_graph", "figure"),
        Input("object_dropdown", "value"),
        Input("roi_store", "data"),
        Input("colorpicker", "value"),
    )
    def render_figures(object_num: str | None, roi_store: dict, color: dict):
        if not object_num:
            return {}, {}

        cube, wavelengths = load_cube(data_dict, object_num)
        height, width, _ = cube.shape
        rgb_figure = px.imshow(cube[:, :, [70, 53, 19]], binary_string=True)
        rgb_figure.update_layout(
            dragmode="drawrect",
            newshape={
                "line": {"color": (color or {}).get("hex", DEFAULT_COLOR), "width": 4}
            },
        )

        spectrum_figure = go.Figure(
            go.Scatter(
                x=wavelengths,
                y=cube.mean(axis=(0, 1)),
                mode="lines",
                name="Full Mean Spectrum",
            )
        )
        spectrum_figure.update_layout(
            xaxis_title="Wavelength",
            yaxis_title="Intensity",
            title="ROI Mean Spectra",
        )

        for roi in (roi_store or {}).get(object_num, []):
            x0, x1 = sorted(max(0, min(width, int(roi[key]))) for key in ("x0", "x1"))
            y0, y1 = sorted(max(0, min(height, int(roi[key]))) for key in ("y0", "y1"))
            rgb_figure.add_shape(
                type="rect",
                name=roi["id"],
                editable=True,
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                line={"color": roi["color"], "width": 4},
                fillcolor="rgba(0,0,0,0)",
            )
            roi_cube = cube[y0:y1, x0:x1, :]
            if roi_cube.size:
                spectrum_figure.add_trace(
                    go.Scatter(
                        x=wavelengths,
                        y=roi_cube.mean(axis=(0, 1)),
                        mode="lines",
                        name=roi["name"],
                        line_color=roi["color"],
                    )
                )
        return rgb_figure, spectrum_figure

    @app.callback(
        Output("toml_download", "data"),
        Input("save_btn", "n_clicks"),
        State("roi_store", "data"),
        State("base_toml_store", "data"),
        prevent_initial_call=True,
    )
    def download_toml_contents(_n: int, roi_store: dict, toml_data: dict):
        content = (toml_data or {}).get("content")
        document = tomlkit.parse(content) if content else tomlkit.document()
        roi_table = tomlkit.table()
        for object_num, rois in (roi_store or {}).items():
            object_table = tomlkit.table()
            for roi in rois:
                roi_data = tomlkit.table()
                for key in ("color", "x0", "x1", "y0", "y1"):
                    roi_data[key] = roi[key]
                object_table[roi["name"]] = roi_data
            roi_table[object_num] = object_table
        document["roi"] = roi_table
        return {"content": tomlkit.dumps(document), "filename": "question.toml"}

    return app


def run_app(data_dict: dict, toml_text: str):
    app = create_dashboard(data_dict=data_dict, toml_text=toml_text)
    app.run(jupyter_mode="external", debug=True)


# %%
run_app(data_dict=data, toml_text=toml_txt)

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

toml_path = ''

data = data_now(url, toml_txt)


# %%
from dash import Dash, dcc, html, callback, Input, Output, State, no_update, Patch
import dash_daq as daq
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import tomlkit


# %%
class FairDashboard():

    def __init__(self, data_dict=None, toml_text=None):
        '''Initialize FairDashboard instance'''
        self.data_dict = data_dict
        self.toml_text = toml_text
        self.app = self._create_app()

    def _create_app(self):
        '''Creates the app and the app layout using dash'''
        app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.SPACELAB])
        app.layout = dbc.Container(
            [
                dcc.Store(id='data_dict_store', data=self.data_dict),
                dcc.Store(id='project_toml_store', data={'content': self.toml_text}),
                html.H1("Dashboard Title"),
                dcc.Dropdown(id='object_dropdown', options=list(self.data_dict['npz'].keys()), placeholder='Select Object Number'),
                html.Div(id="container")
            ]
        )
        return app
        
    @callback(
        Output(component_id="container", component_property="children"),
        Input(component_id="object_dropdown", component_property="value"),
        State(component_id="data_dict_store", component_property="data"),
        prevent_initial_call=True
    )
    def _change_object(value: str, data_dict: dict):
        '''Change the visible pseudo_rgb'''
        npz_file = data_dict['npz'][value][0]
        npz = np.load(npz_file)
        cube = npz['image'][:,:, ::-1].transpose(1, 2, 0)
        wavelengths = npz['wavelengths']
        pseudo_rgb = cube[:,:, [70, 53, 19]] 

        fig_rgb = px.imshow(pseudo_rgb, binary_string=True)

        fig_rgb.update_layout(dragmode='drawrect')

        fig_rgb_config = {"modeBarButtonsToAdd": ["drawrect", "eraseshape"], "scrollZoom":True}

        fig_spec = go.Figure()

        fig_spec.add_trace(go.Scatter(
            x=wavelengths,
            y=cube.mean(axis=(0,1)),
            mode='lines',
            name='Full Mean Spectrum'
        ))

        fig_spec.update_layout(
            xaxis_title="Wavelength",
            yaxis_title="Intensity",
            title="ROI Mean Spectra"
        )
    
        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Graph(id="pseudo_rgb_graph", figure=fig_rgb, config=fig_rgb_config), width=8),
                dbc.Col([
                    daq.ColorPicker(id="colorpicker", label="ROI Line Color", value=dict(hex="#119DFF")),
                    dbc.Input(id="annotation_text", type="text", placeholder="annotation label"),
                    dbc.Button("Save ROI's", id="save_btn", color="success", className="mt-1"),
                    dcc.Download(id="toml_download")
                    ], width=4)
            ]),
            dbc.Row(dcc.Graph(id="mean_spectrum_graph", figure=fig_spec))
            ])

    @callback(
        Output(component_id="pseudo_rgb_graph", component_property="figure"),
        Input(component_id="colorpicker", component_property="value")
    )
    def _on_color_select(color :dict):
        patch = Patch()
        patch['layout']['newshape']['line']['color'] = color['hex']
        return patch
    

    @callback(
        Output(component_id="mean_spectrum_graph", component_property="figure"),
        Input(component_id="pseudo_rgb_graph", component_property="relayoutData"),
        State(component_id="mean_spectrum_graph", component_property="figure"),
        State(component_id="data_dict_store", component_property="data"),
        State(component_id="object_dropdown", component_property="value"),
        State(component_id="colorpicker", component_property="value"),
        State(component_id="annotation_text", component_property="value"),
        prevent_initial_call=True
    )
    def _on_drawrect(relayout_data: dict, fig_spec: dict, data_dict: dict, value: str, color: dict, annotation_text: str):
        shapes = (relayout_data or {}).get("shapes")
        if not shapes:
            return no_update
        shape = shapes[-1]
        
        npz_file = data_dict['npz'][value][0]
        npz = np.load(npz_file)
        cube = npz['image'][:,:, ::-1].transpose(1, 2, 0)
        wavelengths = npz['wavelengths'] 
        h, w, d = cube.shape

        x0, x1 = sorted([max(0, min(w, int(shape["x0"]))), max(0, min(w, int(shape["x1"])))])
        y0, y1 = sorted([max(0, min(h, int(shape["y0"]))), max(0, min(h, int(shape["y1"])))])
        
        roi_cube = cube[y0:y1, x0:x1, :]

        if roi_cube.size == 0:
            return no_update
        mean_spectrum = roi_cube.mean(axis=(0, 1))

        fig_spec = go.Figure(fig_spec)

        if not annotation_text:
            annotation_text = x0+x1+y0+y1

        fig_spec.add_trace(go.Scatter(
        x=wavelengths,
        y=mean_spectrum,
        mode='lines',
        name=annotation_text,
        line_color=color['hex']
        ))
        
        return fig_spec

    @callback(
        Output(component_id="toml_download", component_property="data"),
        Input(component_id="save_btn", component_property="n_clicks"),
        State(component_id="pseudo_rgb_graph", component_property="figure"),
        State(component_id="mean_spectrum_graph", component_property="figure"),
        State(component_id="object_dropdown", component_property="value"),
        State(component_id="project_toml_store", component_property="data"),
        prevent_initial_call=True
    )
    def _download_TOML_contents(n: int, rgb: dict, spec: dict, object_num: str, toml_dict: dict):
        if toml_dict['content']:
            doc = tomlkit.parse(toml_dict['content'])
        else:
            doc = tomlkit.document()

        roi_table = tomlkit.table()
        object_table = tomlkit.table()
        
        roi_table[object_num] = object_table

        for shape, line in zip(rgb['layout']['shapes'], spec['data'][1:]):
            sub_table = tomlkit.table()
            sub_table['color'] = shape['line']['color']
            sub_table['x0'] = shape['x0']
            sub_table['x1'] = shape['x1']
            sub_table['y0'] = shape['y0']
            sub_table['y1'] = shape['y1']
            
            roi_table[object_num][line['name']] = sub_table
        
        doc['roi'] = roi_table

        return dict(content=tomlkit.dumps(doc), filename="question.toml")

    def run(self):
        '''Launch the dashboard'''
        self.app.run(jupyter_mode="external", debug=True)

# %%
fd = FairDashboard(data_dict=data, toml_text=toml_txt)

# %%
fd.run()


# %%
def create_dashboard(data_dict: dict, toml_text: str) -> Dash:
    return


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
import plotly.express as px
from fairdatanow import data_now
from skimage import io
import datashader as ds
import xarray as xr
import numpy as np

url = 'https://laboppad.nl/ukiyo-e-world' 

toml_txt = '''
# here are the 10 corresponding spectral data cubes processed by Gauthier and Tessa 

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

# %%
import base64
from io import BytesIO
import numpy as np
from dash import Dash, html, Input, Output
from PIL import Image
from skimage import io

tif_file = data['tif']['RV-1-4470-27'][0]
img_array = io.imread(tif_file)

if img_array.dtype == np.uint16:
    img_array = (img_array / 256).astype(np.uint8)

pil_img = Image.fromarray(img_array)
buffered = BytesIO()
pil_img.save(buffered, format="PNG")
img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

app = Dash(__name__)

app.layout = html.Div(
    id="viewport",
    children=[
        html.Img(
            id="img",
            src=f"data:image/png;base64,{img_b64}",
            style={
                "transform-origin": "0 0",
                "pointer-events": "none",
                "display": "block",
                "image-rendering": "pixelated"
            }
        )
    ],
    style={
        "width": "100%",
        "height": "750px",
        "overflow": "hidden",
        "position": "relative",
        "cursor": "grab",
        "background-color": "#1e1e1e"
    }
)

app.clientside_callback(
    """
    function(id) {
        setTimeout(() => {
            const vp = document.getElementById('viewport'), img = document.getElementById('img');
            if (!vp || vp.dataset.init) return;
            vp.dataset.init = true;

            let scale = 1, x = 0, y = 0, startX = 0, startY = 0, dragging = false;
            const update = () => img.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;

            // Scroll zoom centered at current mouse pointer
            vp.addEventListener('wheel', e => {
                e.preventDefault();
                const rect = vp.getBoundingClientRect(), mx = e.clientX - rect.left, my = e.clientY - rect.top;
                const factor = e.deltaY < 0 ? 1.2 : 0.8;
                const nextScale = Math.min(Math.max(0.2, scale * factor), 25);
                
                x = mx - (mx - x) * (nextScale / scale);
                y = my - (my - y) * (nextScale / scale);
                scale = nextScale;
                update();
            }, { passive: false });

            // Click & Drag panning
            vp.addEventListener('mousedown', e => {
                dragging = true;
                startX = e.clientX - x;
                startY = e.clientY - y;
                vp.style.cursor = 'grabbing';
            });
            window.addEventListener('mousemove', e => {
                if (dragging) {
                    x = e.clientX - startX;
                    y = e.clientY - startY;
                    update();
                }
            });
            window.addEventListener('mouseup', () => {
                dragging = false;
                vp.style.cursor = 'grab';
            });
        }, 100);
        return window.dash_clientside.no_update;
    }
    """,
    Output("viewport", "id"),
    Input("viewport", "id")
)

if __name__ == '__main__':
    app.run(jupyter_mode="external", debug=True)

# %%

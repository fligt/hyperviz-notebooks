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
# # Refactoring the calcium demo 
#
# Given all the incomprehensible bugs in my previous attempts to get an interactive holoviews based ROI editor, let's start all over again with the working calcium demo: https://holoviews.org/gallery/demos/bokeh/box_draw_roi_editor.html 
#
# A problem is that in order to start exactly with the example I would need the `twophoton.npz` file. Instead I will try to use our own hyperspectral data. 

# %%
from fairdatanow import data_now

import holoviews as hv 
from holoviews import RGB, opts 
from holoviews.operation.datashader import rasterize
import panel as pn 
import numpy as np 

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
# Let's see how to inject our data cube into the calcium demo. 

# %%
# create a cube Dataset  
h, w, d = cube.shape 
ds = hv.Dataset((wavelengths, np.arange(w), np.arange(h-1, -1, -1), cube), ['Wavelength', 'x', 'y'], 'Reflectance') 

# %%
ds

# %%
import numpy as np

import holoviews as hv
from holoviews import opts, streams

hv.extension('bokeh')

# %%
polys = hv.Polygons([])
box_stream = streams.BoxEdit(source=polys)

def roi_curves(data):
    if not data or not any(len(d) for d in data.values()):
        return hv.NdOverlay({0: hv.Curve([], 'Wavelength', 'Reflectance')})

    curves = {}
    data = zip(data['x0'], data['x1'], data['y0'], data['y1'])
    for i, (x0, x1, y0, y1) in enumerate(data):
        selection = ds.select(x=(x0, x1), y=(y0, y1))
        curves[i] = hv.Curve(selection.aggregate('Wavelength', np.mean))
    return hv.NdOverlay(curves)

hlines = hv.HoloMap({i: hv.VLine(i) for i in range(len(wavelengths))}, 'Wavelength')
dmap = hv.DynamicMap(roi_curves, streams=[box_stream])

# %%
#im = ds.to(hv.Image, ['x', 'y'], dynamic=True)
im = hv.RGB(pseudo_rgb, bounds=bounds).opts(aspect='equal')
(im * polys + dmap * hlines).opts(
    opts.Curve(width=400, framewise=True),
    opts.Polygons(fill_alpha=0.2, line_color='white'),
    opts.VLine(color='black'))

# %%

# %%

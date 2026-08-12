# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
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
# # A panel and plotly trial 

# %% [markdown]
# Well, actually I can not get a panel plotly pane to display. Alternatively the bokeh pane seems to work fine....  

# %% [markdown]
# Let's start by a look at the panel documentation: https://panel.holoviz.org/reference/index.html# and dive straight into plotly: https://panel.holoviz.org/reference/panes/Plotly.html

# %%
import panel as pn
import numpy as np
import plotly.graph_objs as go

pn.extension("plotly") 

# %%
xx = np.linspace(-3.5, 3.5, 100)
yy = np.linspace(-3.5, 3.5, 100)
x, y = np.meshgrid(xx, yy)
z = np.exp(-((x - 1) ** 2) - y**2) - (x**3 + y**4 - x / 5) * np.exp(-(x**2 + y**2))

surface=go.Surface(z=z)
fig = go.Figure(data=[surface])

fig.update_layout(
    title="Plotly 3D Plot",
    width=500,
    height=500,
    margin=dict(t=50, b=50, r=50, l=50),
)

plotly_pane = pn.pane.Plotly(fig)
plotly_pane

# %%
# Source - https://stackoverflow.com/q/77724445
# Posted by Raein, modified by community. See post 'Timeline' for change history
# Retrieved 2026-08-11, License - CC BY-SA 4.0

import plotly.graph_objects as go
fig = go.Figure()
fig.show()


# %%
pn.Row(plotly_pane)

# %% [markdown]
# Somehow the `plotly_pane` does not appear. Let's try with a bokeh pane: https://panel.holoviz.org/reference/panes/Bokeh.html

# %%
import panel as pn
import numpy as np
import pandas as pd

pn.extension()

# %%
from math import pi

from bokeh.palettes import Category20c, Category20
from bokeh.plotting import figure
from bokeh.transform import cumsum

x = {
    'United States': 157,
    'United Kingdom': 93,
    'Japan': 89,
    'China': 63,
    'Germany': 44,
    'India': 42,
    'Italy': 40,
    'Australia': 35,
    'Brazil': 32,
    'France': 31,
    'Taiwan': 31,
    'Spain': 29
}

data = pd.Series(x).reset_index(name='value').rename(columns={'index':'country'})
data['angle'] = data['value']/data['value'].sum() * 2*pi
data['color'] = Category20c[len(x)]

p = figure(height=350, title="Pie Chart", toolbar_location=None,
           tools="hover", tooltips="@country: @value", x_range=(-0.5, 1.0))

r = p.wedge(x=0, y=1, radius=0.4,
        start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
        line_color="white", fill_color='color', legend_field='country', source=data)

p.axis.axis_label=None
p.axis.visible=False
p.grid.grid_line_color = None

bokeh_pane = pn.pane.Bokeh(p, theme="dark_minimal")
bokeh_pane

# %%
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput

# Set up data
N = 200
x = np.linspace(0, 4*np.pi, N)
y = np.sin(x)
source = ColumnDataSource(data=dict(x=x, y=y))

# Set up plot
plot = figure(height=400, width=400, title="my sine wave",
              tools="crosshair,pan,reset,save,wheel_zoom",
              x_range=[0, 4*np.pi], y_range=[-2.5, 2.5])

plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6)

# Set up widgets
text = TextInput(title="title", value='my sine wave')
offset = Slider(title="offset", value=0.0, start=-5.0, end=5.0, step=0.1)
amplitude = Slider(title="amplitude", value=1.0, start=-5.0, end=5.0, step=0.1)
phase = Slider(title="phase", value=0.0, start=0.0, end=2*np.pi)
freq = Slider(title="frequency", value=1.0, start=0.1, end=5.1, step=0.1)

# Set up callbacks
def update_title(attrname, old, new):
    plot.title.text = text.value

text.on_change('value', update_title)

def update_data(attrname, old, new):

    # Get the current slider values
    a = amplitude.value
    b = offset.value
    w = phase.value
    k = freq.value

    # Generate the new curve
    x = np.linspace(0, 4*np.pi, N)
    y = a*np.sin(k*x + w) + b

    source.data = dict(x=x, y=y)

for w in [offset, amplitude, phase, freq]:
    w.on_change('value', update_data)

# Set up layouts and add to document
inputs = column(text, offset, amplitude, phase, freq)

bokeh_app = pn.pane.Bokeh(row(inputs, plot, width=800))

bokeh_app

# %% [markdown]
# This bokeh pane actually looks quite snappy. How about 

# %%
from bokeh.plotting import figure 
import numpy as np 

# %%
im = np.random.rand(100, 100)

# %%
im.shape

# %%
import numpy as np

from bokeh.plotting import figure, show

x = np.linspace(0, 10, 300)
y = np.linspace(0, 10, 300)
xx, yy = np.meshgrid(x, y)
d = np.sin(xx) * np.cos(yy)

p = figure(width=400, height=400)
p.x_range.range_padding = p.y_range.range_padding = 0

# must give a vector of image data for image parameter
p.image(image=[d], x=0, y=0, dw=20, dh=20, palette="Sunset11", level="image")
p.grid.grid_line_width = 0.5

show(p)

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
# # Steps to syncing

# %% [markdown]
# I changed:
#
# 1) Folder structure to enforce a clean working split
# 2) used `uv python pin 3.14` to upgrade our project version and deleted the old .venv folder
# 3) used `uv sync` to enforce the new version on my own system
# 4) added ipykernel and pip as --dev dependencies to this project to run code
# 5) added `[tool.jupytext]` to the `pyproject.toml` file to enforce automatic syncing in this repo
# 6) added this line by right clicking the py file and opening paired notebook
#

# %%
print("hello world")

# %% [markdown]
# I cant seem to get the autodelete working for now, it did work once but i'll add the recommended .ipynb to the gitignore

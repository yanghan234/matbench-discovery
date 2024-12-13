"""Concatenate M3GNet results from multiple data files generated by slurm job array
into single file.
"""

# %%
import os
from glob import glob
from typing import Literal

import pandas as pd
from pymatgen.core import Structure
from pymatgen.entries.compatibility import MaterialsProject2020Compatibility
from pymatgen.entries.computed_entries import ComputedStructureEntry
from pymatviz.enums import Key
from tqdm import tqdm

from matbench_discovery.data import DataFiles, as_dict_handler
from matbench_discovery.energy import get_e_form_per_atom
from matbench_discovery.enums import Task

__author__ = "Janosh Riebesell"
__date__ = "2022-08-16"


# %%
module_dir = os.path.dirname(__file__)
date = "2023-12-28"
# direct: cluster sampling, ms: manual sampling
model_type: Literal["orig", "direct", "ms"] = "orig"
glob_pattern = f"{date}-m3gnet-{model_type}-wbm-{Task.IS2RE}/*.json.gz"
file_paths = sorted(glob(f"{module_dir}/{glob_pattern}"))
print(f"Found {len(file_paths):,} files for {glob_pattern = }")

# prevent accidental overwrites
dfs: dict[str, pd.DataFrame] = locals().get("dfs", {})


# %%
for file_path in tqdm(file_paths):
    if file_path in dfs:
        continue
    df_i = pd.read_json(file_path).set_index(Key.mat_id)
    # drop trajectory to save memory
    dfs[file_path] = df_i.drop(columns="m3gnet_trajectory", errors="ignore")

df_m3gnet = pd.concat(dfs.values()).round(4)


# %%
df_cse = pd.read_json(DataFiles.wbm_computed_structure_entries.path).set_index(
    Key.mat_id
)
df_cse[Key.computed_structure_entry] = [
    ComputedStructureEntry.from_dict(dct)
    for dct in tqdm(df_cse[Key.computed_structure_entry])
]


# %% transfer M3GNet energies and relaxed structures WBM CSEs since MP2020 energy
# corrections applied below are structure-dependent (for oxides and sulfides)
cse: ComputedStructureEntry
e_col = "m3gnet_orig_energy"
struct_col = "m3gnet_orig_structure"

for mat_id in tqdm(df_m3gnet.index):
    m3gnet_energy = df_m3gnet.loc[mat_id, e_col]
    mlip_struct = Structure.from_dict(df_m3gnet.loc[mat_id, struct_col])
    cse = df_cse.loc[mat_id, Key.computed_structure_entry]
    cse._energy = m3gnet_energy  # cse._energy is the uncorrected energy  # noqa: SLF001
    cse._structure = mlip_struct  # noqa: SLF001
    df_m3gnet.loc[mat_id, Key.computed_structure_entry] = cse


# %% apply energy corrections
processed = MaterialsProject2020Compatibility().process_entries(
    df_m3gnet[Key.computed_structure_entry], verbose=True, clean=True
)
if len(processed) != len(df_m3gnet):
    raise ValueError(f"not all entries processed: {len(processed)=} {len(df_m3gnet)=}")


# %% compute corrected formation energies
df_m3gnet["e_form_per_atom_m3gnet"] = [
    get_e_form_per_atom(cse) for cse in tqdm(df_m3gnet[Key.computed_structure_entry])
]


# %%
out_path = file_paths[0].rsplit("/", 1)[0]
df_m3gnet = df_m3gnet.round(4)
df_m3gnet.select_dtypes("number").to_csv(f"{out_path}.csv.gz")
df_m3gnet.reset_index().to_json(f"{out_path}.json.gz", default_handler=as_dict_handler)


# in_path = f"{module_dir}/2022-10-31-m3gnet-wbm-IS2RE"
# df_m3gnet = pd.read_csv(f"{in_path}.csv.gz").set_index(Key.mat_id)
# df_m3gnet = pd.read_json(f"{in_path}.json.gz").set_index(Key.mat_id)

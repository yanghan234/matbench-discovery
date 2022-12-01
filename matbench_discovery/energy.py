import itertools
from collections.abc import Sequence

import pandas as pd
from pymatgen.analysis.phase_diagram import Entry, PDEntry
from pymatgen.core import Composition
from pymatgen.util.typing import EntryLike
from tqdm import tqdm

from matbench_discovery import ROOT


def get_elemental_ref_entries(
    entries: Sequence[EntryLike], verbose: bool = False
) -> dict[str, Entry]:
    """Get the lowest energy entry for each element in a list of entries.

    Args:
        entries (Sequence[Entry]): pymatgen Entries (PDEntry, ComputedEntry or
            ComputedStructureEntry) to find elemental reference entries for.
        verbose (bool, optional): _description_. Defaults to False.

    Raises:
        ValueError: If some elements are missing terminal reference entries.
        ValueError: If there are more terminal entries than dimensions. Should never
            happen.

    Returns:
        dict[str, Entry]: Map from element symbol to its lowest energy entry.
    """
    entries = [PDEntry.from_dict(e) if isinstance(e, dict) else e for e in entries]
    elements = {elems for entry in entries for elems in entry.composition.elements}
    dim = len(elements)

    if verbose:
        print(f"Sorting {len(entries)} entries with {dim} dimensions...")

    entries = sorted(entries, key=lambda e: e.composition.reduced_composition)

    elemental_ref_entries = {}
    for composition, entry_group in tqdm(
        itertools.groupby(entries, key=lambda e: e.composition.reduced_composition),
        disable=not verbose,
    ):
        min_entry = min(entry_group, key=lambda e: e.energy_per_atom)
        if composition.is_element:
            elem_symb = str(composition.elements[0])
            elemental_ref_entries[elem_symb] = min_entry

    if len(elemental_ref_entries) > dim:
        missing = elements - set(elemental_ref_entries)
        raise ValueError(f"Some terminal entries are {missing = }")
    elif len(elemental_ref_entries) < dim:
        extra = set(elemental_ref_entries) - set(elements)
        raise ValueError(
            f"There are more terminal element entries than dimensions: {extra}"
        )

    return elemental_ref_entries


# contains all MP elemental reference entries to compute formation energies
# produced by get_elemental_ref_entries() in build_phase_diagram.py
mp_elem_refs_path = f"{ROOT}/data/mp/2022-09-19-mp-elemental-reference-entries.json"
try:
    mp_elem_reference_entries = (
        pd.read_json(mp_elem_refs_path, typ="series").map(PDEntry.from_dict).to_dict()
    )
except FileNotFoundError:
    mp_elem_reference_entries = None


def get_e_form_per_atom(
    entry: EntryLike,
    elemental_ref_entries: dict[str, EntryLike] = None,
) -> float:
    """Get the formation energy of a composition from a list of entries and elemental
    reference energies.

    Args:
        entry: Entry | dict[str, float | str | Composition]: pymatgen Entry (PDEntry,
            ComputedEntry or ComputedStructureEntry) or dict with energy and composition
            keys to compute formation energy of.
        elemental_ref_entries (dict[str, Entry], optional): Must be a complete set of
            terminal (i.e. elemental) reference entries containing the lowest energy
            phase for each element present in entry. Defaults to MP elemental reference
            entries as collected on 2022-09-19 get_elemental_ref_entries(). This was
            tested to give the same formation energies as computed by MP.

    Returns:
        float: formation energy in eV/atom.
    """
    if elemental_ref_entries is None:
        if mp_elem_reference_entries is None:
            msg = f"{mp_elem_refs_path=}, pass elemental_ref_entries explicitly."
            raise FileNotFoundError(msg)
        elemental_ref_entries = mp_elem_reference_entries

    if isinstance(entry, dict):
        energy = entry["energy"]
        comp = Composition(entry["composition"])  # is idempotent if already Composition
    elif isinstance(entry, Entry):
        energy = entry.energy
        comp = entry.composition
    else:
        raise TypeError(
            f"{entry=} must be Entry (or subclass like ComputedEntry) or dict"
        )

    refs = {str(el): elemental_ref_entries[str(el)] for el in comp}

    for key, ref_entry in refs.items():
        if isinstance(ref_entry, dict):
            refs[key] = PDEntry.from_dict(ref_entry)

    form_energy = energy - sum(comp[el] * refs[str(el)].energy_per_atom for el in comp)

    return form_energy / comp.num_atoms


def classify_stable(
    e_above_hull_true: pd.Series,
    e_above_hull_pred: pd.Series,
    stability_threshold: float = 0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Classify model stability predictions as true/false positive/negatives depending
    on if material is actually stable or unstable. All energies are assumed to be in
    eV/atom (but shouldn't really matter as long as they're consistent).

    Args:
        e_above_hull_true (pd.Series): Ground truth energy above convex hull values.
        e_above_hull_pred (pd.Series): Model predicted energy above convex hull values.
        stability_threshold (float, optional): Maximum energy above convex hull for a
            material to still be considered stable. Usually 0, 0.05 or 0.1. Defaults to
            0. 0 means a material has to be directly on the hull to be called stable.
            Negative values mean a material has to pull the known hull down by that
            amount to count as stable. Few materials lie below the known hull, so only
            negative values close to 0 make sense.

    Returns:
        tuple[pd.Series, pd.Series, pd.Series, pd.Series]: Indices for true positives,
            false negatives, false positives and true negatives (in this order).
    """
    actual_pos = e_above_hull_true <= stability_threshold
    actual_neg = e_above_hull_true > stability_threshold
    model_pos = e_above_hull_pred <= stability_threshold
    model_neg = e_above_hull_pred > stability_threshold

    true_pos = actual_pos & model_pos
    false_neg = actual_pos & model_neg
    false_pos = actual_neg & model_pos
    true_neg = actual_neg & model_neg

    return true_pos, false_neg, false_pos, true_neg

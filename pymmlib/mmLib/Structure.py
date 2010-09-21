## Copyright 2002-2010 by PyMMLib Development Group (see AUTHORS file)
## This code is part of the PyMMLib distribution and governed by
## its license.  Please see the LICENSE file that should have been
## included as part of this package.
"""Classes for representing biological macromolecules.
"""
import copy
import math
import string
import itertools

try:
    import numpy
    try:
        from numpy.oldnumeric import linear_algebra as linalg
    except ImportError:
        from numpy.linalg import old as linalg
except ImportError:
    import NumericCompat as numpy
    from NumericCompat import linalg

import ConsoleOutput
import Constants
import GeometryDict
import AtomMath
import Library
import UnitCell
import Sequence
import mmCIFDB


class StructureError(Exception):
    """Base class of errors raised by Structure objects.
    """
    pass

class ModelOverwrite(StructureError):
    """Raised by Structure.add_model() when a Model added to a Structure
    has the same model_id of a Model already in the Structure.
    """
    pass

class ChainOverwrite(StructureError):
    """Raised by Structure.add_chain() or by Model.add_chain() when a
    Chain added to a Structure has the same chain_id of a Chain already
    in the Structure.
    """
    pass

class FragmentOverwrite(StructureError):
    """Raised by Chain.add_fragment() when a Fragment added to a Chain
    has the same fragment_id as a Fragment already in the Chain.
    """
    pass

class AtomOverwrite(StructureError):
    """Raised by Structure.add_atom() or Fragment.add_atom() when a Atom
    added to a Structure or Fragment has the same chain_id, fragment_id,
    name, and alt_loc as a Atom already in the Structure or Fragment.
    """
    def __init__(self, text):
        StructureError.__init__(self)
        self.text = text
    def __str__(self):
        return self.text

class Structure(object):
    """The Structure object is the parent container object for the entire
    macromolecular data structure.  It contains a list of the Chain objects
    in the structure hierarchy, and contains these additional data
    objects:

    cifdb(mmLib.mmCIFDB) A mmCIF database with additional structure data.

    unit_cell(mmLib.UnitCell) Unit cell/Spacegroup for the structure.

    default_alt_loc(string) The default alternate location identifier used
    when iterating or retreiving Atom objects in the structure.
    """
    def __init__(self, **args):
        self.structure_id = args.get("structure_id") or "XXXX"
        self.header = None
        self.title = None
        self.experimental_method = None
        self.cifdb = args.get("cifdb") or mmCIFDB.mmCIFDB("XXXX")

        self.unit_cell = args.get("unit_cell") or UnitCell.UnitCell()

        self.default_alt_loc = "A"
        self.default_model = None
        self.model_list = []
        self.model_dict = {}

    def __str__(self):
        return "Struct(%s)" % (self.structure_id)
 
    def __deepcopy__(self, memo):
        structure = Structure(
            cifdb     = copy.deepcopy(self.cifdb, memo),
            unit_cell = copy.deepcopy(self.unit_cell, memo))

        for model in self.model_list:
            structure.add_model(copy.deepcopy(model, memo), True)

        return structure

    def __len__(self):
        """Returns the number of stored Chain objects.
        """
        try:
            return len(self.default_model)
        except TypeError:
            return 0
    
    def __getitem__(self, chain_idx):
        """Same as get_chain, but raises KeyError if the requested chain_id
        is not found.
        """
        try:
            return self.default_model[chain_idx]
        except TypeError:
            raise KeyError, chain_idx

    def __iter__(self):
        """Iterates the Chain objects in the Structure.
        """
        if self.default_model:
            return iter(self.default_model.chain_list)
        return iter(list())

    def __contains__(self, model_chain_idx):
        """Returns True if item is a Model in the Structure, or a
        Chain or chain_id in the default Model.
        """
        if isinstance(model_chain_idx, Model):
            return self.model_list.__contains__(model_chain_idx)
        elif isinstance(model_chain_idx, Chain) or \
             isinstance(model_chain_idx, str):
            try:
                return self.default_model.__contains__(model_chain_idx)
            except AttributeError:
                raise KeyError, model_chain_idx
        raise TypeError, model_chain_idx

    def index(self, model_chain):
        """If item is a Model, returns the index of the Model in the
        Structure, or if the item is a Chain, returns the index of the
        Chain in the default Model.
        """
        if isinstance(model_chain, Model):
            return self.model_list.index(model_chain)
        elif isinstance(model_chain, Chain):
            try:
                return self.default_model.index(model_chain)
            except AttributeError:
                raise ValueError, model_chain
        raise TypeError, model_chain

    def sort(self):
        """Sorts all Models and Chains in the Structure according to standard
        model_id, chain_id, and fragment_id sorting rules.
        """
        self.model_list.sort()
        for model in self.model_list:
            model.sort()

    def add_model(self, model, delay_sort=True):
        """Adds a Model to a Structure. Raises the ModelOverwrite exception
        if the model_id of the Model matches the model_id of a Model
        already in the Structure. If there are no Models in the Structure,
        the Model is used as the default Model.
        """
        assert isinstance(model, Model)

        if self.model_dict.has_key(model.model_id):
            raise ModelOverwrite()

        ## set default model if not set
        if self.default_model is None:
            self.default_model = model

        self.model_list.append(model)
        self.model_dict[model.model_id] = model

        model.structure = self

        if not delay_sort:
            self.model_list.sort()

    def remove_model(self, model):
        """Removes a child Model object.  If the Model object is the default
        Model, then choose the Model with the lowest model_id as the
        new default Model, or None if there are no more Models.
        """
        assert isinstance(model, Model)
        
        self.model_list.remove(model)
        del self.model_dict[model.model_id]
        model.structure = None

        ## if the default model is being removed, choose a new default model
        ## if possible
        if model == self.default_model:
            if len(self.model_list) > 0:
                self.default_model = self.model_list[0]
            else:
                self.default_model = None

    def get_model(self, model_id):
        """Return the Model object with the argument model_id, or None if
        not found.
        """
        if self.model_dict.has_key(model_id):
            return self.model_dict[model_id]
        return None

    def get_default_model(self):
        """Returns the default Model object.
        """
        return self.default_model
    
    def set_default_model(self, model_id):
        """Sets the default Model for the Structure to model_id.  Returns
        False if a Model with the proper model_id does
        not exist in the Structure.
        """
        try:
            self.default_model = self.model_dict[model_id]
        except KeyError:
            return False
        return False

    def set_model(self, model_id):
        """DEP: Use set_default_model()
        Sets the default Model for the Structure to model_id.  Returns
        False if a Model with the proper model_id does
        not exist in the Structure.
        """
        self.set_default_model(model_id)

    def iter_models(self):
        """Iterates over all Model objects.
        """
        return iter(self.model_list)

    def count_models(self):
        """Counts all Model objects in the Structure.
        """
        return len(self.model_list)
    
    def add_chain(self, chain, delay_sort = True):
        """Adds a Chain object to the Structure.  Creates necessary parent
        Model if necessary
        """
        assert isinstance(chain, Chain)

        try:
            model = self.model_dict[chain.model_id]
        except KeyError:
            model = Model(model_id = chain.model_id)
            self.add_model(model, delay_sort)

        model.add_chain(chain, delay_sort)

    def remove_chain(self, chain):
        """Removes a Chain object.
        """
        assert isinstance(chain, Chain)
        self.model_dict[chain.model_id].remove_chain(chain)

    def get_chain(self, chain_id):
        """Returns the Chain object matching the chain_id character.
        """
        if self.default_model is None:
            return None
        if self.default_model.chain_dict.has_key(chain_id):
            return self.default_model.chain_dict[chain_id]
        return None

    def count_chains(self):
        """Counts all Chain objects in the default Model.
        """
        if self.default_model:
            return self.default_model.count_chains()
        return 0

    def iter_chains(self):
        """Iterates over all Chain objects in the default Model, in
        alphabetical order according to their chain_id.
        """
        if self.default_model:
            return iter(self.default_model.chain_list)
        return iter(list())

    def iter_all_chains(self):
        """Iterates over all Chain objects in all Model objects.
        """
        for model in self.model_list:
            for chain in model.chain_list:
                yield chain

    def add_fragment(self, fragment, delay_sort=True):
        """Adds a Fragment object.
        """
        assert isinstance(fragment, Fragment)

        try:
            model = self.model_dict[fragment.model_id]
        except KeyError:
            model = Model(model_id=fragment.model_id)
            self.add_model(model, delay_sort)

        model.add_fragment(fragment)

    def remove_fragment(self, fragment):
        """Removes a Fragment object.
        """
        assert isinstance(fragment, Fragment)
        self.model_dict[fragment.model_id].remove_fragment(fragment)

    def count_fragments(self):
        """Counts all Fragment objects in the default Model.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_fragments()
        return n
    
    def iter_fragments(self):
        """Iterates over all Fragment objects in the default Model.
        The iteration is performed in order according the the parent
        Chain's chain_id, and the Fragment's position within the chain.
        """
        if self.default_model is None:
            raise StopIteration
        
        for chain in self.default_model.chain_list:
            for frag in chain.fragment_list:
                yield frag

    def iter_all_fragments(self):
        """Iterates over all Fragment objects in all Models.
        The iteration is performed in order according the the parent
        Chain's chain_id, and the Fragment's position within the chain.
        """
        for model in self.model_list:
            for chain in model.chain_list:
                for frag in chain.fragment_list:
                    yield frag
    
    def has_amino_acids(self):
        """Returns True if there are AminoAcidResidue objects in the
        default Model of the Structure.
        """
        for frag in self.iter_amino_acids():
            return True
        return False
                    
    def count_amino_acids(self):
        """Counts all AminoAcidResidue objects in the default Model.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_amino_acids()
        return n
    
    def iter_amino_acids(self):
        """Same as iter_fragments() but only iterates over Fragments of the
        subclass AminoAcidResidue.
        """
        for chain in self.iter_chains():
            for frag in chain.iter_amino_acids():
                yield frag

    def iter_all_amino_acids(self):
        """Iterates over all AminoAcidResidue objects in all Models.
        """
        for model in self.model_list:
            for chain in model.chain_list:
                for frag in chain.iter_amino_acids():
                    yield frag

    def has_nucleic_acids(self):
        """Returns True if the Structure contains NucleicAcidResiudes in the
        default Model.
        """
        for frag in self.iter_nucleic_acids():
            return True
        return False
                  
    def count_nucleic_acids(self):
        """Counts all NucleicAcidResidue objects in the default Model.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_nucleic_acids()
        return n
    
    def iter_nucleic_acids(self):
        """Same as iter_fragments() but only iterates over Fragments of the
        subclass NucleicAcidResidue.
        """
        for chain in self.iter_chains():
            for frag in chain.iter_nucleic_acids():
                yield frag

    def iter_all_nucleic_acids(self):
        """Iterates over all NucleicAcidResidue objects in all Models.
        """
        for model in self.model_list:
            for chain in model.chain_list:
                for frag in chain.iter_nucleic_acids():
                    yield frag

    def has_standard_residues(self):
        """Returns True if the Structure contains amino or nucleic acids
        in the default Model.
        """
        for frag in self.iter_standard_residues():
            return True
        return False

    def count_standard_residues(self):
        """Counts the number of standard residues in the default Model.
        """
        n = 0
        for na in self.iter_standard_residues():
            n += 1
        return n
    
    def iter_standard_residues(self):
        """Iterates over standard residues in the default Model.
        """
        fpred = lambda f: f.is_standard_residue()
        return itertools.ifilter(fpred, self.iter_fragments())

    def has_non_standard_residues(self):
        """Returns True if there are non-standard residues in the default
        Model.
        """
        for frag in self.iter_non_standard_residues():
            return True
        return False

    def count_non_standard_residues(self):
        """Counts all non-standard residues in the default Model.
        """
        n = 0
        for frag in self.iter_non_standard_residues():
            n += 1
        return n
    
    def iter_non_standard_residues(self):
        """Iterates over non-standard residues in the default Model.
        Non-standard residues are any Fragments which are not a amino or
        nucleic acid.
        """
        fpred = lambda f: f.is_standard_residue()
        return itertools.ifilterfalse(fpred, self.iter_fragments())

    def has_waters(self):
        """Returns True if there are waters in the default Model.
        """
        for frag in self.iter_waters():
            return True
        return False

    def count_waters(self):
        """Counts all waters in the default Model.
        """
        n = 0
        for frag in self.iter_waters():
            n += 1
        return n

    def iter_waters(self):
        """Iterate over all waters in the default Model.
        """
        fpred = lambda f: f.is_water()
        return itertools.ifilter(fpred, self.iter_fragments())

    def add_atom(self, atom, delay_sort = False):
        """Adds a Atom object to the Structure.  If a collision occurs, a
        error is raised.
        """
        assert isinstance(atom, Atom)

        ## add new model if necesary
        try:
            model = self.model_dict[atom.model_id]
        except KeyError:
            model = Model(model_id = atom.model_id)
            self.add_model(model, delay_sort)

        ## optimized add_atom()
        chain_id    = atom.chain_id
        fragment_id = atom.fragment_id
            
        if model.chain_dict.has_key(chain_id):
            chain = model.chain_dict[chain_id]

            if chain.fragment_dict.has_key(fragment_id):
                fragment = chain.fragment_dict[fragment_id]

                if fragment.res_name == atom.res_name:
                    fragment.add_atom(atom)
                else:
                    raise FragmentOverwrite()
            else:
                chain.add_atom(atom, delay_sort)
        else:
            model.add_atom(atom, delay_sort)

    def remove_atom(self, atom):
        """Removes a Atom.
        """
        assert isinstance(atom, Atom)
        self.model_dict[atom.model_id].remove_atom(atom)

    def iter_atoms(self):
        """Iterates over all Atom objects in the default Model, using the
        default alt_loc.  The iteration is preformed in order according to
        the Chain and Fragment ordering rules the Atom object is a part of.
        """
        if self.default_model is None:
            raise StopIteration
        
        for chain in self.default_model.chain_list:
            for frag in chain.fragment_list:
                for atm in frag.atom_list:
                    yield atm

    def count_atoms(self):
        """Counts all Atom objects in the default Model using the
        default alt_loc.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_atoms()
        return n
                
    def iter_all_atoms(self):
        """Iterates over all Atom objects in the Structure.  The iteration
        is performed according to common PDB ordering rules, over all Models
        and all alternate conformations.
        """
        for model in self.iter_models():
            for atm in model.iter_all_atoms():
                yield atm

    def count_all_atoms(self):
        """Counts all atoms in the default Model using the default alt_loc.
        """
        n = 0
        for model in self.iter_models():
            n += model.count_all_atoms()
        return n

    def get_equivalent_atom(self, atom):
        """Returns the atom with the same fragment_id and name as the
        argument atom, or None if it is not found.
        """
        try:
            return self.model_dict[atom.model_id].chain_dict[atom.chain_id].fragment_dict[atom.fragment_id].atom_dict[atom.name]
        except KeyError:
            return None

    def iter_bonds(self):
        """Iterates over all Bond objects.  The iteration is preformed by
        iterating over all Atom objects in the same order as iter_atoms(),
        then iterating over each Atom's Bond objects.
        """
        visited = {}
        for atm in self.iter_atoms():
            for bond in atm.iter_bonds():
                if visited.has_key(bond):
                    continue
                yield bond
                visited[bond] = True

    def count_bonds(self):
        """Counts all Bond objects using the default Model and default
        alt_loc.
        """
        n = 0
        for bond in self.iter_bonds():
            n += 1
        return n

    def alt_loc_list(self):
        """Return the unique list of Atom alternate location IDs found in
        the Structure.
        """
        al_list = []
        for atm in self.iter_all_atoms():
            if atm.alt_loc != "" and atm.alt_loc not in al_list:
                al_list.append(atm.alt_loc)
        return al_list

    def add_alpha_helix(self, alpha_helix):
        """Adds a AlphaHelix to the default Model object.
        """
        assert self.default_model is not None
        self.default_model.add_alpha_helix(alpha_helix)

    def iter_alpha_helicies(self):
        """Iterates over all child AlphaHelix objects in the default
        Model.
        """
        if self.default_model:
            return self.default_model.iter_alpha_helicies()
        return iter(list())

    def add_beta_sheet(self, beta_sheet):
        """Adds a BetaSheet to the default Model object.
        """
        assert self.default_model is not None
        self.default_model.add_beta_sheet(beta_sheet)
        
    def iter_beta_sheets(self):
        """Iterate over all beta sheets in the Structure.
        """
        if self.default_model:
            return self.default_model.iter_beta_sheets()
        return iter(list())

    def add_site(self, site):
        """Adds a Site object to the default Model.
        """
        assert self.default_model is not None
        self.default_model.add_site(site)

    def iter_sites(self):
        """Iterate over all active/important sites defined in the Structure.
        """
        if self.default_model:
            return self.default_model.iter_sites()
        return iter(list())

    def get_structure(self):
        """Returns self.
        """
        return self

    def get_default_alt_loc(self):
        """Returns the default alt_loc string.
        """
        return self.default_alt_loc

    def set_default_alt_loc(self, alt_loc):
        """Sets the default alt_loc for the Stucture.
        """
        assert isinstance(alt_loc, str)

        self.default_alt_loc = alt_loc        
        for frag in self.iter_all_fragments():
            frag.set_default_alt_loc(alt_loc)

    def add_bonds_from_covalent_distance(self):
        """Builds a Structure's bonds by atomic distance distance using
        the covalent radii in element.cif.  A bond is built if the the
        distance between them is less than or equal to the sum of their
        covalent radii + 0.54A.
        """
        for model in self.iter_models():
            xyzdict = GeometryDict.XYZDict(2.0)
            
            for atm in model.iter_all_atoms():
                if atm.position is not None:
                    xyzdict.add(atm.position, atm)

            for (p1,atm1),(p2,atm2),dist in xyzdict.iter_contact_distance(2.5):

                if (atm1.alt_loc == "" or atm2.alt_loc == "") or (atm1.alt_loc == atm2.alt_loc):

                    ## calculate the expected bond distance by adding the
                    ## covalent radii + 0.54A
                    edesc1 = Library.library_get_element_desc(atm1.element)
                    edesc2 = Library.library_get_element_desc(atm2.element)

                    ## this will usually occur if an atom name does not match
                    ## the one found in the associated monomer library
                    if edesc1 is None or edesc2 is None:
                        continue

                    bond_dist = edesc1.covalent_radius + edesc2.covalent_radius + 0.54

                    ## this will usually occur if the bond distance between
                    ## between two atoms does not match the description in
                    ## in the monomer library
                    if dist > bond_dist:
                        continue

                    if atm1.get_bond(atm2) is None:
                        atm1.create_bond(atom = atm2, standard_res_bond = False)
        
    def add_bonds_from_library(self):
        """Builds bonds for all Fragments in the Structure from bond
        tables for monomers retrieved from the Library implementation
        of the Structure.
        """
        for frag in self.iter_all_fragments():
            frag.create_bonds()


class Model(object):
    """Multiple models support.
    """
    def __init__(self, model_id=1, **args):
        assert isinstance(model_id, int)

        self.structure        = None

        self.model_id         = model_id
        self.chain_dict       = {}
        self.chain_list       = []

        self.alpha_helix_list = []
        self.beta_sheet_list  = []
        self.site_list        = []

    def __str__(self):
        return "Model(model_id=%d)" % (self.model_id)

    def __deepcopy__(self, memo):
        model = Model(model_id = self.model_id)
        for chain in self.chain_list:
            model.add_chain(copy.deepcopy(chain, memo), True)
        return model

    def __lt__(self, other):
        assert isinstance(other, Model)
        return int(self.model_id) < int(other.model_id)
        
    def __le__(self, other):
        assert isinstance(other, Model)
        return int(self.model_id) <= int(other.model_id)
        
    def __gt__(self, other):
        assert isinstance(other, Model)
        return int(self.model_id) > int(other.model_id)

    def __ge__(self, other):
        assert isinstance(other, Model)
        return int(self.model_id) >= int(other.model_id)

    def __len__(self):
        """Returns the number of stored Chain objects.
        """
        return len(self.chain_list)
    
    def __getitem__(self, chain_idx):
        """Same as get_chain, but raises KeyError if the requested chain_id
        is not found.
        """
        if isinstance(chain_idx, str):
            return self.chain_dict[chain_idx]
        elif isinstance(chain_idx, int):
            return self.chain_list[chain_idx]
        raise TypeError, chain_idx

    def __iter__(self):
        """Iterates the Chain objects in the Model.
        """
        return iter(self.chain_list)

    def __contains__(self, chain_idx):
        """Returns True if the argument Chain or chain_id is in the Model.
        """
        if isinstance(chain_idx, Chain):
            return self.chain_list.__contains__(chain_idx)
        elif isinstance(chain_idx, str):
            return self.chain_dict.__contains__(chain_idx)
        raise TypeError, chain_idx

    def index(self, chain):
        """Returns the numeric index of the Chain object in the Model.
        """
        assert isinstance(chain, Chain)
        return self.chain_list.index(chain)

    def sort(self):
        """Sorts all Chains in the Model by their chain_id.
        """
        self.chain_list.sort()
        for chain in self.chain_list:
            chain.sort()

    def add_chain(self, chain, delay_sort=False):
        """Adds a Chain to the Model.
        """
        assert isinstance(chain, Chain)

        if self.chain_dict.has_key(chain.chain_id):
            raise ChainOverwrite()

        self.chain_list.append(chain)
        self.chain_dict[chain.chain_id] = chain
        chain.model = self

        if not delay_sort:
            self.chain_list.sort()

    def remove_chain(self, chain):
        """Removes the Chain from the Model.
        """
        assert isinstance(chain, Chain)
        self.chain_list.remove(chain)
        del self.chain_dict[chain.chain_id]
        chain.model = None

    def get_chain(self, chain_id):
        """Returns the Chain object matching the chain_id character.
        """
        if self.chain_dict.has_key(chain_id):
            return self.chain_dict[chain_id]
        return None

    def iter_chains(self):
        """Iterates over all Chain objects in alphabetical order according
        to their chain_id.
        """
        return iter(self.chain_list)

    def count_chains(self):
        """Counts all Chain objects.
        """
        return len(self.chain_list)

    def add_fragment(self, fragment, delay_sort = False):
        """Adds a Fragment instance
        """
        assert isinstance(fragment, Fragment)
        assert fragment.model_id == self.model_id

        ## add new chain if necessary
        try:
            chain = self.chain_dict[fragment.chain_id]
        except KeyError:
            chain = Chain(
                model_id = fragment.model_id,
                chain_id = fragment.chain_id)
            self.add_chain(chain, delay_sort)
        
        chain.add_fragment(fragment, delay_sort)

    def remove_fragment(self, fragment):
        """Removes a Fragment object.
        """
        assert isinstance(fragment, Fragment)
        self.chain_dict[fragment.chain_id].remove_fragment(fragment)

    def count_fragments(self):
        """Counts all Fragment objects.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_fragments()
        return n

    def iter_fragments(self):
        """Iterates over all Fragment objects. The iteration is performed
        in order according the the parent Chain's chain_id, and the
        Fragment's position within the chain.
        """
        for chain in self.chain_list:
            for frag in chain.fragment_list:
                yield frag

    def has_amino_acids(self):
        for frag in self.iter_amino_acids():
            return True
        return False

    def count_amino_acids(self):
        n = 0
        for chain in self.iter_chains():
            n += chain.count_amino_acids()
        return n

    def iter_amino_acids(self):
        for chain in self.iter_chains():
            for frag in chain.iter_amino_acids():
                yield frag

    def has_nucleic_acids(self):
        for frag in self.iter_nucleic_acids():
            return True
        return False

    def count_nucleic_acids(self):
        n = 0
        for chain in self.iter_chains():
            n += chain.count_nucleic_acids()
        return n

    def iter_nucleic_acids(self):
        for chain in self.iter_chains():
            for frag in chain.iter_nucleic_acids():
                yield frag

    def has_standard_residues(self):
        for frag in self.iter_standard_residues():
            return True
        return False

    def count_standard_residues(self):
        n = 0
        for na in self.iter_standard_residues():
            n += 1
        return n

    def iter_standard_residues(self):
        fpred = lambda f: f.is_standard_residue()
        return itertools.ifilter(fpred, self.iter_fragments())

    def count_non_standard_residues(self):
        n = 0
        for frag in self.iter_non_standard_residues():
            n += 1
        return n

    def has_non_standard_residues(self):
        for frag in self.iter_non_standard_residues():
            return True
        return False

    def iter_non_standard_residues(self):
        fpred = lambda f: f.is_standard_residue()
        return itertools.ifilterfalse(fpred, self.iter_fragments())

    def has_waters(self):
        for frag in self.iter_waters():
            return True
        return False

    def count_waters(self):
        n = 0
        for frag in self.iter_waters():
            n += 1
        return n

    def iter_waters(self):
        fpred = lambda f: f.is_water()
        return itertools.ifilter(fpred, self.iter_fragments())

    def add_atom(self, atom, delay_sort=False):
        assert isinstance(atom, Atom)
        assert atom.model_id == self.model_id

        ## add new chain if necessary
        try:
            chain = self.chain_dict[atom.chain_id]
        except KeyError:
            chain = Chain(
                model_id = atom.model_id,
                chain_id = atom.chain_id)
            self.add_chain(chain, delay_sort)

        ## add the atom to the chain
        chain.add_atom(atom, delay_sort)

    def remove_atom(self, atom):
        """Removes a Atom object.
        """
        assert isinstance(atom, Atom)
        assert atom.model_id == self.model_id        
        self.chain_dict[atom.chain_id].remove_atom(atom)

    def iter_atoms(self):
        """Iterates over all Atom objects according to the Structure
        defaults.
        """
        for chain in self.chain_list:
            for frag in chain.fragment_list:
                for atm in frag.atom_list:
                    yield atm

    def count_atoms(self):
        """Counts all Atom objects in according to the Structure defaults.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_atoms()
        return n

    def iter_all_atoms(self):
        """Iterates over all Atom objects including all atoms in multiple
        conformations.
        """
        for chain in self.iter_chains():
            for atm in chain.iter_all_atoms():
                yield atm

    def count_all_atoms(self):
        """Counts all Atom objects including all atoms in multiple
        conformations.
        """
        n = 0
        for chain in self.iter_chains():
            n += chain.count_all_atoms()
        return n

    def get_equivalent_atom(self, atom):
        """Returns the atom with the same fragment_id and name as the
        argument atom, or None if it is not found.
        """
        try:
            return self.chain_dict[atom.chain_id].fragment_dict[atom.fragment_id].atom_dict[atom.name]
        except KeyError:
            return None

    def add_alpha_helix(self, alpha_helix):
        """Adds a AlphaHelix object to the Model.
        """
        assert isinstance(alpha_helix, AlphaHelix)
        self.alpha_helix_list.append(alpha_helix)
        alpha_helix.model = self

    def remove_alpha_helix(self, alpha_helix):
        """Removes a AlphaHelix object from the Model.
        """
        assert isinstance(alpha_helix, AlphaHelix)
        self.alpha_helix_list.remove(alpha_helix)
        alpha_helix.model = None
        
    def iter_alpha_helicies(self):
        """Iterates over all AlphaHelix objects in the Model.
        """
        return iter(self.alpha_helix_list)

    def add_beta_sheet(self, beta_sheet):
        """Adds a BetaSheet object to the Model.
        """
        assert isinstance(beta_sheet, BetaSheet)
        self.beta_sheet_list.append(beta_sheet)
        beta_sheet.model = self

    def remove_beta_sheet(self, beta_sheet):
        """Removes a BetaSheet object from the Model.
        """
        assert isinstance(beta_sheet, BetaSheet)
        self.beta_sheet_list.remove(beta_sheet)
        beta_sheet.model = None

    def iter_beta_sheets(self):
        """Iterate over all child BetaSheet objects in the Model.
        """
        return iter(self.beta_sheet_list)

    def add_site(self, site):
        """Adds a Site (of interest) object to the Model.
        """
        assert isinstance(site, Site)
        self.site_list.append(site)
        site.model = self

    def remove_site(self, site):
        """Removes a Site (of interest) object from the Model.
        """
        assert isinstance(site, Site)
        self.site_list.append(site)
        site.model = None

    def iter_sites(self):
        """Iterate over all active/important sites defined in the Structure.
        """
        return iter(self.site_list)
    
    def get_structure(self):
        """Returns the parent Structure.
        """
        return self.structure

    def iter_bonds(self):
        """Iterates over all Bond objects.  The iteration is preformed by
        iterating over all Atom objects in the same order as iter_atoms(),
        then iterating over each Atom's Bond objects.
        """
        visited = {}
        for atm in self.iter_atoms():
            for bond in atm.iter_bonds():
                if visited.has_key(bond):
                    continue
                yield bond
                visited[bond] = True

    def count_bonds(self):
        """Counts all Bond objects.
        """
        n = 0
        for bond in self.iter_bonds():
            n += 1
        return n

    def set_model_id(self, model_id):
        """Sets the model_id of all contained objects.
        """
        assert isinstance(model_id, int)

        if self.structure is not None:
            chk_model = self.structure.get_model(model_id)
            if chk_model is not None or chk_model != self:
                raise ModelOverwrite()

        self.model_id = model_id

        for chain in self.iter_chains():
            chain.set_model_id(model_id)

        if self.structure is not None:
            self.structure.model_list.sort()


class Segment(object):
    """Segment objects are a container for Fragment objects, but are
    disaccociated with the Structure object hierarch.  Chain objects are
    a subclass of Segment objects which are part of the Structure hierarchy.
    """
    def __init__(self,
                 model_id = 1,
                 chain_id = "",
                 **args):

        assert isinstance(model_id, int)
        assert isinstance(chain_id, str)

        self.model    = None
        self.chain    = None

        self.model_id = model_id
        self.chain_id = chain_id

        ## fragments are contained in the list and also cached in
        ## a dictionary for fast random-access lookup
        self.fragment_list  = []
        self.fragment_dict  = {}

        ## sequence associated with the segment
        self.sequence = Sequence.Sequence()

    def __str__(self):
        try:
            return "Segment(%d:%s, %s...%s)" % (
                self.model_id, self.chain_id, self.fragment_list[0], self.fragment_list[-1])
        except IndexError:
             return "Segment(%d:%s)" % (self.model_id, self.chain_id)

    def __deepcopy__(self, memo):
        """Implements copy module protocol for deepcopy() operation.
        """
        segment = Segment(model_id = self.model_id, chain_id = self.chain_id)

        for fragment in self.fragment_list:
            segment.add_fragment(copy.deepcopy(fragment, memo), True)

        return segment
    
    def __lt__(self, other):
        """Less than operator based on the chain_id.
        """
        assert isinstance(other, Segment)
        return self.chain_id < other.chain_id
        
    def __le__(self, other):
        """Less than or equal operator based on chain_id.
        """
        assert isinstance(other, Segment)
        return self.chain_id <= other.chain_id
        
    def __gt__(self, other):
        """Greator than operator based on chain_id.
        """
        assert isinstance(other, Segment)
        return self.chain_id > other.chain_id

    def __ge__(self, other):
        """Greator than or equal to operator based on chain_id.
        """
        assert isinstance(other, Segment)
        return self.chain_id >= other.chain_id

    def __len__(self):
        """Return the number of Fragments in the Segment.
        """
        return len(self.fragment_list)

    def __getitem__(self, fragment_idx):
        """Retrieve a Fragment within the Segment.  This can take a integer
        index of the Fragment's position within the segment, the fragment_id
        string of the Fragment to retrieve, or a slice of the Segment to
        return a new Segment object containing the sliced subset of Fragments.
        If the slice values are fragment_id strings, then the Segment which
        is returned includes those Fragments.  If the slice values are
        integers, then normal list slicing rules apply.
        """
        if isinstance(fragment_idx, int):
            return self.fragment_list[fragment_idx]

        elif isinstance(fragment_idx, str):
            return self.fragment_dict[fragment_idx]

        elif isinstance(fragment_idx, slice):
            
            ## determine if the slice is on list indexes or on fragment_id
            ## strings
            start = fragment_idx.start
            stop  = fragment_idx.stop
            
            ## check for index (list) slicing
            if (start is None and stop is None) or \
               (start is None and isinstance(stop, int)) or \
               (stop is None  and isinstance(start, int)) or \
               (isinstance(start, int) and isinstance(stop, int)):

                segment = self.construct_segment()
                for frag in self.fragment_list[start:stop]:
                    segment.add_fragment(frag, True)
                return segment
            
            ## check for fragment_id slicing
            if (start is None and isinstance(stop, str)) or \
               (stop is None  and isinstance(start, str)) or \
               (isinstance(start, str) and isinstance(stop, str)):

                return self.construct_sub_segment(start, stop)

        raise TypeError, fragment_idx

    def __iter__(self):
        """Iterate all Fragments contained in the Segment.
        """
        return iter(self.fragment_list)

    def __contains__(self, fragment_idx):
        """Checks for Fragment objects, or the fragment_id string.
        """
        if isinstance(fragment_idx, Fragment):
            return self.fragment_list.__contains__(fragment_idx)
        elif isinstance(fragment_idx, str):
            return self.fragment_dict.__contains__(fragment_idx)
        raise TypeError, fragment_idx

    def index(self, fragment):
        """Return the 0-based index of the fragment in the segment list.
        """
        return self.fragment_list.index(fragment)

    def sort(self):
        """Sort the Fragments in the Segment into proper order.
        """
        self.fragment_list.sort()

    def construct_segment(self):
        """Constructs a new Segment object so that it has a valid .chain
        reference.
        """
        segment = Segment(
            model_id = self.model_id,
            chain_id = self.chain_id)

        segment.chain = self.chain
        segment.model = self.model

        return segment

    def construct_sub_segment(self, start_frag_id, stop_frag_id):
        """Construct and return a sub-Segment between start_frag_id 
        and stop_frag_id.  If start_frag_id is None, then the slice
        is taken from the beginning of this Segment, and if stop_frag_id
        is None it is taken to the end of this Segment.
        """
        fragiter = iter_fragments(iter(self.fragment_list), start_frag_id, stop_frag_id)
        segment = self.construct_segment()
        for frag in fragiter:
            segment.add_fragment(frag, True)
        return segment
    
    def add_fragment(self, fragment, delay_sort = False):
        """Adds a Fragment instance to the Segment.  If delay_sort is True,
        then the fragment is not inserted in the proper position within the
        segment.
        """
        assert isinstance(fragment, Fragment)
        assert fragment.chain_id == self.chain_id

        if self.fragment_dict.has_key(fragment.fragment_id):
            raise FragmentOverwrite()

        self.fragment_list.append(fragment)
        self.fragment_dict[fragment.fragment_id] = fragment

        if not delay_sort:
            self.fragment_list.sort()

    def remove_fragment(self, fragment):
        """Removes a Fragment object from the Segment.
        """
        assert isinstance(fragment, Fragment)
        self.fragment_list.remove(fragment)
        del self.fragment_dict[fragment.fragment_id]

    def get_fragment(self, fragment_id):
        """Returns the PDB fragment uniquely identified by its fragment_id.
        """
        if self.fragment_dict.has_key(fragment_id):
            return self.fragment_dict[fragment_id]
        return None

    def iter_fragments(self, frag_id_begin = None, frag_id_end = None):
        """Iterates over all Fragment objects.  The iteration is performed
        in order according to the Fragment's position within the Segment
        object.
        """
        return iter_fragments(iter(self.fragment_list), frag_id_begin, frag_id_end)

    def count_fragments(self):
        """Return the number of Fragment objects.
        """
        return len(self.fragment_list)

    def has_amino_acids(self):
        for frag in self.fragment_list:
            if frag.is_amino_acid():
                return True
        return False

    def count_amino_acids(self):
        n = 0
        for frag in self.fragment_list:
            if frag.is_amino_acid():
                n += 1
        return n
    
    def iter_amino_acids(self):
        fpred = lambda f: f.is_amino_acid()
        return itertools.ifilter(fpred, self.fragment_list)

    def has_nucleic_acids(self):
        for frag in self.fragment_list:
            if frag.is_nucleic_acid():
                return True
        return False

    def count_nucleic_acids(self):
        n = 0
        for frag in self.fragment_list:
            if frag.is_nucleic_acid():
                n += 1
        return n

    def iter_nucleic_acids(self):
        fpred = lambda f: f.is_nucleic_acid()
        return itertools.ifilter(fpred, self.fragment_list)

    def has_standard_residues(self):
        for frag in self.fragment_list:
            if frag.is_standard_residue():
                return True
        return False

    def count_standard_residues(self):
        n = 0
        for frag in self.fragment_list:
            if frag.is_standard_residue():
                n += 1
        return n

    def iter_standard_residues(self):
        fpred = lambda f: f.is_standard_residue()
        return itertools.ifilter(fpred, self.fragment_list)

    def has_non_standard_residues(self):
        for frag in self.fragment_list:
            if not frag.is_standard_residue():
                return True
        return False

    def count_non_standard_residues(self):
        n = 0
        for frag in self.fragment_list:
            if not frag.is_standard_residue():
                n += 1
        return n

    def iter_non_standard_residues(self):
        fpred = lambda f: f.is_standard_residue()
        return itertools.ifilterfalse(fpred, self.fragment_list)

    def has_waters(self):
        for frag in self.fragment_list:
            if frag.is_water():
                return True
        return False

    def count_waters(self):
        n = 0
        for frag in self.fragment_list:
            if frag.is_water():
                n += 1
        return n

    def iter_waters(self):
        fpred = lambda f: f.is_water()
        return itertools.ifilter(fpred, self.fragment_list)

    def add_atom(self, atom, delay_sort = False):
        """Adds a Atom.
        """
        assert isinstance(atom, Atom)
        assert atom.model_id == self.model_id
        assert atom.chain_id == self.chain_id

        ## add new fragment if necessary 
        if not self.fragment_dict.has_key(atom.fragment_id):
            
            if Library.library_is_amino_acid(atom.res_name):
                fragment = AminoAcidResidue(
                    model_id    = atom.model_id,
                    chain_id    = atom.chain_id,
                    fragment_id = atom.fragment_id,
                    res_name    = atom.res_name)

            elif Library.library_is_nucleic_acid(atom.res_name):
                fragment = NucleicAcidResidue(
                    model_id    = atom.model_id,
                    chain_id    = atom.chain_id,
                    fragment_id = atom.fragment_id,
                    res_name    = atom.res_name)
            else:
                fragment = Fragment(
                    model_id    = atom.model_id,
                    chain_id    = atom.chain_id,
                    fragment_id = atom.fragment_id,
                    res_name    = atom.res_name)

            self.add_fragment(fragment, delay_sort)

        else:
            fragment = self.fragment_dict[atom.fragment_id]
            if fragment.res_name != atom.res_name:
                raise FragmentOverwrite()

        fragment.add_atom(atom)
            
    def remove_atom(self, atom):
        """Removes a Atom object.
        """
        assert isinstance(atom, Atom)
        self.fragment_dict[atom.fragment_id].remove_atom(atom)

    def iter_atoms(self):
        """Iterates over all Atom objects within the Segment using the
        default conformation set in the parent Structure.
        """
        for frag in self.fragment_list:
            for atm in frag.atom_list:
                yield atm

    def count_atoms(self):
        n = 0
        for frag in self.iter_fragments():
            n += frag.count_atoms()
        return n
    
    def iter_all_atoms(self):
        """Performs a in-order iteration of all atoms in the Segment,
        including alternate conformations.
        """
        for frag in self.fragment_list:
            for atm in frag.iter_all_atoms():
                yield atm

    def count_all_atoms(self):
        n = 0
        for frag in self.iter_fragments():
            n += frag.count_all_atoms()
        return n

    def get_equivalent_atom(self, atom):
        """Returns the atom with the same fragment_id and name as the
        argument atom, or None if it is not found.
        """
        try:
            return self.fragment_dict[atom.fragment_id].atom_dict[atom.name]
        except KeyError:
            return None
                
    def iter_bonds(self):
        """Iterates over all Bond objects attached to Atom objects within the
        Segment.
        """
        visited = {}
        for atm in self.iter_atoms():
            for bond in atm.iter_bonds():
                if visited.has_key(bond):
                    continue
                yield bond
                visited[bond] = True

    def get_chain(self):
        """Returns the Chain object this Segment is part of.
        """
        return self.chain

    def get_model(self):
        """Returns the parent Model object.
        """
        return self.model
            
    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.model.structure

    def set_model_id(self, model_id):
        """Sets the model_id of all contained objects.
        """
        assert isinstance(model_id, int)
        self.model_id = model_id

        for frag in self.iter_fragments():
            frag.set_model_id(model_id)

    def set_chain_id(self, chain_id):
        """Sets the model_id of all contained objects.
        """
        assert isinstance(chain_id, str)
        self.chain_id = chain_id

        for frag in self.iter_fragments():
            frag.set_chain_id(chain_id)

    def is_homolog(self, segment2):
        """Returns True if there are no disagreements in the sequences of 
        this segment and segment2.
        """
        hdict = {}

        for fragment in self.fragment_list:
            hdict[fragment.fragment_id] = fragment.res_name

        for fragment in segment2.fragment_list:
            if hdict.get(fragment.fragment_id, fragment.res_name) != fragment.res_name:
                return False

        return True

class Chain(Segment):
    """Chain objects contain an ordered list of Fragment objects.
    """
    def __init__(self,
                 model_id = 1,
                 chain_id = "",
                 **args):

        args["model_id"] = model_id
        args["chain_id"] = chain_id
        Segment.__init__(self, **args)
        self.model = None

    def __str__(self):
        try:
            return "Chain(%d:%s, %s...%s)" % (
                self.model_id, self.chain_id, self.fragment_list[0], self.fragment_list[-1])
        except IndexError:
             return "Chain(%d:%s)" % (self.model_id, self.chain_id)

    def __deepcopy__(self, memo):
        """Implements the copy module deepcopy() protocol.
        """
        chain = Chain(model_id = self.model_id,
                      chain_id = self.chain_id)
        for fragment in self.fragment_list:
            chain.add_fragment(copy.deepcopy(fragment, memo), True)
        return chain
        
    def construct_segment(self):
        """Constructs a new Segment object so that it has a valid .chain
        reference.
        """
        segment = Segment(
            model_id = self.model_id,
            chain_id = self.chain_id)

        segment.chain = self
        segment.model = self.model

        return segment

    def set_sequence(self, sequence_list):
        """The sequence_list is a list of 3-letter residue name codes which
        define the polymer sequence for the chain.  Setting the sequence
        attempts to map the sequence codes to Fragment objects.
        """
        self.sequence_fragment_list = []
        for res_name in sequence_list:
            self.sequence_fragment_list.append((res_name, None))

    def remove_sequence(self):
        """Removes the current sequence mapping.
        """
        self.sequence_fragment_list = []

    def iter_sequence(self):
        """Iterates over all 3-letter residue codes for the polymer sequence.
        """
        for res_name, fragment in self.sequence_fragment_list:
            yield res_name

    def construct_sequence_list(self):
        """Constructs and returns a list with the 3-letter residue codes
        for the polymer sequence.
        """
        return list(self.iter_sequence())

    def get_fragment_sequence_index(self, seq_index):
        return self.sequence_fragment_list[seq_index][1]

    def add_fragment(self, fragment, delay_sort=False):
        """Adds a Fragment instance to the Chain.  If delay_sort is True,
        then the fragment is not inserted in the proper position within the
        chain.
        """
        Segment.add_fragment(self, fragment, delay_sort)
        fragment.chain = self

    def remove_fragment(self, fragment):
        """Remove the Fragment from the Chain.
        """
        Segment.remove_fragment(self, fragment)
        fragment.chain = None
            
    def set_chain_id(self, chain_id):
        """Sets a new ID for the Chain, updating the chain_id
        for all objects in the Structure hierarchy.
        """
        ## check for conflicting chain_id in the structure
        if self.model is not None:
            chk_chain = self.model.get_chain(chain_id)
            if chk_chain is not None or chk_chain != self:
                raise ChainOverwrite()

        Segment.set_chain_id(self, chain_id)

        ## resort the parent structure
        if self.model is not None:
            self.model.chain_list.sort()


class Fragment(object):
    """Fragment objects are a basic unit for organizing small groups of
    Atoms.  Amino acid residues are fragments, as well as nucleic
    acids and other small molecules.  In terms of a PDB file, they are
    all the atoms from a unique residue in a chain.  Fragments have the
    following attributes:

    Fragment.res_name     - the fragment/residue name
    Fragment.res_seq      - the sequence id of the fragment/residue
    Fragment.chain_id     - the ID of the chain containing this fragment
    """
    def __init__(self,
                 model_id    = 1,
                 chain_id    = "",
                 fragment_id = "",
                 res_name    = "",
                 **args):

        assert isinstance(model_id, int)
        assert isinstance(res_name, str)
        assert isinstance(fragment_id, str)
        assert isinstance(chain_id, str)

        self.chain           = None

        self.model_id        = model_id
        self.chain_id        = chain_id
        self.fragment_id     = fragment_id        
        self.res_name        = res_name

        self.default_alt_loc = "A"

        ## Atom objects stored in the original order as
        ## they were added to the Fragment
        self.atom_order_list = []

        ## dictionary of atom name->Altloc objects
        self.alt_loc_dict    = {}

        ## Atom object list/dict setup according to the current
        ## default_alt_loc
        self.atom_list       = []
        self.atom_dict       = {}

    def __str__(self):
        return "Frag(%s,%s,%s)" % (
            self.res_name,
            self.fragment_id,
            self.chain_id)
    
    def __deepcopy__(self, memo):
        fragment = Fragment(
            model_id    = self.model_id,
            chain_id    = self.chain_id,
            fragment_id = self.fragment_id,
            res_name    = self.res_name)

        for atom in self.iter_all_atoms():
            fragment.add_atom(copy.deepcopy(atom, memo))

        return fragment

    def __lt__(self, other):
        assert isinstance(other, Fragment)
        return fragment_id_lt(self.fragment_id, other.fragment_id)
        
    def __le__(self, other):
        assert isinstance(other, Fragment)
        return fragment_id_le(self.fragment_id, other.fragment_id)

    def __gt__(self, other):
        assert isinstance(other, Fragment)
        return fragment_id_gt(self.fragment_id, other.fragment_id)

    def __ge__(self, other):
        assert isinstance(other, Fragment)
        return fragment_id_ge(self.fragment_id, other.fragment_id)

    def __len__(self):
        return len(self.atom_list)
    
    def __getitem__(self, name_idx):
        """Lookup a atom contained in a fragment by its name, or by its index
        within the fragment's private atom_list.  If the atom is not found,
        a exception is raised.  The type of exception depends on the argument
        type.  If the argument was a integer, then a IndexError is raised.
        If the argument was a string, then a KeyError is raised.
        """
        if isinstance(name_idx, str):
            return self.atom_dict[name_idx]
        elif isinstance(name_idx, int):
            return self.atom_list[name_idx]
        raise TypeError, name_idx

    def __iter__(self):
        """Iterates the atoms within the fragment.  If the fragment contains
        atoms in alternate conformations, only the atoms with the structure's
        default_alt_loc are iterated.
        """
        return iter(self.atom_list)

    def __contains__(self, atom_idx):
        """Return True if the Atom object is contained in the fragment.
        """
        if isinstance(atom_idx, Atom):
            return self.atom_list.__contains__(atom_idx)
        elif isinstance(atom_idx, str):
            return self.atom_dict.__contains__(atom_idx)
        raise TypeError, atom_idx

    def index(self, atom):
        """Returns the sequential index of the atom.
        """
        return self.atom_list.index(atom)

    def set_default_alt_loc(self, alt_loc):
        """Sets the default alt_loc of the Fragment.
        """
        self.default_alt_loc = alt_loc

        ishift = 0
        for i, atm in enumerate(self.atom_order_list):
            if isinstance(atm, Atom):
                ## case 1: atom has no alt_locs
                try:
                    self.atom_list[i-ishift] = atm
                except IndexError:
                    self.atom_list.append(atm)
                self.atom_dict[atm.name] = atm

            else:
                try:
                    atmx = atm[alt_loc]
                except KeyError:
                    ## case 2: atom has alt_loc partners, but not one
                    ##         for this given alt_loc
                    try:
                        del self.atom_list[i-ishift]
                    except IndexError:
                        pass
                    for atmx in atm.itervalues():
                        try:
                            del self.atom_dict[atmx.name]
                        except KeyError:
                            pass
                        break
                    ishift += 1
                else:
                    ## case 3: atom has alt_loc partners, and one for
                    ##         this alt_loc too
                    try:
                        self.atom_list[i-ishift] = atmx
                    except IndexError:
                        self.atom_list.append(atmx)
                    self.atom_dict[atmx.name] = atmx
        
    def add_atom(self, atom):
        """Adds a atom to the fragment, and sets the atom's atom.fragment
        attribute to the fragment.
        """
        assert isinstance(atom, Atom)
        assert atom.chain_id    == self.chain_id
        assert atom.fragment_id == self.fragment_id
        assert atom.res_name    == self.res_name

        name    = atom.name
        alt_loc = atom.alt_loc

        if alt_loc == "":
            if not self.alt_loc_dict.has_key(name):
                ## CASE:
                ##     add atom without alt_loc partners to the fragment
                ## procedure:
                ##     check if a atom with the same name is already in the
                ##     fragment, and raise a AtomOverwrite exception if
                ##     it is, otherwise, add the atom to the fragment

                if not self.atom_dict.has_key(name):
                    self.atom_order_list.append(atom)
                    self.atom_list.append(atom)
                    self.atom_dict[name] = atom

                else:
                    ## CASE:
                    ##     multiple atoms with the same name, without
                    ##     alt_loc labels, but they are really alt_loc
                    ##     partners
                    atomA = self.atom_dict[name]
                    assert atomA != atom

                    ConsoleOutput.warning("atom name clash %s, automatically assigning ALTLOC labels" % (str(atomA)))

                    iA = self.atom_order_list.index(atomA)

                    self.alt_loc_dict[name] = altloc = Altloc()
                    self.atom_order_list[iA] = altloc

                    altloc.add_atom(atomA)
                    altloc.add_atom(atom)
                    self.set_default_alt_loc(self.default_alt_loc)

            else:
                ## CASE:
                ##    adding atom without alt_loc, but partner atoms
                ##    are already in the fragment with alt_loc
                ## procedure:
                ##    set the atom.alt_loc to the next reasonable alt_loc
                ##    and add it to the fragment
                altloc = self.alt_loc_dict[name]
                altloc.add_atom(atom)
                self.set_default_alt_loc(self.default_alt_loc)

                
        else: ## alt_loc!=""

            ## CASE:
            ##     add a atom with alt_loc partners to the
            ##     fragment for the first time
            ## procedure:
            ##    *check for atoms without alt_locs already in the
            ##     fragment, and 
            ##    *create new Altloc, and place it in the
            ##     alt_loc_dict under the atom name
            ##    *add the atom to the atom_order_list to preserve
            ##     sequential order of added atoms
            ##    *place atom in the atom_list and atom_dict 

            if not self.alt_loc_dict.has_key(name):

                if not self.atom_dict.has_key(name):
                    ## CASE:
                    ##     add a atom with alt_loc partners to the
                    ##     fragment for the first time
                    self.alt_loc_dict[name] = altloc = Altloc()
                    altloc.add_atom(atom)

                    self.atom_order_list.append(altloc)

                    self.atom_list.append(atom)
                    self.atom_dict[name] = atom

                else:
                    ## CASE:
                    ##     add atom with alt_loc, but there is already a
                    ##     atom in the fragment with a null alt_loc which
                    ##     needs to be given a valid alt_loc and placed
                    ##     in the Altloc container before adding the new
                    ##     atom
                    atomA = self.atom_dict[name]
                    iA = self.atom_order_list.index(atomA)

                    self.alt_loc_dict[name] = altloc = Altloc()
                    self.atom_order_list[iA] = altloc

                    altloc.add_atom(atomA)
                    altloc.add_atom(atom)

            else:
                ## CASE:
                ##     add a atom with alt_loc partners to the
                ##     fragment when there are already alt_loc
                ##     partner atoms in the fragment
                altloc = self.alt_loc_dict[name]
                altloc.add_atom(atom)

            self.set_default_alt_loc(self.default_alt_loc)
            
        atom.fragment = self

    def remove_atom(self, atom):
        """Removes the Atom instance from the Fragment.
        """
        assert atom.fragment == self
        
        if self.alt_loc_dict.has_key(atom.name):
            altloc = self.alt_loc_dict[atom.name]
            if altloc.has_key(atom.alt_loc):
                altloc.remove_atom(atom)
                if len(altloc) == 0:
                    del self.alt_loc_dict[atom.name]
                    self.atom_order_list.remove(altloc)
                if atom in self.atom_list:
                    self.atom_list.remove(atom)
                    del self.atom_dict[atom.name]
        else:
            self.atom_order_list.remove(atom)
            self.atom_list.remove(atom)
            del self.atom_dict[atom.name]

        atom.fragment = None

    def get_atom(self, name, alt_loc = None):
        """Returns the matching Atom instance contained in the Fragment.
        Returns None if a match is not found. If alt_loc is not given,
        then the default alt_loc is used.
        """
        if alt_loc:
            if self.alt_loc_dict.has_key(name):
                altloc = self.alt_loc_dict[name]
                if altloc.has_key(alt_loc):
                    return altloc[alt_loc]
            return None
        else:
            if not self.atom_dict.has_key(name):
                return None
            return self.atom_dict[name]
    
    def get_equivalent_atom(self, atom):
        """Returns the atom with the same fragment_id and name as the
        argument atom, or None if it is not found.
        """
        try:
            return self.atom_dict[atom.name]
        except KeyError:
            return None
        
    def iter_atoms(self):
        """Iterates over all Atom objects contained in the Fragment matching
        the current model and default alt_loc.
        """
        return iter(self.atom_list)

    def count_atoms(self):
        """Counts Atom objects.
        """
        return len(self.atom_list)

    def iter_all_atoms(self):
        """Iterates of all Atoms in the Fragment including Altlocs.
        """
        for atm in self.atom_order_list:
            if isinstance(atm, Atom):
                yield atm
            else:
                for atmx in atm:
                    yield atmx

    def count_all_atoms(self):
        """Counts all Atom objects including Atoms in alternate conformations.
        """
        n = 0
        for atm in self.atom_order_list:
            if isinstance(atm, Atom):
                n += 1
            else:
                n += len(atm)
        return n

    def iter_bonds(self):
        """Iterates over all Bond objects.  The iteration is preformed by
        iterating over all Atom objects in the same order as iter_atoms(),
        then iterating over each Atom's Bond objects."""
        visited = {}
        for atm in self.iter_atoms():
            for bond in atm.iter_bonds():
                if not visited.has_key(bond):
                    yield bond
                    visited[bond] = True

    def get_offset_fragment(self, offset):
        """Returns the fragment in the same chain at integer offset from
        self.  Returns None if no fragment is found.
        """
        assert isinstance(offset, int)

        i = self.chain.index(self) + offset
        if i < 0:
            return None
        try:
            return self.chain[i]
        except IndexError:
            return None

    def get_model(self):
        """Returns the parent Chain object.
        """
        return self.chain.model

    def get_chain(self):
        """Returns the parent Chain object.
        """
        return self.chain

    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.chain.model.structure

    def create_bonds(self):
        """Constructs bonds within a fragment. Bond definitions are retrieved
        from the monomer library.
        """
        mdesc = Library.library_get_monomer_desc(self.res_name)
        if mdesc is None:
            return

        def find_atom(name):
            try:
                return self[name]
            except KeyError:
                return self[mdesc.alt_atom_dict[name]]
        for bond in mdesc.bond_list:
            try:
                atm1 = find_atom(bond["atom1"])
                atm2 = find_atom(bond["atom2"])
            except KeyError:
                continue
            else:
                atm1.create_bonds(atom = atm2, standard_res_bond = True)

    def is_standard_residue(self):
        """Returns True if the Fragment/Residue object is one of the
        PDB defined standard residues.  PDB standard residues are amino
        and nucleic acid residues.
        """
        return False

    def is_amino_acid(self):
        """Returns True if the Fragment is a Amino Acid residue.
        """
        return False

    def is_nucleic_acid(self):
        """Returns True if the Fragment is a Nucleic Acid residue.
        """
        return False

    def is_water(self):
        """Returns True if the Fragment is a water molecule, returns False
        otherwise.
        """
        return Library.library_is_water(self.res_name)

    def set_model_id(self, model_id):
        """Sets the model_id of the Fragment and all contained Atom
        objects.
        """
        assert isinstance(model_id, int)
        self.model_id = model_id

        for atm in self.iter_atoms():
            atm.set_model_id(model_id)

    def set_chain_id(self, chain_id):
        """Sets the chain_id of the Fragment and all contained Atom
        objects.
        """
        assert isinstance(chain_id, str)
        self.chain_id = chain_id

        for atm in self.iter_atoms():
            atm.set_chain_id(chain_id)

    def set_fragment_id(self, fragment_id):
        """Sets the fragment_id of the Fragment and all contained Atom
        objects.
        """
        assert isinstance(fragment_id, str)

        if self.chain is not None:
            chk_frag = self.chain.get_fragment(fragment_id)
            if chk_frag is not None or chk_frag != self:
                raise FragmentOverwrite()

        self.fragment_id = fragment_id

        for atm in self.iter_atoms():
            atm.set_fragment_id(fragment_id)

        if self.chain is not None:
            self.chain.sort()

    def set_res_name(self, res_name):
        """Sets the res_name of the Fragment and all contained Atom
        objects.
        """
        assert isinstance(res_name, str)
        self.res_name = res_name

        for atm in self.iter_atoms():
            atm.set_res_name(res_name)

            
class Residue(Fragment):
    """A subclass of Fragment representing one residue in a polymer chain.
    """
    def __str__(self):
        return "Res(%s,%s,%s)" % (self.res_name,
                                  self.fragment_id,
                                  self.chain_id)

    def get_offset_residue(self, offset):
        """Returns the residue along the chain at the given integer offset
        from self. Returns None if there is no residue at that offset, or
        if the fragment found is not the same type of residue as self.
        """
        assert isinstance(offset, int)
        frag = Fragment.get_offset_fragment(self, offset)
        if type(self) == type(frag):
            return frag
        return None

    def create_bonds(self):
        """Constructs bonds within a fragment. Bond definitions are retrieved
        from the monomer library. This version also constructs the bonds
        between adjacent residues.
        """
        Fragment.create_bonds(self)
        return

        ## XXX: fixme
        next_res = self.get_offset_residue(1)
        if next_res is None:
            return

        mdesc1 = Library.library_get_monomer_desc(self.res_name)
        mdesc2 = Library.library_get_monomer_desc(next_res.res_name)

        if mdesc1 is None or mdesc2 is None:
            return

        for (name1, name2) in mdesc1.get_polymer_bond_list(self, next_res):
            try:
                atm1 = self[name1]
                atm2 = next_res[name2]
            except KeyError:
                continue
            else:
                atm1.create_bonds(atom = atm2, standard_res_bond = True)


class AminoAcidResidue(Residue):
    """A subclass of Residue representing one amino acid residue in a
    polypeptide chain.
    """
    def __deepcopy__(self, memo):
        fragment = AminoAcidResidue(
            model_id    = self.model_id,
            res_name    = self.res_name,
            fragment_id = self.fragment_id,
            chain_id    = self.chain_id)

        for atom in self.iter_all_atoms():
            fragment.add_atom(copy.deepcopy(atom, memo))

        return fragment

    def is_standard_residue(self):
        """Returns True if the Fragment/Residue object is one of the
        PDB defined standard residues.  PDB standard residues are amino
        and nucleic acid residues.
        """
        return True
    
    def is_amino_acid(self):
        """Returns True if the Fragment is a Amino Acid residue.
        """
        return True

    def is_water(self):
        """Returns True if the Fragment is a water molecule, returns False
        otherwise.
        """
        return False
    
    def calc_mainchain_bond_length(self):
        """Calculates the main chain bond lengths: (N-CA, CA-C, C-O, CA-CB,
        CA-(next)N).  The result is returned as a 5-tuple in that order.  Bond
        lengths involving missing atoms are returned as None in the tuple.
        """
        aN  = self.get_atom('N')
        aCA = self.get_atom('CA')
        aC  = self.get_atom('C')
        aO  = self.get_atom('O')
        aCB = self.get_atom('CB')

        try:
            naN = self.get_offset_residue(1).get_atom('N')
        except AttributeError:
            naN = None
     
        N_CA  = AtomMath.calc_distance(aN, aCA)
        CA_C  = AtomMath.calc_distance(aCA, aC)
        C_O   = AtomMath.calc_distance(aC, aO)
        C_nN  = AtomMath.calc_distance(aC, naN)
        CA_CB = AtomMath.calc_distance(aCA, aCB)
        return (N_CA, CA_C, C_O, CA_CB, C_nN)

    def calc_mainchain_bond_angle(self):
        """Calculates main chain bond angles (N-CA-C, N-CA-CB, CB-CA-C,
        CA-C-O, CA-C-(next)N, C-(next residue)N-(next residue)CA) and
        returns the result as a 6-tuple in that order. Angles involving
        missing atoms are returned as None in the tuple.
        """
        aN       = self.get_atom('N')
        aCA      = self.get_atom('CA')
        aC       = self.get_atom('C')
        aO       = self.get_atom('O')
        aCB      = self.get_atom('CB')

        naN      = None
        naCA     = None
        next_res = self.get_offset_residue(1)
        if next_res:
            naN  = next_res.get_atom('N')
            naCA = next_res.get_atom('CA')

        N_CA_C   = AtomMath.calc_angle(aN, aCA, aC)
        CA_C_O   = AtomMath.calc_angle(aCA, aC, aO)
        N_CA_CB  = AtomMath.calc_angle(aN, aCA, aCB)
        CB_CA_C  = AtomMath.calc_angle(aCB, aCA, aC)
        CA_C_nN  = AtomMath.calc_angle(aCA, aC, naN)
        C_nN_nCA = AtomMath.calc_angle(aC, naN, naCA)

        return (N_CA_C, N_CA_CB, CB_CA_C, CA_C_O, CA_C_nN, C_nN_nCA) 

    def calc_torsion_psi(self):
        """Calculates the Psi torsion angle of the amino acid.  Raises a
        CTerminal exception if called on a C-terminal residue which does
        not have a Psi torsion angle.
        """
        next_res = self.get_offset_residue(1)
        if next_res is None:
            return None

        aN  = self.get_atom('N')
        aCA = self.get_atom('CA')
        aC  = self.get_atom('C')
        naN = next_res.get_atom('N')
        return AtomMath.calc_torsion_angle(aN, aCA, aC, naN)

    def calc_torsion_phi(self):
        """Calculates the Phi torsion angle of the amino acid.  Raises a
        NTerminal exception if called on a N-terminal residue which does
        not have a Phi torsion angle.
        """
        prev_res = self.get_offset_residue(-1)
        if prev_res is None:
            return None

        paC = prev_res.get_atom('C')
        aN  = self.get_atom('N')
        aCA = self.get_atom('CA')
        aC  = self.get_atom('C')
        return AtomMath.calc_torsion_angle(paC, aN, aCA, aC)

    def calc_torsion_omega(self):
        """Calculates the Omega torsion angle of the amino acid. Raises a
        CTerminal exception if called on a C-terminal residue which does
        not have a Omega torsion angle.
        """
        next_res = self.get_offset_residue(1)
        if next_res is None:
            return None

        aCA  = self.get_atom('CA')
        aC   = self.get_atom('C')
        naN  = next_res.get_atom('N')
        naCA = next_res.get_atom('CA')
        return AtomMath.calc_torsion_angle(aCA, aC, naN, naCA)

    def is_cis(self):
        """Returns True if this is a CIS amino acid, otherwise returns False.
        It uses calc_torsion_omega, and if there are missing atoms this method
        will return None.
        """
        prev_res = self.get_offset_residue(-1)
        if prev_res is None:
            return None

        prev_omega = prev_res.calc_torsion_omega()
        if prev_omega is None:
            return None

        if abs(prev_omega) <= (math.pi/2.0):
            return True

        return False

    def calc_torsion(self, torsion_angle_name):
        """Calculates the given torsion angle for the monomer.  The torsion
        angles are defined by name in monomers.cif.
        """
        mdesc = Library.library_get_monomer_desc(self.res_name)
        try:
            (atom1_name,
             atom2_name,
             atom3_name,
             atom4_name) = mdesc.torsion_angle_dict[torsion_angle_name]
        except KeyError:
            return None

        atom1 = self.get_atom(atom1_name)
        atom2 = self.get_atom(atom2_name)
        atom3 = self.get_atom(atom3_name)
        atom4 = self.get_atom(atom4_name)
        
        return AtomMath.calc_torsion_angle(atom1, atom2, atom3, atom4)

    def calc_torsion_chi1(self):
        return self.calc_torsion("chi1")

    def calc_torsion_chi2(self):
        return self.calc_torsion("chi2")

    def calc_torsion_chi3(self):
        return self.calc_torsion("chi3")

    def calc_torsion_chi4(self):
        return self.calc_torsion("chi4")

    def calc_torsion_chi(self):
        """Calculates CHI side-chain torsion angles according to the
        amino acid specific definitions in the AminoAcids library.
        Returns the 4-tuple (CHI1, CHI2, CHI3, CHI4).  Angles involving
        missing atoms, or angles which do not exist for the amino acid
        are returned as None in the tuple.
        """
        return (self.calc_torsion("chi1"),
                self.calc_torsion("chi2"),
                self.calc_torsion("chi3"),
                self.calc_torsion("chi4"))
        
    def calc_pucker_torsion(self):
        """Calculates the Pucker torsion of a ring system.  Returns None
        for Amino Acids which do not have Pucker torsion angles.
        """
        return self.calc_torsion("pucker")

    
class NucleicAcidResidue(Residue):
    """A subclass of Residue representing one nuclic acid in a strand of
    DNA or RNA.
    """
    def __deepcopy__(self, memo):
        fragment = NucleicAcidResidue(
            model_id    = self.model_id,
            res_name    = self.res_name,
            fragment_id = self.fragment_id,
            chain_id    = self.chain_id)

        for atom in self.iter_all_atoms():
            fragment.add_atom(copy.deepcopy(atom, memo))

        return fragment
    
    def is_standard_residue(self):
        """Returns True if the Fragment/Residue object is one of the
        PDB defined standard residues.  PDB standard residues are amino
        and nucleic acid residues.
        """
        return True

    def is_nucleic_acid(self):
        """Returns True if the Fragment is a Nucleic Acid residue.
        """
        return True

    def is_water(self):
        """Returns True if the Fragment is a water molecule, returns False
        otherwise.
        """
        return False


class Altloc(dict):
    """Container holding the same atom, but for different conformations and
    occupancies.
    """
    def __deepcopy__(self, memo):
        altloc = Altloc()
        for atom in self.itervalues():
            altloc.add_atom(copy.deepcopy(atom, memo))
        return altloc
    
    def __iter__(self):
        """Iterates over all Altloc representations of this Atom.
        """
        alt_locs = self.keys()
        alt_locs.sort()
        for alt_loc in alt_locs:
            yield self[alt_loc]
    
    def add_atom(self, atom):
        """Adds a atom to the Altloc.
        """
        if self.has_key(atom.alt_loc) or atom.alt_loc == "":
            atom.alt_loc = self.calc_next_alt_loc_id(atom)

        self[atom.alt_loc] = atom
        atom.altloc = self

    def remove_atom(self, atom):
        """Removes the atom from this Altloc container.
        """
        assert atom.altloc == self
        del self[atom.alt_loc]
        atom.altloc = None
    
    def calc_next_alt_loc_id(self, atom):
        """Returns the next vacant alt_loc letter to be used for a key.
        This is part of a half-ass algorithm to deal with disordered
        input Atoms with improper alt_loc tagging.
        """
        if len(self) == 0:
            return "A"
        for alt_loc in string.uppercase:
            if not self.has_key(alt_loc):
                return alt_loc
            
        raise AtomOverwrite("exhausted availible alt_loc labels for "+str(atom))
        

class Atom(object):
    """Class representing a single atom.  Atoms have the following default
    attributes.  If an attribute has the value None, then the attribute was
    never set.  If the attribute has a default, then it is required.

    Atom[alt_loc]    - Atom objects in alternate locations can be accessed
                       by using Python's dictionary syntax with the alt_loc
                       character
    iter(Atom)       - iterates over all alt_loc versions of the Atom
    Atom.name        - label of the atom
    Atom.alt_loc     - alternate location indicater for the atom
    Atom.res_name    - the name of the resiude/fragment this atom is part of
    Atom.res_seq     - the residue/fragment sequence number
    Atom.icode       - the insertion code for the residue/fragment
    Atom.chain_id    - the chain ID of the chain containing this atom
    Atom.element     - symbol for the element
    Atom.position    - a numpy.array[3] (Numeric Python)
    Atom.occupancy   - [1.0 - 0.0] float 
    Atom.temp_factor - float represting B-style temp factor
    Atom.column6768  - string value. Can be used for anything in columns 67+68
    Atom.U           - a 6-tuple of the anisotropic values
    Atom.charge      - charge on the atom
    Atom.label_entity_id -
                       entity id corresponding to entity_poly_seq.entity_id
    Atom.label_asym_id -
                       asym id corresponding to struct_conf.beg_label_asym_id
    Atom.label_seq_id -
                       sequence id corresponding to entity_poly_seq_num
                       and struct_conn.ptnr?_label_seq_id
    """
    def __init__(
        self,
        name            = "",
        alt_loc         = "",
        res_name        = "",
        fragment_id     = "",
        chain_id        = "",
        model_id        = 1,
        element         = "",
        position        = None,
        x               = None,
        y               = None,
        z               = None,
        sig_position    = None,
        sig_x           = None,
        sig_y           = None,
        sig_z           = None,
        temp_factor     = None,
        column6768      = None,
        sig_temp_factor = None,
        occupancy       = None,
        sig_occupancy   = None,
        charge          = None,
        label_entity_id = None,
        label_asym_id   = None,
        label_seq_id    = None,

        U   = None,
        u11 = None, u22 = None, u33 = None,
        u12 = None, u13 = None, u23 = None,

        sig_U   = None,
        sig_u11 = None, sig_u22 = None, sig_u33 = None,
        sig_u12 = None, sig_u13 = None, sig_u23 = None,

        **args):

        assert isinstance(name, str)
        assert isinstance(model_id, int)
        assert isinstance(alt_loc, str)
        assert isinstance(res_name, str)
        assert isinstance(fragment_id, str)
        assert isinstance(chain_id, str)

        self.fragment        = None
        self.altloc          = None

        self.name            = name
        self.alt_loc         = alt_loc
        self.res_name        = res_name
        self.fragment_id     = fragment_id
        self.chain_id        = chain_id
        self.asym_id         = chain_id
        self.model_id        = model_id
        self.element         = element
        self.temp_factor     = temp_factor
        self.column6768      = column6768
        self.sig_temp_factor = sig_temp_factor
        self.occupancy       = occupancy
        self.sig_occupancy   = sig_occupancy
        self.charge          = charge
        self.label_entity_id = label_entity_id
        self.label_asym_id   = label_asym_id
        self.label_seq_id    = label_seq_id

        ## position
        if position is not None:
            self.position = position
        elif x is not None and y is not None and z is not None:
            self.position = numpy.array([x, y, z], float)
        else:
            self.position = None

        ## sig_position
        if sig_position is not None:
            self.sig_position = sig_position
        elif sig_x is not None and sig_y is not None and sig_z is not None:
            self.sig_position = numpy.array([sig_x, sig_y, sig_z], float)
        else:
            self.sig_position = None

        if U is not None:
            self.U = U
        elif u11 is not None:
            self.U = numpy.array(
                [ [u11, u12, u13],
                  [u12, u22, u23],
                  [u13, u23, u33] ], float)
        else:
            self.U = None

        if sig_U is not None:
            self.sig_U = sig_U
        elif sig_u11 is not None:
            self.sig_U = numpy.array(
                [ [sig_u11, sig_u12, sig_u13],
                  [sig_u12, sig_u22, sig_u23],
                  [sig_u13, sig_u23, sig_u33] ], float)
        else:
            self.sig_U = None

        self.bond_list = []

    def __str__(self):
        return "Atom(n=%s alt=%s res=%s chn=%s frag=%s mdl=%d)" % (
            self.name, self.alt_loc, self.res_name,
            self.chain_id, self.fragment_id, self.model_id)
        
        return "Atom(%4s%2s%4s%2s%4s%2d)" % (
            self.name, self.alt_loc, self.res_name,
            self.chain_id, self.fragment_id, self.model_id)

    def __deepcopy__(self, memo):
        atom_cpy = Atom(
            name            = self.name,
            alt_loc         = self.alt_loc,
            res_name        = self.res_name,
            fragment_id     = self.fragment_id,
            chain_id        = self.chain_id,
            model_id        = copy.copy(self.model_id),
            element         = self.element,
            position        = copy.deepcopy(self.position),
            sig_position    = copy.deepcopy(self.sig_position),
            temp_factor     = copy.copy(self.temp_factor),
            column6768      = copy.copy(self.column6768),
            sig_temp_factor = copy.copy(self.sig_temp_factor),
            occupancy       = copy.copy(self.occupancy),
            sig_occupancy   = copy.copy(self.sig_occupancy),
            charge          = copy.copy(self.charge),
            U               = copy.deepcopy(self.U),
            sig_U           = copy.deepcopy(self.sig_U),
            label_entity_id = self.label_entity_id,
            label_asym_id   = self.label_asym_id,
            label_seq_id    = self.label_seq_id)
        
        for bond in self.bond_list:
            partner = bond.get_partner(self)
            if memo.has_key(id(partner)):
                partner_cpy = memo[id(partner)]
                bond_cpy = copy.deepcopy(bond, memo)

                if bond.atom1 == self:
                    bond_cpy.atom1 = atom_cpy
                    bond_cpy.atom2 = partner_cpy
                else:
                    bond_cpy.atom1 = partner_cpy
                    bond_cpy.atom2 = atom_cpy
                
                atom_cpy.bond_list.append(bond_cpy)
                partner_cpy.bond_list.append(bond_cpy)
        
        return atom_cpy

    def __lt__(self, other):
        assert isinstance(other, Atom)

        if self.chain_id < other.chain_id:
            return True
        if self.chain_id > other.chain_id:
            return False

        if fragment_id_lt(self.fragment_id, other.fragment_id):
            return True
        if fragment_id_gt(self.fragment_id, other.fragment_id):
            return False

        if self.name < other.name:
            return True
        if self.name > other.name:
            return False

        if self.alt_loc == "" and other.alt_loc != "":
            return False
        if self.alt_loc != "" and other.alt_loc == "":
            return True

        return self.name < other.name
            
    def __le__(self, other):
        assert isinstance(other, Atom)

        if self.chain_id < other.chain_id:
            return True
        if self.chain_id > other.chain_id:
            return False

        if fragment_id_lt(self.fragment_id, other.fragment_id):
            return True
        if fragment_id_gt(self.fragment_id, other.fragment_id):
            return False

        if self.name < other.name:
            return True
        if self.name > other.name:
            return False

        if self.alt_loc == "" and other.alt_loc != "":
            return False
        if self.alt_loc != "" and other.alt_loc == "":
            return True

        return self.name <= other.name

    def __gt__(self, other):
        assert isinstance(other, Atom)

        if self.chain_id > other.chain_id:
            return True
        if self.chain_id < other.chain_id:
            return False

        if fragment_id_gt(self.fragment_id, other.fragment_id):
            return True
        if fragment_id_lt(self.fragment_id, other.fragment_id):
            return False

        if self.name > other.name:
            return True
        if self.name < other.name:
            return False

        if self.alt_loc == "" and other.alt_loc != "":
            return True
        if self.alt_loc != "" and other.alt_loc == "":
            return False

        return self.name > other.name

    def __ge__(self, other):
        assert isinstance(other, Atom)

        if self.chain_id > other.chain_id:
            return True
        if self.chain_id < other.chain_id:
            return False

        if fragment_id_gt(self.fragment_id, other.fragment_id):
            return True
        if fragment_id_lt(self.fragment_id, other.fragment_id):
            return False

        if self.name > other.name:
            return True
        if self.name < other.name:
            return False

        if self.alt_loc == "" and other.alt_loc != "":
            return True
        if self.alt_loc != "" and other.alt_loc == "":
            return False

        return self.name >= other.name

    def __len__(self):
        """Returns the number of alternate conformations of this atom.
        """
        if self.altloc:
            return len(self.altloc)
        return 0

    def __getitem__(self, alt_loc):
        """This is an alternative to calling get_alt_loc, but a KeyError
        exception is raised if the alt_loc Atom is not found.
        """
        assert isinstance(alt_loc, str)
        
        if self.altloc is None:
            if self.alt_loc == alt_loc:
                return self
            raise KeyError, alt_loc

        else:
            return self.altloc[alt_loc]

    def __iter__(self):
        """Iterates over all Altloc representations of this Atom.
        """
        if self.altloc is None:
            yield self

        else:
            alt_locs = self.altloc.keys()
            alt_locs.sort()
            for alt_loc in alt_locs:
                yield self.altloc[alt_loc]

    def __contains__(self, atom_alt_loc):
        """Returns True if the argument matches a alternate conformation of
        the Atom.  The argument can be a alt_loc label, or a Atom object.
        """
        if isinstance(atom_alt_loc, Atom):
            if self.altloc is None:
                return atom_alt_loc == self
            else:
                return self.altloc[atom_alt_loc.alt_loc] == atom_alt_loc

        elif isinstance(atom_alt_loc, str):
            if self.altloc is None:
                return atom_alt_loc == self.alt_loc
            else:
                return self.altloc.__contains__(atom_alt_loc)
            
        return False

    def remove_alt_loc(self, atom):
        """Removes the argument Atom from the Altloc. 
        """
        try:
            self.fragment.remove_atom(atom)
        except AttributeError:
            if self.altloc is not None and self.altloc.has_key(atom.alt_loc):
                del self.altloc[atom.alt_loc]

    def get_alt_loc(self, alt_loc):
        """Returns the Atom object matching the alt_loc argument.
        """
        try:
            return self[alt_loc]
        except KeyError:
            return None

    def iter_alt_loc(self):
        """Iterate over all alt_loc versions of this atom in the
        alphabetical order of the alt_loc labels, within the current model.
        """
        return iter(self)

    def create_bond(self,
                    atom              = None,
                    bond_type         = None,
                    atom1_symop       = None,
                    atom2_symop       = None,
                    standard_res_bond = False):

        """Creates a bond between this atom and the argumentatom. The
        argument bond_type is a string, atom1_symop and atom2_symop are
        symmetry operations to be applied to self and the argument atom
        before distance calculations, and standard_res_bond is a flag
        used to indicate this bond is a standard bond.
        """
        assert isinstance(atom, Atom)
        assert ((self.alt_loc == atom.alt_loc) or
                (self.alt_loc == "" and atom.alt_loc != "") or
                (self.alt_loc != "" and atom.alt_loc == ""))

        bond = Bond(atom1             = self,
                    atom2             = atom,
                    bond_type         = bond_type,
                    atom1_symop       = atom1_symop,
                    atom2_symop       = atom2_symop,
                    standard_res_bond = standard_res_bond)

        self.bond_list.append(bond)
        atom.bond_list.append(bond)

    def create_bonds(self,
                     atom              = None,
                     bond_type         = None,
                     atom1_symop       = None,
                     atom2_symop       = None,
                     standard_res_bond = False):
        """Like create_bonds, but it bonds all alternate locations of this
        atom.
        """
        assert isinstance(atom, Atom)

        if self.altloc is None:
            if atom.altloc is None:
                ## case 1: self has no alt_loc, atom no alt_loc
                self.create_bond(
                    atom              = atom,
                    bond_type         = bond_type,
                    atom1_symop       = atom1_symop,
                    atom2_symop       = atom2_symop,
                    standard_res_bond = standard_res_bond)
            else:
                ## case 2: self.has no alt_loc, atom has alt_loc
                for atmx in atom.altloc.itervalues():
                    self.create_bond(
                        atom              = atmx,
                        bond_type         = bond_type,
                        atom1_symop       = atom1_symop,
                        atom2_symop       = atom2_symop,
                        standard_res_bond = standard_res_bond)


        else:
            if atom.altloc is None:
                ## case 3: self has alt_loc, atom has no alt_loc
                for (alt_loc, atmx) in self.altloc.iteritems():
                    atmx.create_bond(
                        atom              = atom,
                        bond_type         = bond_type,
                        atom1_symop       = atom1_symop,
                        atom2_symop       = atom2_symop,
                        standard_res_bond = standard_res_bond)

            else:
                ## case 4: self has alt_loc, atom has alt_loc
                for (alt_loc, atmx) in self.altloc.iteritems():
                    if atom.altloc.has_key(alt_loc):
                        atmx.create_bond(
                            atom              = atom.altloc[alt_loc],
                            bond_type         = bond_type,
                            atom1_symop       = atom1_symop,
                            atom2_symop       = atom2_symop,
                            standard_res_bond = standard_res_bond)

    def get_bond(self, atom):
        """Returns the Bond connecting self with the argument atom.
        """
        assert isinstance(atom, Atom)
        assert atom != self

        for bond in self.bond_list:
            if atom == bond.atom1 or atom == bond.atom2:
                return bond
        return None

    def iter_bonds(self):
        """Iterates over all the Bond edges connected to self.
        """
        for bond in self.bond_list:
            yield bond

    def iter_bonded_atoms(self):
        """Iterates over all the Atoms bonded to self.
        """
        for bond in self.iter_bonds():
            partner = bond.get_partner(self)
            assert partner is not None
            yield partner

    def get_bonded_atom(self, name_list):
        """From atom, follow the bonding path specified by
        a sequence of atom names given in name_list and return the last
        atom instance in the list.  Returns None if any atom in the
        bonding path cannot be found.
        """
        current_atom = self
        for name in name_list:
            moveto_atom = None
            for atom in current_atom.iter_bonded_atoms():
                if atom.name == name:
                    moveto_atom = atom
                    break
            if moveto_atom is None:
                return None
            current_atom = moveto_atom
        return current_atom        

    def get_fragment(self):
        """Returns the parent Fragment object.
        """
        return self.fragment

    def get_chain(self):
        """Returns the parent Chain object.
        """
        return self.fragment.chain

    def get_model(self):
        """Returns the parent Model object.
        """
        return self.fragment.chain.model
    
    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.fragment.chain.model.structure

    def set_U(self, u11, u22, u33, u12, u13, u23):
        """Sets the symmetric U tensor from the six unique values.
        """
        self.U = numpy.array([[u11, u12, u13],
                              [u12, u22, u23],
                              [u13, u23, u33]], float)

    def set_sig_U(self, u11, u22, u33, u12, u13, u23):
        """Sets the symmetric sig_U tensor from the six unique values.
        """
        self.sig_U = numpy.array([[u11, u12, u13],
                                  [u12, u22, u23],
                                  [u13, u23, u33]], float)

    def calc_Uiso(self):
        """Calculates the Uiso tensor from the Atom's temperature factor.
        """
        if self.temp_factor is None:
            return None
        return numpy.identity(3, float) * (self.temp_factor * Constants.B2U)

    def get_U(self):
        """Returns the Atoms's U tensor if it exists, otherwise returns
        the isotropic U tensor calculated by self.calc_Uiso
        """
        if self.U is not None:
            return self.U
        return self.calc_Uiso()

    def calc_anisotropy(self):
        """Calculates the anisotropy of that atom.  Anisotropy is defined
        as the ratio of the minimum/maximum eigenvalues of the 3x3
        symmetric tensor defined by U.
        """
        ## no Anisotropic values, we have a spherical isotropic atom
        if self.U is None:
            return 1.0

        evals = linalg.eigenvalues(self.U)
        ansotropy = min(evals) / max(evals)
        return ansotropy

    def calc_anisotropy3(self):
        """Calculates the eigenvalues of the U matrix and returns the
        3-tuple of the eigenvalue ratios: (e1/e2, e1/e3, e2/e3)
        """
        ## no Anisotropic values, we have a spherical atom
        if self.U is None:
            return (1.0, 1.0, 1.0)

        e1, e2, e3 = linalg.eigenvalues(self.U)
        elist = [e1, e2, e3]
        elist.sort()
        e1, e2, e3 = elist
        
        return (min(e1, e2) / max(e1, e2),
                min(e1, e3) / max(e1, e3),
                min(e2, e3) / max(e2, e3))
        
    def iter_atoms_by_distance(self, max_distance = None):
        """Iterates all atoms in the Structure object from the closest to the
        farthest up to the cutoff distance max_distance if given.  Yields
        the 2-tuple (dist, atm).
        """
        listx = []

        if max_distance:
            for atm in self.get_structure().iter_atoms():
                d = AtomMath.calc_distance(self, atm)
                if d <= max_distance:
                    listx.append((AtomMath.calc_distance(self, atm), atm))
        else:
            for atm in self.get_structure().iter_atoms():
                listx.append((AtomMath.calc_distance(self, atm), atm))

        listx.sort()
        return iter(listx)

    def set_model_id(self, model_id):
        """Sets the chain_id of the Atom and all alt_loc Atom
        objects.
        """
        assert isinstance(model_id, int)
        for atm in self.iter_alt_loc():
            atm.model_id = model_id 

    def set_chain_id(self, chain_id):
        """Sets the chain_id of the Atom and all alt_loc Atom
        objects.
        """
        assert isinstance(chain_id, str)
        for atm in self.iter_alt_loc():
            atm.chain_id = chain_id

    def set_fragment_id(self, fragment_id):
        """Sets the fragment_id of the Atom and all alt_loc Atom
        objects.
        """
        assert isinstance(fragment_id, str)
        for atm in self.iter_alt_loc():
            atm.fragment_id = fragment_id

    def set_res_name(self, res_name):
        """Sets the fragment_id of the Atom and all alt_loc Atom
        objects.
        """
        assert isinstance(res_name, str)
        for atm in self.iter_alt_loc():
            atm.res_name = res_name
            

class Bond(object):
    """Indicates two atoms are bonded together.
    """
    def __init__(
        self,
        atom1             = None,
        atom2             = None,
        bond_type         = None,
        atom1_symop       = None,
        atom2_symop       = None,
        standard_res_bond = False,
        **args):
        
        self.atom1             = atom1
        self.atom2             = atom2
        self.bond_type         = bond_type
        self.atom1_symop       = atom1_symop
        self.atom2_symop       = atom2_symop
        self.standard_res_bond = standard_res_bond

    def __str__(self):
        return "Bond(%s %s)" % (self.atom1, self.atom2)

    def __deepcopy__(self, memo):
        return Bond(
            bond_type         = self.bond_type,
            atom1_symop       = self.atom1_symop,
            atom2_symop       = self.atom2_symop,
            standard_res_bond = self.standard_res_bond)
    
    def get_partner(self, atm):
        """Returns the other atom involved in the bond.
        """
        if atm == self.atom1:
            return self.atom2
        elif atm == self.atom2:
            return self.atom1
        return None

    def get_atom1(self):
        """Returns atom #1 of the pair of bonded atoms. This is also 
        accessible by bond.atom1.
        """
        return self.atom1

    def get_atom2(self):
        """Returns atom #2 of the pair of bonded atoms.
        """
        return self.atom2

    def get_fragment1(self):
        """Returns the Fragment object of atom #1.
        """
        return self.atom1.fragment

    def get_fragment2(self):
        """Returns the Fragment object of atom #2.
        """
        return self.atom2.fragment

    def get_chain1(self):
        """Returns the Chain object of atom #1.
        """
        return self.atom1.fragment.chain

    def get_chain2(self):
        """Returns the Chain object of atom #2.
        """
        return self.atom2.fragment.chain

    def get_model1(self):
        """Returns the Model object of atom #1.
        """
        return self.atom1.fragment.chain.model

    def get_model2(self):
        """Returns the Structure object of atom #2.
        """
        return self.atom2.fragment.chain.model

    def get_structure1(self):
        """Returns the Structure object of atom #1.
        """
        return self.atom1.fragment.chain.model.structure

    def get_structure2(self):
        """Returns the Structure object of atom #2.
        """
        return self.atom2.fragment.chain.model.structure

    def calc_length(self):
        """Returns the length of the bond.
        """
        return AtomMath.length(self.atom1.position - self.atom2.position)


class AlphaHelix(object):
    """Class containing information on a protein alpha helix.
    """
    def __init__(self,
                 helix_id     = "",
                 helix_class  = "1",
                 helix_length = 0,
                 chain_id1    = "",
                 frag_id1     = "",
                 res_name1    = "",
                 chain_id2    = "",
                 frag_id2     = "",
                 res_name2    = "",
                 details      = "",
                 **args):

        assert isinstance(helix_id, str)
        assert isinstance(helix_class, str)
        assert isinstance(helix_length, int)
        assert isinstance(details, str)
        assert isinstance(chain_id1, str)
        assert isinstance(frag_id1, str)
        assert isinstance(res_name1, str)
        assert isinstance(chain_id2, str)
        assert isinstance(frag_id2, str)
        assert isinstance(res_name2, str)
        assert isinstance(details, str)

        self.model        = None

        self.helix_id     = helix_id
        self.helix_class  = helix_class
        self.helix_length = helix_length
        self.chain_id1    = chain_id1
        self.fragment_id1 = frag_id1
        self.res_name1    = res_name1
        self.chain_id2    = chain_id2
        self.fragment_id2 = frag_id2
        self.res_name2    = res_name2
        self.details      = details

        self.segment      = None

    def __str__(self):
        return "AlphaHelix(%s %s %s:%s...%s:%s)" % (
            self.helix_id, self.helix_class,
            self.chain_id1,
            self.fragment_id1,
            self.chain_id2,
            self.fragment_id2)

    def add_segment(self, segment):
        """Adds the Segment object this AlphaHelix spans.  If the AlphaHelix
        already has a Segment, then it is replaced.  The Segment objects added
        to AlphaHelix objects must have the attribute segment.chain referencing
        the source Chain object the Segment was sliced from.
        """
        assert segment is None or isinstance(segment, Segment)
        self.segment = segment

        ## just return if the segment is None
        if segment is None:
            return

        ## reset AlphaHelix description with the description derived
        ## from the new Segment
        try:
            frag1 = segment[0]
            frag2 = segment[-1]
        except IndexError:
            return
        
        self.chain_id1    = frag1.chain_id
        self.fragment_id1 = frag1.fragment_id
        self.res_name1    = frag1.res_name

        self.chain_id2    = frag2.chain_id
        self.fragment_id2 = frag2.fragment_id
        self.res_name2    = frag2.res_name

        self.helix_length = len(segment)

    def construct_segment(self):
        """Constructs the child Segment object from the Chain object found in
        the parent Structure object by the AlphaHelix chain_id/fragment_id
        information.  Returns True if the Segment was created, or False if
        it was not.  The Segment is not created when the fragment range
        fragment_id1:fragment_id2 cannot be found in the parent Chain object.
        """
        if self.chain_id1 != self.chain_id2:
            ConsoleOutput.fatal("alpha helix spans multiple chains -- not supported") 

        ## get the Chain object from the parent Model
        try:
            chain = self.model[self.chain_id1]
        except KeyError:
            self.add_segment(None)
            return False

        ## cut the Segment from the Chain using the given fragment_id
        ## range for the AlphaHelix
        try:
            segment = chain[self.fragment_id1:self.fragment_id2]
            segment.chain = chain
        except KeyError:
            self.add_segment(None)
            return False

        self.add_segment(segment)
        return True

    def get_chain(self):
        """Returns the parent Chain object.  If the AlphaHelix does not have
        a Segment child the raised AttributeError.
        """
        return self.segment.chain

    def get_model(self):
        """Returns the parent Model object.
        """
        return self.model

    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.model.structure

    def get_segment(self):
        """Return the child Segment object this AlphaHelix spans in the
        parent Model.
        """
        return self.segment

    def iter_fragments(self):
        """Iterates all Fragment objects in the AlphaHelix.
        """
        if self.segment is None:
            return iter(list())
        return self.segment.iter_fragments()

    def iter_atoms(self):
        """Iterates all Atom objects in the AlphaHelix.
        """
        if self.segment is None:
            return iter(list())
        return self.segment.iter_atoms()

    def iter_all_atoms(self):
        """Iterates all Atom objects in all AlphaHelix, plus any in
        non-default alt_loc conformations. 
        """
        if self.segment is None:
            return iter(list())
        return self.segment.iter_all_atoms()


class Strand(object):
    """One strand of a BetaSheet.
    """
    def __init__(self,
                 chain_id1         = "",
                 frag_id1          = "",
                 res_name1         = "",
                 chain_id2         = "",
                 frag_id2          = "",
                 res_name2         = "",
                 reg_chain_id      = "",
                 reg_frag_id       = "",
                 reg_res_name      = "",
                 reg_atom          = "",
                 reg_prev_chain_id = "",
                 reg_prev_frag_id  = "",
                 reg_prev_res_name = "",
                 reg_prev_atom     = "",
                 **args):

        assert isinstance(chain_id1, str)
        assert isinstance(frag_id1, str)
        assert isinstance(res_name1, str)
        assert isinstance(chain_id2, str)
        assert isinstance(frag_id2, str) 
        assert isinstance(res_name2, str)
        assert isinstance(reg_chain_id, str)
        assert isinstance(reg_frag_id, str)
        assert isinstance(reg_res_name, str)
        assert isinstance(reg_atom, str)
        assert isinstance(reg_prev_chain_id, str)
        assert isinstance(reg_prev_frag_id, str)
        assert isinstance(reg_prev_res_name, str)
        assert isinstance(reg_prev_atom, str)

        self.beta_sheet            = None
        
        self.chain_id1             = chain_id1
        self.fragment_id1          = frag_id1
        self.res_name1             = res_name1
        self.chain_id2             = chain_id2
        self.fragment_id2          = frag_id2
        self.res_name2             = res_name2
        self.reg_chain_id          = reg_chain_id
        self.reg_fragment_id       = reg_frag_id
        self.reg_res_name          = reg_res_name
        self.reg_atom              = reg_atom
        self.reg_prev_chain_id     = reg_prev_chain_id
        self.reg_prev_fragment_id  = reg_prev_frag_id
        self.reg_prev_res_name     = reg_prev_res_name
        self.reg_prev_atom         = reg_prev_atom
        
        self.segment               = None

    def __str__(self):
        return "Strand(%s:%s-%s:%s %s:%s:%s-%s:%s:%s)" % (
            self.chain_id1, self.fragment_id1,
            self.chain_id2, self.fragment_id2,
            self.reg_chain_id, self.reg_fragment_id, self.reg_atom,
            self.reg_prev_chain_id, self.reg_prev_fragment_id,
            self.reg_prev_atom)

    def add_segment(self, segment):
        """Adds the Segment object this Strand spans.  If the Strand
        already has a Segment, then it is replaced.  The Segment objects added
        to Strand objects must have the attribute segment.chain referencing
        the source Chain object the Segment was sliced from.
        """
        assert segment is None or isinstance(segment, Segment)

        self.segment = segment
        if segment is None:
            return

        ## reset Strand description with the description derived
        ## from the new Segment
        try:
            frag1 = segment[0]
            frag2 = segment[-1]
        except IndexError:
            return
        
        self.chain_id1    = frag1.chain_id
        self.fragment_id1 = frag1.fragment_id
        self.res_name1    = frag1.res_name

        self.chain_id2    = frag2.chain_id
        self.fragment_id2 = frag2.fragment_id
        self.res_name2    = frag2.res_name

    def construct_segment(self):
        """Constructs the child Segment object from the Chain object found in
        the parent Structure object by the BetaSheet chain_id/fragment_id
        information.  Returns True if the Segment was created, or False if
        it was not.  The Segment is not created when the fragment range
        fragment_id1:fragment_id2 cannot be found in the parent Chain object.
        """
        assert self.chain_id1 == self.chain_id2

        ## get the Chain object from the parent Model
        try:
            chain = self.beta_sheet.model[self.chain_id1]
        except KeyError:
            self.add_segment(None)
            return False

        ## cut the Segment from the Chain using the given fragment_id
        ## range for the BetaSheet
        try:
            segment = chain[self.fragment_id1:self.fragment_id2]
            segment.chain = chain
        except KeyError:
            self.add_segment(None)
            return False

        self.add_segment(segment)
        return True

    def get_beta_sheet(self):
        """Returns the parent BetaSheet object.
        """
        return self.beta_sheet

    def get_chain(self):
        """Returns the parent Chain object.  If the Strand does not have
        a Segment child the raised AttributeError.
        """
        return self.segment.chain

    def get_model(self):
        """Returns the parent Model object.
        """
        return self.beta_sheet.model

    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.beta_sheet.model.structure

    def get_segment(self):
        """Return the child Segment object this AlphaHelix spans in the
        parent Model.
        """
        return self.segment

    def iter_fragments(self):
        """Iterates all Fragment objects.
        """
        if self.segment is None:
            return iter(list())
        return self.segment.iter_fragments()

    def iter_atoms(self):
        """Iterates all Atom objects.
        """
        if self.segment is None:
            return iter(list())
        return self.segment.iter_atoms()

    def iter_all_atoms(self):
        """Iterates all Atom objects plus any in non-default alt_loc
        conformations. 
        """
        if self.segment is None:
            return iter(list())
        return self.segment.iter_all_atoms()


class BetaSheet(object):
    """Class containing information on a protein beta sheet.  BetaSheet
    objects contain a list of Segments spanning the beta sheet.
    """
    def __init__(self,
                 sheet_id  = "",
                 **args):

        assert isinstance(sheet_id, str)
        
        self.model       = None

        self.sheet_id    = sheet_id
        self.strand_list = []

    def __str__(self):
        return "BetaSheet(%s %d)" % (self.sheet_id, len(self.strand_list))

    def add_strand(self, strand):
        """Adds a Segment instance.
        """
        assert isinstance(strand, Strand)
        assert strand not in self.strand_list
        self.strand_list.append(strand)
        strand.beta_sheet = self

    def construct_segments(self):
        """Calls Strand.construct_segment() on all child Strand objects.
        """
        for strand in self.strand_list:
            strand.construct_segment()

    def get_model(self):
        """REturns the parent Model object.
        """
        return self.model

    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.model.structure

    def iter_strands(self):
        """Iterates over all child Strands objects.
        """
        return iter(self.strand_list)

    def iter_fragments(self):
        """Iterates over all Fragment objects.
        """
        for strand in self.strand_list:
            for frag in strand.iter_fragments():
                yield frag

    def iter_atoms(self):
        """Iterates all Atom objects.
        """
        for strand in self.strand_list:
            for atm in strand.iter_atoms():
                yield atm

    def iter_all_atoms(self):
        """Iterates all Atom objects plus any in non-default alt_loc
        conformations. 
        """
        for strand in self.strand_list:
            for atm in strand.iter_all_atoms():
                yield atm


class Site(object):
    """List of Fragments within a structure involved in a SITE description.
    """
    def __init__(self,
                 site_id            = "",
                 fragment_list      = [],
                 **args):

        assert isinstance(site_id, str)
        assert isinstance(fragment_list, list)

        self.model              = None
        self.site_id            = site_id
        self.fragment_dict_list = fragment_list

    def __str__(self):
        return "Site(id=%s)" % (self.site_id)

    def add_fragment(self, fragment_dict, fragment):
        """Adds a Fragment object to the fragment_dict and updates the
        values in fragment_dict to reflect the new Fragment object.  The
        fragment_dict is added to the Site if it is not already in it.
        """
        if fragment is not None:
            fragment_dict["fragment"]    = fragment
            fragment_dict["chain_id"]    = fragment.chain_id
            fragment_dict["frag_id"]     = fragment.fragment_id
            fragment_dict["res_name"]    = fragment.res_name
            
            if fragment_dict not in self.fragment_dict_list:
                self.fragment_dict_list.append(fragment_dict)

        else:
            if fragment_dict.has_key("fragment"):
                del fragment_dict["fragment"]

    def construct_fragments(self):
        """Using the site fragment descriptions, finds the Fragment objects
        in the parent Model.
        """
        for frag_dict in self.fragment_dict_list:
            try:
                chain = self.model[frag_dict["chain_id"]]
                frag  = chain[frag_dict["frag_id"]]
            except KeyError:
                self.add_fragment(frag_dict, None)
                continue

            self.add_fragment(frag_dict, frag)

    def get_model(self):
        """Returns the parent Model object.
        """
        return self.model

    def get_structure(self):
        """Returns the parent Structure object.
        """
        return self.model.structure

    def iter_fragments(self):
        """Iterates child Fragment objects.
        """
        for frag_dict in self.fragment_dict_list:
            try:
                yield frag_dict["fragment"]
            except KeyError:
                pass

    def iter_atoms(self):
        """Iterates all Atom objects.
        """
        for frag in self.iter_fragments():
            for atm in frag.iter_atoms():
                yield atm

    def iter_all_atoms(self):
        """Iterates all Atom objects plus any in non-default alt_loc
        conformations. 
        """
        for frag in self.iter_fragments():
            for atm in frag.iter_all_atoms():
                yield atm

def fragment_id_split(frag_id):
    """Split a string fragment_id into a 2-tuple of:
    (sequence_num, insertion_code)
    """
    try:
        return (int(frag_id), None)
    except ValueError:
        return (int(frag_id[:-1]), frag_id[-1:])

def fragment_id_eq(frag_id1, frag_id2):
    """Performs a proper equivalency of fragment_id strings according
    to their sequence number, then insertion code.
    """
    return frag_id1 == frag_id2
    
def fragment_id_lt(frag_id1, frag_id2):
    """Performs a proper less than comparison of fragment_id strings
    according to their sequence number, then insertion code.
    """
    return fragment_id_split(frag_id1) < fragment_id_split(frag_id2)
    
def fragment_id_le(frag_id1, frag_id2):
    """Performs a proper less than or equal to comparison of fragment_id
    strings according to their sequence number, then insertion code.
    """
    return fragment_id_split(frag_id1) <= fragment_id_split(frag_id2)

def fragment_id_gt(frag_id1, frag_id2):
    """Performs a proper greater than comparison of fragment_id strings
    according to their sequence number, then insertion code.
    """
    return fragment_id_split(frag_id1) > fragment_id_split(frag_id2)
    
def fragment_id_ge(frag_id1, frag_id2):
    """Performs a proper greater than or equal to comparison of
    fragment_id strings according to their sequence number, then
    insertion code.
    """
    return fragment_id_split(frag_id1) >= fragment_id_split(frag_id2)

def fragment_id_cmp(frag_id1, frag_id2):
    """Compare two fragment ids.
    """
    if fragment_id_lt(frag_id1, frag_id2):
        return -1
    if fragment_id_lt(frag_id1, frag_id2):
        return 0
    return 1

def iter_fragments(fragiter, start_frag_id = None, stop_frag_id = None):
    """Given a fragment iterator and a start and end fragment id,
    return a iterator which yields only fragments within the range.
    """
    if start_frag_id and stop_frag_id:
        dpred = lambda f: fragment_id_lt(f.fragment_id, start_frag_id)
        tpred = lambda f: fragment_id_le(f.fragment_id, stop_frag_id)
        return itertools.takewhile(tpred, itertools.dropwhile(dpred, fragiter))
    elif start_frag_id and not stop_frag_id:
        dpred = lambda f: fragment_id_lt(f.fragment_id, start_frag_id)
        return itertools.dropwhile(dpred, fragiter)
    elif not start_frag_id and stop_frag_id:
        tpred = lambda f: fragment_id_le(f.fragment_id, stop_frag_id)
        return itertools.takewhile(tpred, fragiter)
    return fragiter

class FragmentID(object):
    """Stores a fragment_id as integer residue sequence number and a
    single-character insertion code.
    """
    def __init__(self, frag_id):
        self.res_seq = 1
        self.icode = ""
        try:
            self.res_seq = int(frag_id)
        except ValueError:
            try:
                self.res_seq = int(frag_id[:-1])
            except ValueError:
                pass
            else:
                self.icode = frag_id[-1]
    def __str__(self):
        return "%d%s" % (self.res_seq, self.icode)
    def __lt__(self, other):
        assert isinstance(other, FragmentID)
        return (self.res_seq, self.icode) < (other.res_seq, other.icode)
    def __le__(self, other):
        assert isinstance(other, FragmentID)
        return (self.res_seq, self.icode) <= (other.res_seq, other.icode)
    def __eq__(self, other):
        assert isinstance(other, FragmentID)
        return (self.res_seq, self.icode) == (other.res_seq, other.icode)
    def __ne__(self, other):
        assert isinstance(other, FragmentID)
        return (self.res_seq, self.icode) != (other.res_seq, other.icode)
    def __gt__(self, other):
        assert isinstance(other, FragmentID)
        return (self.res_seq, self.icode) > (other.res_seq, other.icode)
    def __ge__(self, other):
        assert isinstance(other, FragmentID)
        return (self.res_seq, self.icode) >= (other.res_seq, other.icode)
                
class AtomList(list):
    """Provides the functionality of a Python list class for containing
    Atom instances.  It also provides class methods for performing some
    useful calculations on the list of atoms.
    """
    def calc_centroid(self):
        """Calculates the centroid of all contained Atom instances and
        returns a Vector to the centroid.
        """
        num      = 0
        centroid = numpy.zeros(3, float)
        for atm in self:
            if atm.position is not None:
                centroid += atm.position
                num += 1
        return centroid / num
        
    def calc_adv_temp_factor(self):
        """Calculates the average temperature factor of all contained Atom 
        instances and returns the average temperature factor.
        """
        num_tf = 0
        adv_tf = 0.0

        for atm in self:
            if atm.temp_factor is not None:
                adv_tf += atm.temp_factor
                num_tf += 1

        return adv_tf / num_tf

    def calc_adv_U(self):
        """Calculates the average U matrix of all contained Atom instances and 
        returns the 3x3 symmetric U matrix of that average.
        """
        num_U = 0
        adv_U = numpy.zeros((3,3), float)

        for atm in self:
            ## use the atom's U matrix if it exists, otherwise use the
            ## temperature factor

            if atm.U is not None:
                adv_U += atm.U
                num_U += 1

        return adv_U / num_U

    def calc_adv_anisotropy(self):
        """Calculates the average anisotropy for all Atoms in the AtomList.
        """
        num_atoms = 0
        adv_aniso = 0.0

        for atm in self:
            try:
                adv_aniso += atm.calc_anisotropy()
            except ZeroDivisionError:
                pass
            else:
                num_atoms += 1

        return adv_aniso / num_atoms
        
    def calc_adv_anisotropy3(self):
        """Calculates the average anisotropy 3-tuple for all Atoms in the 
        AtomList.
        """
        num_atoms  = 0
        adv_aniso1 = 0.0
        adv_aniso2 = 0.0
        adv_aniso3 = 0.0

        for atm in self:
            try:
                a1, a2, a3 = atm.calc_anisotropy3()
            except ZeroDivisionError:
                pass
            else:
                adv_aniso1 += a1
                adv_aniso2 += a2
                adv_aniso3 += a3
                num_atoms  += 1

        return (adv_aniso1 / num_atoms,
                adv_aniso2 / num_atoms,
                adv_aniso3 / num_atoms)


### <testing>
def test_module():
    struct = Structure()

    for mx in xrange(1, 4):
        mid = str(mx)
        for cid in ["A", "B", "C", "D"]:
            for fx in xrange(1, 4): 
                fid = str(fx)

                for name in ["N", "CA", "C", "O"]:

                    for alt_loc in ["A", "B", "C"]:

                        if alt_loc == "C" and name == "CA": continue

                        atm = Atom(
                            name = name,
                            alt_loc = alt_loc,
                            model = mid,
                            chain_id = cid,
                            res_name = "GLY",
                            fragment_id = fid)

                        struct.add_atom(atm)

    for cx in struct.iter_chains():
        print "iter_chains: ",cx
    for fx in struct.iter_fragments():
        print "iter_fragments: ",fx
        for ax in fx.iter_all_atoms():
            print "iter_all_atoms: ",ax

    for ax in struct.iter_atoms():
        print "iter_atoms: ",ax

    struct.set_default_alt_loc("C")
    for ax in struct.iter_atoms():
        print "iter_atoms: ",ax


    ## make some exceptions happen
    chk_atm = Atom(
        name = "CX",
        alt_loc = "B",
        model = "1",
        chain_id = "A",
        res_name = "GLY",
        fragment_id = "1")

    for a in struct.iter_atoms():
        print "WARNING! Bad atom name: ", a

if __name__ == "__main__":
    test_module()
### </testing>

import os
import csv
import json
import numpy as np

from app.config import Config
from copy import deepcopy
from openbabel import openbabel
from rdkit import Chem
from rdkit.Chem.rdmolfiles import MolFromMolFile

class _ChemicalFeaturesFactory:
    """This is a singleton class for RDKit base features."""
    _instance = None

    @classmethod
    def get_instance(cls):
        try:
            from rdkit import RDConfig
            from rdkit.Chem import ChemicalFeatures

        except ModuleNotFoundError:
            raise ImportError("This class requires RDKit to be installed.")

        if not cls._instance:
            fdefName = os.path.join(RDConfig.RDDataDir, 'BaseFeatures.fdef')
            cls._instance = ChemicalFeatures.BuildFeatureFactory(fdefName)
        return cls._instance


def pdb2sdf(inputfile, outputfile):
    obConversion = openbabel.OBConversion()
    obConversion.SetInAndOutFormats("pdb", "sdf")
    obConversion.OpenInAndOutFiles(inputfile,outputfile)
    obConversion.Convert()
    obConversion.CloseOutFile() 


def get_feature_dict(mol):
    if mol == None:
        return {}
        
    feature_by_group = {}
    factory = _ChemicalFeaturesFactory.get_instance()
    for f in factory.GetFeaturesForMol(mol):
        feature_by_group[f.GetAtomIds()] = f.GetFamily()


    feature_dict = {}
    for key in feature_by_group:
        for atom_idx in key:
            if atom_idx in feature_dict:
                feature_dict[atom_idx].append(feature_by_group[key])
            else:
                feature_dict[atom_idx] = [feature_by_group[key]]

    return feature_dict, feature_by_group

def RecommendChange(ligand, ligand_bonding_info, dict_centroid):
    recommend_change = []
    pharmacophore_not_empty = {}
    for index, type_interact_ligand in ligand_bonding_info.items():
        pos = ligand.GetConformer().GetAtomPosition(int(index))
        coord_ligand = np.array([pos.x, pos.y, pos.z])

        have_pharmacophore = None
        recommend = []
        for type_interact_receptor, list_centroid in dict_centroid.items():
            if type_interact_receptor not in pharmacophore_not_empty:
                pharmacophore_not_empty[type_interact_receptor] = []
            for centroid in list_centroid:
                # check with radius + 5.5
                distance = np.linalg.norm(np.array(centroid[0]-coord_ligand))
                if distance<(centroid[1]):
                    if centroid[0] not in pharmacophore_not_empty[type_interact_receptor]:
                        pharmacophore_not_empty[type_interact_receptor].append(centroid[0])
                    
                    if type_interact_receptor == 'HD':
                        if 'Acceptor' not in type_interact_ligand:
                            recommend.append(('HA',distance, list(coord_ligand)))
                            have_pharmacophore = False
                        else:
                            have_pharmacophore = True
                        
                    elif type_interact_receptor == 'HA':
                        if 'Donor' not in type_interact_ligand:
                            recommend.append(('HD',distance, list(coord_ligand)))
                            have_pharmacophore = False
                        else:
                            have_pharmacophore = True

                    elif type_interact_receptor == 'HY':
                        if 'Aromatic' not in type_interact_ligand or 'LumpedHydrophobe' not in type_interact_ligand:
                            recommend.append(('HY',distance, list(coord_ligand)))
                            have_pharmacophore = False
                        else:
                            have_pharmacophore = True
        #Nếu không thuộc bất cứ pharmacophore nào
        if have_pharmacophore is not None:
            if not have_pharmacophore:
                for rec in recommend:
                    recommend_change.append((rec[0], rec[2]))

    return recommend_change, pharmacophore_not_empty

def GetEmptyPharmacophore(pharmacophore_not_empty, dict_centroid):
    pharmacophore_empty = {}
    for type, centroids in dict_centroid.items():
        if type not in pharmacophore_empty:
            pharmacophore_empty[type] = []
        
        for centroid in centroids:
            if centroid[0] not in pharmacophore_not_empty[type]:
                pharmacophore_empty[type].append(centroid[0])
    
    return pharmacophore_empty


def GetAllAtoms(ligand):
    list_atoms = []
    for i in range(0, ligand.GetNumAtoms()):
        pos = ligand.GetConformer().GetAtomPosition(i)
        list_atoms.append([pos.x, pos.y, pos.z])
    
    return list_atoms

def RecommendAdd(pharmacophore_not_empty, ligand, dict_centroid):
    pharmacophore_empty = GetEmptyPharmacophore(pharmacophore_not_empty, dict_centroid)
    list_atoms = GetAllAtoms(ligand)
    recommend_add = []
    for type, centroids in pharmacophore_empty.items():
        if len(centroids) == 0:
            continue
        for centroid in centroids:
            list_distance = [(atom,np.linalg.norm(np.array(atom)-np.array(centroid))) for atom in list_atoms]
            list_distance.sort(key = lambda x: x[1])
            if type == 'HD':
                recommend_add.append(('HA',list_distance[0][0]))
            elif type == 'HA':
                recommend_add.append(('HD',list_distance[0][0]))
            elif type == 'HY':
                recommend_add.append(('HY',list_distance[0][0]))
    return recommend_add


def CheckNotInCircuit(index, ligand, feature_by_group):
    atom = ligand.GetAtomWithIdx(index)
    bond = [bond.GetBondType() for bond in atom.GetBonds()]
    if len(bond) >= 2:
        if atom.IsInRing():
            for k, v in feature_by_group.items():
                if index in k and v == 'Aromatic':
                    count = 0
                    for i in k:
                        atom_i = ligand.GetAtomWithIdx(i)
                        bond_i = [bond.GetBondType() for bond in atom_i.GetBonds()]
                        if len(bond_i)>=3:
                            count+=1
                    if count>1:
                        return False, 0
                    else:
                        return True, k

        return False, 0
    
    return True, index

def ReconstructLigand(ligand):
    for a in ligand.GetAtoms():
        a.SetAtomMapNum(a.GetIdx())

    smiles_ligand = Chem.MolToSmiles(ligand)
    new_ligand = Chem.MolFromSmiles(smiles_ligand)

    mapping_smiles_idx = {}
    for i in new_ligand.GetAtoms():
        atommapnum = i.GetAtomMapNum()
        if atommapnum not in mapping_smiles_idx:
            mapping_smiles_idx[atommapnum] = i.GetIdx()

    num_atom = len(ligand.GetAtoms())

    return new_ligand, mapping_smiles_idx, num_atom

def GetIndexInteract(mol):
    index_interact = 0
    mol_temp = Chem.MolFromMolBlock(Chem.MolToMolBlock(mol))
    for i in range(0, mol_temp.GetNumAtoms()):
        pos = mol_temp.GetConformer().GetAtomPosition(i)
        if pos.x==0 and pos.y==0 and pos.z==0:
            index_interact = i

    return index_interact

def RemoveBond(ligand, combo, mol, index, num_atom):
    if len(index) == 1:
        atom = ligand.GetAtomWithIdx(index[0])
        bond = [bond.GetBondType() for bond in atom.GetBonds()]
        all_bonds = []
        for bond in atom.GetBonds():
            other_atom = bond.GetOtherAtom(atom)
            all_bonds.append([other_atom.GetIdx(), bond])

        combo.RemoveAtom(index[0])
        first_bond = num_atom + GetIndexInteract(mol) - len(index)
        for bond in all_bonds:
            second_bond = bond[0] if bond[0] < index[0] else bond[0] - len(index)
            combo.AddBond(first_bond,second_bond, Chem.rdchem.BondType.SINGLE)
    else:
        list_index = []
        for i in index:
            atom = ligand.GetAtomWithIdx(i)
            bond = [bond.GetBondType() for bond in atom.GetBonds()]
            if len(bond) == 3:
                for bond_atom in atom.GetBonds():
                    other_atom = bond_atom.GetOtherAtom(atom)
                    list_index.append(other_atom.GetIdx())

        new_index = deepcopy(index)
        new_index.sort(reverse=True)
        for i in new_index:
            combo.RemoveAtom(i)

        first_bond = num_atom + GetIndexInteract(mol) - len(index)
        second_bond = 0
        for idx in list_index:
            if idx not in index:
                second_bond = idx
        count_less = 0
        for idx in index:
            if idx < second_bond:
                count_less+=1
        second_bond = second_bond - count_less

        combo.AddBond(first_bond,second_bond, Chem.rdchem.BondType.SINGLE)

    return combo

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class DSSSystem(metaclass=Singleton):
    def __init__(self) -> None:
        self.dict_centroid = None
        self.data_fragment = {}
        self.data_recommend = {}

        with open(Config.PHARMACOPHORE_MODEL, 'r') as f:
            self.dict_centroid = json.load(f)

        with open(Config.DATA_FRAGMENT, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file, delimiter=';')
            for row in reader:
                if int(row[0]) not in self.data_fragment:
                    self.data_fragment[int(row[0])] = row[2]

        with open(Config.DATA_RECOMMENDATION, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file, delimiter=';')
            for row in reader:
                list_fragment = [int(index_fragment) for index_fragment in row[1].split(',')]
                if row[0] not in self.data_recommend:
                    self.data_recommend[row[0]] = list_fragment

    def run(self, docked_ligand_file):
        # Read ligand and calculate features
        ligand = MolFromMolFile(docked_ligand_file)
        list_atoms = GetAllAtoms(ligand)
        ligand_bonding_info, feature_by_group = get_feature_dict(ligand)
        
        # Recommend change
        recommend_change, pharmacophore_not_empty = RecommendChange(ligand, ligand_bonding_info, self.dict_centroid)
        
        # Recommend add
        recommend_add = RecommendAdd(pharmacophore_not_empty, ligand, self.dict_centroid)

        result = []

        for rec_change in recommend_change:
            index = list_atoms.index(rec_change[1])
            list_fragment = None
            if rec_change[0]=='HA':
                list_fragment = self.data_recommend['H-Acceptor']
            elif rec_change[0]=='HD':
                list_fragment = self.data_recommend['H-Donor']
            elif rec_change[0]=='HY':
                list_fragment = self.data_recommend['Aromatic'] + self.data_recommend['LumpedHydrophobe']
            
            flag, index = CheckNotInCircuit(index, ligand, feature_by_group)
            if flag:
                for fragment in list_fragment:
                    new_rec = {'type': 'replace', 'atom_idx': index, 'fragment': self.data_fragment[fragment]}
                    if new_rec not in result:
                        result.append(new_rec)

        for rec_add in recommend_add:
            index = list_atoms.index(rec_add[1])
            list_fragment = None
            if rec_add[0]=='HA':
                list_fragment = self.data_recommend['H-Acceptor']
            elif rec_add[0]=='HD':
                list_fragment = self.data_recommend['H-Donor']
            elif rec_add[0]=='HY':
                list_fragment = self.data_recommend['Aromatic'] + self.data_recommend['LumpedHydrophobe']
            
            for fragment in list_fragment:
                new_rec = {'type': 'add', 'atom_idx': index, 'fragment': self.data_fragment[fragment]}
                if new_rec not in result:
                    result.append(new_rec)

        return result

    def GenRecommendAdd(self, ligand, atom_idx, fragment):
        new_ligand, mapping_smiles_idx, num_atom = ReconstructLigand(ligand)

        index_atom = int(atom_idx)
        mol = Chem.MolFromSmiles(fragment)
        edcombo = Chem.EditableMol(Chem.CombineMols(new_ligand, mol))
        edcombo.AddBond(mapping_smiles_idx[index_atom],num_atom + GetIndexInteract(mol), order=Chem.rdchem.BondType.SINGLE)
        return edcombo.GetMol()

    def GenRecommendReplace(self, ligand, atom_idx, fragment):
        new_ligand, mapping_smiles_idx, num_atom = ReconstructLigand(ligand)

        if isinstance(atom_idx, int):
            index_atom = [mapping_smiles_idx[atom_idx]]
        else:
            index_atom = list(map(lambda x: mapping_smiles_idx[x], atom_idx))

        mol = Chem.MolFromSmiles(fragment)
        edcombo = Chem.EditableMol(Chem.CombineMols(new_ligand, mol))
        edcombo = RemoveBond(new_ligand, edcombo, mol, index_atom, num_atom)
        return edcombo.GetMol()

    def apply(self, ligand_file, suggestion):
        ligand = MolFromMolFile(ligand_file)
        
        if suggestion["type"] == "add":
            mol = self.GenRecommendAdd(ligand, suggestion["atom_idx"], suggestion["fragment"])
        elif suggestion["type"] == "replace":
            mol = self.GenRecommendReplace(ligand, suggestion["atom_idx"], suggestion["fragment"])
        
        molString = Chem.MolToMolBlock(mol, kekulize = False)
        return molString

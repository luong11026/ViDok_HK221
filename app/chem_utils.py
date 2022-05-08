from app.config import Config
from app.models import Users, Ligands
from app.dss_system import DSSSystem

import os
import time
import numpy as np
from vina import Vina
from openbabel import openbabel as ob
from rdkit.Geometry import Point3D
from rdkit.Chem.rdmolfiles import MolFromMolFile, MolToMolFile

def save_compound(user_id, file_name, compound):
    with open(
                os.path.join(Config.CHEM_DIR, "compounds", str(user_id), file_name), \
                "w", encoding="utf-8"
             ) as f:
        f.write(compound)

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class DockingAgent(metaclass=Singleton):
    """
    Get: .mol file ligand -> convert to PDBQT by using openbabel
    """
    def __init__(self) -> None:
        self.agent = Vina(sf_name = 'vina')
        self.receptor_path = os.path.join(Config.CHEM_DIR, "receptors", "receptor.pdbqt")
        self.receptor_PDB_clean_H = os.path.join(Config.CHEM_DIR, "receptors", "Mpro_clean_H.pdb")
        self.box_center = [-4.971, 16.522, 68.039]
        self.box_size = [20, 30, 28]
        self.agent.set_receptor(rigid_pdbqt_filename = self.receptor_path)
        self.converter = ob.OBConversion()
        self.gen3D = ob.OBOp.FindType("gen3D")
        self.dss_system = DSSSystem()
    
    def convert_IN_OUT(self, ligand_mol, ligand_file, IN, OUT) -> str:
        self.converter.SetInAndOutFormats(IN, OUT) 
        file_dest = ligand_file.replace("."+IN, "."+OUT)
        self.converter.WriteFile(ligand_mol, file_dest)
        return file_dest

    def docking(self, user_id, compound_name, dtime) -> dict:
        """
            Convert .mol -> .pdbqt to execute docking process
            Executing Docking process.
            Convert from .pdbqt -> .mol 
                --> Write to /dockings/user_id/
        """
        ligand_file = os.path.join(Config.CHEM_DIR, "compounds", str(user_id), compound_name)
        
        # Generate 3D
        self.converter.SetInFormat("mol")
        ligand_mol = ob.OBMol()
        self.converter.ReadFile(ligand_mol, ligand_file)
        self.gen3D.Do(ligand_mol, "--best")

        self.converter.SetInAndOutFormats("mol", "mol") 
        self.converter.WriteFile(ligand_mol, ligand_file)

        # Compute centroid and move to centroid
        ligand_rdkit_mol = MolFromMolFile(ligand_file)
        conf = ligand_rdkit_mol.GetConformer()
        ligand_atom_coord = np.array(conf.GetPositions())
        ligand_centroid = np.mean(ligand_atom_coord, axis=0)
        for i in range(ligand_rdkit_mol.GetNumAtoms()):
            x,y,z = ligand_atom_coord[i] + (np.array(self.box_center) - ligand_centroid)
            conf.SetAtomPosition(i, Point3D(x,y,z))
        MolToMolFile(ligand_rdkit_mol, ligand_file)

        # Convert to PDBQT
        self.converter.ReadFile(ligand_mol, ligand_file)
        file_pdbqt = self.convert_IN_OUT(ligand_mol, ligand_file, "mol", "pdbqt")
        self.agent.set_ligand_from_file(file_pdbqt)
        
        self.agent.compute_vina_maps(center=self.box_center, box_size=self.box_size)
        self.agent.optimize()
        self.agent.dock(exhaustiveness=20, n_poses=1)
        docking_score = self.agent.score()[0] # Total score

        dest_path = os.path.join(Config.CHEM_DIR, "dockings", str(user_id), "DOCKED"+compound_name.replace(".mol", ".pdbqt"))
        dest_path_MOL = dest_path.replace(".pdbqt", ".mol")
        
        self.agent.write_pose(dest_path) 

        # Convert to PDB format
        self.converter.SetInFormat("pdbqt")
        self.converter.ReadFile(ligand_mol, dest_path)
        self.converter.SetOutFormat("mol")
        self.converter.WriteFile(ligand_mol, dest_path_MOL)

        # Save information to DB
        user = Users.query.filter_by(id=user_id).first()
        ligand = Ligands(dtime, dest_path_MOL, docking_score, user.user)
        ligand.save()

        result = {"receptor": self.receptor_path, "ligand": dest_path_MOL, "score": docking_score}
        return result

    def run(self, user_id, compound_name, dtime):
        start_time = time.time()

        try:
            docking_result = self.docking(user_id, compound_name, dtime)
        except:
            return None
        
        try:
            suggestions = self.dss_system.run(docking_result["ligand"])
        except:
            suggestions = []

        end_time = time.time()

        return {
                "receptor": os.path.basename(docking_result["receptor"]),
                "ligand": os.path.basename(docking_result["ligand"]),
                "score": docking_result["score"],
                "suggestions": suggestions,
                "time": "%.3f" % (end_time - start_time)
               }


"""
-> ["compound", "result"]
Docking Process:
    1. Prepare Ligand & Receptor (convert (mol, pdb) to PDBQT)

After Docking:
    Convert to view in 3D by making use of ChemDoodle (mol or pdb)
    Save seperately ligand and receptor 

    /dockings
        /usr_id
            /compound_name
                ligand.mol
                receptor.mol
    Read ligand, receptor.mol -> text(pass to dictionary) -> return to front-end 

    Visualize 3D result by reading from dictionary  

Question:
    How can determined the acceptable size for docking box
"""
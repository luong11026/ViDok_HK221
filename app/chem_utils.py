import os
from app.config import Config
from vina import Vina
from openbabel import openbabel as ob
import json 

receptor_path = os.path.join(Config.CHEM_DIR, "receptors", "receptor.pdbqt")

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
        self.agent.set_receptor(rigid_pdbqt_filename = receptor_path)
        self.converter = ob.OBConversion()
        self.writer = ob.OBConversion()
        self.mol = ob.OBMol()
        self.gen3D = ob.OBOp.FindType("gen3D")
    
    def convert_IN_OUT(self, user_id, compound_name, IN, OUT) -> str:

        filename = os.path.join(Config.CHEM_DIR, "compounds", str(user_id), compound_name)
        self.converter.SetInAndOutFormats(IN, OUT) 
        self.converter.WriteFile(self.mol, filename.replace("."+IN, "."+OUT))
        file_dest = filename.replace("."+IN, "."+OUT)
        return file_dest
    
    def docking(self, user_id, compound_name) -> dict:
        """
            Convert .mol -> .pdbqt to execute docking process
            Executing Docking process.
            Convert from .pdbqt -> .mol 
                --> Write to /dockings/user_id/
        """
        filename = os.path.join(Config.CHEM_DIR, "compounds", str(user_id), compound_name)
        self.converter.SetInFormat("mol")
        self.converter.ReadFile(self.mol, filename)
        self.gen3D.Do(self.mol, "--best")
        
        file_pdbqt = self.convert_IN_OUT(user_id, compound_name, "mol", "pdbqt")
        self.agent.set_ligand_from_file(file_pdbqt)
        self.agent.compute_vina_maps(center=[5, 10, 10], box_size=[100, 100, 100])
        self.agent.optimize()
        self.agent.dock(exhaustiveness=20, n_poses=1)

        dest_path = os.path.join(Config.CHEM_DIR, "dockings", str(user_id), "DOCKED"+compound_name.replace(".mol", ".pdbqt"))
        rec_path = receptor_path
        self.agent.write_pose(dest_path)
    
        path = {"receptor": rec_path, "ligand": dest_path}
        return path

    def run(self, user_id, compound_name) -> dict:
        path = self.docking(user_id, compound_name)
        return {k:os.path.basename(v) for k, v in path.items()}


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
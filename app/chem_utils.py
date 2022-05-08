from app.config import Config
from app.models import Users, Ligands
from app.dss_system import DSSSystem

import os
import time
from vina import Vina
from openbabel import openbabel as ob
from pymol import cmd

def save_compound(user_id, file_name, compound):
    with open(
                os.path.join(Config.CHEM_DIR, "compounds", str(user_id), file_name), \
                "w", encoding="utf-8"
             ) as f:
        f.write(compound)

def getbox(selection='sele', extending = 6.0, software='vina'):
    
    ([minX, minY, minZ],[maxX, maxY, maxZ]) = cmd.get_extent(selection)

    minX = minX - float(extending)
    minY = minY - float(extending)
    minZ = minZ - float(extending)
    maxX = maxX + float(extending)
    maxY = maxY + float(extending)
    maxZ = maxZ + float(extending)
    
    SizeX = maxX - minX
    SizeY = maxY - minY
    SizeZ = maxZ - minZ
    CenterX =  (maxX + minX)/2
    CenterY =  (maxY + minY)/2
    CenterZ =  (maxZ + minZ)/2
    
    cmd.delete('all')
    
    if software == 'vina':
        return {'center': (CenterX, CenterY, CenterZ), 'size': (SizeX, SizeY, SizeZ)}
    elif software == 'ledock':
        return {'minX':minX, 'maxX': maxX},{'minY':minY, 'maxY':maxY}, {'minZ':minZ,'maxZ':maxZ}
    elif software == 'both':
        return {'center': (CenterX, CenterY, CenterZ), 'size': (SizeX, SizeY, SizeZ)}, ({'minX':minX, 'maxX': maxX},{'minY':minY, 'maxY':maxY}, {'minZ':minZ,'maxZ':maxZ})
    
    else:
        print('software options must be "vina", "ledock" or "both"')

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

        self.agent.set_receptor(rigid_pdbqt_filename = self.receptor_path)
        self.converter = ob.OBConversion()
        self.writer = ob.OBConversion()
        self.mol = ob.OBMol()
        self.gen3D = ob.OBOp.FindType("gen3D")
        self.dss_system = DSSSystem()
    
    def convert_IN_OUT(self, user_id, compound_name, IN, OUT) -> str:

        filename = os.path.join(Config.CHEM_DIR, "compounds", str(user_id), compound_name)
        self.converter.SetInAndOutFormats(IN, OUT) 
        self.converter.WriteFile(self.mol, filename.replace("."+IN, "."+OUT))
        file_dest = filename.replace("."+IN, "."+OUT)
        return file_dest
    
    def calculateBox(self, ligand_file):
        cmd.load(filename=self.receptor_PDB_clean_H, format='pdb', object='prot')
        cmd.load(filename=ligand_file, format='mol', object='lig')

        docking_box = getbox(selection='lig', extending=5.0, software='vina')

        cmd.delete('all')

        return docking_box["center"], docking_box["size"]

    def docking(self, user_id, compound_name, dtime) -> dict:
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
        box_center, box_size = self.calculateBox(filename)
        self.agent.compute_vina_maps(center=box_center, box_size=box_size)
        self.agent.optimize()
        self.agent.dock(exhaustiveness=20, n_poses=1)
        docking_score = self.agent.score()[0] # Total score

        dest_path = os.path.join(Config.CHEM_DIR, "dockings", str(user_id), "DOCKED"+compound_name.replace(".mol", ".pdbqt"))
        dest_path_MOL = dest_path.replace(".pdbqt", ".mol")
        
        self.agent.write_pose(dest_path) 

        # Convert to PDB format
        self.converter.SetInFormat("pdbqt")
        self.converter.ReadFile(self.mol, dest_path)
        self.converter.SetOutFormat("mol")
        self.converter.WriteFile(self.mol, dest_path_MOL)

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
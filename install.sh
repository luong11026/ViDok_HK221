#Create new conda env
conda create -n vidok_test python=3.8
conda activate vidok_test 

#Install pymol-open-source 
conda install -c conda-forge pymol-open-source

#Install collada2gltf
conda install -c schrodinger collada2gltf

#Run test scripts
python test.py
#!/bin/bash
cd ../jupyter_contrib_nbextensions/                 
pip install -e jupyter_contrib_nbextensions         
pip install jupyter_nbextensions_configurator       
jupyter nbextensions_configurator enable --user     
jupyter contrib nbextension install --sys-prefix    
pip install autopep8                                


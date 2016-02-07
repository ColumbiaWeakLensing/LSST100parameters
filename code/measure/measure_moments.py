#!/usr/bin/env python-mpi
import argparse,logging

import library.driver_mpi as driver
from library.featureDB import LSSTSimulationBatch
from lenstools.statistics.ensemble import Ensemble
from lenstools.pipeline.settings import EnvironmentSettings

import numpy as np
import pandas as pd

#Measure the cross spectrum of a list of convergence maps
def moments(maps,indices):

	"""

	:param maps: list of convergence maps (one for each redshift bin)
	:type maps: list.

	:returns: Ensemble

	"""

	#Allocate memory
	moments_array = np.zeros((len(indices),9))
		
	#Measure the auto and cross power spectrum
	for n,i in enumerate(indices):
		moments_array[n] = maps[i].moments(connected=True)

	#Build the Ensemble
	columns = [ "sigma0","sigma1","S0","S1","S2","K0","K1","K2","K3" ]
	ensemble = Ensemble(moments_array,columns=columns)

	#Add the indices labels
	ensemble["b1"] = indices

	#Return
	return ensemble


###############################################################################################

if __name__=="__main__":

	#parse command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-e","--environment",dest="environment",help="Environment options file")
	parser.add_argument("-c","--config",dest="config",help="Configuration file")
	parser.add_argument("-n","--noise",dest="noise",action="store_true",default=False,help="Add shape noise")
	parser.add_argument("-d","--database",dest="database",default="moments",help="Database name to populate")
	parser.add_argument("id",nargs="*")
	cmd_args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)

	#Handle on the current batch
	batch = LSSTSimulationBatch(EnvironmentSettings.read(cmd_args.environment))

	#Redshift bin indices
	indices = range(5) 

	#Database name
	database_name = cmd_args.database
	if cmd_args.noise:
		database_name += "_noise"
	database_name += ".sqlite"

	#Execute
	for model_id in cmd_args.id:
		
		cosmo_id,n = model_id.split("|")
		
		if cosmo_id==batch.fiducial_cosmo_id:
			driver.measure(batch,cosmo_id,["Shear","ShearEmuIC"],int(n),cmd_args.noise,database_name,["features_fiducial","features_fiducial_EmuIC"],measurer=moments,pool=None,indices=indices)
		else:
			driver.measure(batch,cosmo_id,"Shear",int(n),cmd_args.noise,database_name,"features",measurer=moments,pool=None,indices=indices)

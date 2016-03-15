#!/usr/bin/env python-mpi
import argparse,logging

import library.driver_mpi as driver
from library.featureDB import LSSTSimulationBatch
from lenstools.statistics.ensemble import Ensemble
from lenstools.pipeline.settings import EnvironmentSettings

import numpy as np
import pandas as pd

#Measure the cross spectrum of a list of convergence maps
def cross_power(maps,ell_edges,indices):

	"""

	:param maps: list of convergence maps (one for each redshift bin)
	:type maps: list.
		
	:param ell_edges: multipoles
	:type ell_edges: array

	:param indices: pairs of indices; each pair corresponds to a pair of redshift bins to cross correlate
	:type indices: list of tuples

	:returns: Ensemble

	"""

	#Allocate memory
	cross_power_array = np.zeros((len(indices),len(ell_edges)-1))
		
	#Measure the auto and cross power spectrum
	for n,(i,j) in enumerate(indices):
		ell,cross_power_array[n] = maps[i].cross(maps[j],statistic="power_spectrum",l_edges=ell_edges)

	#Build the Ensemble
	columns = [ "l{0}".format(n) for n in range(1,len(ell)+1) ]
	ensemble = Ensemble(cross_power_array,columns=columns)

	#Add the indices labels
	ensemble["b1"],ensemble["b2"] = zip(*indices)

	#Return
	return ensemble


###############################################################################################

if __name__=="__main__":

	#parse command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-e","--environment",dest="environment",help="Environment options file")
	parser.add_argument("-c","--config",dest="config",help="Configuration file")

	parser.add_argument("-n","--noise",dest="noise",action="store_true",default=False,help="Add shape noise")
	parser.add_argument("-pb","--photoz_bias",dest="photoz_bias",action="store",default=None,help="Read photoz biases from this file")
	parser.add_argument("-ps","--photoz_sigma",dest="photoz_sigma",action="store",default=None,help="Read photoz sigmas from this file")
	
	parser.add_argument("-d","--database",dest="database",default="cross_spectra",help="Database name to populate")
	parser.add_argument("id",nargs="*")
	cmd_args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)

	#Handle on the current batch
	batch = LSSTSimulationBatch(EnvironmentSettings.read(cmd_args.environment))

	#Redshift bin index pairs and multipoles
	indices = zip(*np.triu_indices(5))
	ell_edges = pd.read_pickle("/global/homes/a/apetri/LSST100Parameters/data/edges.pkl")["ell_edges"].values

	#Database name
	database_name = cmd_args.database
	
	if cmd_args.noise:
		database_name += "_noise"

	if (cmd_args.photoz_bias is not None) or (cmd_args.photoz_sigma is not None):
		database_name += "_photoz" 
	
	database_name += ".sqlite"

	#Execute
	for model_id in cmd_args.id:
		
		cosmo_id,n = model_id.split("|")
		
		if cosmo_id==batch.fiducial_cosmo_id:
			driver.measure(batch,cosmo_id,["Shear","ShearEmuIC"],int(n),cmd_args.noise,cmd_args.photoz_bias,cmd_args.photoz_sigma,database_name,["features_fiducial","features_fiducial_EmuIC"],measurer=cross_power,pool=None,ell_edges=ell_edges,indices=indices)
		else:
			driver.measure(batch,cosmo_id,"Shear",int(n),cmd_args.noise,cmd_args.photoz_bias,cmd_args.photoz_sigma,database_name,"features",measurer=cross_power,pool=None,ell_edges=ell_edges,indices=indices)
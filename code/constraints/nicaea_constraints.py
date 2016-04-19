#!/usr/bin/env python
from __future__ import division
import sys
sys.modules["mpi4py"] = None

import itertools
import numpy as np
import astropy.units as u
import pandas as pd

from lenstools.statistics.ensemble import Ensemble
from lenstools.statistics.constraints import FisherAnalysis
from lenstools.simulations.nicaea import Nicaea

################################
#######Tunable options##########
################################

options = {

#Multipoles
"multipoles" : np.linspace(150.,2000.,15) ,

#Redshift distribution parameters
"zbins" : [(0.0052829915857917076, 0.46370802037163456), 
(0.46370802037163456, 0.68921284184762954),
(0.68921284184762954, 0.93608623056054063),
(0.93608623056054063, 1.2872107430836479),
(1.2872107430836479, 2.9998163872653354)] ,

"alpha_p" : 2,
"beta_p" : 1,
"z0" : 0.3,

#Cosmological parameters
"fiducial" : {"Om0" : 0.26, "w0" : -1. , "sigma8" : 0.8},
"derivative_percentage" : 0.01 ,
"parameters_rename" : {"Om0" : "Om" , "w0" : "w" , "sigma8" : "sigma8"} ,

#Shape noise
"add_shape_noise" : True,
"ngal" : 22.*(u.arcmin**-2),

#Sky fraction
"fsky" : 0.47

}


##################################################################################################################################

#Build FisherAnalysis instance from predicted power spectrum with NICAEA
def predict_power(options):

	#From options
	multipoles = options["multipoles"]
	zbins = options["zbins"]
	alpha_p = options["alpha_p"]
	beta_p = options["beta_p"]
	z0 = options["z0"]
	fiducial = options["fiducial"]
	derivative_percentage = options["derivative_percentage"]

	#Pack the zbins and distribution parameters into lists 
	distribution = ["ludo"]*len(zbins)
	distribution_parameters = [ [zmin,zmax,alpha_p,beta_p,z0] for (zmin,zmax) in zbins]

	#Variations of cosmological parameters
	cosmo_parameters = dict((k,[fiducial[k]]*(len(fiducial)+1)) for k in fiducial)
	for n,k in enumerate(fiducial):
		cosmo_parameters[k][n+1] = fiducial[k] + np.abs(fiducial[k])*derivative_percentage

	#Parse into Ensemble
	cosmo_parameters = Ensemble.from_dict(cosmo_parameters)

	#Use NICAEA to compute the predictions
	predicted_power = np.zeros((len(fiducial)+1,len(multipoles)*len(zbins)*(len(zbins)+1)//2))
	for n in range(len(cosmo_parameters)):
		cosmo = Nicaea(**cosmo_parameters.iloc[n])
		predicted_power[n] = cosmo.convergencePowerSpectrum(multipoles,z=None,distribution=distribution,distribution_parameters=distribution_parameters).flatten()

	#Parse the predicted power into an Ensemble with properly named columns
	multipole_indices = [ "l{0}".format(n) for n in range(len(multipoles)) ]
	redshift_indices = zip(*np.triu_indices(len(zbins),k=0))
	column_names = [ "{0}-z{1}-z{2}".format(l,z1,z2) for l,(z1,z2) in itertools.product(multipole_indices,redshift_indices) ]
	predicted_power = Ensemble(predicted_power,columns=column_names)

	#Add the shape noise: assumption, each bin has the same number of galaxies. Median redshift is representative. Only diagonal terms in (zi,zj) are present
	if options["add_shape_noise"]:
		ngal = options["ngal"].to(u.rad**-2).value

		for n,zb in enumerate(zbins):
			columns_to_modify = ["{0}-z{1}-z{1}".format(l,n) for l in multipole_indices]
			predicted_power[columns_to_modify] += ((0.15+0.035*0.5*(zb[0]+zb[1]))**2) / ngal

	#Connect the parameters and predicted power spectrum
	cosmo_parameters.add_name("parameters")
	predicted_power.add_name("power_kk")
	fisher = FisherAnalysis.from_features(predicted_power,cosmo_parameters)

	#Return
	return fisher


#Calculate the single redshift constraints
def singleZ_constraints(fisher,options):

	#Multipole spacing
	dl_bin = options["multipoles"][1] - options["multipoles"][0]

	#Rows
	rows = list()

	#Cycle over redshift bins
	for nz,zb in enumerate(options["zbins"]):

		#Select the appropriate columns from the FisherAnalysis instance
		fisher_singleZ = fisher.features({ "power_kk" : [ "l{0}-z{1}-z{1}".format(nl,nz) for nl in range(len(options["multipoles"])) ] })

		#Estimate the covariance matrix and errorbars
		singleZ_covariance = (fisher_singleZ["power_kk"].iloc[fisher._fiducial]**2) / (options["fsky"]*dl_bin*(0.5+options["multipoles"]))
		parameter_covariance = fisher_singleZ.parameter_covariance(singleZ_covariance)

		#Rename the columns for convenience
		new_column_names = [ options["parameters_rename"][k] for k in parameter_covariance.columns ]

		#Put the whole parameter covariance in a database
		row = pd.Series(parameter_covariance.values.flatten(),index=["{0}-{1}".format(p1,p2) for (p1,p2) in itertools.product(*(new_column_names,)*2)])
		row["bins"] = fisher_singleZ["power_kk"].shape[1]
		row["feature_label"] = "power_spectrum_z{0}".format(nz+1)
		rows.append(row)

	#Return formed dataframe
	return Ensemble.from_records(rows)
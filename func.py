# func of mod_ccn
# version :
# 20200330 main_v0   : setting target and build structure
# 20200330 main_v0.2 : add file name identify, nan data with discontinue data, data collect from chosen start time
# 20200331 main_v0.3 : replace time when same time at diff. row
# 20200331 main_v0.4 : alarm code sensor
# 20200401 main_v0.5 : calib_SS : add table on figure
# 20200402 main_v0.6 : calibration : add figure path
# 20200404 main_v0.7 : read smps data completely, add function of checkout time
# 20200405 main_v0.8 : smps2date fig fix out, correct_time_data : recieve kwarg, use object array, save datetime object instead of datetime string
# 20200405 main_v0.9 : correct_time_data : continue data test rewrite (check out next time with tolerence)
# 20200408 main_v1.0 : cpc_raw : use time correct, correct_time_data : deal with blank line adta and unfortunate header, mdfy_data_mesr, plot_smps2date, plot_cpc2date : build completely
# 20200415 main_v1.1 : data from start to final time, use os.path.join to build path, cpc_raw : start time + 1s to fit its true start time, start building calculate kappa function 
# 20200415 main_v1.2 : correct_time_data : from processing cpc_raw to processing correct_time_data, skip start time test, add nan data to current time, change to the time which has first data

# target : make a CCNc exclusive func with python 3.6
# 0. read file with discontinue data : CCNc, SMPS, CPC, DMS
# 	method : use time stamp -> test by calibraion data
# 1. calibration and measurement data process:
# 	(1) calibration : deal with time due to the data may be unstable in first 4 min by CCNc,
#		then DMA changes diameter every 2 min, however, first and last 30s
#		may either be unstable
# 	(2) measurement : different deltatime of different SS table
# 2. calibration : S curve, calibration line
# 3. measurement : Eulia's result

import os
from os.path import join as pth
import numpy as n
from scipy.stats import linregress
import matplotlib.pyplot as pl
from datetime import datetime as dtm
from datetime import timedelta as dtmdt

# file reader
class reader:
	def __init__(self,start,final,td1DtPrces=True,**kwarg):
		## set data path parameter
		default = {'path_ccn'  : 'ccn/',
				   'path_dma'  : 'dma/',
				   'path_cpc'  : 'cpc/',
				   'path_smps' : 'smps/'}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
		default.update(kwarg)

		## set class parameter
		self.start = start ## datetime object
		self.final = final ## datetime object
		self.kil_date   = lambda time: dtm.strptime(dtm.strftime(time,'%X'),'%X')
		self.td1DtPrces = td1DtPrces
		self.path_ccn   = default['path_ccn']
		self.path_dma   = default['path_dma']
		self.path_cpc   = default['path_cpc']
		self.path_smps  = default['path_smps']

	## data of corrected time
	## start test
	## wrong current time test
	## discountinue data test
	## output data
	def correct_time_data(self,_begin_,_fout_,_line,tm_start,td1_start=False,**_par):
		## raw data
		nan_dt	 = _par['nanDt']
		_data_	 = _par['dtSplt'](_line)

		try:
			## deal with blank line data and unfortunate header
			## skip it
			cur_tm = _data_[_par['tmIndx']]
			chkDtmOb = dtm.strptime(cur_tm,'%X') ## if cur_tm is not datetime object, it will error
		except:
			return tm_start, _begin_

		err_tm, del_tm = _par['errTm'], _par['delTm']
		cort_tm_now = lambda time: dtm.strftime(time,'%X')
		cort_tm_low = lambda time: dtm.strftime(time-err_tm,'%X')
		cort_tm_upr = lambda time: dtm.strftime(time+err_tm,'%X')

		## (start time different = 1) test
		if (td1_start&_begin_): 
			_begin_ = False					## skip the start test
			_fout_.append(nan_dt(tm_start)) ## add nan to current time data
			tm_start += del_tm				## change to the time which has first data

		## start test
		if _begin_:
			_begin_ = True if cur_tm != cort_tm_now(tm_start) else False
			if _begin_: return tm_start, _begin_

		## wrong current time test
		## check out data time series by current time +/- error time
		if ((cur_tm == cort_tm_low(tm_start))|(cur_tm == cort_tm_upr(tm_start))):
			cur_tm = dtm.strftime(tm_start,'%X')

		## discountinue data test
		while ((cur_tm != cort_tm_low(tm_start))&(cur_tm != cort_tm_upr(tm_start))&(cur_tm != cort_tm_now(tm_start))):
			_fout_.append(nan_dt(tm_start)) ## add nan data to discontinue time
			tm_start += del_tm

		## data colllect
		_data_[_par['tmIndx']] = tm_start

		_fout_.append(_data_)
		tm_start += del_tm
		if tm_start<=self.final: return tm_start, _begin_
		else: return None, _begin_
		

	## SMPS
	## change time every 5 min
	## keys index : 'Date' : 1 (%D)
	## 				'Start Time' : 2 (%X)
	## 				'diameter' : 4~110
	def smps_raw(self):
		path, fout, switch, begin = self.path_smps, [], True, True
		tmStart = self.start

		for file in os.listdir(path):
			if '.txt' not in file: continue
			with open(pth(path,file),errors='replace') as f:
				## get header and skip instrument information
				if switch==True:
					[ f.readline() for i in range(15) ]
					header = f.readline()[:-1].split('\t')
					switch = False
				else: [ f.readline() for i in range(16) ]

				## collect data from start time, and make nan array for discontinue data
				## [2] is current time index
				par = { 'nanDt'  : lambda _tmStart: n.array([n.nan]*2+[_tmStart]+[n.nan]*len(header[3::])),
						'dtSplt' : lambda _li: n.array(_li[:-1].split('\t'),dtype=object),
						'delTm'  : dtmdt(minutes=5.),
						'errTm'  : dtmdt(seconds=1.),
						'hdrLn'	 : len(header),
						'tmIndx' : 2 }

				for line in f:
					## time check out and collect data
					if tmStart: tmStart, begin = self.correct_time_data(begin,fout,line,tmStart,**par)
					else: break
			if not tmStart: break

		return dict(zip(header,n.array(fout).T))

	## CCNc
	## name : CCN 100 data %y%m%d%M0000.csv
	## change time every second
	## keys index : '    Time' : 0 (%X)
	## 				' CCN Number Conc' : 45
	def ccn_raw(self):
		path, fout, switch, begin = self.path_ccn, [], True, True
		tmStart = self.start

		for file in os.listdir(path):
			if '.csv' not in file: continue
			with open(pth(path,file),errors='replace') as f:
				## get header and skip instrument information
				if switch:
					[ f.readline() for i in range(4) ]
					header = f.readline()[:-1].split(',')[:-1]
					f.readline()
					switch = False
				else: [ f.readline() for i in range(6) ]

				## collect data from start time, and make nan array for discontinue data
				## [0] is current time

				par = { 'nanDt'  : lambda _tmStart: n.array([_tmStart]+['nan']*len(header[1::])),
						'dtSplt' : lambda _li: n.array(_li[:-1].split(','),dtype=object),
						'delTm'  : dtmdt(seconds=1.),
						'errTm'  : dtmdt(seconds=1.),
						'hdrLn'	 : len(header),
						'tmIndx' : 0 }

				for line in f:
					## check out time and collect data
					tmStart, begin = self.correct_time_data(begin,fout,line,tmStart,**par)

		## alarm code
		raw_dt = dict(zip(header,n.array(fout).T))
		alarm_dt = raw_dt[' Alarm Code']!='    0.00'
		raw_dt[' CCN Number Conc'][alarm_dt] = 'nan'
		return raw_dt

	## DMA
	## name : %Y%m%d.txt
	## change time every second
	## keys index : 'Date' : 0 (%Y/%m/%d)
	## 				'Time' : 1 (%X)
	## 				'Diameter' : 3
	def dma_raw(self):
		path, fout = self.path_dma, []
		header = ['Date','Time','Diameter','SPD']
		for file in os.listdir(path):
			if '.txt' not in file: continue
			with open(pth(path,file),errors='replace') as f:
				[ fout.append(n.array(line[:-1].split('\t'))) for line in f ]

		return dict(zip(header,n.array(fout).T))

	## CPC
	## name : %y%m%d_cpc.csv
	## change time every second
	## keys index : 'Time' : 0 (%X)
	## 				'Concentration (#/cm?)' : 1
	def cpc_raw(self):
		path, fout, switch, begin = self.path_cpc, [], True, True
		tmStart = self.start

		for file in os.listdir(path):
			if '.csv' not in file: continue
			with open(pth(path,file),errors='replace') as f:
				if switch:
					[ f.readline() for i in range(17) ]
					header = f.readline()[:-1].split(',')[:-1]
					switch = False
				else: [ f.readline() for i in range(18) ]

				## collect data from start time, and make nan array for discontinue data
				## [0] is current time
				par = { 'nanDt'  : lambda _tmStart: n.array([_tmStart]+['nan']*len(header[1::])),
						'dtSplt' : lambda _li: n.array(_li[:-1].split(',')[:-1],dtype=object),
						'delTm'  : dtmdt(seconds=1.),
						'errTm'  : dtmdt(seconds=1.),
						'hdrLn'	 : len(header),
						'tmIndx' : 0 }

				for line in f:
					## check out time and collect data
					if tmStart: tmStart, begin = self.correct_time_data(begin,fout,line,tmStart,td1_start=self.td1DtPrces,**par)
					else: break
			if not tmStart: break

		return dict(zip(header,n.array(fout).T))

	## data for CCNc calibration
	## use data of CCNc, DMA, CPC, and modified by time
	def mdfy_data_calib(self):
		ccn, dma, cpc = self.ccn_raw(), self.dma_raw(), self.cpc_raw()
		time_ccn, SS_ccn = ccn['    Time'], ccn[' Current SS']
		conc_ccn = ccn[' CCN Number Conc'].astype(float)
		conc_cpc = cpc['Concentration (#/cm�)'].astype(float)
		d_dma = dma['Diameter']
		mdfy_data_calib = {}

		final_index = n.where(time_ccn==self.final)[0][0]

		## for calibration, SS change every 30 mins, and diameter change every 2 mins,
		## however, CCNc is unstable on first 4 mins, then DMA is unstable 30 seconds
		## after the start and 30 seconds before the end
		## | ---- || -- || -- |.....| -- |	for ch : | - || -- || - |
		## < uns  >< ch >< ch >.....< ch >	  	   	 <uns>< st ><uns>
		## <            30 min           > 	   	   	 <    2 min     >
		## stable(st), unstable(uns), diameter change(ch)
		## 30min = 1800s, 4min 30s = 270s, 4min 90s = 330s, 2min = 120s
		## (30-4)/2 = 13 different diameter

		for i in range(0,len(time_ccn),1800):
			if i>final_index: break

			conc_ccn_ave, conc_cpc_ave, diameter = [], [], []
			for num in range(13):
				diameter.append(round(float(d_dma[i+270+120*num])))
				conc_ccn_ave.append(n.nanmean(conc_ccn[i+270+120*num:i+330+120*num]))
				conc_cpc_ave.append(n.nanmean(conc_cpc[i+270+120*num:i+330+120*num]))

			mdfy_data_calib.setdefault(SS_ccn[i],[n.array(diameter),n.array(conc_ccn_ave),n.array(conc_cpc_ave)])
		return mdfy_data_calib

	def mdfy_data_mesr(self,smps_data=True,cpc_data=True):
		## smps data
		if smps_data:
			smps = self.smps_raw()
			smpsKey = list(smps.keys())
			smpsBin = n.array([ smps[key] for key in smpsKey[4:111] ],dtype=float)
			smpsTm  = smps[smpsKey[2]]
			smpsData = {'time' 	   : smpsTm,
						'bin_data' : smpsBin,
						'bins'	   : n.array(smpsKey[4:111],dtype=float)}
		else: smpsData = None

		## cpc data
		# raise ValueError(' CPC error value')
		if cpc_data:
			cpc = self.cpc_raw()
			cpcData = {'time' : cpc['Time'],
					   'conc' : cpc['Concentration (#/cm�)'].astype(float)}
		else: cpcData = None

		mdfy_data_mesr = {'smps' : smpsData, 'cpc' : cpcData}

		## calculate kappa
		## find out Da
		'''
		smps = read.smps_raw()
		key  = n.array(list(smps.keys())[4:111],dtype=float)
		ary, stp = n.linspace(n.log10(key[0]),n.log10(key[-1]),len(key)-1,retstep=True)
		nd = n.array([ n.array([ smps[ky][i] for ky in list(smps.keys())[4:111] ],dtype=float) for i in range(500) ])

		from scipy.integrate import simps as sim
		def int_f(_nd):
			da_val = 0.
			value  = sim(_nd,key,stp)*303.78/349.2
			if n.isnan(_nd).sum()<50:
				for num in range(len(key),2,-1):
					int_part = sim(_nd[num-2:num],key[num-2:num],stp)
					da_val += int_part
					if da_val>value: 
						return key[num-2] if (da_val-value)/int_part<=.5 else key[num-1] 
			return n.nan
		da = n.array([int_f(i) for i in nd])
		'''

		return mdfy_data_mesr

class calibration:
	def __init__(self,data,date,**kwarg):
		## set calculating parameter
		default = {'kappa'	  : .61,
				   'inst_T'   : 299.15, ## lab temperature [K]
				   'rho_w_T'  : 997.,
				   'fig_path' : './',
				   'sig_wa'	  : .072}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
			default.update(kwarg)

		## set class parameter
		self.data = data
		self.size = len(data)
		self.fs	  = 12
		self.date = date.strftime('%Y/%m/%d')
		self.kappa = default['kappa']
		self.coe_A = 4.*default['sig_wa']/(461.*default['inst_T']*default['rho_w_T'])*1e9 ## diameter [nm]
		self.figPath = default['fig_path']

	## activation of CCN may be like a S curve, there is a very sharp activation changing which variety
	## by diameter
	def calib_data(self,SS,get_dc=True,kohler_calib=False):
		d_ = self.data[SS][0] ## diameter
		activation = (self.data[SS][1]/self.data[SS][2])*100. ## CCN/CPC
		if get_dc:
			## data for S curve and regression line of activation changing
			line_bottom = n.where((activation-activation.min())<10.)[0][-1]
			line_top = n.where((100.-activation)<10.)[0][0]
			line_coe = linregress(d_[line_bottom:line_top+1],activation[line_bottom:line_top+1])
			line_x = n.array([0.,250.])
			line_y = line_coe[0]*line_x+line_coe[1]
			dc = (50.-line_coe[1])/line_coe[0]

			if kohler_calib==False:
				return {'dia' : d_,
						'acti' : activation,
						'line_data' : [line_x,line_y],
						'dc' : dc}
			else:
				## data for calibration SS, which calibrating by kappa Kohler equation
				SS_calib = lambda dc_ : n.exp((4.*self.coe_A**3./(27.*self.kappa*dc_**3.))**.5)*100.-100.
				return n.array([float(SS),SS_calib(dc)])
		else:
			## data for S curve
			return {'dia' : d_, 'acti' : activation}

	## plot S curve to find out criticle diameter
	def S_curve(self,plot_dc=False,**kwarg):
		## set plotting parameter
		default = {'color'	  	: '#b8dbff',
				   'line_color' : '#ff5f60',
				   'mfc'	  	: '#7fdfff',
				   'mec'	  	: '#297db7',
				   'order' 		: [ i-1 for i in range(self.size) ], ## order of axes
				   'fig_name' 	: r'calib_Scurve.png'}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
			default.update(kwarg)

		## parameter
		fs = self.fs
		if self.size==1: fig_row = 1
		else: fig_row = 2
		fig_col = round(self.size/2)

		## plot
		fig, ax = pl.subplots(fig_row,fig_col,figsize=(8,6),dpi=200,sharex=True,sharey=True)
		ax = ax.reshape(fig_col*fig_row)

		for i, SS in zip(default['order'],self.data.keys()):
			calib_dt = self.calib_data(SS,get_dc=plot_dc) ## if plot dc, should get dc first
			ax[i].plot(calib_dt['dia'],calib_dt['acti'],c=default['color'],
					   marker='o',mfc=default['mfc'],mec=default['mec'],label='S curve')
			if plot_dc:
				## plot regression line
				dc = calib_dt['dc']
				ax[i].plot(calib_dt['line_data'][0],calib_dt['line_data'][1],
						   c=default['line_color'],label='regression',ls='--')
				ax[i].plot(dc,50.,c=default['line_color'],ms=5.,marker='o')
				ax[i].text(dc+15.,45.,'$d_c$ = {:.2f} nm'.format(dc),fontsize=fs-2)

			ax[i].tick_params(direction='in')
			ax[i].spines['top'].set_visible(False)
			ax[i].spines['right'].set_visible(False)
			ax[i].set(xlim=(-30.,299.),ylim=(0.,119.))

			ax[i].set_title('SS = {:4.2f} %'.format(float(SS)),fontsize=fs-2)

		ax[1].legend(framealpha=0.,fontsize=fs-3.,loc=4)
		fig.text(.38,.03,'Dry Particle Diameter (nm)',fontsize=fs)
		fig.text(.04,.4,'Activation (%)',rotation=90.,fontsize=fs)
		## for odd axes
		if ((self.size%2==1)&(self.size!=1)): ax[-1].remove()

		fig.suptitle('Activation of CCN (Date : {:})'.format(self.date),fontsize=fs+3,style='italic')
		fig.savefig(pth(self.figPath,default['fig_name']))
		pl.close()

	## use kappa kohler eq. and modified data to calculate the SS, then plotting regression line
	## with CCNc's SS
	def calib_SS(self,**kwarg):
		## set plotting parameter
		default = {'mec'	    : '#00b386',
				   'mfc'		: '#ffffff',
				   'ms'			: 6.,
				   'mew'		: 1.8,
				   'fig_name'   : r'calib_CalibTable.png'}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
			default.update(kwarg)

		## parameter
		fs, SS_ = self.fs, []
		height = .15

		## plot
		fig, ax = pl.subplots(figsize=(8,6),dpi=200)
		box = ax.get_position()
		ax.set_position([box.x0,box.y0+.03,box.width,box.height*.95])

		for SS in self.data.keys():
			SS_.append(self.calib_data(SS,kohler_calib=True))
		SS_ = n.array(SS_).T
		SS_.sort()

		## plot 6 calibration data, to align with table, x data use index data
		ax.plot(n.arange(.1,.7,.1),SS_[1],mec=default['mec'],mew=default['mew'],mfc=default['mfc'],ms=default['ms'],marker='o',ls='')
		table = ax.table(cellText=[list(n.round(SS_[1],3))],rowLabels=['Calib SS'],colLabels=list(SS_[0]),
						 cellLoc='center',rowLoc='center',colLoc='center',
						 bbox=[0.,-height,1.,height])
		table.auto_set_font_size(False)
		table.set_fontsize(self.fs)

		ax.tick_params(which='both',direction='in',labelsize=fs,right=True,top=True,labelbottom=False)
		ax.set(xlim=(.05,.65),ylim=(.05,.95))

		# ax.set_xlabel('CCNc SS (%)',fontsize=fs)
		ax.set_ylabel('Calibration SS (%)',fontsize=fs)
		ax.set_title('CCNc SS (%)',fontsize=fs)

		fig.suptitle('Calibration Table of Supersaturation (Date : {:})'.format(self.date),
					 fontsize=fs+3,style='italic')
		fig.savefig(pth(self.figPath,default['fig_name']))
		pl.close()

class measurement:
	def __init__(self,data,start,final,**kwarg):
		## set calculating parameter
		default = {'fig_Path' : './'}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
			default.update(kwarg)

		## func
		def timeIndex(_time):
			return n.where(_time==start)[0][0], n.where(_time==final)[0][0]

		## set class parameter
		self.timeIndex = timeIndex
		self.smpsData  = data['smps']
		self.cpcData   = data['cpc']
		self.fs = 13.
		self.start = start
		self.final = final
		self.figPath = default['fig_Path']

	## plot smps with date and set log scale data
	def plot_smps2date(self,**kwarg):
		import matplotlib.colors as colr
		## set plot parameter
		default = {'splt_hr'  : 6,
				   'fig_name' : r'mesr_smps2date.png'}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
			default.update(kwarg)

		## set plot variable
		if self.smpsData is not None: smps = self.smpsData 
		else: raise ValueError('SMPS data is None !!!')
		time = smps['time']
		start_indx, final_indx = self.timeIndex(time)

		time = time[start_indx:final_indx+1]
		data = smps['bin_data'][:,start_indx:final_indx+1]
		data[data==0] = 1e-5
		data[n.isnan(data)] = 0.
		fs = self.fs

		## plot
		fig, ax = pl.subplots(figsize=(10.,6.),dpi=150.)

		pm = ax.pcolormesh(n.arange(len(time)),smps['bins'],data,cmap='jet',norm=colr.LogNorm(vmin=10**.5,vmax=10**5.3))
		cb = fig.colorbar(pm,ax=ax,pad=0.1,shrink=.93,fraction=0.05,aspect=25)

		box = ax.get_position()
		ax.set_position([box.x0,box.y0+0.02,box.width,box.height])

		ax.tick_params(which='major',length=6.,labelsize=fs-2.)
		ax.tick_params(which='minor',length=3.5)
		cb.ax.tick_params(which='major',length=5.,labelsize=fs-2.)
		cb.ax.tick_params(which='minor',length=2.5)
		ax.set(yscale='log')

		ax.set_xlabel(f"Time({self.start.strftime('%Y')})",fontsize=fs)
		ax.set_ylabel('Electric modify diameter (nm)',fontsize=fs)
		ax.set_xticks(n.arange(0,len(time),int(default['splt_hr']*12)))
		ax.set_xticklabels([ time[indx].strftime('%m/%d%n%X') for indx in ax.get_xticks() ])
		cb.ax.set_title('number conc.\n(#/$cm^3$/$\Delta log D_p$)',fontsize=fs-2.)

		fig.suptitle(f"SMPS data from ({self.start.strftime('%Y/%m/%d %X')}) to ({self.final.strftime('%Y/%m/%d %X')})",fontsize=fs+2.,style='italic')
		fig.savefig(pth(self.figPath,default['fig_name']))
		pl.close()

	## plot cpc with date
	def plot_cpc2date(self,**kwarg):
		## set plot parameter
		default = {'splt_hr'  : 12,
				   'fig_name' : r'mesr_cpc2date.png'}
		for key in kwarg:
			if key not in default.keys(): raise TypeError("got an unexpected keyword argument '"+key+"'")
			default.update(kwarg)

		## set plot variable
		if self.cpcData is not None: cpc = self.cpcData 
		else: raise ValueError('CPC data is None !!!')
		time = cpc['time']
		start_indx, final_indx = self.timeIndex(time)

		time = time[start_indx:final_indx+1]
		data = cpc['conc'][start_indx:final_indx+1]/1e3
		fs = self.fs
		ylim = (0.,max(data)+10.) if max(data)<30. else (0.,30.)
		tm_num = len(time)

		## plot
		fig, ax = pl.subplots(figsize=(10.,6.),dpi=150.)
		
		ax.plot(n.arange(tm_num),data,c='#7396ff',lw=1.5)

		ax.tick_params(which='major',direction='in',length=7,labelsize=fs-2.5)
		ax.tick_params(which='minor',direction='in',length=4.5)
		ax.set(ylim=ylim,xlim=(0.,tm_num))

		ax.set_xlabel(f"Time({self.start.strftime('%Y')})",fontsize=fs)
		ax.set_ylabel(r'Condense Nuclei Number Conc. (#$\times 10^3 /cm^3$)',fontsize=fs)
		ax.set_xticks(n.arange(0,tm_num,int(default['splt_hr']*3600)))
		ax.set_xticklabels([ time[indx].strftime('%m/%d%n%X') for indx in ax.get_xticks() ])

		fig.suptitle(f"CPC data from ({self.start.strftime('%Y/%m/%d %X')}) to ({self.final.strftime('%Y/%m/%d %X')})",fontsize=fs+2.,style='italic')
		fig.savefig(pth(self.figPath,default['fig_name']))
		pl.close()
#hydro_plot - some python functions for hydrological visualisation
#(cc) jackisch@kit.edu
import numpy as np
import pandas as pd
import scipy as sp
import matplotlib.pyplot as plt
import matplotlib

#TOOLS
# a simple progress bar
import sys, time
try:
    from IPython.display import clear_output
    have_ipython = True
except ImportError:
    have_ipython = False

class ProgressBar:
    def __init__(self, iterations):
        self.iterations = iterations
        self.prog_bar = '[]'
        self.fill_char = '*'
        self.width = 40
        self.__update_amount(0)
        if have_ipython:
            self.animate = self.animate_ipython
        else:
            self.animate = self.animate_noipython

    def animate_ipython(self, iter):
        print '\r', self,
        sys.stdout.flush()
        self.update_iteration(iter + 1)

    def update_iteration(self, elapsed_iter):
        self.__update_amount((elapsed_iter / float(self.iterations)) * 100.0)
        self.prog_bar += '  %d of %s complete' % (elapsed_iter, self.iterations)

    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = '[' + self.fill_char * num_hashes + ' ' * (all_full - num_hashes) + ']'
        pct_place = (len(self.prog_bar) // 2) - len(str(percent_done))
        pct_string = '%d%%' % percent_done
        self.prog_bar = self.prog_bar[0:pct_place] + \
            (pct_string + self.prog_bar[pct_place + len(pct_string):])

    def __str__(self):
        return str(self.prog_bar)

#euler richards solver
def darcy(psi,z,k):
    phi=psi+z
    dz=np.diff(z)
    Q=np.sqrt(k[:-1]*k[1:])*np.diff(phi)/dz
    return Q

def euler(psi_l,c_l,q,qb_u,qb_l,dt,z):
    dz=np.diff(z)
    #psinew=psi_l[:-1]+dt/(c_l[:-1]*dz*dz)*np.append(qb_u,np.diff(q))
    psinew=psi_l[:-1]+dt/(c_l[:-1]*dz*dz)*np.diff(np.append((qb_u+q[0])/2.,q))
    psilow=psi_l[-1]+dt/(c_l[-1]*dz[-1])*qb_l
    return np.append(psinew,psilow)

def richards(t_end,psi,mc,vG):
    time=0.
    soil=mc.soilgrid[:,1]-1
    dzmn=mc.mgrid.latfac.values
    while time<t_end:
        k=vG.ku_psi(psi, mc.soilmatrix.ks[soil], mc.soilmatrix.alpha[soil], mc.soilmatrix.n[soil]).values
        c=vG.c_psi(psi, mc.soilmatrix.ts[soil], mc.soilmatrix.tr[soil], mc.soilmatrix.alpha[soil], mc.soilmatrix.n[soil]).values
        q=darcy(psi,mc.zgrid[:,1],k)
        dt=np.amin([0.1,0.05*dzmn/np.amax(np.abs(q))])
        #predictor
        psinew=euler(psi,c,q,0.,0.,dt*0.5,mc.zgrid[:,1])

        k=vG.ku_psi(psinew, mc.soilmatrix.ks[soil], mc.soilmatrix.alpha[soil], mc.soilmatrix.n[soil]).values
        c=vG.c_psi(psinew, mc.soilmatrix.ts[soil], mc.soilmatrix.tr[soil], mc.soilmatrix.alpha[soil], mc.soilmatrix.n[soil]).values
        q=darcy(psinew,mc.zgrid[:,1],k)
    
        #corrector
        psinew=euler(psinew,c,q,0.,0.,dt,mc.zgrid[:,1])
        psi=psinew
        time=time+dt
    
    return psi


#PLOTTING
#define plot function for soil moisture data
def hydroplot(obs,mlab,mlabcols,fsize=(6, 6),saving=False,upbound=40,lowbound=10,catch='Catchment',precscale=100.,cumprec=False,align=False,tspacehr=6,ccontrast=False,descriptor='Sensor\nLocation'):
    '''
    This is a rather simple function to plot hydrological data (soil moisture and precipitation) of a pandas data frame.
    It is based on some excellent examples by Randy Olson and may need heavy adaption to your data.
    (CC BY-NC-SA 4.0) jackisch@kit.edu
    
    fsize: Provide figure size as tuple.
    saving: Provide a file name if you want it saving.
    XXbound: Give bounds of left axis.
    catch: Provide catchment name.
    precscale: Scaling if your prec data is not in mm.
    cumprec: True: cumulative precipitation is plotted.
    
    The functions assumes a pandas data frame with a time stamp as row names.
    You may prepare this as:
    obs=pd.read_csv('soil_moisture_file.csv')
    obs.index=pd.to_datetime(obs['DATE'] + ' ' + obs['TIME'],format='%d/%m/%y %H:%M')
    obs = obs.drop(['DATE','TIME'], 1)
    Moreover, precipitation should reside in column 'Prec'
    '''
    
    # These are the "Tableau 20" colors as RGB.  
    tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),  
             (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),  
             (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),  
             (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),  
             (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]  
    # Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.  
    for i in range(len(tableau20)):  
        r, g, b = tableau20[i]  
        tableau20[i] = (r / 255., g / 255., b / 255.)  
        
    
    plt.figure(figsize=fsize)  
      
    # Remove the plot frame lines. They are unnecessary chartjunk.  
    ax = plt.subplot(111)  
    ax.spines["top"].set_visible(False)  
    ax.spines["bottom"].set_visible(False)  
    ax.spines["right"].set_visible(False)  
    ax.spines["left"].set_visible(False)  
      
    # Ensure that the axis ticks only show up on the bottom and left of the plot.  
    # Ticks on the right and top of the plot are generally unnecessary chartjunk.  
    ax.get_xaxis().tick_bottom()  
    ax.get_yaxis().tick_left()  
      
    # Limit the range of the plot to only where the data is.  
    # Avoid unnecessary whitespace.  
    plt.ylim(lowbound, upbound)  
    
          
    # Make sure your axis ticks are large enough to be easily read.  
    # You don't want your viewers squinting to read your plot.  
    plt.yticks(range(lowbound, upbound, 10), [str(x) + "%" for x in range(lowbound, upbound, 10)], fontsize=14)  
    plt.xticks(fontsize=14)  
    
    ax.xaxis.set_minor_locator(matplotlib.dates.HourLocator(interval=tspacehr))
    ax.xaxis.set_minor_formatter(matplotlib.dates.DateFormatter('\n%H'))
    ax.xaxis.grid(False, which="minor")
    ax.xaxis.grid(True, which="major")
    ax.xaxis.set_major_locator(matplotlib.dates.DayLocator())
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('\n\n%d.%m.%y'))
    
    # Now that the plot is prepared, it's time to actually plot the data!  
    # Note that I plotted the majors in order of the highest % in the final year.  
    majors = mlab  
    colnames=mlabcols
    
    #get positions
    yposlab=obs[colnames].values[-1,:]
    yposlab=np.round(yposlab)
    if align:
        while any(np.diff(yposlab)==0.):
            overlap=np.diff(yposlab)
            overlapavoid=0.*overlap
            overlapavoid[overlap==0.]=1.
            overlap[np.where(overlap==0.)[0]+1][overlap[np.where(overlap==0.)[0]+1]==1.]=overlapavoid[np.where(    overlap==0.)[0]+1]+1.
            yposlab[1:]=yposlab[1:]+overlapavoid
    else:
        if any(np.diff(yposlab)<2.):
            yposlab=upbound-(np.arange(len(yposlab))*2.+15.)
    
    for rank, column in enumerate(majors):  
        # Plot each line separately with its own color, using the Tableau 20  
        # color set in order.
        if ccontrast:
            plt.plot(obs.index, obs[colnames[rank]].values, lw=2.5, color=tableau20[rank*2+2])  
        else:
            plt.plot(obs.index, obs[colnames[rank]].values, lw=2.5, color=tableau20[rank+2])  
    
        # Add a text label to the right end of every line. Most of the code below  
        # is adding specific offsets y position because some labels overlapped.  
        if ccontrast:
            plt.text(obs.index[-1]+ pd.datetools.timedelta(hours=0.1), yposlab[rank], column, fontsize=14, color=tableau20[rank*2+2])
        else:
            plt.text(obs.index[-1]+ pd.datetools.timedelta(hours=0.1), yposlab[rank], column, fontsize=14, color=tableau20[rank+2])
        
    for y in range(10, upbound, 10):  
        plt.axhline(y, lw=0.5, color="black", alpha=0.3)
    
    plt.text(obs.index[len(obs)/2], upbound+2, ''.join(["Soil Moisture and Precipitation at ",catch]) , fontsize=17, ha="center") 
    plt.text(obs.index[0]- pd.datetools.timedelta(hours=0.1),32,'< Soil Moisture\n',rotation='vertical',horizontalalignment='right',verticalalignment='bottom',fontsize=12,alpha=0.7)
    plt.text(obs.index[0]- pd.datetools.timedelta(hours=0.1),32,'> Precipitation',rotation='vertical',horizontalalignment='right',verticalalignment='bottom',fontsize=12,color=tableau20[0],alpha=0.7)
    plt.text(obs.index[-1]+ pd.datetools.timedelta(hours=0.1),10,descriptor,rotation='vertical',verticalalignment='bottom',fontsize=12,alpha=0.7)
    plt.text(obs.index[-1]+ pd.datetools.timedelta(hours=0.1),7.55,'Hr',verticalalignment='bottom',fontsize=12,    alpha=0.7)
    plt.text(obs.index[-1]+ pd.datetools.timedelta(hours=0.1),5.6,'Date',verticalalignment='bottom',fontsize=14,    alpha=0.7)
        
    ax2 = ax.twinx()
    if cumprec:
        obs['Preccum']=np.cumsum(obs['Prec'].values)
        obs=obs.rename(columns={'Prec': 'Prec_m','Preccum': 'Prec'})

    precstp=np.around(obs['Prec'].max()/4.,decimals=-int(np.floor(np.log10(obs['Prec'].max()/4.))))
    ax2.set_ylim((-obs['Prec'].max()*3.,1))
    ax2.set_yticks(-np.arange(0,obs['Prec'].max(), precstp)[::-1])
    ax2.set_yticklabels([str(x) + "mm" for x in np.arange(0.,obs['Prec'].max(), precstp)/precscale][::-1],    fontsize=14,color=tableau20[0])
    ax2.plot(obs.index, -obs['Prec'], color=tableau20[0])
    ax2.fill_between(obs.index, -obs['Prec'], 0., color=tableau20[1])
    ax2.yaxis.grid(True)
    
    if saving!=False:
        plt.savefig(saving, bbox_inches="tight")

def hydroprofile(obs,obs2=None,fsize=(6, 6),xbound=[0.,1.],ybound=[0.,1.],ptitle='Plot',xlab='feature',saving=False,ccontrast=False,colors=None,compress=True,compress2=False,ebar=False):
    '''
    This is a rather simple function to plot hydrological data (profile) of a pandas data frame.
    It is based on some excellent examples by Randy Olson and may need heavy adaption to your data.
    (CC BY-NC-SA 4.0) jackisch@kit.edu
    
    obs: dataframe to plot, index is y axis
    mlab: labels for columns
    mlabcols: columns to plot
    fsize: Provide figure size as tuple.
    saving: Provide a file name if you want it saving.
    XXbound: Give bounds of axis and separations.
    ptitle: Plot title
    ccontrast: option to only use high contrast values from palette
    colors: option to pass own colors
    compress: compress obs to mean with errorbar
    compress2: compress also simulations to mean with errorbar
    '''
    
    # These are the "Tableau 20" colors as RGB.  
    tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),  
             (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),  
             (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),  
             (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),  
             (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]  
    # Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.  
    for i in range(len(tableau20)):  
        r, g, b = tableau20[i]  
        tableau20[i] = (r / 255., g / 255., b / 255.)  
    if colors is None:
        colors=tableau20
    
    plt.figure(figsize=fsize)  
      
    # Remove the plot frame lines. They are unnecessary chartjunk.  
    ax = plt.subplot(111)  
    ax.spines["top"].set_visible(True)  
    ax.spines["bottom"].set_visible(False)  
    ax.spines["right"].set_visible(False)  
    ax.spines["left"].set_visible(True)  
      
    # Ensure that the axis ticks only show up on the bottom and left of the plot.  
    # Ticks on the right and top of the plot are generally unnecessary chartjunk.  
    ax.get_xaxis().tick_bottom()  
    ax.get_yaxis().tick_left()  
      
    # Limit the range of the plot to only where the data is.  
    # Avoid unnecessary whitespace.  
    plt.xlim(xbound[0], xbound[1])  
    plt.ylim(ybound[0], ybound[1])  
          
    # Make sure your axis ticks are large enough to be easily read.  
    # You don't want your viewers squinting to read your plot.  
    plt.yticks(np.linspace(ybound[0], ybound[1], ybound[2]), [str(x) for x in np.linspace(ybound[0], ybound[1], ybound[2])], fontsize=14)  
    plt.xticks(np.linspace(xbound[0], xbound[1], xbound[2]), [str(x) for x in np.linspace(xbound[0], xbound[1], xbound[2])],fontsize=14)  
    plt.ylabel('depth [m]')
    plt.xlabel(xlab)
    ax.xaxis.grid(True)
    ax.yaxis.grid(True)
    
    # Now that the plot is prepared, it's time to actually plot the data!  
    # Note that I plotted the majors in order of the highest % in the final year.  
    if compress:
        plt.plot(obs.mean(axis=1).values,obs.index, lw=2., color=colors[0], label='observed')  
        if ebar==True:
            plt.errorbar(obs.mean(axis=1).values,obs.index,xerr=obs.std(axis=1).values, lw=1., color=colors[0])  
        else:
            plt.fill_betweenx(np.array(obs.index,dtype=float),(obs.mean(axis=1)-obs.std(axis=1)).values,(obs.mean(axis=1)+obs.std(axis=1)).values, color=colors[0],alpha=0.3)
        offset=2
        if (obs2 is not None):
            if compress2:
                plt.plot(obs2.mean(axis=1).values,obs2.index, lw=2., color=colors[2], label='simulated')  
                plt.errorbar(obs2.mean(axis=1).values,obs2.index,xerr=obs2.std(axis=1).values, lw=1., color=colors[2])  
            else:
                for rank in range(len(obs2.columns)): 
                    plt.plot(obs2.iloc[:,rank].values,obs2.index, lw=2., color=colors[rank+offset], label=str(obs2.columns[rank]))  
        
    else:
        for rank in range(len(obs.columns)):  
            # Plot each line separately with its own color, using the Tableau 20  
            # color set in order.
            if ccontrast:
                plt.plot(obs.iloc[:,rank].values,obs.index, lw=2., color=colors[rank*2], label=str(obs.columns[rank]))  
            else:
                plt.plot(obs.iloc[:,rank].values,obs.index, lw=2., color=colors[rank], label=str(obs.columns[rank]))  
        offset=len(obs.columns)
        if obs2 is not None:
            for rank in range(len(obs2.columns)):  
            # Plot each line separately with its own color, using the Tableau 20  
            # color set in order.
                if ccontrast:
                    plt.plot(obs2.iloc[:,rank].values,obs2.index, lw=2., color=colors[rank*2+offset], label=str(obs2.columns[rank]))  
                else:
                    plt.plot(obs2.iloc[:,rank].values,obs2.index, lw=2., color=colors[rank+offset], label=str(obs2.columns[rank]))  
    
    plt.title(ptitle,fontsize=16)
    plt.legend(loc=4,frameon=False,ncol=int(np.ceil(len(obs2.columns)/8.)))
    
    if saving!=False:
        plt.savefig(saving, bbox_inches="tight")


def oneDplot(particles,obsx,theta_r,theta_re,gridupdate_thS1D,pdyn,vG,dt,sigma,runname,ti,i,mc,saving=False,t=1,store=False,fsize=(8, 5),xlimset=[0.15,0.3,2],ad_diff=False):
    #plot 1D profile
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    thS=gridupdate_thS1D(particles.cell,mc,pdyn)
    theta_p=vG.theta_thst(thS/100., mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
    thpx=gaussian_filter1d(theta_p,sigma)
    if ad_diff:
        thSdiff=gridupdate_thS1D(particles.cell[particles.flag==0],mc,pdyn)
        theta_pdiff=vG.theta_thst(thSdiff/100., mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
        thpxdiff=gaussian_filter1d(theta_pdiff,sigma)
    n=len(particles)
    obs_id=np.argmin([np.abs(obsx.index[x]-ti) for x in range(len(obsx))])
    probloc=[-0.03,-0.1,-0.2,-0.3,-0.4]
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(1, 2, width_ratios=[2,1])
    plt.subplot(gs[0])
    plt.plot(thpx,mc.zgrid[:,1],label='Particle')
    if ad_diff:
        plt.plot(thpxdiff,mc.zgrid[:,1],label='Particle_diffusive')
    plt.plot(theta_r,mc.zgrid[:,1],label='Rich SimpegFlow')
    plt.plot(theta_re,mc.zgrid[:,1],label='Rich Euler')
    plt.plot(obsx.iloc[obs_id]/100.,probloc,'.',label='Observation')
    plt.legend(loc=4)
    #text(0.35, -0.4, ''.join(['t=',str(int(t)),'m']), fontsize=12)
    #text(0.3, -0.5, ''.join(['particles: ',str(n)]), fontsize=12)
    plt.xlim(xlimset[:2])
    plt.xticks(np.arange(xlimset[0],xlimset[1],xlimset[2]))
    plt.xlabel('theta [m3/m3]')
    plt.ylabel('depth [m]')
    #title(''.join(['Model and Obs @ ',str(int(ti)),'s']))
    plt.title(''.join(['Model and Observation\nTime: ',str(int(t)),'min']))
    #title(''.join(['echoRD1D @ ',str(int(ti)),'s']))
    ax1=plt.subplot(gs[1])
    zi=np.arange(-0.0,mc.soildepth-0.01,-0.01)
    oldp=np.bincount(np.round(np.append(-particles.z[particles.flag==0].values,-zi)*100.).astype(int))-1
    allp=np.bincount(np.round(np.append(-particles.z[particles.flag<2].values,-zi)*100.).astype(int))-1
    plt.plot(gaussian_filter1d(oldp,sigma),zi,label='old')
    plt.plot(gaussian_filter1d(allp[0:len(oldp)],sigma),zi,label='all')
    plt.plot(gaussian_filter1d(allp[0:len(oldp)]-oldp,sigma),zi,label='new')
    a=np.ceil(n/1000.)*12.
    plt.xlim([0,a])
    plt.xticks(np.linspace(0,a,4))
    plt.xlabel('particles')
    plt.legend(loc=4)
    #title(''.join(['Max Peclet=',str(np.round(Pe,2))]))
    plt.title(''.join(['total:\n',str(n)]))
    ax1.yaxis.tick_right()
    
    if saving:
        plt.savefig(''.join(['./results/',runname,str(i).zfill(3),'.pdf']))
        plt.close(fig)
    if store:
        idz=[0,10,20,30,40]
        if ad_diff:
            return [obsx.values[obs_id]/100., thpx[idz],theta_re.values[idz],theta_r[idz],thpxdiff[idz]]
        else:
            return [obsx.values[obs_id]/100., thpx[idz],theta_re.values[idz],theta_r[idz]]

def oneDplot2(particles,obsx,theta_r,theta_re,dt,sigma,runname,ti,i,mc,saving=False,t=1,store=False,fsize=(8, 5),xlimset=[0.15,0.3,2],ad_diff=False):
    #plot 1D profile
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    [thS,npart]=gridupdate_thS1D(particles.cell,mc,pdyn)
    theta_p=vG.theta_thst(thS/100., mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
    thpx=gaussian_filter1d(theta_p,sigma)
    if ad_diff:
        [thSdiff,npartdiff]=gridupdate_thS1D(particles.cell[particles.flag==0],mc,pdyn)
        theta_pdiff=vG.theta_thst(thSdiff/100., mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
        thpxdiff=gaussian_filter1d(theta_pdiff,sigma)
    n=len(particles)
    obs_id=np.argmin([np.abs(obsx.index[x]-ti) for x in range(len(obsx))])
    probloc=[-0.03,-0.1,-0.2,-0.3,-0.4]
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(1, 4, width_ratios=[2,1,0.6,0.6])
    subplot(gs[0])
    plot(thpx,mc.zgrid[:,1],label='Particle')
    if ad_diff:
        plot(thpxdiff,mc.zgrid[:,1],label='Particle_diffusive')
    plot(theta_r,mc.zgrid[:,1],label='Rich SimpegFlow')
    plot(theta_re,mc.zgrid[:,1],label='Rich Euler')
    plot(obsx.iloc[obs_id]/100.,probloc,'.',label='Observation')
    legend(loc=4)
    #text(0.35, -0.4, ''.join(['t=',str(int(t)),'m']), fontsize=12)
    #text(0.3, -0.5, ''.join(['particles: ',str(n)]), fontsize=12)
    xlim(xlimset[:2])
    xticks(np.arange(xlimset[0],xlimset[1],xlimset[2]))
    xlabel('theta [m3/m3]')
    ylabel('depth [m]')
    #title(''.join(['Model and Obs @ ',str(int(ti)),'s']))
    title(''.join(['Model and Observation\nTime: ',str(int(t)),'min']))
    #title(''.join(['echoRD1D @ ',str(int(ti)),'s']))
    ax1=subplot(gs[1])
    zi=np.arange(-0.0,mc.soildepth-0.01,-0.01)
    oldp=np.bincount(np.round(np.append(-particles.z[particles.flag==0].values,-zi)*100.).astype(int))-1
    allp=np.bincount(np.round(np.append(-particles.z[particles.flag<2].values,-zi)*100.).astype(int))-1
    plot(gaussian_filter1d(oldp,sigma),zi,label='old')
    plot(gaussian_filter1d(allp[0:len(oldp)],sigma),zi,label='all')
    plot(gaussian_filter1d(allp[0:len(oldp)]-oldp,sigma),zi,label='new')
    a=np.ceil(n/1000.)*12.
    xlim([0,a])
    xticks(np.linspace(0,a,4))
    xlabel('particles')
    legend(loc=4)
    #title(''.join(['Max Peclet=',str(np.round(Pe,2))]))
    title(''.join(['total:\n',str(n)]))
    ax1.get_yaxis().set_visible(False)    
    
    ax2=subplot(gs[2])
    #a=(np.abs(particles.groupby(['cell'], sort=True).max().lastZ.values-particles.groupby(['cell'], sort=True).min().z.values)/dt)/np.sqrt(mc.D[np.amax(thS),4])
    #e=particles.groupby(['cell'], sort=True).mean().lastD.values*mc.mgrid.vertfac.values/mc.D[np.amax(thS),4]
    a=(np.abs(mc.mgrid.vertfac.values)*np.abs(particles.groupby(['cell'], sort=True).mean().lastZ.values-particles.groupby(['cell'], sort=True).mean().z.values)/dt)/mc.D[np.amax(thS),4]
    e=(np.abs(mc.mgrid.vertfac.values)*np.abs(particles.groupby(['cell'], sort=True).max().lastZ.values-particles.groupby(['cell'], sort=True).min().z.values)/dt)/mc.D[np.amax(thS),4]
    plot(a,mc.zgrid[:,1],label='diff')
    #plot(e,mc.zgrid[:,1],alpha=0.5, color='b')
    #fill_betweenx(mc.zgrid[:,1], a, e,alpha=0.2)
    #plot(u,mc.zgrid[:,1],color='adv')
    #errorbar(a,mc.zgrid[:,1],xerr=a-e, ecolor='lightblue')
    xlim([-0.05,np.ceil(np.amax([np.amax(a),0.05])*100.)/100.])
    xticks(np.linspace(0.,np.ceil(np.amax([np.amax(a),0.05])*100.)/100.,2))
    ax2.get_yaxis().set_visible(False)
    #xscale('log')
    plt.xlabel('u(i,z)/D(z)')
    plt.title('Peclet\n(mean)')
    
    ax3=plt.subplot(gs[3])
    plot(e,mc.zgrid[:,1])
    xlim([-0.05,np.ceil(np.amax([np.amax(e),0.05])*100.)/100.])
    xticks(np.linspace(0.,np.ceil(np.amax([np.amax(e),0.05])*100.)/100.,2))
    #xscale('log')
    xlabel('u(i,z)/D(z)')
    title('Peclet\n(max)')
    ax3.yaxis.tick_right()
    
    if saving:
        plt.savefig(''.join(['./results/',runname,str(i).zfill(3),'.pdf']))
        plt.close(fig)
    if store:
        idz=[0,10,20,30,40]
        if ad_diff:
            return [obsx.values[obs_id]/100., thpx[idz],theta_re.values[idz],theta_r[idz],thpxdiff[idz]]
        else:
            return [obsx.values[obs_id]/100., thpx[idz],theta_re.values[idz],theta_r[idz]]

def plotparticles_t_obs(particles,obsx,thS,mc,vG,runname='test',t=0.,ix=0,sigma=0.5,fsize=(8, 8),saving=False,store=False):
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(2, 3, width_ratios=[2,1,1], height_ratios=[1,5])
    ax1 = plt.subplot(gs[0])
    ax11 = ax1.twinx()
    advect_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age>0.)),'lat'].values).astype(np.int))
    old_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age<=0.)),'lat'].values).astype(np.int))
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:],'b-')
    ax11.plot((np.arange(0,len(old_dummy))/100.)[1:],old_dummy[1:],'g-')
    ax11.set_ylabel('Particles', color='g')
    ax11.set_xlim([0.,mc.mgrid.width.values])
    ax1.set_xlim([0.,mc.mgrid.width.values])
    ax1.set_ylabel('New Particles', color='b')
    ax1.set_xlabel('Lat [m]')
    ax1.set_title('Lateral Marginal Count')
    
    ax2 = plt.subplot(gs[1:2])
    ax2.axis('off')
    ax2.text(0.1, 0.5, 'time:      '+str(np.round(t/60.,1))+'min', fontsize=17)
    ax2.text(0.1, 0.2, 'particles: '+str(sum(particles.z>mc.soildepth)), fontsize=17)
    ax2.text(0.1, 0.8, runname, fontsize=17)    

    ax3 = plt.subplot(gs[3])
    plt.imshow(sp.ndimage.filters.median_filter(thS,size=mc.smooth),vmin=0., vmax=1., cmap='Blues')
    #plt.imshow(npart)
    plt.colorbar()
    plt.xlabel('Width [cells a 5 mm]')
    plt.ylabel('Depth [cells a 5 mm]')
    plt.title('Particle Density')
    plt.tight_layout()

    ax4 = plt.subplot(gs[4])
    #ax41 = ax4.twiny()
    onez=np.append(mc.zgrid[:,1]+0.001,mc.soildepth)
    z1=np.append(particles.loc[((particles.age>0.)),'z'].values,onez)
    advect_dummy=np.bincount(np.round(-100.0*z1).astype(np.int))-1
    z2=np.append(particles.loc[((particles.age<=0.)),'z'].values,onez)
    old_dummy=np.bincount(np.round(-100.0*z2).astype(np.int))-1
    ax4.plot(advect_dummy,(np.arange(0,len(advect_dummy))/-100.),'r-',label='new particles')
    ax4.plot(advect_dummy+old_dummy,(np.arange(0,len(old_dummy))/-100.),'b-',label='all particles')
    ax4.plot(old_dummy,(np.arange(0,len(old_dummy))/-100.),'g-',label='old particles')
    ax4.set_xlabel('Particle Count')
    #ax4.set_xlabel('New Particle Count', color='r')
    ax4.set_ylabel('Depth [m]')
    #ax4.set_title('Number of Particles')
    ax4.set_ylim([mc.mgrid.depth.values,0.])
    ax4.set_xlim([0.,np.max(old_dummy+advect_dummy)])
    #ax41.set_xlim([0.,np.max(old_dummy[1:])])
    #ax41.set_ylim([mc.mgrid.depth.values,0.])
    handles1, labels1 = ax4.get_legend_handles_labels() 
    #handles2, labels2 = ax41.get_legend_handles_labels() 
    ax4.legend(handles1, labels1, loc=4)
    ax4.set_title('Vertical Marginal Count')
    #    ax41.legend(loc=4)
    
    ax5 = plt.subplot(gs[5])
    theta_p=vG.theta_thst(thS.mean(axis=1), mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
    thpx=gaussian_filter1d(theta_p,sigma)
    theta_mn=vG.theta_thst(thS.min(axis=1), mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
    thpmn=gaussian_filter1d(theta_mn,sigma)
    theta_mx=vG.theta_thst(thS.max(axis=1), mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
    thpmx=gaussian_filter1d(theta_mx,sigma)
    obs_id=np.argmin([np.abs(obsx.index[x]-t) for x in range(len(obsx))])
    probloc=[-0.03,-0.1,-0.2,-0.3,-0.4]
    ax5.plot(thpx,mc.zgrid[:,1],label='Particle')
    ax5.plot(thpmx,mc.zgrid[:,1],'b--',label='Particle_min/max')
    ax5.plot(thpmn,mc.zgrid[:,1],'b--')
    ax5.plot(obsx.iloc[obs_id]/100.,probloc,'.',label='Observation')
    ax5.set_xlim([mc.soilmatrix.tr.min(),mc.soilmatrix.ts.max()])
    ax5.set_ylabel('Depth [m]')
    ax5.set_xlabel('Theta')
    handles2, labels2 = ax5.get_legend_handles_labels() 
    ax5.legend(handles2, labels2,loc=4)
    ax5.set_title('Soil Moisture Log')    
    if saving:
        plt.savefig(''.join(['./results/',runname,'t_',str(ix).zfill(3),'.png']))
        plt.close(fig)
    if store:
        idz=[3,10,20,30,40]
        return [np.concatenate([obsx.iloc[obs_id].values/100.,thpx[idz]]),advect_dummy]

def plotparticles_t(particles,thS,mc,vG,runname='test',t=0.,ix=0,sigma=0.5,fsize=(8, 8),saving=False,store=False):
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(2, 3, width_ratios=[2,1,1], height_ratios=[1,5])
    ax1 = plt.subplot(gs[0])
    ax11 = ax1.twinx()
    advect_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age>0.)),'lat'].values).astype(np.int))
    old_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age<=0.)),'lat'].values).astype(np.int))
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:],'b-')
    ax11.plot((np.arange(0,len(old_dummy))/100.)[1:],old_dummy[1:],'g-')
    ax11.set_ylabel('Particles', color='g')
    ax11.set_xlim([0.,mc.mgrid.width.values])
    ax1.set_xlim([0.,mc.mgrid.width.values])
    ax1.set_ylabel('New Particles', color='b')
    ax1.set_xlabel('Lat [m]')
    ax1.set_title('Lateral Marginal Count')
    
    ax2 = plt.subplot(gs[1:2])
    ax2.axis('off')
    ax2.text(0.1, 0.5, 'time:      '+str(np.round(t/60.,1))+'min', fontsize=17)
    ax2.text(0.1, 0.2, 'particles: '+str(sum(particles.z>mc.soildepth)), fontsize=17)
    ax2.text(0.1, 0.8, runname, fontsize=17)    

    ax3 = plt.subplot(gs[3])
    plt.imshow(sp.ndimage.filters.median_filter(thS,size=mc.smooth),vmin=0., vmax=1., cmap='Blues')
    #plt.imshow(npart)
    plt.colorbar()
    plt.xlabel('Width [cells a 5 mm]')
    plt.ylabel('Depth [cells a 5 mm]')
    plt.title('Particle Density')
    plt.tight_layout()

    ax4 = plt.subplot(gs[4])
    #ax41 = ax4.twiny()
    onez=np.append(np.arange(0.,mc.soildepth,-0.01)+0.001,mc.soildepth) #one particle per cm soil
    #onez=np.append(mc.zgrid[:,1]+0.001,mc.soildepth)
    z1=np.append(particles.loc[((particles.age>0.)),'z'].values,onez)
    advect_dummy=np.bincount(np.round(-100.0*z1).astype(np.int))-1
    z2=np.append(particles.loc[((particles.age<=0.)),'z'].values,onez)
    old_dummy=np.bincount(np.round(-100.0*z2).astype(np.int))-1
    ax4.plot(advect_dummy,(np.arange(0,len(advect_dummy))/-100.),'r-',label='new particles')
    ax4.plot(advect_dummy+old_dummy,(np.arange(0,len(old_dummy))/-100.),'b-',label='all particles')
    ax4.plot(old_dummy,(np.arange(0,len(old_dummy))/-100.),'g-',label='old particles')
    ax4.set_xlabel('Particle Count')
    #ax4.set_xlabel('New Particle Count', color='r')
    ax4.set_ylabel('Depth [m]')
    #ax4.set_title('Number of Particles')
    ax4.set_ylim([mc.mgrid.depth.values,0.])
    ax4.set_xlim([0.,np.max(old_dummy+advect_dummy)])
    #ax41.set_xlim([0.,np.max(old_dummy[1:])])
    #ax41.set_ylim([mc.mgrid.depth.values,0.])
    handles1, labels1 = ax4.get_legend_handles_labels() 
    #handles2, labels2 = ax41.get_legend_handles_labels() 
    ax4.legend(handles1, labels1, loc=4)
    ax4.set_title('Vertical Marginal Count')
    #    ax41.legend(loc=4)
    
    ax5 = plt.subplot(gs[5])
    theta_p=vG.theta_thst(thS.mean(axis=1), mc.soilmatrix.ts[mc.soilgrid[:,1]-1], mc.soilmatrix.tr[mc.soilgrid[:,1]-1])
    thpx=gaussian_filter1d(theta_p,sigma)
    ax5.plot(thpx,mc.zgrid[:,1],label='Particle')
    ax5.set_xlim([mc.soilmatrix.tr.min(),mc.soilmatrix.ts.max()])
    ax5.set_ylabel('Depth [m]')
    ax5.set_xlabel('Theta')
    handles2, labels2 = ax5.get_legend_handles_labels() 
    ax5.legend(handles2, labels2,loc=4)
    ax5.set_title('Soil Moisture Log')    
    if saving:
        plt.savefig(''.join(['./results/',runname,'t_',str(ix).zfill(3),'.png']))
        plt.close(fig)
    if store:
        idz=[3,10,20,30,40]
        return [thpx[idz],advect_dummy]

def plotparticles_specht(particles,mc,pdyn,vG,runname='test',t=0.,ix=0,sigma=0.5,fsize=(3.6, 9),saving=False,relative=True):
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    
    [thS,npart]=pdyn.gridupdate_thS(particles.lat,particles.z,mc)
    #[thSn,npartn]=pdyn.gridupdate_thS(particles.loc[((particles.age>0.)),'lat'],particles.loc[((particles.age>0.)),'z'].values,mc)
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(2, 2, width_ratios=[4,1.1], height_ratios=[1,9],hspace=0.02, wspace=0.02)
    
    #marginal X
    ax1 = fig.add_subplot(gs[0,0])
    old_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age<=0.)),'lat'].values).astype(np.int))
    all_dummy=np.copy(old_dummy)
    advect_dummy=old_dummy*0
    advect_dummy2=np.bincount(np.round(100.0*particles.loc[((particles.age>0.)),'lat'].values).astype(np.int))
    advect_dummy[advect_dummy2>0]+=advect_dummy2[advect_dummy2>0]
    all_dummy+=advect_dummy
    if relative:
        old_dummy/=np.sum(old_dummy)
        advect_dummy/=np.sum(advect_dummy)
        all_dummy/=np.sum(all_dummy)
    
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:],'r-',label='new particles')
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:],'b-',label='all particles')
    ax1.plot((np.arange(0,len(old_dummy))/100.)[1:],old_dummy[1:],'g-',label='old particles')
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:], 0., color='b',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],old_dummy[1:], 0., color='g',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:], 0., color='r',alpha=0.3)
    ax1.set_xlim((0,0.34))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["top"].set_visible(False)  
    ax1.spines["right"].set_visible(False)
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["left"].set_visible(False)
   
    #marginal Y
    ax1 = fig.add_subplot(gs[1,1])
    onez=np.append(mc.zgrid[:,1]+0.001,mc.soildepth)
    z1=np.append(particles.loc[((particles.age>0.)),'z'].values,onez)
    advect_dummy=np.bincount(np.round(-100.0*z1).astype(np.int))-1
    all_dummy=np.copy(advect_dummy)
    z2=np.append(particles.loc[((particles.age<=0.)),'z'].values,onez)
    old_dummy=np.bincount(np.round(-100.0*z2).astype(np.int))-1
    all_dummy+=old_dummy
    if relative:
        advect_dummy/=np.sum(advect_dummy)
        old_dummy/=np.sum(old_dummy)
        all_dummy/=np.sum(all_dummy)
    ax1.plot(advect_dummy,(np.arange(0,len(advect_dummy))/-100.),'r-',label='new particles')
    ax1.plot(advect_dummy+old_dummy,(np.arange(0,len(old_dummy))/-100.),'b-',label='all particles')
    ax1.plot(old_dummy,(np.arange(0,len(old_dummy))/-100.),'g-',label='old particles')
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,all_dummy, color='b',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,old_dummy, color='g',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,advect_dummy, color='r',alpha=0.3)
    handles1, labels1 = ax1.get_legend_handles_labels() 
    ax1.set_ylim((-1.,0.))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["right"].set_visible(False)  
    ax1.spines["top"].set_visible(False)  
    ax1.spines["left"].set_visible(False)

    
    #legend
    ax1 = fig.add_subplot(gs[0,1])
    ax1.text(0.05, 0.1, 'run:\n'+runname[-6:-2]+'\n\n'+'time:\n'+str(np.round(t/60.,1))+'min')
    #ax1.legend(handles1, labels1, loc=3)
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False) 
    
    #main
    ax1 = fig.add_subplot(gs[1,0])
    plt.imshow(sp.ndimage.filters.median_filter(thS,size=mc.smooth),vmin=0., vmax=100., cmap='Blues',origin='lower')
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False)

    # decorate axes
    ax1.set_xlim((0,34))
    ax1.set_ylim((100,0))
    ax1.set_xticks([0,10,20,30])
    ax1.set_yticks([100,75,50,25,0])
    ax1.set_xticklabels([0,0.1,'width [m]',0.3])
    ax1.set_yticklabels([-1.0,-0.75,-0.5,-0.25,0])
    #ax1.text(40,-5,'width [m]')
    ax1.text(-4,85,'depth [m]',rotation='vertical')
    
    if saving:
        plt.savefig(''.join(['./results/NWL',runname[-6:-2],'_',str(ix).zfill(3),'.pdf']))
        plt.close(fig)


def plotparticles_colpach(particles,mc,pdyn,vG,runname='test',t=0.,ix=0,sigma=0.5,fsize=(3, 9.5),saving=False,relative=True):
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    
    [thS,npart]=pdyn.gridupdate_thS(particles.lat,particles.z,mc)
    #[thSn,npartn]=pdyn.gridupdate_thS(particles.loc[((particles.age>0.)),'lat'],particles.loc[((particles.age>0.)),'z'].values,mc)
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(2, 2, width_ratios=[4,1.1], height_ratios=[1,9],hspace=0.02, wspace=0.02)
    
    #marginal X
    ax1 = fig.add_subplot(gs[0,0])
    old_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age<=0.)),'lat'].values).astype(np.int)).astype(float)
    all_dummy=np.copy(old_dummy)
    advect_dummy=old_dummy*0.
    advect_dummy2=np.bincount(np.round(100.0*particles.loc[((particles.age>0.)),'lat'].values).astype(np.int)).astype(float)
    advect_dummy[advect_dummy2>0]+=advect_dummy2[advect_dummy2>0]
    all_dummy+=advect_dummy
    if relative:
        old_dummy/=np.sum(old_dummy)
        advect_dummy/=np.sum(advect_dummy)
        all_dummy/=np.sum(all_dummy)
    
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:],'r-',label='new particles')
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:],'b-',label='all particles')
    ax1.plot((np.arange(0,len(old_dummy))/100.)[1:],old_dummy[1:],'g-',label='old particles')
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:], 0., color='b',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],old_dummy[1:], 0., color='g',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:], 0., color='r',alpha=0.3)
    ax1.set_xlim((0,0.32))
    ax1.set_ylim((0,np.amax(all_dummy)))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["top"].set_visible(False)  
    ax1.spines["right"].set_visible(False)
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["left"].set_visible(False)
   
    #marginal Y
    ax1 = fig.add_subplot(gs[1,1])
    onez=np.append(mc.zgrid[:,1]+0.001,mc.soildepth)
    z1=np.append(particles.loc[((particles.age>0.)),'z'].values,onez)
    advect_dummy=np.bincount(np.round(-100.0*z1).astype(np.int)).astype(float)-1
    all_dummy=np.copy(advect_dummy)
    z2=np.append(particles.loc[((particles.age<=0.)),'z'].values,onez)
    old_dummy=np.bincount(np.round(-100.0*z2).astype(np.int)).astype(float)-1
    all_dummy+=old_dummy
    if relative:
        advect_dummy/=np.sum(advect_dummy)
        old_dummy/=np.sum(old_dummy)
        all_dummy/=np.sum(all_dummy)
    ax1.plot(advect_dummy,(np.arange(0,len(advect_dummy))/-100.),'r-',label='new particles')
    ax1.plot(advect_dummy+old_dummy,(np.arange(0,len(old_dummy))/-100.),'b-',label='all particles')
    ax1.plot(old_dummy,(np.arange(0,len(old_dummy))/-100.),'g-',label='old particles')
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,all_dummy, color='b',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,old_dummy, color='g',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,advect_dummy, color='r',alpha=0.3)
    handles1, labels1 = ax1.get_legend_handles_labels() 
    ax1.set_ylim((-1.2,0.))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["right"].set_visible(False)  
    ax1.spines["top"].set_visible(False)  
    ax1.spines["left"].set_visible(False)

    
    #legend
    ax1 = fig.add_subplot(gs[0,1])
    ax1.text(0.05, 0.1, 'run:\n'+runname[-6:-2]+'\n\n'+'time:\n'+str(np.round(t/60.,1))+'min')
    #ax1.legend(handles1, labels1, loc=3)
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False) 
    
    #main
    ax1 = fig.add_subplot(gs[1,0])
    plt.imshow(sp.ndimage.filters.median_filter(thS,size=mc.smooth),vmin=0., vmax=100., cmap='Blues',origin='upper')
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False)

    # decorate axes
    ax1.set_xlim((0,64))
    ax1.set_ylim((240,0))
    ax1.set_xticks([0,20,40,60])
    ax1.set_yticks([240,180,120,60,0])
    ax1.set_xticklabels([0,0.1,'width [m]',0.3])
    ax1.set_yticklabels([-1.2,-0.9,-0.6,-0.3,0])
    #ax1.text(40,-5,'width [m]')
    ax1.text(-8,200,'depth [m]',rotation='vertical')
    
    if saving:
        plt.savefig(''.join(['./results/NC',runname[-6:-2],'_',str(ix).zfill(3),'.pdf']))
        plt.close(fig)

def plotparticles_column(particles,mc,pdyn,vG,runname='test',t=0.,ix=0,sigma=0.5,fsize=(4,4),saving=False,relative=False):
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    
    [thS,npart]=pdyn.gridupdate_thS(particles.lat,particles.z,mc)
    #[thSn,npartn]=pdyn.gridupdate_thS(particles.loc[((particles.age>0.)),'lat'],particles.loc[((particles.age>0.)),'z'].values,mc)
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(2, 2, width_ratios=[4,0.5], height_ratios=[0.5,4],hspace=0.02, wspace=0.02)
    
    #marginal X
    ax1 = fig.add_subplot(gs[0,0])
    old_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age<=0.)),'lat'].values).astype(np.int)).astype(float)
    all_dummy=np.copy(old_dummy)
    advect_dummy=old_dummy*0.
    advect_dummy2=np.bincount(np.round(100.0*particles.loc[((particles.age>0.)),'lat'].values).astype(np.int)).astype(float)
    advect_dummy[advect_dummy2>0]+=advect_dummy2[advect_dummy2>0]
    all_dummy+=advect_dummy
    if relative:
        old_dummy/=np.sum(old_dummy)
        advect_dummy/=np.sum(advect_dummy)
        all_dummy/=np.sum(all_dummy)
    
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:],'r-',label='new particles')
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:],'b-',label='all particles')
    ax1.plot((np.arange(0,len(old_dummy))/100.)[1:],old_dummy[1:],'g-',label='old particles')
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:], 0., color='b',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],old_dummy[1:], 0., color='g',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:], 0., color='r',alpha=0.3)
    ax1.set_xlim((0,1.))
    #ax1.set_ylim((0,np.amax(all_dummy)))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["top"].set_visible(False)  
    ax1.spines["right"].set_visible(False)
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["left"].set_visible(False)
   
    #marginal Y
    ax1 = fig.add_subplot(gs[1,1])
    onez=np.append(mc.zgrid[:,1]+0.001,mc.soildepth)
    z1=np.append(particles.loc[((particles.age>0.)),'z'].values,onez)
    advect_dummy=np.bincount(np.round(-100.0*z1).astype(np.int)).astype(float)-1
    all_dummy=np.copy(advect_dummy)
    z2=np.append(particles.loc[((particles.age<=0.)),'z'].values,onez)
    old_dummy=np.bincount(np.round(-100.0*z2).astype(np.int)).astype(float)-1
    all_dummy+=old_dummy
    if relative:
        advect_dummy/=np.sum(advect_dummy)
        old_dummy/=np.sum(old_dummy)
        all_dummy/=np.sum(all_dummy)
    ax1.plot(advect_dummy,(np.arange(0,len(advect_dummy))/-100.),'r-',label='new particles')
    ax1.plot(advect_dummy+old_dummy,(np.arange(0,len(old_dummy))/-100.),'b-',label='all particles')
    ax1.plot(old_dummy,(np.arange(0,len(old_dummy))/-100.),'g-',label='old particles')
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,all_dummy, color='b',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,old_dummy, color='g',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,advect_dummy, color='r',alpha=0.3)
    handles1, labels1 = ax1.get_legend_handles_labels() 
    ax1.set_ylim((-1.,0.))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["right"].set_visible(False)  
    ax1.spines["top"].set_visible(False)  
    ax1.spines["left"].set_visible(False)

    
    #legend
    ax1 = fig.add_subplot(gs[0,1])
    ax1.text(0.05, 0.1, 'run:\n'+runname[-6:-2]+'\n\n'+'time:\n'+str(np.round(t/60.,1))+'min')
    #ax1.legend(handles1, labels1, loc=3)
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False) 
    
    #main
    ax1 = fig.add_subplot(gs[1,0])
    plt.imshow(sp.ndimage.filters.median_filter(thS,size=mc.smooth),vmin=0., vmax=80., cmap='Blues',origin='upper')
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False)

    # decorate axes
    ax1.set_xlim((0,200))
    ax1.set_ylim((200,0))
    ax1.set_xticks([0,50,100,150,200])
    ax1.set_yticks([200,150,100,50,0])
    ax1.set_xticklabels([0,0.25,0.5,'width [m]',1])
    ax1.set_yticklabels([-1.0,'',-0.5,-0.25,0])
    #ax1.text(40,-5,'width [m]')
    ax1.text(-16,130,'depth [m]',rotation='vertical')
   
    if saving:
        plt.savefig(''.join(['./results/NCol',runname[-6:-2],'_',str(ix).zfill(3),'.pdf']))
        plt.close(fig)

def plotparticles_hoevelerbach(particles,mc,pdyn,vG,runname='test',t=0.,ix=0,sigma=0.5,fsize=(2., 9.5),saving=False,relative=True):
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.ndimage.filters import gaussian_filter1d
    
    [thS,npart]=pdyn.gridupdate_thS(particles.lat,particles.z,mc)
    #[thSn,npartn]=pdyn.gridupdate_thS(particles.loc[((particles.age>0.)),'lat'],particles.loc[((particles.age>0.)),'z'].values,mc)
    
    fig=plt.figure(figsize=fsize)
    gs = gridspec.GridSpec(2, 2, width_ratios=[5,1.5], height_ratios=[1,19],hspace=0.02, wspace=0.02)
    
    #marginal X
    ax1 = fig.add_subplot(gs[0,0])
    old_dummy=np.bincount(np.round(100.0*particles.loc[((particles.age<=0.)),'lat'].values).astype(np.int)).astype(float)
    all_dummy=np.copy(old_dummy)
    advect_dummy=old_dummy*0.
    advect_dummy2=np.bincount(np.round(100.0*particles.loc[((particles.age>0.)),'lat'].values).astype(np.int)).astype(float)
    advect_dummy[advect_dummy2>0]+=advect_dummy2[advect_dummy2>0]
    all_dummy+=advect_dummy
    if relative:
        old_dummy/=np.sum(old_dummy)
        advect_dummy/=np.sum(advect_dummy)
        all_dummy/=np.sum(all_dummy)
    
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:],'r-',label='new particles')
    ax1.plot((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:],'b-',label='all particles')
    ax1.plot((np.arange(0,len(old_dummy))/100.)[1:],old_dummy[1:],'g-',label='old particles')
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:]+old_dummy[1:], 0., color='b',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],old_dummy[1:], 0., color='g',alpha=0.15)
    ax1.fill_between((np.arange(0,len(advect_dummy))/100.)[1:],advect_dummy[1:], 0., color='r',alpha=0.3)
    ax1.set_xlim((0,0.302))
    ax1.set_ylim((0,np.amax(all_dummy)))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["top"].set_visible(False)  
    ax1.spines["right"].set_visible(False)
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["left"].set_visible(False)
   
    #marginal Y
    ax1 = fig.add_subplot(gs[1,1])
    onez=np.append(mc.zgrid[:,1]+0.001,mc.soildepth)
    z1=np.append(particles.loc[((particles.age>0.)),'z'].values,onez)
    advect_dummy=np.bincount(np.round(-100.0*z1).astype(np.int)).astype(float)-1
    all_dummy=np.copy(advect_dummy)
    z2=np.append(particles.loc[((particles.age<=0.)),'z'].values,onez)
    old_dummy=np.bincount(np.round(-100.0*z2).astype(np.int)).astype(float)-1
    all_dummy+=old_dummy
    if relative:
        advect_dummy/=np.sum(advect_dummy)
        old_dummy/=np.sum(old_dummy)
        all_dummy/=np.sum(all_dummy)
    ax1.plot(advect_dummy,(np.arange(0,len(advect_dummy))/-100.),'r-',label='new particles')
    ax1.plot(advect_dummy+old_dummy,(np.arange(0,len(old_dummy))/-100.),'b-',label='all particles')
    ax1.plot(old_dummy,(np.arange(0,len(old_dummy))/-100.),'g-',label='old particles')
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,all_dummy, color='b',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,old_dummy, color='g',alpha=0.15)
    ax1.fill_betweenx((np.arange(0,len(old_dummy))/-100.),0.,advect_dummy, color='r',alpha=0.3)
    handles1, labels1 = ax1.get_legend_handles_labels() 
    ax1.set_ylim((-1.8,0.))
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False)  
    ax1.spines["right"].set_visible(False)  
    ax1.spines["top"].set_visible(False)  
    ax1.spines["left"].set_visible(False)

    
    #legend
    ax1 = fig.add_subplot(gs[0,1])
    ax1.text(0.05, 0.1, 'run:\n'+runname[-6:-2]+'\n\n'+'time:\n'+str(np.round(t/60.,1))+'min')
    #ax1.legend(handles1, labels1, loc=3)
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False) 
    
    #main
    ax1 = fig.add_subplot(gs[1,0])
    plt.imshow(sp.ndimage.filters.median_filter(thS,size=mc.smooth),vmin=0., vmax=100., cmap='Blues',origin='upper')
    ax1.spines["bottom"].set_visible(False) 
    ax1.spines["top"].set_visible(False) 
    ax1.spines["left"].set_visible(False) 
    ax1.spines["right"].set_visible(False)

    # decorate axes
    ax1.set_xlim((0,60))
    ax1.set_ylim((360,0))
    ax1.set_xticks([0,20,40,60])
    ax1.set_yticks([360,300,240,180,120,60,0])
    ax1.set_xticklabels([0,0.1,'width\n[m]',0.3])
    ax1.set_yticklabels([-1.8,-1.5,-1.2,-0.9,-0.6,-0.3,0])
    #ax1.text(40,-5,'width [m]')
    ax1.text(-9,315,'depth [m]',rotation='vertical')
    
    if saving:
        plt.savefig(''.join(['./results/NC',runname[-6:-2],'_',str(ix).zfill(3),'.pdf']))
        plt.close(fig)

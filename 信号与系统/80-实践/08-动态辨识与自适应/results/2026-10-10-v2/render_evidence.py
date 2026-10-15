from pathlib import Path
import json,cairosvg,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path(__file__).resolve().parent;plots=base/'plots';plots.mkdir()
cairosvg.svg2png(url=str(base/'snapshot/assets/noise-paths.svg'),write_to=str(plots/'noise-paths.png'),output_width=1620,output_height=1050)
r=json.loads((base/'output/results.json').read_text());o=json.loads((base/'independent-oracle.json').read_text());dr=list(csv.DictReader((base/'output/drift.csv').open()))
fig,axs=plt.subplots(2,1,figsize=(10,7),sharex=True)
x=list(range(1,2048));axs[0].plot(x,[float(row['h0_true']) for row in dr[1:]],color='black',ls='--',label='Physical h0 truth')
axs[1].plot(x,[-.25]*2047,color='black',ls='--',label='Physical h1 truth')
for name,label in [('RLS_lambda_1','RLS lambda=1'),('RLS_lambda_098','RLS lambda=0.98'),('LMS_mu_002','LMS mu=0.02')]:
 for j,ax in enumerate(axs):ax.plot(x,[row[j] for row in r['drift'][name]['trajectory']],label=label,lw=1)
for j,ax in enumerate(axs):ax.axvline(1024,color='gray',ls=':');ax.set_ylabel(f'h{j} (dimensionless)');ax.grid(alpha=.2);ax.legend(loc='best',fontsize=9)
axs[1].set_xlabel('Physical sample k; drift begins at k=1024');fig.suptitle('Actual fixed-seed parameter trajectories (all retained)');fig.tight_layout();fig.savefig(plots/'actual-drift-trajectories.png',dpi=160);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11,4))
for name,label in [('ideal_observation','Ideal observation'),('output_measurement_noise','Output measurement noise')]:
 d=o['AR'][name]['all_lags'];axs[0].plot(range(9),d['residual_covariance'],'o-',label=label);axs[1].plot(range(9),d['input_residual_covariance'],'o-',label=label)
for ax in axs:ax.axhline(0,color='gray',lw=1);ax.set_xlabel('Physical lag ell');ax.set_xticks(range(9));ax.grid(alpha=.2);ax.legend(fontsize=8)
axs[0].set_ylabel('Residual covariance (normalized V squared)');axs[1].set_ylabel('Cov(u[k-ell], e[k]) (normalized V squared)');axs[0].set_title('Full-window mean centering, denominator N=4096');axs[1].set_title('lag 0 is u[k]; predictor input is lag 1');fig.suptitle('Actual AR held-out residual diagnostics; no whiteness certificate');fig.tight_layout();fig.savefig(plots/'actual-AR-nine-lags.png',dpi=160);plt.close(fig)
print(json.dumps({'status':'RENDERED','files':['noise-paths.png','actual-drift-trajectories.png','actual-AR-nine-lags.png'],'CairoSVG':cairosvg.__version__,'matplotlib':matplotlib.__version__,'real_data':True}))

"""Three explanatory SVGs and Cairo renders of those exact SVG bytes.

No default output directory. CairoSVG must already be available; never installs.
"""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import cairosvg
from state_lab import write_data

def plots(output):
    output=Path(output);d=write_data(output)
    plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','svg.hashsalt':'wwl-state-v1'})
    def save(fig,name):
        fig.tight_layout()
        svg=output/(name+'.svg')
        fig.savefig(svg,metadata={'Date':None,'Creator':'WWL state teaching source'})
        # Render frozen SVG directly, preserving its labels/layout, at actual 425px.
        cairosvg.svg2png(bytestring=svg.read_bytes(),write_to=str(output/(name+'-425.png')),output_width=425)
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,3.1));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
    def box(x,y,w,h,label):
        ax.add_patch(plt.Rectangle((x,y),w,h,facecolor='white',edgecolor='black'))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=11)
    def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'black'})
    box(1.6,2.7,1.3,1,'B');box(3.6,2.7,.8,1,'sum');box(5.1,2.7,1.6,1,'integrate');box(7.4,2.7,1.1,1,'C')
    box(4.7,.65,1.3,.8,'A');box(6.8,4.7,1.1,.8,'D')
    ax.text(.5,3.2,'u(t)',ha='center');arrow((.9,3.2),(1.6,3.2));arrow((2.9,3.2),(3.6,3.2));arrow((4.4,3.2),(5.1,3.2));arrow((6.7,3.2),(7.4,3.2));arrow((8.5,3.2),(9.5,3.2))
    ax.text(9.6,3.6,'y(t)',ha='center');ax.text(7.0,3.6,'x(t)',ha='center')
    ax.plot([7,7,6],[3.2,1.05,1.05],'k-');arrow((6.35,1.05),(6,1.05))
    ax.plot([4.7,4,4],[1.05,1.05,2.7],'k-');arrow((4,2.4),(4,2.7))
    ax.plot([1.2,1.2,6.8],[3.2,5.1,5.1],'k-');ax.plot([7.9,9,9],[5.1,5.1,3.2],'k-');arrow((9,3.8),(9,3.2))
    ax.text(5.9,4.2,'x(0)=x0',ha='center');arrow((5.9,4),(5.9,3.7))
    ax.text(5,-.05,'dx/dt = A x + B u;   y = C x + D u',ha='center',fontsize=11)
    ax.set_title('State port: initial condition is a separate input')
    save(fig,'state-port')
    fig,ax=plt.subplots(2,1,figsize=(5,5),sharex=True)
    ax[0].plot(d['t'],d['x'][:,1],'k-',label='x2 = exp(t)-1 (hidden)')
    ax[0].plot(d['t'],d['x'][:,0],'k--',label='x1 = 1-exp(-t)')
    ax[0].set(ylabel='normalized state',title='A=diag(-1,+1), B=[1,1], x0=0, u=1')
    ax[0].legend(fontsize=9)
    ax[1].plot(d['t'],d['y'],'k-',label='C=[1,0]: y=x1')
    ax[1].plot(d['t'],d['visible'],'k--',label='C=[1,0.001]: y=x1+0.001 x2')
    ax[1].set(xlabel='time (s)',ylabel='normalized output',title='Output port hides or reveals the same state')
    ax[1].legend(fontsize=8);save(fig,'hidden-output')
    fig=plt.figure(figsize=(5,6.6));ax=fig.add_subplot(2,1,1,projection='3d')
    ax.plot_surface(d['q1'],d['q2'],d['energy'],color='.8',edgecolor='.35',linewidth=.15,alpha=1)
    ax.set(xlabel='x01 (norm.)',ylabel='x02 (norm.)',zlabel='integral y^2 dt',title='Wo energy: A=diag(-1,-2), C=[1,1]')
    ax.view_init(elev=28,azim=-60);ax.tick_params(labelsize=8)
    ax.text2D(0,.92,'u=0; window T=1 s; height in norm.^2 s',transform=ax.transAxes,fontsize=8)
    q=np.linspace(-1,1,101);ax2=fig.add_subplot(2,1,2)
    ax2.plot(q,d['W'][0,0]*q*q,'k-',label='x0=[q,0]')
    ax2.plot(q,d['W'][1,1]*q*q,'k--',label='x0=[0,q]')
    ax2.plot(q,np.zeros_like(q),'k:',label='hidden C=[1,0], x0=[0,q]')
    ax2.set(xlabel='initial coordinate q (normalized)',ylabel='output energy (norm.^2 s)',title='Slices: visible directions vs exact hidden axis')
    ax2.legend(fontsize=8);save(fig,'gramian-energy')
    return d['results']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    print(plots(p.parse_args().output))

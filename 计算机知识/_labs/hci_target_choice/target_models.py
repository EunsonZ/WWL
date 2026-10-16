"""Finite model arithmetic. Fixed teaching data cannot establish human laws."""
from pathlib import Path
import argparse
import json
import math
import statistics

ROOT=Path(__file__).resolve().parent


def real(value, name, minimum=0, maximum=1e9):
    if type(value) not in (int,float) or not minimum <= value <= maximum or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite real within declared bounds, excluding bool')
    return float(value)


def fitts_id(distance, width):
    distance=real(distance,'distance');width=real(width,'width',minimum=1e-9)
    return math.log2(1+distance/width)


def entropy(probabilities):
    if type(probabilities) not in (list,tuple) or not 1 <= len(probabilities) <= 1024:
        raise ValueError('1..1024 declared probabilities required')
    values=[real(p,'probability',maximum=1) for p in probabilities]
    if not math.isclose(math.fsum(values),1,rel_tol=0,abs_tol=1e-12):
        raise ValueError('probabilities must sum to one; no implicit normalization')
    return -math.fsum(p*math.log2(p) for p in values if p)


def predict(x,a,b):
    return real(a,'intercept_s')+real(b,'slope_s_per_bit')*real(x,'bits')


def fit(xs,ys):
    if len(xs)!=len(ys) or len(xs)<3:
        raise ValueError('at least three paired model records required')
    x=[real(v,'x') for v in xs];y=[real(v,'time_s',minimum=1e-9,maximum=3600) for v in ys]
    xm=statistics.mean(x);ym=statistics.mean(y)
    sxx=math.fsum((v-xm)**2 for v in x)
    if sxx==0:raise ValueError('distinct predictor values required')
    b=math.fsum((u-xm)*(v-ym) for u,v in zip(x,y))/sxx;a=ym-b*xm
    residuals=[v-(a+b*u) for u,v in zip(x,y)]
    sse=math.fsum(r*r for r in residuals);sst=math.fsum((v-ym)**2 for v in y)
    return {'a_s':a,'b_s_per_bit':b,'residuals_s':residuals,'SSE_s2':sse,
            'R2':1-sse/sst if sst else None,'n_constructed_records':len(x),
            'inference':'descriptive OLS only, no participants, population interval or empirical validation'}


def channel(c):
    c=real(c,'sRGB channel',maximum=1)
    return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4


def luminance(rgb):
    if type(rgb) not in (list,tuple) or len(rgb)!=3:raise ValueError('three sRGB channels required')
    return math.fsum(w*channel(c) for w,c in zip((.2126,.7152,.0722),rgb))


def contrast(a,b):
    aa=luminance(a);bb=luminance(b)
    return (max(aa,bb)+.05)/(min(aa,bb)+.05)


def generate(output):
    data=json.loads((ROOT/'model-inputs.json').read_text())
    f=data['fitts'];c=data['choice']
    fx=[fitts_id(r['D_css_px'],r['W_css_px']) for r in f['rows']]
    cx=[entropy(r['probabilities']) for r in c['rows']]
    result={'identity':data['identity'],
        'fitts_rows':[{**r,'ID_bits':x,'declared_prediction_s':predict(x,f['a_s'],f['b_s_per_bit'])} for r,x in zip(f['rows'],fx)],
        'choice_rows':[{**r,'H_bits':x,'declared_prediction_s':predict(x,c['a_s'],c['b_s_per_bit'])} for r,x in zip(c['rows'],cx)],
        'fitts_OLS':fit(fx,[r['movement_s'] for r in f['rows']]),
        'choice_OLS':fit(cx,[r['reaction_s'] for r in c['rows']]),
        'change_conditions':{'double_D_and_W_same_ID':[fitts_id(128,64),fitts_id(256,128)],
            'double_W_at_D256':[fitts_id(256,64),fitts_id(256,128)],
            'same_n_different_uncertainty':[entropy([.25]*4),entropy([.7,.1,.1,.1])],
            'n4_H_vs_log2nplus1':[entropy([.25]*4),math.log2(5)],
            'outside_fit_new_device_example':{'D_css_px':256,'W_css_px':64,'a_s':.3,'b_s_per_bit':.25,
                'time_s':predict(fitts_id(256,64),.3,.25),
                'identity':'chosen alternative device coefficients, not a measurement'}},
        'attention_conditional':{k:v['notice']*v['interpret_given_notice'] for k,v in data['attention'].items() if isinstance(v,dict)},
        'speed_accuracy':{k:{**v,'correct_rate':v['correct']/v['attempts']} for k,v in data['speed_accuracy'].items() if isinstance(v,dict)},
        'contrast':{'black_white':contrast([0,0,0],[1,1,1]),'gray119_white':contrast([119/255]*3,[1,1,1])}}
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'model-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    plot(output,result)
    return result


def plot(output,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for i,(rows,key,time,fitkey) in enumerate([(result['fitts_rows'],'ID_bits','movement_s','fitts_OLS'),(result['choice_rows'],'H_bits','reaction_s','choice_OLS')]):
        xs=[r[key] for r in rows];ys=[r[time] for r in rows];f=result[fitkey]
        ax[i].scatter(xs,ys,label='constructed records')
        xx=[min(xs),max(xs)];ax[i].plot(xx,[f['a_s']+f['b_s_per_bit']*v for v in xx],label='descriptive OLS')
        ax[i].set(xlabel=key+' / bits',ylabel='time / seconds',title='Fitts' if i==0 else 'Hick-Hyman entropy form');ax[i].legend(fontsize=8)
    for i,k in enumerate(('narrow','wide')):
        row=result['speed_accuracy'][k];ax[2].scatter(row['mean_correct_s'],row['correct_rate'],label=k,s=70)
        ax[2].annotate(f"{row['correct']}/{row['attempts']}",(row['mean_correct_s'],row['correct_rate']),xytext=(3,3),textcoords='offset points')
    ax[2].set(xlim=(.39,.54),ylim=(.6,1),xlabel='mean among correct only / seconds',ylabel='correct / all attempts',title='Faster correct trials can hide more errors');ax[2].legend(fontsize=8)
    fig.suptitle('Synthetic teaching inputs; fit quality does not validate a human law')
    fig.savefig(Path(output)/'models.png',dpi=130);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();print(json.dumps(generate(args.output),ensure_ascii=False,indent=2))

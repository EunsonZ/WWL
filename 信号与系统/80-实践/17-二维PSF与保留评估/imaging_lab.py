"""Finite image operator, scatter adjoint, FFT boundary variants and certified convex reconstruction."""
import numpy as np


def kernel(value):
    h=np.asarray(value,dtype=float)
    if h.shape!=(3,3) or not np.isfinite(h).all() or np.any(h<0) or abs(h.sum()-1)>1e-12:raise ValueError('normalized_nonnegative_3x3_psf')
    return h


def image(value):
    x=np.asarray(value,dtype=float)
    if x.ndim!=2 or any(n<2 or n>16 for n in x.shape) or not np.isfinite(x).all():raise ValueError('finite_image_shape')
    return x


def blur(value,psf,boundary):
    x=image(value);h=kernel(psf);height,width=x.shape
    if boundary not in ('zero','periodic'):raise ValueError('boundary')
    y=np.zeros_like(x)
    for r in range(height):
        for c in range(width):
            for i in range(3):
                for j in range(3):
                    a,b=r-(i-1),c-(j-1)
                    if boundary=='periodic':a%=height;b%=width
                    if 0<=a<height and 0<=b<width:y[r,c]+=h[i,j]*x[a,b]
    return y


def blur_adjoint(value,psf,boundary):
    z=image(value);h=kernel(psf);height,width=z.shape
    if boundary not in ('zero','periodic'):raise ValueError('boundary')
    x=np.zeros_like(z)
    for r in range(height):
        for c in range(width):
            for i in range(3):
                for j in range(3):
                    a,b=r-(i-1),c-(j-1)
                    if boundary=='periodic':a%=height;b%=width
                    if 0<=a<height and 0<=b<width:x[a,b]+=h[i,j]*z[r,c]
    return x


def blur_fft(value,psf,boundary):
    x=image(value);h=kernel(psf);height,width=x.shape
    if boundary=='zero':
        shape=(height+2,width+2);full=np.fft.ifft2(np.fft.fft2(x,s=shape)*np.fft.fft2(h,s=shape)).real;return full[1:height+1,1:width+1]
    if boundary=='periodic':
        embedded=np.zeros_like(x)
        for i in range(3):
            for j in range(3):embedded[(i-1)%height,(j-1)%width]+=h[i,j]
        return np.fft.ifft2(np.fft.fft2(x)*np.fft.fft2(embedded)).real
    raise ValueError('boundary')


def acquire(value,psf,boundary,detector_rows):
    x=image(value)
    if any(n%2 for n in x.shape):raise ValueError('even_binning_shape')
    if not detector_rows or len(set(detector_rows))!=len(detector_rows) or any(type(r)!=int or not 0<=r<x.shape[0]//2 for r in detector_rows):raise ValueError('detector_rows')
    y=blur(x,psf,boundary);b=y.reshape(x.shape[0]//2,2,x.shape[1]//2,2).mean(axis=(1,3));return b[detector_rows,:].ravel()


def acquire_adjoint(value,shape,psf,boundary,detector_rows):
    if len(shape)!=2 or any(type(n)!=int or not 2<=n<=16 or n%2 for n in shape):raise ValueError('even_binning_shape')
    if not detector_rows or len(set(detector_rows))!=len(detector_rows) or any(type(r)!=int or not 0<=r<shape[0]//2 for r in detector_rows):raise ValueError('detector_rows')
    z=np.asarray(value,dtype=float)
    if z.shape!=(len(detector_rows)*shape[1]//2,) or not np.isfinite(z).all():raise ValueError('measurement_shape')
    full=np.zeros((shape[0]//2,shape[1]//2));full[detector_rows,:]=z.reshape(len(detector_rows),shape[1]//2)
    scattered=np.repeat(np.repeat(full,2,axis=0),2,axis=1)/4;return blur_adjoint(scattered,psf,boundary)


def dense_operator(shape,psf,boundary,detector_rows):
    if len(shape)!=2 or any(type(n)!=int or not 2<=n<=16 or n%2 for n in shape):raise ValueError('finite_operator_shape')
    n=int(np.prod(shape));return np.column_stack([acquire(np.eye(n)[i].reshape(shape),psf,boundary,detector_rows) for i in range(n)])


def difference(shape):
    height,width=shape
    if any(type(n)!=int or not 2<=n<=16 for n in shape):raise ValueError('difference_shape')
    rows=[]
    for r in range(height):
        for c in range(width):
            for rr,cc in ((r,c+1),(r+1,c)):
                if rr<height and cc<width:
                    row=np.zeros(height*width);row[r*width+c]=-1;row[rr*width+cc]=1;rows.append(row)
    return np.array(rows)


def quadratic(a,y,parameter,method):
    a=np.asarray(a,float);y=np.asarray(y,float)
    if not np.isfinite(parameter) or parameter<0:raise ValueError('regularization_parameter')
    u,s,vt=np.linalg.svd(a,full_matrices=False)
    if method=='ridge':
        if parameter==0:raise ValueError('positive_ridge')
        factors=s/(s*s+parameter)
    elif method=='tsvd':factors=np.divide(1,s,out=np.zeros_like(s),where=s>max(parameter*s[0],1e-12*s[0]))
    else:raise ValueError('quadratic_method')
    x=vt.T@(factors*(u.T@y));return {'x':x.tolist(),'singular_values':s.tolist(),'objective':float(.5*np.linalg.norm(a@x-y)**2+(.5*parameter*np.dot(x,x) if method=='ridge' else 0))}


def tv(a,y,d,lam,epsilon,rho=.2,tolerance=1e-7,max_iterations=10000):
    a=np.asarray(a,float);y=np.asarray(y,float);d=np.asarray(d,float)
    if not np.isfinite([lam,epsilon,rho,tolerance]).all() or lam<=0 or epsilon<=0 or rho<=0 or tolerance<=0 or type(max_iterations)!=int or not 1<=max_iterations<=10000:raise ValueError('tv_parameter')
    q=a.T@a+epsilon*np.eye(a.shape[1])+rho*d.T@d;inverse=np.linalg.solve(q,np.eye(len(q)));x=np.zeros(a.shape[1]);z=np.zeros(d.shape[0]);u=np.zeros_like(z);history=[]
    for iteration in range(1,max_iterations+1):
        x=inverse@(a.T@y+rho*d.T@(z-u));dx=d@x;old=z.copy();t=dx+u;z=np.sign(t)*np.maximum(np.abs(t)-lam/rho,0);u+=dx-z
        primal=float(np.linalg.norm(dx-z));dual=float(np.linalg.norm(rho*d.T@(z-old)))
        if iteration==1 or iteration==max_iterations or iteration%25==0 or max(primal,dual)<=tolerance:
            residual=a@x-y;p=residual;s=np.clip(rho*u,-lam,lam);station=a.T@p+d.T@s;primal_objective=.5*residual@residual+.5*epsilon*x@x+lam*np.abs(dx).sum();dual_objective=-.5*p@p-y@p-.5/epsilon*(station@station);gap=float(primal_objective-dual_objective)
            history.append({'iteration':iteration,'objective':float(primal_objective),'primal_residual':primal,'dual_residual':dual,'dual_objective':float(dual_objective),'gap':gap})
            if max(primal,dual)<=tolerance and gap<=1e-6:break
    converged=max(primal,dual)<=tolerance and history[-1]['gap']<=1e-6
    return {'x':x.tolist(),'dual_data':p.tolist(),'dual_tv':s.tolist(),'z':z.tolist(),'history':history,'converged':bool(converged),'iterations':iteration,'objective':float(primal_objective),'gap':gap,'lambda':lam,'epsilon':epsilon}


def fit(a,y,d,candidate,config):
    if candidate['method']=='tv':return tv(a,y,d,candidate['parameter'],config['epsilon'],config['rho'],config['tolerance'],config['max_iterations'])
    return quadratic(a,y,candidate['parameter'],candidate['method'])


def select(a,y_fit,y_validation,d,candidates,config):
    """No reference image or evaluation observations are arguments to selection."""
    results=[]
    for candidate in candidates:
        estimate=fit(a,y_fit,d,candidate,config)
        if estimate.get('converged',True) is not True:raise RuntimeError('candidate_not_converged')
        score=float(np.mean((a@estimate['x']-y_validation)**2));results.append({'candidate':candidate,'validation_mse':score,'fit':estimate})
    winners={}
    for method in sorted({c['method'] for c in candidates}):
        chosen=min((i for i,row in enumerate(results) if row['candidate']['method']==method),key=lambda i:(results[i]['validation_mse'],i));winners[method]=results[chosen]['candidate']
    overall=min(range(len(results)),key=lambda i:(results[i]['validation_mse'],i))
    return {'rows':results,'by_family':winners,'overall':results[overall]['candidate'],'rule':'minimum independent validation prediction MSE, earliest declared candidate breaks ties'}

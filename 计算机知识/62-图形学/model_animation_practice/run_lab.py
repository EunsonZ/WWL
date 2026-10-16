"""Finite workload; new output directory required; reuse canonical arrays and renderer."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np


def run(spec,shared,out):
    if out.exists():raise FileExistsError('new_output_required')
    if spec['input_version']!='surface-animation-v1' or not 1<=len(spec['patch_n'])<=3 or any(type(n)!=int or not 1<=n<=12 for n in spec['patch_n']) or len(set(spec['patch_n']))!=len(spec['patch_n']):raise ValueError('workload_patch_limit')
    if type(spec['loop_start_n'])!=int or not 1<=spec['loop_start_n']<=4 or type(spec['loop_levels'])!=int or not 0<=spec['loop_levels']<=2 or spec['resolution'] not in (64,128):raise ValueError('workload_render_limit')
    if not 1<=len(spec['skin_parameters'])<=4 or not 0<=spec['skin_max_degrees']<=45 or len(spec['ik_targets'])>8:raise ValueError('workload_pose_limit')
    sp=spec['spring']
    if len(sp['h'])>4 or sp['final_time']!=1 or any(not .03125<=h<=.5 or abs(round(1/h)*h-1)>1e-12 for h in sp['h']):raise ValueError('workload_time_limit')
    if any(len(spec[name]['parameters'])>32 for name in ('spline','repeated_spline')):raise ValueError('workload_spline_limit')
    sys.path.insert(0,str(shared));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import surface_lab as s,animation_lab as a,renderer,curve_mesh_lab
    result={'input_version':spec['input_version'],'numpy':np.__version__,'bindings':{name:hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest() for name,mod in [('surface_lab',s),('animation_lab',a),('renderer',renderer),('curve_mesh_lab',curve_mesh_lab)]},'splines':[],'patches':[],'loop':[],'poses':[],'ik':[],'spring':[],'renders':[]}
    for name in ('spline','repeated_spline'):
        c=spec[name];rows=[{'t':t,**s.spline(c['control'],c['knots'],c['degree'],t)} for t in c['parameters']];item={'id':name,'samples':rows}
        if name=='spline':
            changed=np.array(c['control'],float);changed[c['edit_index']]+=c['edit_delta'];item['edited_samples']=[{'t':t,**s.spline(changed,c['knots'],c['degree'],t)} for t in c['parameters']]
        result['splines'].append(item)
    control=np.array(spec['patch_control'],float)
    # General patch evaluation recorded independently of its mesh samples.
    result['patch_samples']=[{'uv':[u,v],'point':s.patch(control,u,v)[0].tolist(),'du':s.patch(control,u,v)[1].tolist(),'dv':s.patch(control,u,v)[2].tolist(),'normal':s.patch(control,u,v)[3].tolist()} for u,v in [(0,0),(.25,.75),(.5,.5),(1,1)]]
    for n in spec['patch_n']:
        mesh=s.patch_mesh(control,n);mesh['n']=n
        errors=[]
        for j in range(n):
            for i in range(n):
                u=(i+.5)/n;v=(j+.5)/n;v0=j*(n+1)+i+1;v1=(j+1)*(n+1)+i
                chord=(np.array(mesh['positions'][v0])+mesh['positions'][v1])/2;errors.append(float(np.linalg.norm(s.patch(control,u,v)[0]-chord)))
        mesh['cell_diagonal_midpoint_errors']=errors;result['patches'].append(mesh)
    mesh=s.patch_mesh(control,spec['loop_start_n']);result['loop'].append({'level':0,**mesh})
    for level in range(1,spec['loop_levels']+1):mesh=s.loop_step(mesh['positions'],mesh['triangles']);result['loop'].append({'level':level,**mesh})
    qa=a.axis_angle([0,0,1],math.radians(spec['quaternion_degrees'][0]));qb=a.axis_angle([0,0,1],math.radians(spec['quaternion_degrees'][1]));qm=a.slerp(qa,qb,.5)
    result['quaternion']={'a':qa.tolist(),'b':qb.tolist(),'mid':qm.tolist(),'mid_matrix':a.rotation(qm).tolist(),'linear_angle_mid_matrix':a.rotation(a.axis_angle([0,0,1],math.radians(sum(spec['quaternion_degrees'])/2))).tolist()}
    bind=a.hierarchy([-1,0],[np.eye(4),a.translation(1,0,0)]);base=result['patches'][0];pos=np.array(base['positions']);weights=np.c_[1-pos[:,0]/2,pos[:,0]/2]
    for t in spec['skin_parameters']:
        q=a.slerp([1,0,0,0],a.axis_angle([0,0,1],math.radians(spec['skin_max_degrees'])),t);local=[a.translation(.2*t,0,0),a.translation(1,0,0)@a.rotation(q)];pose=a.hierarchy([-1,0],local);skinned=a.skin(pos,weights,pose,bind)
        result['poses'].append({'t':t,'parents':[-1,0],'local':np.array(local).tolist(),'world':pose.tolist(),'bind':bind.tolist(),'weights':weights.tolist(),'quaternion':q.tolist(),**skinned,'triangles':base['triangles']})
    collapse=a.skin([[1,1,0]],[[.5,.5]],[np.eye(4),a.rotation(a.axis_angle([0,0,1],math.pi))],[np.eye(4),np.eye(4)])
    result['collapse']=collapse
    scale=np.diag([2,1,1,1]);shift=a.translation(3,0,0);point=np.array([1,0,0,1]);linear=scale[:3,:3];normal=np.array([1,-1,0.]);tangent=np.array([1,1,0.])
    result['nonrigid']={'TS':(shift@scale@point).tolist(),'ST':(scale@shift@point).tolist(),'naive_normal':(linear@normal).tolist(),'inverse_transpose_normal':(np.linalg.inv(linear).T@normal).tolist(),'transformed_tangent':(linear@tangent).tolist(),'parent_world':a.hierarchy([-1,0],[scale,a.translation(1,0,0)@a.rotation(a.axis_angle([0,0,1],math.pi/4))]).tolist()}
    for target in spec['ik_targets']:
        try:angles=a.ik2(spec['ik_lengths'],target);result['ik'].append({'target':target,'status':'solved','solutions':[{'angles':q,**a.fk2(spec['ik_lengths'],q)} for q in angles]})
        except ValueError as e:result['ik'].append({'target':target,'status':str(e)})
    for method in ('explicit','symplectic'):
        for h in sp['h']:result['spring'].append({'method':method,'h':h,'trace':a.spring(sp['omega'],h,round(1/h),method)})
        result['spring'].append({'method':method,'h':sp['unstable_h'],'unstable_probe':True,'trace':a.spring(sp['omega'],sp['unstable_h'],sp['unstable_steps'],method)})
    out.mkdir(parents=True)
    def render(name,mesh,x=0,flat=False):
        if flat:p,f,n=s.flat_arrays(mesh)
        else:p=np.array(mesh['positions']);f=np.array(mesh['triangles']);n=np.array(mesh['normals'])
        color=np.tile([.2,.55,.9],(len(p),1));model=a.translation(x,0,-4)@a.rotation(a.axis_angle([1,0,0],math.radians(25)))@a.translation(-1,-1,0)
        image,depth=renderer.render(p,f,color,n,model=model,width=spec['resolution'],height=spec['resolution']);png=out/(name+'.png');curve_mesh_lab.write_png(png,np.rint(renderer.srgb(image)*255).astype(np.uint8))
        result['renders'].append({'id':name,'positions':p.tolist(),'triangles':f.tolist(),'normals':n.tolist(),'colors':color.tolist(),'model':model.tolist(),'covered_pixels':int(np.isfinite(depth).sum()),'png':png.name,'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest()})
    for mesh in result['patches']:render('patch_n'+str(mesh['n']),mesh)
    for mesh in result['loop']:render('loop_'+str(mesh['level']),mesh,flat=True)
    for i,mesh in enumerate(result['poses']):render('skin_'+str(i),mesh,flat=True)
    result['comparison']=[]
    for mesh in result['patches']:
        for h in sp['h'][:2]:
            row=next(x for x in result['spring'] if x['method']=='symplectic' and x['h']==h);end=row['trace'][-1];name=f'motion_n{mesh["n"]}_h{h:g}';render(name,mesh,end['q']);result['comparison'].append({'n':mesh['n'],'h':h,'geometry_error':max(mesh['cell_diagonal_midpoint_errors']),'q_error':end['q_error'],'phase_state_error':end['phase_state_error'],'render':name})
    render('motion_exact',base,math.cos(sp['omega']))
    (out/'actual.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--shared-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=run(json.loads(a.spec.read_text()),a.shared_dir,a.out);print(json.dumps({'splines':len(result['splines']),'patches':len(result['patches']),'renders':len(result['renders']),'comparisons':len(result['comparison'])}))
if __name__=='__main__':main()

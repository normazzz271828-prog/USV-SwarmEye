"""LOS/PID adapters of supplied o3/s3/z3 scripts; reconstructed smoothing.

The controller is a kinematic demonstration, separate from the quantum risk model.
See docs/CONTROL_MODELS.md for source differences and verification limits.
"""
import math
import numpy as np
from .team_control import TeamCoordinator

MODELS={'control_o':'圆形航线 · 协同避障','control_s':'S 形航线 · 协同避障','control_z':'Z 形航线 · 协同避障'}

def fields(model):
    z=model=='control_z';o=model=='control_o'
    return {
        'duration':('回放时长 / s',120,30,300,10),
        'horizon':('片段检索范围 / s',360,60,600,20),
        'cruise':('基准航速 / m·s⁻¹',4.2 if z else 4.,1,6,.2),
        'avoid_gain':('避障强度',4.2 if z else 4.,0,8,.2),
        'stat_radius':('静态避障触发半径 / m',30,15,80,5),
        'dyn_radius':('动态避障触发半径 / m',42 if z else 40,15,100,5),
        'lookahead':('前视距离 / m',8 if model=='control_s' else 10,4,30,1),
        'kp':('航向比例增益',2. if o else 1.8 if z else 1.5,.1,4,.1),
        'ki':('航向积分增益',.05 if o else .015 if z else .01,0,.1,.005),
        'kd':('航向微分增益',.8 if o else .45 if z else .5,0,1,.05),
        'tau':('转向响应时间 / s',.35,.05,2,.05),
        'max_omega':('最大转向角速度 / rad·s⁻¹',1.,.1,1.5,.1),
        'max_rate':('转向角加速度上限 / rad·s⁻²',.9,.1,2,.1),
        'team_avoid':('成员互避（0 关 / 1 开）',1,0,1,1),
        'team_separation':('成员最小期望间距 / m',18,12,40,1),
        'team_horizon':('成员预测时间 / s',12,3,30,1),
        'sync':('编队同步增益',.45 if z else .5,0,1,.05),
    }

def wrap(a):
    return math.atan2(math.sin(a),math.cos(a))

def smooth_omega(raw, previous, dt, tau, max_rate, max_omega):
    """Backward-Euler low-pass then slew and amplitude limits (reconstructed)."""
    values=(raw,previous,dt,tau,max_rate,max_omega)
    if not all(math.isfinite(x) for x in values) or min(dt,tau,max_rate,max_omega)<=0:
        raise ValueError('Invalid smoothing parameters')
    target=max(-max_omega,min(max_omega,raw))
    previous=max(-max_omega,min(max_omega,previous))
    filtered=previous+dt/(tau+dt)*(target-previous)
    return max(-max_omega,min(max_omega,previous+max(-max_rate*dt,min(max_rate*dt,filtered-previous))))

def setup(c):
    model=c['model'];o=model=='control_o';z=model=='control_z'
    if o:
        p=np.array([[60,0],[30,0],[90,0]],float);psi=np.full(3,3*math.pi/2)
        obstacles=np.array([[80,10],[400,150],[400,60],[55,-100],[350,-40],[550,-15],[250,55]],float)
        speeds=[0,0,.5,.6,.506,.9,.6];angles=[0,0,3*math.pi/4,math.pi/4,-math.pi/2,math.pi,5*math.pi/6];stat=2
    elif z:
        p=np.array([[0,60],[0,105],[0,15]],float);psi=np.zeros(3)
        obstacles=np.array([[155,78],[280,5],[445,-68],[230,92],[320,-25],[550,-25]],float)
        speeds=[0,0,0,.8,.7,.9];angles=[0,0,0,-2*math.pi/3,2*math.pi/3,math.pi];stat=3
    else:
        p=np.array([[0,5],[0,50],[0,-50]],float);psi=np.zeros(3)
        obstacles=np.array([[80,10],[250,-15],[400,60],[180,40],[350,-40],[520,-15],[100,55]],float)
        speeds=[0,0,2,.6,.506,.9,1.5];angles=[0,0,6*math.pi/5,-math.pi/2,math.pi/2,math.pi,-math.pi/3];stat=2
    ov=np.array([[s*math.cos(a),s*math.sin(a)] for s,a in zip(speeds,angles)])
    radii=np.array([c['stat_radius']]*stat+[c['dyn_radius']]*(len(obstacles)-stat))
    return p,psi,obstacles,ov,radii,stat

def initial(c):
    p,psi,obs,ov,r,stat=setup(c)
    speeds=c['cruise']*np.array([1,1.15,.85]) if c['model']=='control_o' else np.full(3,c['cruise'])
    v=np.vstack([np.column_stack([speeds*np.cos(psi),speeds*np.sin(psi)]),ov])
    # Controlled ship hull radius 6 m; obstacle radii shown are trigger domains.
    radii=np.r_[np.full(3,6.),r]
    return np.vstack([p,obs]),v,radii,radii,(90-np.degrees(np.r_[psi,np.arctan2(ov[:,1],ov[:,0])]))%360,3

def simulate(c):
    o=c['model']=='control_o';z=c['model']=='control_z';dt=.02
    p,psi,obs,ov,rr,stat=setup(c)
    if 'ships' in c:
        rows=np.array(c['ships']);p=rows[:3,:2].copy();psi=np.radians(90-rows[:3,3]);obs=rows[3:,:2].copy()
        ov=np.column_stack([rows[3:,2]*np.sin(np.radians(rows[3:,3])),rows[3:,2]*np.cos(np.radians(rows[3:,3]))])
    base=c['cruise']*(np.array([1.,1.15,.85]) if o else np.ones(3))
    if 'ships' in c: base=np.array(c['ships'])[:3,2].copy()
    speed=base.copy()
    low=(.5*base.min() if o else 1.2 if z else 1.);high=(1.5*base.max() if o else 6.2 if z else 6.)
    sums=np.zeros(3);prev=np.zeros(3);usums=np.zeros(3);uprev=np.zeros(3);omega=np.zeros(3);memory=np.zeros(3);cmd=psi.copy()
    coordinator=TeamCoordinator(c['team_separation'],c['team_horizon'])
    team_active=np.zeros(3,dtype=bool);team_pairs=[];recovery=np.zeros(3);team_sample=np.zeros(3,dtype=bool)
    team_angles=[None]*3;team_caps=np.full(3,np.inf)
    max_acceleration=0.;previous_speed=speed.copy()
    progress=math.pi if o else 0.;frames=[];first_avoid=None;min_obstacle=math.inf;min_team=math.inf
    def snapshot(t,active):
        distances=np.linalg.norm(p[:,None,:]-obs[None,:,:],axis=2)
        i,j=np.unravel_index(np.argmin(distances),distances.shape)
        team_distances=[(float(np.linalg.norm(p[ii]-p[jj])),ii,jj) for ii,jj in ((0,1),(0,2),(1,2))]
        team_distance,ti,tj=min(team_distances)
        closest=[int(i),int(j+3)];nearest=float(distances.min())
        if team_distance<nearest:closest=[ti,tj];nearest=team_distance
        points=np.vstack([p,obs]);head=np.r_[psi,np.arctan2(ov[:,1],ov[:,0])]
        return {'p':np.round(points,4).tolist(),'heading':np.round((90-np.degrees(head))%360,3).tolist(),
                'risk':round(float(np.maximum(0,1-distances/rr).max()),5),'distance':round(nearest,3),
                'nearest_pair':closest,'intrusion':bool(np.any(distances<rr) or team_distance<c['team_separation']), 'domains':[],'groups':[],
                'team_avoiding':team_sample.tolist(),'team_pairs':team_pairs,'team_distance':round(team_distance,3),'recovering':(recovery>0).tolist(),'avoiding':[bool(a) for a in active],'omega':omega.tolist(),'speed':speed.tolist(),'time':round(t,3)}
    frames.append(snapshot(0,[False]*3));active_sample=np.zeros(3,dtype=bool)
    for step in range(1,int(c['horizon']/dt)+1):
        if c['team_avoid']:
            team_angles,team_caps,team_active,team_pairs=coordinator.step(p.copy(),psi.copy(),speed.copy(),step*dt)
            recovery=np.where(team_active,4.,np.maximum(0,recovery-dt))
            team_sample|=team_active
        if o:
            phase=np.arctan2(p[:,1],p[:,0]-260)
            err=sum(wrap(progress-a) for a in phase)
            virtual=max(.2*c['cruise']/200,c['cruise']/200-c['sync']*err)
        else:
            virtual=max((.25 if z else .2)*c['cruise'],c['cruise']-c['sync']*sum(progress-p[:,0]))
            if z:virtual=min(1.4*c['cruise'],virtual)
        # The formation clock keeps running: freezing it while a pair is active left the
        # ships with a large catch-up demand after release, so they accelerated through
        # whichever external trigger domain they happened to be crossing.
        progress+=virtual*dt;obs+=ov*dt
        active=np.zeros(3,dtype=bool)
        for k in range(3):
            delta=c['lookahead'];gain=c['avoid_gain']
            if o:
                radius=[200,230,170][k];target=progress%(2*math.pi);gamma=target+math.pi/2
                ref=np.array([260+radius*math.cos(target),radius*math.sin(target)])
                lateral=-(p[k,0]-ref[0])*math.sin(gamma)+(p[k,1]-ref[1])*math.cos(gamma)
                delta*=radius/200;uerr=wrap(target-math.atan2(p[k,1],p[k,0]-260))
            else:
                target=min(560 if z else 520,max(0,progress if z else p[k,0]))
                target=round(target*10)/10
                if z:
                    y=60 if target<=145 else -60 if target>=390 else 60-120*(target-145)/245
                    gamma=math.atan2(-120/245,1) if 145<=target<390 else 0
                    ref=np.array([target,y+[0,45,-45][k]])
                    lateral=-(p[k,0]-ref[0])*math.sin(gamma)+(p[k,1]-ref[1])*math.cos(gamma)
                    if k==1:delta*=1.6;gain*=3.2/4.2
                else:
                    ref=np.array([target,30*math.sin(.03*target)+[0,50,-50][k]])
                    gamma=math.atan2(30*(math.sin(.03*(target+.1))-math.sin(.03*target)),.1) if target<520 else 0
                    lateral=p[k,1]-ref[1]
                uerr=progress-p[k,0]
            los=gamma+math.atan(-lateral/delta);vx=math.cos(los);vy=math.sin(los)
            best=(0.,0.,False);margin=math.inf
            for j in range(len(obs)):
                dx=obs[j,0]-p[k,0];dy=obs[j,1]-p[k,1];dist=math.hypot(dx,dy);margin=min(margin,dist-rr[j])
                if dist>=rr[j]:continue
                alpha=wrap(math.atan2(dy,dx)-los)
                if abs(alpha)>=math.pi/2:continue
                weight=1-dist/rr[j]
                if z:
                    if weight>best[0]:best=(weight,alpha,j>=stat)
                elif gain>0:
                    active[k]=True;side=1 if (j>=stat and abs(alpha)<.2) or alpha>=0 else -1
                    vx+=gain*weight*side*math.sin(los);vy-=gain*weight*side*math.cos(los)
            if z and best[0]>0 and gain>0:
                active[k]=True;weight,alpha,dynamic=best
                if memory[k]==0:memory[k]=1 if dynamic and abs(alpha)<.2 or alpha>=0 else -1
                side=1 if dynamic and abs(alpha)<.2 else memory[k]
                vx+=gain*weight*side*math.sin(los);vy-=gain*weight*side*math.cos(los)
            target_angle=math.atan2(vy,vx)
            if z:
                if not active[k] and margin>8:memory[k]=0
                target_angle=cmd[k]+.22*wrap(target_angle-cmd[k]);cmd[k]=target_angle
            if team_angles[k] is not None:
                target_angle=team_angles[k]
            elif recovery[k]>0:
                target_angle=psi[k]+(1-recovery[k]/4)*wrap(target_angle-psi[k])
            error=wrap(target_angle-psi[k])
            if recovery[k]==0:sums[k]+=error*dt
            else:sums[k]*=max(0,1-dt)
            raw=c['kp']*error+c['ki']*sums[k]+c['kd']*(error-prev[k])/dt;prev[k]=error
            omega[k]=smooth_omega(raw,omega[k],dt,c['tau'],c['max_rate'],c['max_omega'])
            # Anti-windup in the speed loop: while external avoidance is active the request
            # is repeatedly turned away from the obstacle, so an integrating speed error
            # would build up and later accelerate the ship through the same trigger domain.
            holding=bool(active[k]) and bool(c['team_avoid'])
            if recovery[k]==0 and not holding:usums[k]+=uerr*dt
            else:usums[k]*=max(0,1-dt)
            ku,iu,du=(.8,.02,.1) if o else (1.,.012,.08) if z else (1.,.01,.1)
            requested=max(low,min(high,base[k]+ku*uerr+iu*usums[k]+du*(uerr-uprev[k])/dt));uprev[k]=uerr
            requested=min(requested,team_caps[k])
            previous_speed[k]=speed[k]
            if c['team_avoid']:
                speed[k]+=max(-1.5*dt,min(.8*dt,requested-speed[k]))
            else:speed[k]=requested
            max_acceleration=max(max_acceleration,abs(speed[k]-previous_speed[k])/dt)
            psi[k]+=omega[k]*dt;p[k]+=speed[k]*dt*np.array([math.cos(psi[k]),math.sin(psi[k])])
        active|=team_active
        if active.any() and first_avoid is None:first_avoid=step*dt
        active_sample|=active
        min_obstacle=min(min_obstacle,float(np.linalg.norm(p[:,None,:]-obs[None,:,:],axis=2).min()))
        min_team=min(min_team,*(float(np.linalg.norm(p[i]-p[j])) for i,j in ((0,1),(0,2),(1,2))))
        if step%50==0:
            frames.append(snapshot(step*dt,active_sample));active_sample[:]=False;team_sample[:]=False
            if (o and progress>=3*math.pi) or (not o and np.all(p[:,0]>(620 if z else 600))):break
    start=max(0,min(len(frames)-2,int(first_avoid or 8)-8))
    duration=min(int(c['duration']),len(frames)-1-start)
    selected=frames[start:start+duration+1]
    points=np.array([f['p'] for f in selected]);lo=points.min(axis=(0,1))-50;hi=points.max(axis=(0,1))+50
    if o:
        angles=np.linspace(math.pi,3*math.pi,241)
        routes=[np.column_stack([260+r*np.cos(angles),r*np.sin(angles)]).tolist() for r in (200,230,170)]
    else:
        xs=np.linspace(0,560 if z else 520,241)
        ys=np.where(xs<=145,60,np.where(xs>=390,-60,60-120*(xs-145)/245)) if z else 30*np.sin(.03*xs)
        routes=[np.column_stack([xs,ys+offset]).tolist() for offset in ((0,45,-45) if z else (0,50,-50))]
    radii=[6.]*3+rr.tolist()
    return {'version':'control-adapter-3','config':c,'start':start,'duration':duration,'frames':selected,'bounds':[*lo,*hi],
            'a':radii,'b':radii,'independent':3,'labels':['USV1','USV2','USV3']+[f'礁石{i+1}' if i<stat else f'目标船{i-stat+1}' for i in range(len(obs))],
            'static_indices':list(range(3,3+stat)),'controlled':True,'first_avoid':first_avoid,
            'reference_paths':routes,'team_events':coordinator.events,
            'diagnostics':{'max_acceleration':max_acceleration,'minimum_obstacle_center_distance':min_obstacle,'minimum_team_center_distance':min_team,'computed_seconds':len(frames)-1}}

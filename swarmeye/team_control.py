"""Deterministic teammate coordination for the kinematic demonstration.

All pair decisions use the same pre-integration snapshot. This is an engineering
extension, not part of the supplied MATLAB scripts or a COLREGs certification.
"""
import math
import numpy as np


class TeamCoordinator:
    def __init__(self, separation=18., horizon=12.):
        self.separation=separation
        self.horizon=horizon
        self.encounters={}
        self.events=[]

    def step(self, positions, headings, speeds, time):
        n=len(positions); velocities=np.column_stack((np.cos(headings),np.sin(headings)))*speeds[:,None]
        angles=[None]*n;caps=np.full(n,np.inf);active=np.zeros(n,dtype=bool);pairs=[]
        priorities=np.full(n,np.inf)
        for i in range(n):
            for j in range(i+1,n):
                delta=positions[j]-positions[i];relative=velocities[j]-velocities[i]
                distance=float(np.linalg.norm(delta));vv=float(relative@relative)
                tcpa=-float(delta@relative)/vv if vv>1e-8 else math.inf
                dcpa=float(np.linalg.norm(delta+relative*tcpa)) if math.isfinite(tcpa) else distance
                closing=float(delta@relative)<-1e-5
                key=(i,j);record=self.encounters.get(key)
                dangerous=(0<=tcpa<=self.horizon and dcpa<self.separation) or distance<self.separation
                if record is None and dangerous:
                    dot=float(np.cos(headings[i]-headings[j]))
                    head_on=dot<-.5
                    if head_on:yielders=(i,j)
                    elif dot>.7:
                        # Same-course encounter: the vessel behind yields.
                        along=float(delta@np.array([math.cos(headings[i]),math.sin(headings[i])]))
                        yielders=(i,) if along>=0 else (j,)
                    else:
                        # Stable ID priority for crossing; no reciprocal indecision.
                        yielders=(j,)
                    record={'yielders':yielders,'angles':{},'start':time}
                    for k in yielders:
                        other=j if k==i else i
                        away=positions[k]-positions[other]
                        # Head-on: both turn starboard; otherwise move away from the
                        # crossing partner. Store direction until the encounter clears.
                        angle=float(headings[k]-math.pi/3) if head_on else math.atan2(away[1],away[0])
                        record['angles'][k]=angle
                    self.encounters[key]=record
                    self.events.append({'time':round(time,3),'pair':[i,j],'yielders':list(yielders),'type':'enter'})
                if record is None:continue
                if not dangerous and not closing and distance>self.separation+8:
                    del self.encounters[key]
                    self.events.append({'time':round(time,3),'pair':[i,j],'type':'clear'})
                    continue
                pairs.append([i,j]);active[i]=active[j]=True
                urgency=distance
                for k in record['yielders']:
                    if urgency<priorities[k]:
                        angles[k]=record['angles'][k];priorities[k]=urgency
                    caps[k]=min(caps[k],1.)
                # Both vessels brake if current separation cannot accommodate their
                # conservative stopping distances (1.5 m/s² plus one-second margin).
                gap=max(0.,distance-self.separation)
                stop=(speeds[i]**2+speeds[j]**2)/3+speeds[i]+speeds[j]
                if closing and gap<stop or distance<self.separation:
                    caps[i]=caps[j]=0.
        return angles,caps,active,pairs

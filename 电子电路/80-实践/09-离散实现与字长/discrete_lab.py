"""RC interval-state and integer arithmetic teaching models; import does no I/O.

Every interval simulation returns len(inputs)+1 states, including initial.
Input u[k] acts over [kT,(k+1)T). Standard bilinear H is a separate filter
transfer contract; it is never presented as this ZOH interval simulation.
"""
from dataclasses import dataclass
import cmath
import math


def real(value,positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError('finite real required')
    try:value=float(value)
    except OverflowError as exc:raise ValueError('outside float range') from exc
    if not math.isfinite(value) or (positive and value<=0):raise ValueError('finite positive required' if positive else 'finite real required')
    return value


def finite(value):
    if isinstance(value,complex):okay=math.isfinite(value.real) and math.isfinite(value.imag)
    else:okay=math.isfinite(value)
    if not okay:raise ValueError('derived value outside range')
    return value


def coefficients(T_s=.00025,tau_s=.001,method='exact'):
    T=real(T_s,True);tau=real(tau_s,True);h=finite(T/tau)
    if h==0:raise ValueError('step ratio underflow')
    if method=='exact':a=math.exp(-h);b=-math.expm1(-h)
    elif method=='euler':a=1-h;b=h
    elif method=='backward':a=1/(1+h);b=h/(1+h)
    elif method=='trapezoid_hold':
        # Equivalent to (1-h/2)/(1+h/2), without forming h+2 near range limit.
        a=2/(1+h/2)-1;b=h/(1+h/2)
    else:raise ValueError('unknown interval integration method')
    return finite(a),finite(b)


def simulate(inputs,T_s=.00025,initial_V=.4,method='exact',tau_s=.001):
    a,b=coefficients(T_s,tau_s,method);state=real(initial_V);result=[state]
    for value in inputs:
        u=real(value);state=finite(a*state+b*u);result.append(state)
    return result


def interval_h(theta_rad_sample,T_s=.00025,method='exact'):
    theta=real(theta_rad_sample);a,b=coefficients(T_s,method=method)
    q=cmath.exp(-1j*theta);denominator=1-a*q
    if denominator==0:raise ValueError('singular frequency')
    return finite(b*q/denominator)


def bilinear_h(theta_rad_sample,T_s=.00025,prototype_tau_s=.001):
    """Zero-state endpoint-input filter H with numerator 1+z^-1, no IC API."""
    theta=real(theta_rad_sample);T=real(T_s,True);tau=real(prototype_tau_s,True)
    h=finite(T/tau);a=2/(1+h/2)-1;c=(h/2)/(1+h/2)
    q=cmath.exp(-1j*theta);denominator=1-a*q
    if denominator==0:raise ValueError('singular frequency')
    return finite(c*(1+q)/denominator)


def modal_map(s_per_s,T_s,method='exact'):
    if isinstance(s_per_s,bool) or not isinstance(s_per_s,(int,float,complex)):raise ValueError('finite scalar mode required')
    try:s=complex(s_per_s)
    except (ValueError,OverflowError) as exc:raise ValueError('mode outside float range') from exc
    finite(s);T=real(T_s,True);q=finite(s*T)
    try:
        if method=='exact':z=cmath.exp(q)
        elif method=='euler':z=1+q
        elif method=='backward':
            if 1-q==0:raise ValueError('singular backward mode')
            z=1/(1-q)
        elif method=='bilinear':
            if 1-q/2==0:raise ValueError('singular bilinear mode')
            z=(1+q/2)/(1-q/2)
        else:raise ValueError('unknown mode map')
    except OverflowError as exc:raise ValueError('mode overflow') from exc
    return finite(z)


def prewarp(theta_rad_sample,T_s=.00025):
    theta=real(theta_rad_sample);T=real(T_s,True)
    if not -math.pi<theta<math.pi:raise ValueError('principal digital frequency must be strictly inside +/-pi')
    return finite((2/T)*math.tan(theta/2))


@dataclass(frozen=True)
class Format:
    """Signed W-bit code times 2^-F; caller declares volts or unitless coefficient."""
    bits:int=16
    fraction:int=14
    def __post_init__(self):
        if type(self.bits) is not int or type(self.fraction) is not int or not 2<=self.bits<=32 or not 0<=self.fraction<self.bits:raise ValueError('integer 2<=W<=32, 0<=F<W required')
    @property
    def scale(self):return 1<<self.fraction
    @property
    def low(self):return -(1<<(self.bits-1))
    @property
    def high(self):return (1<<(self.bits-1))-1
    def code(self,value):
        if type(value) is not int or not self.low<=value<=self.high:raise ValueError('signed code outside format')
        return value
    def encode(self,value):
        value=real(value);value=max(self.low/self.scale,min(self.high/self.scale,value))
        return round(value*self.scale)
    def decode(self,code):return self.code(code)/self.scale
    def narrow(self,code,overflow='saturate'):
        if type(code) is not int:raise ValueError('integer required')
        if overflow=='saturate':return max(self.low,min(self.high,code))
        if overflow=='wrap':return (code-self.low)%(1<<self.bits)+self.low
        raise ValueError('overflow must be saturate or wrap')


def round_divide(numerator,denominator,rounding='nearest_even'):
    """Exact signed integer rescaling, with tie handling independent of float."""
    if type(numerator) is not int or type(denominator) is not int or denominator<=0:raise ValueError('integer numerator/positive denominator required')
    sign=-1 if numerator<0 else 1;whole,remainder=divmod(abs(numerator),denominator)
    if rounding=='nearest_even':
        if 2*remainder>denominator or (2*remainder==denominator and whole%2):whole+=1
    elif rounding!='toward_zero':raise ValueError('unknown rounding')
    return sign*whole


def simulate_codes(input_codes,a_code,b_code,initial_code,fmt=Format(),rounding='nearest_even',overflow='saturate',accumulator_bits=None):
    """Exact multiply/add -> signed accumulator guard -> one round -> narrowing.

    Coefficients use the same fraction F; codes are preserved initial and n+1.
    Python integers compute the oracle exactly; guard represents chosen hardware
    accumulator range, not the actual host's integer storage.
    """
    if not isinstance(fmt,Format):raise ValueError('Format required')
    fmt.code(a_code);fmt.code(b_code);state=fmt.code(initial_code);result=[state]
    # Validate policies even for an empty input list.
    round_divide(0,fmt.scale,rounding);fmt.narrow(0,overflow)
    width=2*fmt.bits+1 if accumulator_bits is None else accumulator_bits
    if type(width) is not int or not 2<=width<=128:raise ValueError('accumulator width 2..128 required')
    lower=-(1<<(width-1));upper=(1<<(width-1))-1
    for input_code in input_codes:
        u=fmt.code(input_code);accumulator=a_code*state+b_code*u
        if not lower<=accumulator<=upper:raise OverflowError('declared accumulator overflow')
        state=fmt.narrow(round_divide(accumulator,fmt.scale,rounding),overflow);result.append(state)
    return result


def fir_codes(input_codes,coefficient_codes,fmt=Format(),rounding='nearest_even',overflow='saturate',accumulator_bits=None):
    """Nonrecursive tapped delay line, zero history, one output per input sample."""
    if not isinstance(fmt,Format):raise ValueError('Format required')
    coefficients=[fmt.code(x) for x in coefficient_codes]
    if not coefficients:raise ValueError('at least one FIR tap required')
    inputs=[fmt.code(x) for x in input_codes];round_divide(0,fmt.scale,rounding);fmt.narrow(0,overflow)
    width=2*fmt.bits+math.ceil(math.log2(len(coefficients)))+1 if accumulator_bits is None else accumulator_bits
    if type(width) is not int or not 2<=width<=128:raise ValueError('accumulator width 2..128 required')
    lower=-(1<<(width-1));upper=(1<<(width-1))-1;result=[]
    for n in range(len(inputs)):
        accumulator=sum(c*inputs[n-j] for j,c in enumerate(coefficients) if n>=j)
        if not lower<=accumulator<=upper:raise OverflowError('declared accumulator overflow')
        result.append(fmt.narrow(round_divide(accumulator,fmt.scale,rounding),overflow))
    return result

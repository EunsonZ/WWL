---
type: reference
domain: mathematics
stage: 3
content_status: usable
evidence_status: partial
aliases: []
sources: []
prerequisites:
  - "[[数学/60-数值计算与量化/84-梯度流离散与精度复算]]"
---

# test_gradient_flow_precision_lab 源码镜像

本块供阅读与正式 code-sync 检查；规范真源是上一级 [test_gradient_flow_precision_lab.py](../test_gradient_flow_precision_lab.py)。修改时同步真源与本块。运行方法和证据范围见 [[数学/60-数值计算与量化/84-梯度流离散与精度复算|复算页]]。

<!-- code-sync: ../test_gradient_flow_precision_lab.py -->
```python
"""Independent identities and observed failure cases for the same-object lesson."""
from fractions import Fraction as F
import unittest
import numpy as np
import gradient_flow_precision_lab as lab


class GradientFlowPrecisionTests(unittest.TestCase):
    def test_real_closed_form_against_rational_update_and_one_step(self):
        state=lab.INITIAL
        h=F(1,10)
        for k in range(13):
            self.assertEqual(lab.real_gd(h,k),state)
            state=tuple(a-h*lam*a for a,lam in zip(state,lab.CURVATURE))
        self.assertEqual(lab.real_gd(h,1),(F(9,5),F(0)))
        self.assertEqual(lab.real_gd(h,0),lab.INITIAL)

    def test_stable_is_not_accurate_or_same_decision(self):
        np.testing.assert_allclose(lab.ode(0),[2,.6],rtol=0,atol=0)
        real=np.asarray(lab.real_gd(F(1,10),10),dtype=float)
        truth=lab.ode(1)
        self.assertGreater(np.linalg.norm(real-truth),.03)
        self.assertLess(real[0],.72)
        self.assertGreater(truth[0],.72)
        # Smooth exact solution has a positive one-step defect in each coordinate.
        self.assertTrue(np.all(lab.ode(.1)-np.asarray(lab.real_gd(F(1,10),1),dtype=float)>0))

    def test_fixed_T_first_order_before_rounding_dominates(self):
        errors=[np.linalg.norm(np.asarray(lab.real_gd(F(1,n),n),dtype=float)-lab.ode(1)) for n in [40,80,160]]
        for a,b in zip(errors,errors[1:]):
            self.assertGreater(a/b,1.99)
            self.assertLess(a/b,2.03)

    def test_zero_coordinate_hides_unstable_mode(self):
        initial=(F(2),F(0))
        perturbed=(F(2),F(1,10**6))
        a=lab.real_gd(F(1,4),12,initial)
        b=lab.real_gd(F(1,4),12,perturbed)
        self.assertEqual(a[1],0)
        self.assertEqual(b[1]/perturbed[1],F(3,2)**12)
        self.assertGreater(abs(b[1]),abs(perturbed[1]))

    def test_small_step_normal_value_stagnation(self):
        path=lab.rounded_gd(F(1,10000),10000,np.float16)
        self.assertEqual(path.dtype,np.dtype(np.float16))
        self.assertTrue(np.all(path[:,0]==2))
        # x=2 is normal, so this failure precedes subnormal underflow.
        self.assertGreater(2,np.finfo(np.float16).tiny)
        predecessor=np.nextafter(np.float16(2),np.float16(0))
        delta=np.float16(np.float16(.0001)*np.float16(2))
        self.assertLess(float(delta),(2-float(predecessor))/2)
        self.assertGreater(float(delta),0)
        self.assertLess(float(lab.real_gd(F(1,10000),10000)[0]),.74)

    def test_finite_nonzero_gradient_can_be_a_fixed_state(self):
        for dtype,steps in [(np.float16,400),(np.float32,1600)]:
            path=lab.rounded_gd(F(1,10),steps,dtype)
            self.assertTrue(np.all(np.isfinite(path)))
            np.testing.assert_array_equal(path[-1],path[-2])
            self.assertGreater(float(path[-1,0]),0)
            gradient=np.multiply(np.asarray([1,10],dtype=dtype),path[-1],dtype=dtype)
            delta=np.multiply(np.asarray(.1,dtype=dtype),gradient,dtype=dtype)
            self.assertGreater(float(gradient[0]),0)
            np.testing.assert_array_equal(delta,[0,0])
        self.assertGreater(float(lab.rounded_gd(F(1,10),400,np.float16)[-1,0]),1e-8)
        self.assertLess(float(lab.real_gd(F(1,10),400)[0]),1e-8)

    def test_joint_curvature_precision_time_migration(self):
        c=(F(1),F(100))
        a=lab.rounded_gd(F(1,4000),4000,np.float32,curvature=c)[-1].astype(float)
        self.assertLess(np.linalg.norm(a-lab.ode(1,curvature=c)),1e-4)
        b=lab.rounded_gd(F(1,100),4000,np.float16,curvature=c)[-1].astype(float)
        d=lab.rounded_gd(F(1,100),4000,np.float32,curvature=c)[-1].astype(float)
        self.assertGreater(np.linalg.norm(b),1e-8)
        self.assertLess(np.linalg.norm(d),1e-8)

    def test_invalid_input_is_rejected(self):
        for h,steps in [(F(0),2),(F(-1),2),(float('nan'),2),(F(1,10),-1),(F(1,10),2.5),(F(1,10),True)]:
            with self.assertRaises(ValueError):lab.rounded_gd(h,steps,np.float16)
        for initial,curvature in [([1],[1,10]),([2,.6],[1,-10]),([2,float('inf')],[1,10])]:
            with self.assertRaises(ValueError):lab.rounded_gd(F(1,10),2,np.float32,initial,curvature)
        with self.assertRaises(ValueError):lab.rounded_gd(F(1,10),2,np.float64)
        with self.assertRaises(ValueError):lab.ode(-1)
        with self.assertRaises(TypeError):lab.real_gd(.1,2)
        with self.assertRaises(ValueError):lab.rounded_gd(F(1,10**100),2,np.float16)


if __name__=='__main__':unittest.main()
```

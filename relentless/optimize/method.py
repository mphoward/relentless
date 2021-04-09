"""
Algorithms
==========

An optimization algorithm seeks to determine the minima of a defined objective
function, subject to design constraints.

The following optimization algorithms have been implemented:

.. autosummary::
    :nosignatures:

    FixedStepDescent
    SteepestDescent

.. rubric:: Developer notes

To implement your own optimization algorithm, create a class that derives from
:class:`Optimizer` and define the required properties and methods.

.. autosummary::
    :nosignatures:

    Optimizer
    LineSearch

.. autoclass:: Optimizer
    :member-order: bysource
    :members: optimize,
        has_converged,
        abs_tol

.. autoclass:: LineSearch
    :member-order: bysource
    :members: find,
        rel_tol,
        max_iter

.. autoclass:: FixedStepDescent
    :member-order: bysource
    :members: descent_amount

.. autoclass:: SteepestDescent
    :member-order: bysource
    :members: descent_amount,
        optimize,
        max_iter,
        step_size,
        scale,
        line_search

"""
import abc

import numpy as np

from relentless import _collections
from .objective import ObjectiveFunction

class Optimizer(abc.ABC):
    """Abstract base class for optimization algorithm.

    A :class:`Optimizer` defines the optimization algorithm with specified parameters.

    Parameters
    ----------
    abs_tol : float or dict
        The absolute tolerance or tolerances (keyed on the :class:`~relentless.optimize.objective.ObjectiveFunction`
        design variables).

    """
    def __init__(self, abs_tol):
        self.abs_tol = abs_tol

    @abc.abstractmethod
    def optimize(self, objective):
        """Minimize an objective function.

        The design variables of the objective function are adjusted until convergence
        (see :meth:`has_converged()`).

        Parameters
        ----------
        objective : :class:`~relentless.optimize.objective.ObjectiveFunction`
            The objective function to be optimized.

        """
        pass

    def has_converged(self, result):
        """Check if the convergence criteria is satisfied.

        The absolute value of the gradient for each design variable of the objective
        function must be less than the absolute tolerance for that variable.

        Parameters
        ----------
        result : :class:`~relentless.optimize.objective.ObjectiveFunctionResult`
            The computed value of the objective function.

        Returns
        -------
        bool
            ``True`` if the criteria is satisfied.

        Raises
        ------
        KeyError
            If the absolute tolerance value is not set for all design variables.
        """
        for x in result.design_variables:
            grad = result.gradient[x]
            try:
                tol = self.abs_tol[x]
            except TypeError:
                tol = self.abs_tol
            except KeyError:
                raise KeyError('Absolute tolerance not set for design variable ' + str(x))
            if abs(grad) > tol:
                return False

        return True

    @property
    def abs_tol(self):
        """float or dict: The absolute tolerance(s). Must be non-negative."""
        return self._abs_tol

    @abs_tol.setter
    def abs_tol(self, value):
        try:
            abs_tol = dict(value)
            err = any([tol < 0 for tol in value.values()])
        except TypeError:
            abs_tol = value
            err = value < 0
        if err:
            raise ValueError('Absolute tolerances must be non-negative.')
        else:
            self._abs_tol = abs_tol

class LineSearch:
    r"""Line search algorithm.

    Given an :class:`~relentless.optimize.objective.ObjectiveFunction` :math:`f\left(\mathbf{x}\right)`
    and a search interval defined as :math:`\mathbf{d}=\mathbf{x}_{end}-\mathbf{x}_{start}`,
    the line search algorithm seeks an optimal step size :math:`0<\alpha<1` such
    that the following quantity is minimized:

    .. math::

        f\left(\mathbf{x}_{start}+\alpha\mathbf{d}\right)

    This is done by defining a scalar "target" value :math:`t` as:

    .. math::

        t = -\mathbf{d} \cdot \nabla{f\left(\mathbf{x}\right)}

    With an input relative tolerance value :math:`c`, the tolerance is defined as:

    .. math::

        c\lvert t_{start} \rvert

    where :math:`t_{start}` is the target value at the start of the search interval.

    Because :math:`\mathbf{d}` is a descent direction, the target at the
    start of the search interval is always positive. If the target is positive
    (or within the tolerance) at the end of the search interval, then the maximum
    step size is acceptable and the algorithm steps to the end of the search
    interval. If the target is negative (outside of the tolerance) at the end of
    the search interval, then the algorithm iteratively computes a new step size
    by linear interpolation within the search interval until the target at the
    new location is minimized to within the tolerance.

    Note: This algorithm applies the
    `strong Wolfe condition on curvature <https://wikipedia.org/wiki/Wolfe_conditions#Strong_Wolfe_condition_on_curvature>`_.

    Parameters
    ----------
    rel_tol : float
        The relative tolerance for the target (:math:`c`).
    max_iter : int
        The maximum number of line search iterations allowed.

    """
    def __init__(self, rel_tol, max_iter):
        self.rel_tol = rel_tol
        self.max_iter = max_iter

    def find(self, objective, start, end):
        """Apply the line search algorithm to take the optimal step.

        Note that the objective function is kept at its initial state, and the
        function evaluted after taking the optimal step is returned separately.

        Parameters
        ----------
        objective : :class:`~relentless.optimize.objective.ObjectiveFunction`
            The objective function for which the line search is applied.
        start : :class:`~relentless.optimize.objective.ObjectiveFunctionResult`
            The objective function evaluated at the start of the search interval.
        end : :class:`~relentless.optimize.objective.ObjectiveFunctionResult`
            The objective function evaluated at the end of the search interval.

        Raises
        ------
        ValueError
            If the start and the end of the search interval are identical.
        ValueError
            If the defined search interval is not a descent direction.

        Returns
        -------
        :class:`~relentless.optimize.objective.ObjectiveFunctionResult`
            The objective function evaluated at the new, "optimal" location.

        """
        ovars = {x: x.value for x in objective.design_variables()}

        # compute search direction
        d = end.design_variables - start.design_variables
        if d.norm() == 0:
            raise ValueError('The start and end of the search interval must be different.')

        # compute start and end target values
        targets = np.array([-d.dot(start.gradient), -d.dot(end.gradient)])
        if targets[0] < 0:
            raise ValueError('The defined search interval must be a descent direction.')

        # compute tolerance
        tol = self.rel_tol*np.abs(targets[0])

        # check if max step size acceptable, else iterate to minimize target
        if targets[1] > 0 or np.abs(targets[1]) < tol:
            result = end
        else:
            steps = np.array([0., 1.])
            iter_num = 0
            new_target = np.inf
            new_res = targets[1]
            while np.abs(new_target) >= tol and iter_num < self.max_iter:
                # linear interpolation for step size
                new_step = (steps[0]*targets[1] - steps[1]*targets[0])/(targets[1] - targets[0])

                # adjust variables based on new step size, compute new target
                for x in ovars:
                    x.value = start.design_variables[x] + new_step*d[x]
                new_res = objective.compute()
                new_target = -d.dot(new_res.gradient)

                # update search intervals
                if new_target > 0:
                    steps[0] = new_step
                    targets[0] = new_target
                else:
                    steps[1] = new_step
                    targets[1] = new_target

                iter_num += 1

            result = new_res

        for x in ovars:
            x.value = ovars[x]
        return result

    @property
    def rel_tol(self):
        """float: The relative tolerance for the target. Must be in the range :math:`0<c<1`."""
        return self._abs_tol

    @rel_tol.setter
    def rel_tol(self, value):
        try:
            if value <= 0 or value >= 1:
                raise ValueError('The absolute tolerance must be between 0 and 1.')
            else:
                self._abs_tol = value
        except TypeError:
            raise TypeError('The absolute tolerance must be a scalar float.')

    @property
    def max_iter(self):
        """int: The maximum number of line search iterations allowed."""
        return self._max_iter

    @max_iter.setter
    def max_iter(self, value):
        if not isinstance(value, int):
            raise TypeError('The maximum number of iterations must be an integer.')
        if value < 1:
            raise ValueError('The maximum number of iterations must be positive.')
        self._max_iter = value

class SteepestDescent(Optimizer):
    r"""Steepest descent algorithm.

    For an :class:`~relentless.optimize.objective.ObjectiveFunction` :math:`f\left(\mathbf{x}\right)`,
    the steepest descent algorithm seeks to approach a minimum of the function.

    The optimization is performed using scaled variables :math:`\mathbf{y}`.
    Define :math:`\mathbf{X}` as the scaling parameters for each variable such
    that :math:`y_i=\frac{x_i}{X_i}`. (A variable can be left unscaled by setting
    :math:`X_i=1`).

    Define :math:`\alpha` as the descent step size hyperparameter. A :class:`LineSearch`
    can optionally be performed to optimize the value of :math:`\alpha` between
    :math:`0` and the input value.

    The function is iteratively minimized by taking successive steps down the
    gradient of the functional. If the scaled variables are :math:`\mathbf{y}_n`
    at iteration :math:`n`, the next value of the variables is:

    .. math::

        \mathbf{y}_{n+1} = \mathbf{y}_n-\alpha\nabla f\left(\mathbf{y}\right)

    The gradient of the function with respect to the scaled variables is:

    .. math::

        \nabla f\left(\mathbf{y}\right) = \left[X_1 \frac{\partial f}{\partial x_1},
                                                      \cdots,
                                                X_n \frac{\partial f}{\partial x_n}\right]

    Note that this optimization procedure is equivalent to:

    .. math::

        \left(x_i\right)_{n+1} = \left(x_i\right)_n-\alpha{X_i}^2 \frac{\partial f}{\partial x_i}

    for each unscaled design variable :math:`x_i`.

    Parameters
    ----------
    abs_tol : float or dict
        The absolute tolerance or tolerances keyed on the
        :class:`~relentless.optimize.objective.ObjectiveFunction` design variables.
        The tolerance is defined on the `scaled gradient`.
    max_iter : int
        The maximum number of optimization iterations allowed.
    step_size : float
        The step size hyperparameter (:math:`\alpha`).
    scale : float or dict
        A scalar scaling parameter or scaling parameters (:math:`\mathbf{X}`)
        keyed on one or more :class:`~relentless.optimize.objective.ObjectiveFunction`
        design variables (defaults to ``1.0``, so that the variables are unscaled).
    line_search : :class:`LineSearch`
        The line search object used to find the optimal step size, using the
        specified step size value as the "maximum" step size (defaults to ``None``).

    """
    def __init__(self, abs_tol, max_iter, step_size, scale=1.0, line_search=None):
        super().__init__(abs_tol)
        self.max_iter = max_iter
        self.step_size = step_size
        self.scale = scale
        self.line_search = line_search

    def descent_amount(self, gradient):
        r"""Calculate the descent amount for the optimization.

        The amount that each update descends down the scaled gradient is:

        .. math::

            \alpha

        Parameters
        ----------
        gradient : :class:`~relentless._collections.KeyedArray`
            The scaled gradient of the objective function.

        Returns
        -------
        :class:`~relentless._collections.KeyedArray`
            The descent amount, keyed on the objective function design variables.

        """
        k = _collections.KeyedArray(keys=gradient.keys)
        for i in k:
            k[i] = self.step_size
        return k

    def optimize(self, objective):
        r"""Perform the steepest descent optimization for the given objective function.

        If specified, a :class:`LineSearch` is performed to choose an optimal step size.

        Parameters
        ----------
        objective : :class:`~relentless.optimize.objective.ObjectiveFunction`
            The objective function to be optimized.

        Returns
        -------
        bool or None
            ``True`` if converged, ``False`` if not converged, ``None`` if no
            design variables are specified for the objective function.

        """
        dvars = objective.design_variables()
        if len(dvars) == 0:
            return None

        #fix scaling parameters
        scale = _collections.KeyedArray(keys=dvars)
        for x in dvars:
            if np.isscalar(self.scale):
                scale[x] = self.scale
            else:
                try:
                    scale[x] = self.scale[x]
                except KeyError:
                    scale[x] = 1.0

        iter_num = 0
        cur_res = objective.compute()
        while not self.has_converged(cur_res) and iter_num < self.max_iter:
            grad_y = scale*cur_res.gradient
            update = self.descent_amount(grad_y)*grad_y

            #steepest descent update
            for x in dvars:
                x.value = cur_res.design_variables[x] - update[x]
            next_res = objective.compute()

            #if line search, attempt backtracking in interval
            if self.line_search is not None:
                line_res = self.line_search.find(objective=objective, start=cur_res, end=next_res)
                for x in dvars:
                    x.value = line_res.design_variables[x]
                next_res = line_res

            #recycle next result
            cur_res = next_res
            iter_num += 1

        return self.has_converged(cur_res)

    @property
    def max_iter(self):
        """int: The maximum number of optimization iterations allowed."""
        return self._max_iter

    @max_iter.setter
    def max_iter(self, value):
        if not isinstance(value, int):
            raise TypeError('The maximum number of iterations must be an integer.')
        if value < 1:
            raise ValueError('The maximum number of iterations must be positive.')
        self._max_iter = value

    @property
    def step_size(self):
        r"""float: The step size hyperparameter (:math:`\alpha`). Must be positive."""
        return self._step_size

    @step_size.setter
    def step_size(self, value):
        if value <= 0:
            raise ValueError('The step size must be positive.')
        self._step_size = value

    @property
    def scale(self):
        r"""float or dict: A scalar scaling parameter or scaling parameters (:math:`\mathbf{X}`)
        keyed on one or more :class:`~relentless.optimize.objective.ObjectiveFunction`
        design variables. Must be positive."""
        return self._scale

    @scale.setter
    def scale(self, value):
        try:
            scale = dict(value)
            err = any([s <= 0 for s in value.values()])
        except TypeError:
            scale = value
            err = value <= 0
        if err:
            raise ValueError('The scaling parameters must be positive.')
        self._scale = scale

    @property
    def line_search(self):
        """:class:`LineSearch`: The line search object used to optimize the step size."""
        return self._line_search

    @line_search.setter
    def line_search(self, value):
        if value is not None and not isinstance(value, LineSearch):
            raise TypeError('If defined, the line search parameter must be a LineSearch object.')
        self._line_search = value

class FixedStepDescent(SteepestDescent):
    r"""Fixed-step steepest descent algorithm.

    This is a modification of :class:`SteepestDescent` in which the function is
    iteratively minimized by taking successive steps of fixed magnitude down
    the normalized gradient of the functional.

    If the scaled variables are :math:`\mathbf{y}_n` at iteration :math:`n`, the
    next value of the variables is:

    .. math::

        \mathbf{y}_{n+1} = \mathbf{y}_n
                          -\frac{\alpha}{\lVert\nabla f\left(\mathbf{y}\right)\rVert}\nabla f\left(\mathbf{y}\right)

    Parameters
    ----------
    abs_tol : float or dict
        The absolute tolerance or tolerances keyed on the
        :class:`~relentless.optimize.objective.ObjectiveFunction` design variables.
        The tolerance is defined on the `scaled gradient`.
    max_iter : int
        The maximum number of optimization iterations allowed.
    step_size : float
        The step size hyperparameter (:math:`\alpha`).
    scale : float or dict
        A scalar scaling parameter or scaling parameters (:math:`\mathbf{X}`)
        keyed on one or more :class:`~relentless.optimize.objective.ObjectiveFunction`
        design variables (defaults to ``1.0``, so that the variables are unscaled).
    line_search : :class:`LineSearch`
        The line search object used to find the optimal step size, using the
        specified step size value as the "maximum" step size (defaults to ``None``).

    """
    def __init__(self, abs_tol, max_iter, step_size, scale=1.0, line_search=None):
        super().__init__(abs_tol, max_iter, step_size, scale, line_search)

    def descent_amount(self, gradient):
        r"""Calculate the descent amount for the optimization.

        The amount that each update descends down the scaled gradient is:

        .. math::

            \frac{\alpha}{\lVert\nabla y\rVert}

        Parameters
        ----------
        gradient : :class:`~relentless._collections.KeyedArray`
            The scaled gradient of the objective function.

        Returns
        -------
        :class:`~relentless._collections.KeyedArray`
            The descent amount, keyed on the objective function design variables.

        """
        k = _collections.KeyedArray(keys=gradient.keys)
        for i in k:
            k[i] = self.step_size
        return k/gradient.norm()

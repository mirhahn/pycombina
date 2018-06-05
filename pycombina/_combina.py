# -*- coding: utf-8 -*-
#
# This file is part of pycombina.
#
# Copyright 2017-2018 Adrian Bürger, Clemens Zeile, Sebastian Sager, Moritz Diehl
#
# pycombina is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pycombina is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pycombina. If not, see <http://www.gnu.org/licenses/>.

import os
import time
import numpy as np

class Combina():


    @property
    def t(self):

        '''Discrete time points.'''

        return self._t


    @property
    def b_rel(self):

        '''Relaxed binary controls.'''

        return self._b_rel


    @property
    def tol(self):

        '''If a value b_rel,k,i is smaller than tol it is considered 0, if it is bigger than 1-tol it is considered 1.'''

        return self._tol


    @property
    def n_b(self):

        '''Number of discrete values per control.'''

        return self._n_b


    @property
    def n_c(self):

        '''Number of mutually exclusive controls.'''

        return self._n_c


    @property
    def max_switches(self):

        '''Maximum possible amount of switches per control.'''

        try:
            return self._max_switches

        except AttributeError:
           raise AttributeError("max_switches not yet available, call solve() first.")


    @property
    def dt(self):

        '''Duration between sequent time points.'''

        try:

            return self._dt

        except AttributeError:
           raise AttributeError("dt not yet available, call solve() first.")


    @property
    def eta(self):

        '''Objective value of the combinatorial integral approximation problem.'''

        try:
            return self._eta

        except AttributeError:
           raise AttributeError("eta not yet available, call solve() first.")


    @property
    def b_bin(self):

        '''Binary controls obtained from the solution of the combinatorial integral approximation problem.'''

        try:
            return self._b_bin

        except AttributeError:
           raise AttributeError("b_bin not yet available, call solve() first.")


    def _check_if_prompt_init_messages(self):

        try:
        
            if os.environ["PYCOMBINA_PROMPTS_SHOWN"] == "True":
                
                self._prompt_init_messages = False
        
        except KeyError:
            
            os.environ["PYCOMBINA_PROMPTS_SHOWN"] = "True"
            self._prompt_init_messages = True
            


    def _welcome_prompt(self):

        if self._prompt_init_messages:

            print("\n-----------------------------------------------------------")
            print("|                                                         |")
            print("|                      You're using                       |")
            print("|                                                         |")
            print("|    pycombina -- Combinatorial Integral Approximation    |")
            print("|                                                         |")
            print("|       by A. Buerger, C. Zeile, S. Sager, M. Diehl       |")
            print("|                                                         |")
            print("-----------------------------------------------------------\n")


    def _check_available_solvers(self):

        self._available_solvers = {}

        try:
            from _combina_bnb_solver import CombinaBnBSolver
            self._available_solvers["bnb"] = CombinaBnBSolver
        except ImportError:
            if self._prompt_init_messages:
                print("- pycombina C++ extension not built, BnB solver disabled.")

        try:
            import pyscipopt
            from _combina_milp_solver import CombinaScipSolver
            self._available_solvers["scip"] = CombinaScipSolver
        except ImportError:
            if self._prompt_init_messages:
                print("- pyscipopt not found, SCIP solver disabled.")

        try:
            import gurobipy
            from _combina_milp_solver import CombinaGurobiSolver
            self._available_solvers["gurobi"] = CombinaGurobiSolver
        except ImportError:
            if self._prompt_init_messages:
                print("- gurobipy not found, Gurobi solver disabled.")

        if not self._available_solvers:
            raise RuntimeError("No solvers available for pycombina.")


    def _initialize_combina(self):

        self._check_if_prompt_init_messages()
        self._welcome_prompt()
        self._check_available_solvers()


    def _validate_input_dimension_t(self):

        self._t = np.squeeze(self._t)

        if not self._t.ndim == 1:

                raise ValueError("Input t must be a vector.")


    def _validate_input_dimension_b_rel(self):

        self._b_rel = np.atleast_2d(self._b_rel)

        if not self._b_rel.shape[1] == self._t.size-1:

            self._b_rel = self._b_rel.T

        if not self._b_rel.shape[1] == self._t.size-1:

            raise ValueError("One dimension of b_rel must be |t|-1.")


    def _validate_input_values_t(self):

        if not np.all((self._t[1:] - self._t[:-1]) > 0):

            raise ValueError("Values in t must be strictly increasing.")


    def _validate_input_values_b_rel(self):

        if not (np.all(self._b_rel >= 0) and np.all(self._b_rel <= 1)):

            raise ValueError("All elements of the relaxed binary input must be 0 <= b <= 1.")


    def _validate_input_values(self):

        self._validate_input_values_t()
        self._validate_input_values_b_rel()


    def _validate_input_dimensions(self):

        self._validate_input_dimension_t()
        self._validate_input_dimension_b_rel()


    def _validate_input_data(self):

        self._validate_input_dimensions()
        self._validate_input_values()


    def _round_input_data_to_tolerance(self):

        self.b_rel[self.b_rel < self._tol] = 0
        self.b_rel[self.b_rel > 1.0-self._tol] = 1


    def _determine_number_of_control_intervals(self):

        self._n_b = self._t.size - 1


    def _determine_number_of_controls(self):

        self._n_c = self._b_rel.shape[0]


    def _compute_time_grid_from_time_points(self):

        self._dt = self._t[1:] - self._t[:-1]


    def __init__(self, t, b_rel, tol = 1e-4):

        r'''
        :raises: ValueError, RuntimeError

        :param t: One-dimensional array that contains the discrete time points
                  of the combinatorial integral approximation problem. The
                  values in t must be strictly increasing.
        :type t: numpy.ndarray

        :param b_rel: Two-dimensional array that contains the relaxed binary
                      controls to be approximated. One dimension of the array
                      must be of size |t|-1 and all entries of the array 
                      must be 0 <= b_k,i <= 1.
        :type b_rel: numpy.ndarray

        :param tol: If a value b_rel,k,i is smaller than tol it is considered 0,
                    and if it is bigger than 1-tol it is considered 1.
        :type tol: float

        Specifies a combinatorial integral approximation problem.

        '''

        self._initialize_combina()

        self._t = t
        self._b_rel = b_rel
        self._tol = tol

        self._validate_input_data()
        self._round_input_data_to_tolerance()
        self._determine_number_of_controls()
        self._determine_number_of_control_intervals()


    def _raise_error_if_reduced_problem(self):

        if hasattr(self, "_t_orig") or hasattr(self, "_inactive_controls"):

            raise NotImplementedError('''
Locking the initial binary control sequence for a reduced problem is not possible
yet. Please lock the control sequence first, and then reduce the problem.
''')


    def _raise_error_if_already_locked(self):

        if hasattr(self, "_t_orig") or hasattr(self, "_inactive_controls"):

            raise NotImplementedError("The initial binary control sequence has already been locked.")


    def _validate_input_dt_lock(self, dt_lock):

        try:
            self._dt_lock = float(dt_lock)

        except ValueError, TypeError:
            raise ValueError("Input dt_lock must be a scalar value.")


    def _validate_input_b_bin_lock(self, b_bin_lock):

        try:

            if not np.atleast_1d(np.squeeze(b_bin_lock)).ndim == 1:
                raise ValueError

            b_bin_lock = list(np.atleast_1d(np.squeeze(b_bin_lock)))
            b_bin_lock = [int(b) for b in b_bin_lock]

            if not len(b_bin_lock) == self._n_c:
                raise ValueError

        except ValueError:
            raise ValueError("The number of values in b_bin_lock must be equal to the number of binary controls.")

        if not np.all(np.isin(b_bin_lock, [0, 1])):

            raise ValueError("All elements of b_bin_lock must be either 0 or 1.")

        self._b_bin_lock = np.atleast_2d(b_bin_lock)


    def _lock_initial_binary_sequence(self):

        self._t_locked = self._t[self._t < self._dt_lock]

        self._b_rel = self._b_rel[:, self._t[:-1] >= self._dt_lock]
        self._t =  self._t[self._t >= self._dt_lock]

        print "Using new version!"


    def lock_initial_binary_sequence(self, dt_lock, b_bin_lock):

        r'''
        :raises: NotImplementedError

        :param dt_lock: Specifies the duration of the locked initial sequence.
        :type dt_lock: float

        :param b_bin_lock: Array of binary values that specifies the values
                             of the controls over the locked initial sequence.
        :type b_bin_lock: list, numpy.ndarray

        This function can be used to lock the binary values of the solution,
        of the combinatorial integral approximation problem, starting from the
        initial time point and for all time points <= dt_lock, to a certain
        configuration b_bin_lock.

        This functionality is necessary to, e. g., preserve compliance with
        required min-up-times within MPC applications.

        '''

        print ("\n- Locking initial binary sequence ...")

        self._raise_error_if_reduced_problem()
        self._raise_error_if_already_locked()
        self._validate_input_dt_lock(dt_lock)
        self._validate_input_b_bin_lock(b_bin_lock)
        self._lock_initial_binary_sequence()
        self._determine_number_of_control_intervals()

        print ("  Locked the values of the binary solution to be \n    " \
            + str(self._b_bin_lock)) + " for all time points < " + str(self._dt_lock)


    def _remove_controls(self):

        self._inactive_controls = []

        for k, b_rel_k in enumerate(self._b_rel):

            if np.all(b_rel_k == 0):

                self._inactive_controls.append(k)

        self._active_controls = [idx for idx in range(self._n_c) if idx not in self._inactive_controls]

        self._b_rel = self._b_rel[self._active_controls, :]


    def _remove_inactive_controls(self):

        print ("\n  - Removing inactive controls ...")

        self._remove_controls()
        self._determine_number_of_controls()

        print ("    Removed "+ str(len(self._inactive_controls)) + " inactive control(s).")


    def _reduce_nodes(self):

        if not hasattr(self, "_t_orig"):

            self._t_orig = self._t
            self._b_rel_orig = self._b_rel

        idx_b_rel_reduced = np.ones((self._n_b,), dtype = bool)

        for k in range(self._n_b-5):

            if np.all(np.isin(self._b_rel[:,k:k+5], [0, 1])):

                if np.all(np.all(self._b_rel[:,k:k+5] == \
                    np.atleast_2d(self._b_rel[:,k]).T, axis=1)):

                    if np.all(idx_b_rel_reduced[k+1] == True):
                        
                        idx_b_rel_reduced[k+2] = False


        self._t = np.append(self._t[:-1][idx_b_rel_reduced], self._t[-1])
        self._b_rel = self._b_rel[:, idx_b_rel_reduced]


    def _print_node_reduction_info(self):

        previous_size = self._n_b
        new_size = self._b_rel.shape[1]

        print("    Node count reduced from " + str(previous_size) + " to " + \
            str(new_size) + " (" + str(round(float(new_size - previous_size)/(previous_size), 2) * 100.0) + " %)")


    def _reduce_node_count(self):

        reduce_count = True
        count = 0

        print ("\n  - Reducing node count ...")

        while reduce_count:

            self._reduce_nodes()
            self._print_node_reduction_info()

            reduce_count = (self._n_b > self._b_rel.shape[1])

            self._determine_number_of_control_intervals()


    def reduce_problem_size(self):

        r'''

        This function reduces the problem size in order to facilitate lower
        computation times and memory consumption by doing the following:

        1.) Reduction of number of controls
            Controls that are inactive during the whole time horizon
            are removed from the problem formulation.
        2.) Reduction of time grid size
            Successive time point with equal values for b_rel,k and all values
            b_rel,k = {0, 1} are grouped to reduced the time grid size.

        The values available after the solution of the integral approximation
        problem are automatically adjusted to match the original time grid and
        number of controls, again.

        '''

        print ("\n- Reducing problem size ...")

        t_start = time.time()

        self._remove_inactive_controls()
        self._reduce_node_count()

        t_end = time.time()

        print("\n  Problem size reduction finished after " + str(round(t_end - t_start, 5)) + " s")


    def _numpy_arrays_to_lists(self):

        # For now, the solver interfaces expect lists, so we need to convert
        # the numpy arrays accordingly

        self._t = self._t.tolist()
        self._b_rel = self._b_rel.tolist()
        self._dt = self._dt.tolist()


    def _lists_to_numpy_arrays(self):

        # For now, the solver interfaces return lists, so we need to convert
        # those into numpy arrays accordingly

        self._t = np.asarray(self._t)
        self._b_rel = np.asarray(self._b_rel)
        self._dt = np.asarray(self._dt)


    def _validate_max_switches_input(self, max_switches):

        try:
            if not np.atleast_1d(np.squeeze(max_switches)).ndim == 1:
                raise ValueError

            if hasattr(self, "_active_controls"):
                max_switches = list(np.asarray(max_switches)[self._active_controls])
            else:
                max_switches = list(np.asarray(max_switches))
            self._max_switches = [int(s) for s in max_switches]

            if not len(self._max_switches) == len(self._b_rel):
                raise ValueError

        except ValueError:
            raise ValueError("The number of integer values in max_switches must be equal to the number of binary controls.")


    def _validate_min_up_time_input(self, min_up_time):

        if not min_up_time:

           min_up_time = [0.0] * self._n_c

        try:

            if not np.atleast_1d(np.squeeze(min_up_time)).ndim == 1:
                raise ValueError

            if hasattr(self, "_active_controls"):
                min_up_time = list(np.asarray(min_up_time)[self._active_controls])
            else:
                min_up_time = list(np.asarray(min_up_time))
            self._min_up_time = [float(m) for m in min_up_time]

            if not len(self._min_up_time) == len(self._b_rel):
                raise ValueError

        except ValueError:
            raise ValueError("The number of values in min_up_time must be equal to the number of binary controls.")


    def _solve_combinatorial_integral_approximation_problem(self, solver):

        if not np.all(np.isin(self._min_up_time, [0])) and solver is not "bnb":

            raise NotImplementedError("Min up times are only supported for solver bnb.")

        if hasattr(self, "_dt_lock") and solver is not "bnb":

            raise NotImplementedError("Locking of initial binary sequences is only supported for solver bnb.")

        try:

            init_active_control = np.where(np.squeeze(self._b_bin_lock) == 1)[0][0]

        except AttributeError:

            # if no control is initially active, set the value to n_c, which in
            # the bnb solver is interpreted as no initially active binary

            init_active_control = self._n_c

        try:
            self._solver = self._available_solvers[solver]( \
                self._dt, self._b_rel, self._n_c, self._n_b, init_active_control)

        except KeyError:
            raise ValueError("Unknown solver '" + solver + "', valid options are:\n" + \
                str(self._available_solvers.keys()))

        self._solver.run(max_switches = self._max_switches, min_up_time = self._min_up_time)


    def _retrieve_solution(self):

        self._eta = self._solver.get_eta()

        if not hasattr(self, "_t_orig"):

            self._b_bin = np.asarray(self._solver.get_b_bin())

        else:

            b_bin_reduced = np.asarray(self._solver.get_b_bin())
            self._b_bin = np.full(self._b_rel_orig.shape, np.nan)

            idx_b_bin_reduced = np.in1d(self._t_orig[:-1], self._t[:-1])
            self._b_bin[:, idx_b_bin_reduced] = b_bin_reduced

            for k, b_bin_k in enumerate(self._b_bin.T):

                if np.all(np.isnan(b_bin_k)):

                    self._b_bin[:,k] = self._b_bin[:,k-1]

        if hasattr(self, "_inactive_controls"):

            b_bin_all_controls = np.zeros((self._n_c + len(self._inactive_controls), self._b_bin.shape[1]))
            b_bin_all_controls[self._active_controls, :] = self._b_bin

            self._b_bin = b_bin_all_controls
            self._t = self._t_orig

        if hasattr(self, "_dt_lock"):

            self._t = np.concatenate([self._t_locked, self._t])
            self._b_bin = np.concatenate([np.repeat( \
                self._b_bin_lock, self._t_locked.size, 0).T, self._b_bin], 1)


    def solve(self, solver = 'bnb', max_switches = [2], min_up_time = None):

        r'''
        :raises: ValueError, NotImplementedError

        :param solver: Specifies which solver to use to solve the combinatorial
                       integral approximation problem. Possible options are:

                       * 'bnb' - solve using a custom Branch-and-Bound algorithm
                       * 'scip' - solve using a MILP formulation with SCIP
                       * 'gurobi' - solve using a MILP formulation with Gurobi

                       Availability of solvers depends on whether the necessary
                       libraries and Python interfaces are installed on your
                       system. Also, not all solver options are available
                       for all solvers.
        :type solver: str

        :param max_switches: Array of integer values that specifies the maximum
                             number of allowed switching actions per control.
        :type max_switches: list, numpy.ndarray

        :param min_up_time: Specifies the minimum time per control that must
                            pass in between two switching actions. If None,
                            no minimum time is considered.
        :type min_up_time: None, list, numpy.ndarray

        Solve the combinatorial integral approximation problem considering
        the specified options.

        '''

        self._compute_time_grid_from_time_points()
        self._numpy_arrays_to_lists()
        self._validate_max_switches_input(max_switches)
        self._validate_min_up_time_input(min_up_time)

        self._solve_combinatorial_integral_approximation_problem(solver)
        self._retrieve_solution()
        self._lists_to_numpy_arrays()
        self._determine_number_of_control_intervals()

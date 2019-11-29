import math
import statistics
import time

import numpy as np
from hmmlearn import hmm

from niq_misc import replace_entry

class HMM(object):
    """
        Houses parameters and functions pretaining to the hidden Markov model.

        Private Attributes:
            _hidden_states (set): hidden states in the model
            _initial (numpy array): initial state probabilities
            _trans_probs (dict of dicts): state transition probabilities
            _emissions (dict of dicts): state emission probabilities
            _dur_thresh (int): minimum duration (in data points) for a bout to be kept
    """ 

    def __init__(self):
        self._hidden_states = set([0, 1])
        self._initial = np.array((2, 0), dtype = float)
        self._trans_probs = {0: {}, 1: {}}
        self._emissions = {0: {}, 1: {}}
        self._dur_thresh = None

    def baum_welch(self, emis_array):
        """
            Determine ideal HMM parameters by the Baum Welch unsupervised learning algorithm.

            Args:
                emis_array (numpy array): vector of temperature change values
        """

        def set_params(self, model):
            """
                Converts HMM parameters from hmmlearn into a format compatable with the rest of NestIQ.

                Args:
                    model (hmmlearn.GaussianHMM)
            """

            self._initial = np.array([0.5, 0.5])

            self._trans_probs = {}
            self._trans_probs[0] = {}
            self._trans_probs[1] = {}

            self._trans_probs[0][0] = model.transmat_[0, 0]
            self._trans_probs[0][1] = model.transmat_[0, 1]
            self._trans_probs[1][1] = model.transmat_[1, 1]
            self._trans_probs[1][0] = model.transmat_[1, 0]

            self._emissions[0] = {}
            self._emissions[1] = {}
            self._emissions[0]["mean"] = model.means_[0][0]
            self._emissions[1]["mean"] = model.means_[1][0]
            self._emissions[0]["stdev"] = model.covars_[0][0][0]
            self._emissions[1]["stdev"] = model.covars_[1][0][0]

        model = hmm.GaussianHMM(n_components = 2, tol = 1e-100, n_iter = 1000, algorithm = "baum_welch")
        
        # Provide inital values
        model.startprob_ = np.array([0.5, 0.5])
        model.transmat_ = np.array([[0.98, 0.02],
                                    [0.02, 0.98]])
        model.means_ = np.array([[0.001], [-0.001]])
        model.covars_ = np.array([[0.001], [0.001]])

        model.fit(emis_array)
        set_params(self, model)

        if self._emissions[0]["mean"] > self._emissions[1]["mean"]:
            self.swap_params_by_state()

    def extract_params_from_verts(self, master_array, training_verts):
        """
            Transition and emission probabilites are derived from the user's placement of verticies.

            Args:
                master_array (numpy array)
                training_verts (list): vertex objects created off of the user's placements
        """

        master_array = self.add_states(master_array, training_verts)

        for state in self._hidden_states:
            self._emissions[state] = {}
            self._emissions[state]["mean"] = statistics.mean(row[5] for row in master_array if row[6] == state)
            self._emissions[state]["stdev"] = statistics.stdev(row[5] for row in master_array if row[6] == state)

        trans_probs = {outer_state: {inner_state: 0 for inner_state in self._hidden_states} for outer_state in self._hidden_states}

        prev_state = int(master_array[0, 6])
        for state in master_array[1:, 6]:
            trans_probs[prev_state][int(state)] += 1
            prev_state = state

        #Convert from counts to probabilites
        for outer_state in self._hidden_states:
            dict_sum = sum(trans_probs[outer_state].values())
            for inner_state in self._hidden_states:
                trans_probs[outer_state][inner_state] /= dict_sum

        self._trans_probs = trans_probs
        self.auto_dur_thresh(master_array)

        if self._emissions[0]["mean"] > self._emissions[1]["mean"]:
            self.swap_params_by_state()

    def swap_params_by_state(self):
        """
            Baum Welch identifies that there are two state but cannot tell which which corresponds to
            an on-bout and which corresponds to an off-bout. This function solves this problem by swapping
            parameters if necessary.
        """

        self._trans_probs[0][0], self._trans_probs[1][1] = self._trans_probs[1][1], self._trans_probs[0][0]
        self._trans_probs[0][1], self._trans_probs[1][0] = self._trans_probs[1][0], self._trans_probs[0][1]
        self._emissions[0]["mean"], self._emissions[1]["mean"] = self._emissions[1]["mean"], self._emissions[0]["mean"]
        self._emissions[0]["stdev"], self._emissions[1]["stdev"] = self._emissions[1]["stdev"], self._emissions[0]["stdev"]

    def auto_dur_thresh(self, master_array):
        """
            Automatically sets duration threshold based on smallest cluster of states in master_array.

            Args:
                master_array (numpy array)
        """

        counts = []
        cur_state = master_array[0, 6]
        count = 0

        for state in master_array[:, 6]:
            if state == cur_state:
                count += 1
            else:
                counts.append(count)
                count = 0
                cur_state = abs(cur_state - 1)

        self._dur_thresh = round(min(counts) / 4)

    def normalize_params(self, gui):
        """
            Normailizes the transisiton probabilites such that the transision probabilities from a given state
            sum to one.

            Args:
                gui (GUIClass)
        """

        self._initial = self._initial / np.sum(self._initial)
        trans_from_0_sum = sum(self._trans_probs[0].values())
        trans_from_1_sum = sum(self._trans_probs[1].values())
        self._trans_probs[0][0] /= trans_from_0_sum
        self._trans_probs[0][1] /= trans_from_0_sum
        self._trans_probs[1][0] /= trans_from_1_sum
        self._trans_probs[1][1] /= trans_from_1_sum

    def decode(self, master_array):
        """
            Assigns the most probable state value to each data point based on HMM parameters.

            Args:
                master_array (numpy array)
        """

        #Run viterbi to get expected states for each input data point
        results = list(self.viterbi(master_array))
        results = list(map(int, results))

        master_array = self.add_states(master_array, results_arr = np.array(results))
        return master_array

    def add_states(self, master_array, verts = None, results_arr = None):
        """
            Adds column 6 to master array: state (0 or 1).

            Args:
                master_array (numpy array)
                verts (list):
                resutls_arr (numpy array):
        """

        # Appends state values based on vertex locations
        if verts is not None:
            start = verts[0].index
            stop = verts[-1].index
            index_range = stop - start
            state_arr = np.zeros((index_range, 1), dtype = float)

            row = 0
            state = 1 # Assume on-bout start -- is corrected by "swap_params_by_state" if necessary
            prev_index = verts[0].index
            for curVert in verts[1:]:
                cur_index = curVert.index
                for _ in range(prev_index, cur_index):				
                    state_arr[row] = [state]
                    row += 1

                prev_index = cur_index
                state = 0 if state else 1

            master_array = np.hstack((master_array[start: stop, :], state_arr))

        # If results are provided, simply append states to master_array
        if results_arr is not None:
            master_array = np.hstack((master_array, results_arr.reshape(results_arr.shape[0], 1)))
        
        return master_array

    def viterbi(self, master_array):
        """ 
            Determines the most likly sequence of states given HMM parameters and a sequence of emission values.

            Args:
                master_array (numpy array)
        """

        def get_cumu_prob(self, state, val, mean = None, stdev = None, pseudocount = 1e-12):
            """
                Gets the cumulative probability for a temperature change occurring in a given state.

                Args:
                    state (int): 1 = on-bout, 0 = off-bout
                    val (float): temperature change from previous (emission)
                    mean (float): mean emission for this state
                    stdev (float): standard deviation for this state
                    pseudocount (float): default value if probability is 0 (avoids downstream errors)
            """

            if mean is None:
                mean = float(self._emissions[state]["mean"])

            if stdev is None:
                stdev = float(self._emissions[state]["stdev"])

            erf_input = ((val - mean) / (stdev * (2 ** 0.5)))
            erf_val = math.erf(erf_input)
            main_prob = (0.5 * (1 + erf_val)) if state == 1 else (1 - (0.5 * (1 + erf_val)))

            if main_prob == 0: main_prob = pseudocount
            return main_prob

        def get_traceback(traceback, last_origin):
            """
                Args:
                    traceback (list of dicts): holds "map" of optimal path through states
                    last_origin (int): starting state

                Returns:
                    tb (string): optimal sequence of states
            """

            tb = ''
            for pos in reversed(traceback):
                prev_origin = pos[int(last_origin)]
                tb += str(prev_origin)
                last_origin = prev_origin

            return tb

        def update_probs(row, previous):
            """
                Args:
                    row (numpy array): single row from master_array
                    previous (dict): probabilities corrisponding to each state possibility

                Returns:
                    next_prob (dict): probabilities corrisponding to transitions from each state
                    tb (dict): ideal state transition from this position
            """
            cur_prob = {}
            next_prob = {}
            tb = {}

            for next_state in self._hidden_states:
                for cur_state in self._hidden_states:
                    cur_prob[cur_state] = previous[cur_state] + np.log10(self._trans_probs[cur_state][next_state])

                origin = max(cur_prob, key = cur_prob.get)
                next_prob[next_state] = np.log10(get_cumu_prob(self, next_state, row[5])) + cur_prob[origin]
                tb[next_state] = origin

            return next_prob, tb

        traceback = []	
        first_row = master_array[0]

        #First set of probabilites are calculated differently
        previous = {}
        previous[0] = np.log10(self._initial[0]) + np.log10(get_cumu_prob(self, 0, first_row[5]))
        previous[1] = np.log10(self._initial[1]) + np.log10(get_cumu_prob(self, 1, first_row[5]))

        for row in master_array[1:, :]:
            update_previous, update_tb = update_probs(row, previous)
            previous = update_previous
            traceback.append(update_tb)

        result = str(max(previous, key = previous.get))
        result += get_traceback(traceback, result)
        
        return result[::-1]

    def build_model_from_entries(self, gui):
        """
            Sets hidden Markov model attributes based on values present in the GUI.

            Args:
                gui (GUIClass)
        """

        self._dur_thresh = float(gui.dur_thresh_E.get())

        self._initial[0] = float(gui.init_off_E.get())
        self._initial[1] = float(gui.init_on_E.get())

        self._trans_probs[0][0] = float(gui.off_off_trans_E.get())
        self._trans_probs[0][1] = float(gui.off_on_trans_E.get())
        self._trans_probs[1][0] = float(gui.on_off_trans_E.get())
        self._trans_probs[1][1] = float(gui.on_on_trans_E.get())

        self._emissions[0]["mean"] = float(gui.off_mean_E.get())
        self._emissions[1]["mean"] = float(gui.on_mean_E.get())
        self._emissions[0]["stdev"] = float(gui.off_stdev_E.get())
        self._emissions[1]["stdev"] = float(gui.on_stdev_E.get())

    def populate_hmm_entries(model, gui):
        """
            Fills out GUI entry boxes based on model attributes.

            Args:
                model (HMM)
                gui (GUIClass)
        """

        if model._dur_thresh is not None:
            replace_entry(gui.dur_thresh_E, int(model._dur_thresh))
            
        replace_entry(gui.init_off_E, round(model._initial[0], 7))
        replace_entry(gui.init_on_E, round(model._initial[1], 7))

        replace_entry(gui.off_off_trans_E, round(model._trans_probs[0][0], 7))
        replace_entry(gui.off_on_trans_E, round(model._trans_probs[0][1], 7))
        replace_entry(gui.on_off_trans_E, round(model._trans_probs[1][0], 7))
        replace_entry(gui.on_on_trans_E, round(model._trans_probs[1][1], 7))

        replace_entry(gui.off_mean_E, round(model._emissions[0]["mean"], 7))
        replace_entry(gui.on_mean_E, round(model._emissions[1]["mean"], 7))
        replace_entry(gui.off_stdev_E, round(model._emissions[0]["stdev"], 7))
        replace_entry(gui.on_stdev_E, round(model._emissions[1]["stdev"], 7))
import numpy as np
import traceback
import pylab as plt
# import spynnaker7.pyNN as sim
# import pyNN.spiNNaker as sim
import spynnaker8 as sim
from function_definitions import *
from argparser import *
from spynnaker8.extra_models import SpikeSourcePoissonVariable
# SpiNNaker setup
start_time = plt.datetime.datetime.now()

sim.setup(timestep=1.0, min_delay=1.0, max_delay=10)
sim.set_number_of_neurons_per_core(sim.IF_cond_exp, 256 // 10)
sim.set_number_of_neurons_per_core(sim.SpikeSourcePoisson, 256 // 5)
# +-------------------------------------------------------------------+
# | General Parameters                                                |
# +-------------------------------------------------------------------+

# Population parameters
model = sim.IF_cond_exp

# Membrane
v_rest = -70  # mV
e_ext = 0  # V
v_thr = -54  # mV
g_max = 0.1
tau_m = 20  # ms
tau_ex = 5  # ms

cell_params = {'cm': 20.0,  # nF
               'i_offset': 0.0,
               'tau_m': 20.0,
               'tau_refrac': args.tau_refrac,
               'tau_syn_E': 5.0,
               'tau_syn_I': 15.0,
               'v_reset': -70.0,
               'v_rest': -70.0,
               'v_thresh': -50.0,
               'e_rev_E': 0.,
               'e_rev_I': -80.
               }

# +-------------------------------------------------------------------+
# | Rewiring Parameters                                               |
# +-------------------------------------------------------------------+
no_iterations = args.no_iterations  # iterations
simtime = no_iterations
# Wiring
n = 28
N_layer = n ** 2
# S = (n, n)
S = (n, n)
grid = np.asarray(S)

s_max = args.s_max
sigma_form_forward = args.sigma_form_ff
sigma_form_lateral = args.sigma_form_lat
p_form_lateral = args.p_form_lateral
p_form_forward = args.p_form_forward
p_elim_dep = args.p_elim_dep
p_elim_pot = args.p_elim_pot
f_rew = 10 ** 4  # Hz

# Inputs
f_mean = args.f_mean  # Hz
f_base = 5  # Hz
f_peak = 60  # Hz
sigma_stim = 2  # 2
t_stim = args.t_stim  # 20  # ms
t_record = args.t_record  # ms

# STDP
a_plus = 0.1
b = args.b
tau_plus = 20.  # ms
tau_minus = 20.  # ms
a_minus = (a_plus * tau_plus * b) / tau_minus

# Reporting

sim_params = {'g_max': g_max,
              't_stim': t_stim,
              'simtime': simtime,
              'f_base': f_base,
              'f_peak': f_peak,
              'f_mean': f_mean,
              'sigma_stim': sigma_stim,
              't_record': t_record,
              'cell_params': cell_params,
              'case': args.case,
              'grid': grid,
              's_max': s_max,
              'sigma_form_forward': sigma_form_forward,
              'sigma_form_lateral': sigma_form_lateral,
              'p_form_lateral': p_form_lateral,
              'p_form_forward': p_form_forward,
              'p_elim_dep': p_elim_dep,
              'p_elim_pot': p_elim_pot,
              'f_rew': f_rew,
              'lateral_inhibition': args.lateral_inhibition,
              'delay': args.delay,
              'b': b,
              't_minus': tau_minus,
              't_plus': tau_plus,
              'tau_refrac': args.tau_refrac,
              'a_minus': a_minus,
              'a_plus': a_plus,
              'input_type': args.input_type,
              'random_partner': args.random_partner,
              'lesion': args.lesion}
# +-------------------------------------------------------------------+
# | Initial network setup                                             |
# +-------------------------------------------------------------------+

stdp_model = sim.STDPMechanism(
    timing_dependence=sim.SpikePairRule(tau_plus=tau_plus, tau_minus=tau_minus, A_plus=a_plus, A_minus=a_minus),
    weight_dependence=sim.AdditiveWeightDependence(w_min=0, w_max=g_max),
    weight=g_max)  # A_plus=0.02, A_minus=0.02

partner_selection_last_neuron = sim.LastNeuronSelection()
formation_distance = sim.DistanceDependentFormation(grid=grid,  # spatial org of neurons
    sigma_form_forward=sigma_form_forward,  # spread of feadforward receptive field
    sigma_form_lateral=sigma_form_lateral,  # spread of lateral receptive field
    p_form_forward=p_form_forward,  # feedforward formation probability
    p_form_lateral=p_form_lateral)  # lateral formation probability

elimination_weight = sim.RandomByWeightElimination(threshold=g_max / 2.,  # Use same weight as initial weight for static connections
    prob_elim_depressed=p_elim_dep)

if args.case == CASE_CORR_AND_REW:
    structure_model_w_stdp = sim.StructuralMechanismSTDP(
        partner_selection_last_neuron, formation_distance, elimination_weight,# Partner selection, formation and elimination rules from above
        initial_weight=g_max, # Use this weight when creating a new synapse
        weight=g_max, # Use this weight for synapses at start of simulation
        initial_delay=args.delay, # Use this delay when creating a new synapse
        delay=args.delay, # Use this weight for synapses at the start of simulation
        s_max=s_max * 2, # Maximum allowed fan-in per target-layer neuron
        f_rew=f_rew, # Frequency of rewiring in Hz
        timing_dependence=sim.SpikePairRule(tau_plus=tau_plus, tau_minus=tau_minus, A_plus=a_plus, A_minus=a_minus),
        weight_dependence=sim.AdditiveWeightDependence(w_min=0, w_max=g_max),
        backprop_delay=False)

elif args.case == CASE_REW_NO_CORR or args.case == CASE_CORR_NO_REW:
    structure_model_w_stdp = sim.StructuralMechanismStatic(
        partner_selection_last_neuron, formation_distance, elimination_weight, # Partner selection, formation and elimination rules from above
        initial_weight=g_max, # Use this weight when creating a new synapse
        weight=g_max, # Use this weight for synapses at start of simulation
        initial_delay=args.delay, # Use this delay when creating a new synapse
        delay=args.delay, # Use this weight for synapses at the start of simulation
        s_max=s_max * 2, # Maximum allowed fan-in per target-layer neuron
        f_rew=f_rew, # Frequency of rewiring in Hz
        # NO STDP rules
    )
# else:
#     raise ValueError("I don't know what {} is supposed to do.".format(args.case))
# if not testing (i.e. training) construct 10 sources + 10 targets
# grouped into 2 columns
# For each source VRPSS load mnist rates from file
# Use the same initial connectivity for all sets of Populations
randomised_testing_numbers = None

number_of_slots = int(simtime / t_stim)
range_of_slots = np.arange(number_of_slots)
slots_starts = np.ones((N_layer, number_of_slots)) * (range_of_slots * t_stim)
durations = np.ones((N_layer, number_of_slots)) * t_stim

if not args.testing:

    source_column_on = []
    source_column_off = []
    ff_on_connections = []
    ff_off_connections = []
    target_column = []
    lat_connections = []

    if args.case == CASE_CORR_NO_REW:
        init_ff_on_connections = [(i, j, g_max, args.delay) for i in range(N_layer) for j in range(N_layer) if np.random.rand() < .1]
        init_lat_connections = []
    else:
        init_ff_on_connections = [(i, j, g_max, args.delay) for i in range(N_layer) for j in range(N_layer) if np.random.rand() < .01]
        init_lat_connections = [(i, j, g_max, args.delay) for i in range(N_layer) for j in range(N_layer) if np.random.rand() < .01]
    init_ff_off_connections = init_ff_on_connections
    for number in range(10):
        if not args.fixed_signal:
            rates_on, rates_off = load_mnist_rates('source_code/INPUT_FILES/averaged/', number, min_noise=f_mean/4.0, max_noise=f_mean/4.0, mean_rate=f_mean)
            # randomise input and allow for arbitrary simulation durations
            rates_on = rates_on.reshape(rates_on.shape[0], N_layer).T.astype(float)
            rates_off = rates_off.reshape(rates_off.shape[0], N_layer).T.astype(float)
            possible_indices = np.arange(rates_on.shape[1])
            choices = np.random.choice(possible_indices, number_of_slots, replace=True)
            final_rates_on = rates_on[:, choices]
            final_rates_off = rates_off[:, choices]
        else:
            rates_on, rates_off = load_mnist_rates('source_code/INPUT_FILES/averaged/', number, min_noise=0, max_noise=0,)
            # randomise input and allow for arbitrary simulation durations
            rates_on = rates_on.reshape(rates_on.shape[0], N_layer).T.astype(float)
            rates_off = rates_off.reshape(rates_off.shape[0], N_layer).T.astype(float)
            possible_indices = np.arange(rates_on.shape[1])
            choices = np.random.choice(possible_indices, number_of_slots, replace=True)
            rates_on_mask = (rates_on[:, choices] > 0).astype(float)
            rates_off_mask = (rates_off[:, choices] > 0).astype(float)
            final_rates_on = rates_on_mask * args.fixed_signal_value + f_base
            final_rates_off = rates_off_mask * args.fixed_signal_value + f_base

        source_column_on.append(
            sim.Population(N_layer,
                           SpikeSourcePoissonVariable,
                           {'rates':final_rates_on, 'starts':slots_starts, 'durations':durations},
                           label='Variable-rate Poisson spike source on # ' + str(number)))
        source_column_off.append(
            sim.Population(N_layer,
                           SpikeSourcePoissonVariable,
                           {'rates':final_rates_off, 'starts':slots_starts, 'durations': durations},
                           label='Variable-rate Poisson spike source off # ' + str(number)))
        # Neuron populations
        target_column.append(sim.Population(N_layer, model, cell_params, label='TARGET_POP # ' + str(number)))

        ff_on_connections.append(sim.Projection(source_column_on[number], target_column[number],
                sim.FromListConnector(init_ff_on_connections),
                synapse_type=structure_model_w_stdp,
                label='plastic_ff_projection'))
        ff_off_connections.append(sim.Projection(source_column_off[number], target_column[number],
                sim.FromListConnector(init_ff_off_connections),
                synapse_type=structure_model_w_stdp,
                label='plastic_ff_projection'))
        if args.case != CASE_CORR_NO_REW:
            lat_connections.append(sim.Projection(target_column[number], target_column[number],
                    sim.FromListConnector(init_lat_connections),
                    synapse_type=structure_model_w_stdp,
                    label='plastic_lat_projection',
                    receptor_type='inhibitory' if args.lateral_inhibition else 'excitatory'))
else:
    # Testing mode is activated.
    # 1. Retrieve connectivity for each pair of populations
    # 2. Create a single VRPSS for testing
    # 3. Create a target column
    # 4. Set up connectivity between the source and targets
    # 5. Run for simtime, showing each digit for a 10th of the time, but
    # shuffled randomly. Keep a track of the digits shown!
    init_ff_on_connections = None
    init_ff_off_connections = None
    init_lat_connections = None

    source_column_on = []
    source_column_off = []
    ff_on_connections = []
    ff_off_connections = []
    target_column = []
    lat_connections = []

    testing_data = np.load(args.testing)
    trained_ff_on_connectivity = testing_data['ff_on_connections'][-10:]
    trained_ff_off_connectivity = testing_data['ff_off_connections'][-10:]
    trained_lat_connectivity = testing_data['lat_connections'][-10:]

    if not args.random_input:
        randomised_testing_numbers = np.random.randint(0, 10, simtime // t_stim)

        # load all rates
        rates_on = []
        rates_off = []
        for number in range(10):
            rate_on, rate_off = load_mnist_rates('source_code/INPUT_FILES/testing_centre_surround/', number, min_noise=f_mean / 4., max_noise=f_mean / 4., mean_rate=f_mean, suffix="CS")
            rates_on.append(rate_on)
            rates_off.append(rate_off)
    testing_rates_on = np.empty((simtime // t_stim, grid[0], grid[1]))
    testing_rates_off = np.empty((simtime // t_stim, grid[0], grid[1]))
    for index in np.arange(testing_rates_on.shape[0]):
        if not args.random_input:
            random_number = np.random.randint(0, rates_on[randomised_testing_numbers[index]].shape[0])
            testing_rates_on[index, :, :] = rates_on[randomised_testing_numbers[index]][random_number, :, :]
            testing_rates_off[index, :, :] = rates_off[randomised_testing_numbers[index]][random_number, :, :]
        else:
            break
    if not args.random_input:
        source_on_pop = sim.Population(N_layer,
            sim.SpikeSourcePoissonVariable,
            {'rate': testing_rates_on.reshape(simtime // t_stim, N_layer),
            'start': 100,
            'duration': simtime,
            'rate_interval_duration': t_stim},
            label="VRPSS for testing on")
        source_off_pop = sim.Population(N_layer,
            sim.SpikeSourcePoissonVariable,
            {'rate': testing_rates_off.reshape(simtime // t_stim, N_layer),
            'start': 100,
            'duration': simtime,
            'rate_interval_duration': t_stim},
            label="VRPSS for testing off")
    else:
        source_on_pop = sim.Population(N_layer,
            sim.SpikeSourcePoisson,
            {'rate': f_mean,
             'start': 100,
             'duration': simtime,},
            label="PSS for testing")
        source_off_pop = sim.Population(N_layer,
            sim.SpikeSourcePoisson,
            {'rate': f_mean,
             'start': 100,
             'duration': simtime,},
            label="PSS for testing")
    source_column_on.append(source_on_pop)
    source_column_off.append(source_off_pop)
    for number in range(10):
        # Neuron populations
        target_column.append(sim.Population(N_layer, model, cell_params,
                           label="TARGET_POP # " + str(number)))
        ff_on_connections.append(sim.Projection(source_on_pop, target_column[number],
                sim.FromListConnector(trained_ff_on_connectivity[number]),
                label="ff_projection on " + str(number)))
        ff_off_connections.append(sim.Projection(source_off_pop, target_column[number],
                sim.FromListConnector(trained_ff_off_connectivity[number]),
                label="ff_projection off " + str(number)))
        if args.case != CASE_CORR_NO_REW:
            lat_connections.append(sim.Projection(target_column[number], target_column[number],
                    sim.FromListConnector(trained_lat_connectivity[number]),
                    label="lat_projection " + str(number),
                    target="inhibitory" if args.lateral_inhibition
                    else "excitatory"))

if args.record_source:
    for source_on_pop in source_column_on:
        source_on_pop.record(['spikes'])
    for source_off_pop in source_column_off:
        source_off_pop.record(['spikes'])
for target_pop in target_column:
    target_pop.record(['spikes'])

# Run simulation
pre_on_spikes = []
pre_off_spikes = []
post_spikes = []

pre_on_weights = []
pre_off_weights = []
post_weights = []

no_runs = simtime // t_record
run_duration = t_record

try:
    for current_run in range(no_runs):
        print("run", current_run + 1, "of", no_runs)
        sim.run(run_duration)

        # Retrieve data if training
    if not args.testing:
        for ff_projection in ff_on_connections:
            pre_on_weights.append(
                np.array([
                    ff_projection._get_synaptic_data(True, 'source'),
                    ff_projection._get_synaptic_data(True, 'target'),
                    ff_projection._get_synaptic_data(True, 'weight'),
                    ff_projection._get_synaptic_data(True, 'delay')]).T)
        for ff_projection in ff_off_connections:
            pre_off_weights.append(
                np.array([
                    ff_projection._get_synaptic_data(True, 'source'),
                    ff_projection._get_synaptic_data(True, 'target'),
                    ff_projection._get_synaptic_data(True, 'weight'),
                    ff_projection._get_synaptic_data(True, 'delay')]).T)
        if args.case != CASE_CORR_NO_REW:
            for lat_projection in lat_connections:
                post_weights.append(
                    np.array([
                        lat_projection._get_synaptic_data(True, 'source'),
                        lat_projection._get_synaptic_data(True, 'target'),
                        lat_projection._get_synaptic_data(True, 'weight'),
                        lat_projection._get_synaptic_data(True, 'delay')]).T)

    if args.record_source:
        for source_on_pop in source_column_on:
            pre_on_spikes.append(source_on_pop.spinnaker_get_data('spikes'))
        for source_on_pop in source_column_off:
            pre_off_spikes.append(source_on_pop.spinnaker_get_data('spikes'))
    for target_pop in target_column:
        post_spikes.append(target_pop.spinnaker_get_data('spikes'))
    # End simulation on SpiNNaker
    sim.end()
except Exception as e:
    traceback.print_exc()
    current_error = e

end_time = plt.datetime.datetime.now()
total_time = end_time - start_time

print("Total time elapsed -- " + str(total_time))

suffix = end_time.strftime("_%H%M%S_%d%m%Y")

if args.filename:
    filename = args.filename
elif args.testing:
    filename = "testing_" + args.testing
else:
    filename = "mnist_topographic_map_rate_results" + str(suffix)

if current_error:
    filename = "error_" + filename

np.savez(filename,
         pre_on_spikes=pre_on_spikes,
         pre_off_spikes=pre_off_spikes,
         post_spikes=post_spikes,
         init_ff_on_connections=init_ff_on_connections,
         init_ff_off_connections=init_ff_off_connections,
         init_lat_connections=init_lat_connections,
         ff_on_connections=pre_on_weights,
         ff_off_connections=pre_off_weights,
         lat_connections=post_weights,
         final_pre_on_weights=pre_on_weights[-10:],
         final_pre_off_weights=pre_off_weights[-10:],
         final_post_weights=post_weights[-10:],
         simtime=simtime,
         sim_params=sim_params,
         total_time=total_time,
         testing_numbers=randomised_testing_numbers,
         testing_file=args.testing, random_input=args.random_input,
         exception=None)

if args.plot:

    def plot_spikes(spikes, title):
        if spikes is not None and len(spikes) > 0:
            f, ax1 = plt.subplots(1, 1, figsize=(16, 8))
            ax1.set_xlim((0, simtime))
            ax1.scatter([i[1] for i in spikes], [i[0] for i in spikes], s=.2)
            ax1.set_xlabel('Time/ms')
            ax1.set_ylabel('spikes')
            ax1.set_title(title)
        else:
            print('No spikes received')

    plot_spikes(pre_on_spikes, 'Source layer spikes')
    plt.savefig('source_layer_spikes.png')
    plot_spikes(post_spikes, 'Target layer spikes')
    plt.savefig('target_layer_spikes.png')
print('Results in', filename)
print('Total time elapsed -- ' + str(total_time))

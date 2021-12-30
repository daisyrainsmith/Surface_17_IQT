import time
from compiled_surface_code_pdd_error_model import *
import numpy as np
from projectq import MainEngine
from projectq.backends import Simulator
eng = MainEngine(Simulator())
ancilla_number = 8
data_number = 9
result_dict = {}
round_count_list = []

run_name = 'test_pdd_low'

number_of_runs = 200
pxctrl = 0.0001
pyctrl = 0.0001
pxxctrl = 0.001
pmot = 0
pd = 0.0001
correction_table = load_lookup_table("correction_table_depolarising.json")

t_begin = time.perf_counter()
for _ in range(number_of_runs):

    round_count = 0
    # max_rounds = 60
    # while round_count < max_rounds:
    while True:

        t_start = time.perf_counter()

        # Initialise qubit register
        data=eng.allocate_qureg(data_number)
        ancilla = eng.allocate_qureg(ancilla_number)

        # #Perfect logical state prep (well motivated as per
        # https://iopscience.iop.org/article/10.1088/1367-2630/aab341/pdf)
        # All(X) | data


        quiescent = np.array(stabilizer_cycle(data, ancilla, eng, reset=True,
                                              pyctrl=0, pxctrl=0, pxxctrl = 0, pmot = 0, pd = 0))

        # # Error correction cycle
        prev_syndrome=np.array(quiescent)

        syndrome = np.array(stabilizer_cycle(data, ancilla, eng, reset=True,
                                             pyctrl=pyctrl, pxctrl=pxctrl, pxxctrl = pxxctrl, pmot = pmot, pd = pd))

        flips_a = (prev_syndrome - syndrome) % 2
        prev_syndrome = syndrome
        if np.all((flips_a == 0)):
            ft_syndrome = flips_a
        else:
            syndrome = np.array(stabilizer_cycle(data, ancilla, eng, reset=True,
                                                 pyctrl=pyctrl, pxctrl=pxctrl, pxxctrl=pxxctrl, pmot=pmot, pd=pd))

            flips_b = (prev_syndrome - syndrome) % 2
            prev_syndrome = syndrome
            ft_syndrome = (flips_a + flips_b) %2
        error_vec = lookup(ft_syndrome, correction_table)
        apply_correction(error_vec, data)
        eng.flush()
        round_count += 1

        # Measure logical qubit
        All(Measure) | data
        eng.flush()  # flush all gates (and execute measurements)
        data_meas = [int(q) for q in data]
        # ## measure leaked states as bright
        # for i, q in enumerate(leaked_q_reg[:9]):
        #     if int(q) == 1:
        #         data_meas[i] = 1
        #         print('leak registered at data meas')
        logic_Z_meas = sum(data_meas)%2
        if logic_Z_meas == 1: #incorrect
            print('incorrect logic meas {}'.format(data_meas))
            print('round {}'.format(round_count))
            break

    t_stop = time.perf_counter()
    time_taken = t_stop-t_start

    # if str(round_count) in result_dict:
    #     result_dict[str(round_count)] += 1
    # else:
    #     result_dict[str(round_count)] = 1
    round_count_list.append(round_count)
    #
    # print('{} QEC rounds til failure'.format(round_count))
    # print('time taken {}s'.format(time_taken))
t_end = time.perf_counter()
total_time_taken = t_end - t_begin
print('total time taken {}'.format(total_time_taken))
print(round_count_list)

results = {
    'pyctrl': pyctrl,
    'pxctrl': pxctrl,
    'pxxctrl': pxxctrl,
    'pmot': pmot,
    'pd': pd,
    # 'rounds_til_fail_tally': result_dict,
    'rounds_til_fail_list': round_count_list,
    'total_time_taken_{}_runs'.format(number_of_runs): total_time_taken
}


with open(run_name+'.txt', 'w') as file:
    json.dump(results, file)

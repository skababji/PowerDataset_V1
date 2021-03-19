import numpy as np
import pandas as pd
import pandapower as pp
import copy
import sys

def get_pu_react4trafo(net, trafo):
    z_pu=(trafo['vk_percent']/100)*(net.sn_mva/trafo['sn_mva'])
    r_pu=(trafo['vkr_percent']/100)*(net.sn_mva/trafo['sn_mva'])
    x_pu=np.sqrt(z_pu**2-r_pu**2)
    return x_pu


def gen_h4all(net):
    #Note: In the following, columns headers represent bus numbers sorted in ascending order
    n_buses=len(net.bus) #no. of angles (states in dc model)=no. of buses (including slack bus)
    data4pf=[]
    labels4pf=[]
    labels4pinj=[] #needed for power injection calculations

    for line_id, row in net.line.iterrows():
        line_row = np.zeros(n_buses)
        this_imp_base=net.bus.loc[row['from_bus']]['vn_kv']**2//net.sn_mva
        z_pu=(row['length_km']*row['x_ohm_per_km']/row['parallel'])/this_imp_base
        b=1/z_pu 
        line_row[row['from_bus']]=b #Convention as per Abur (not Mirsad), so injection will be negative sum
        line_row[row['to_bus']]=-b
        data4pf.append(line_row)
        labels4pf.append('pfl'+str(line_id)+'_'+str(row['from_bus'])+'_'+str(row['to_bus']))
        labels4pinj.append(row['from_bus'])
        data4pf.append(-line_row)
        labels4pf.append('pfl'+str(line_id)+'_'+str(row['to_bus'])+'_'+str(row['from_bus']))
        labels4pinj.append(row['to_bus'])

    for trafo_id, row in net.trafo.iterrows():
        trafo_row = np.zeros(n_buses)
        
        z_pu=get_pu_react4trafo(net, row)
        b=1/z_pu
        trafo_row[row['lv_bus']]=b #lv bus in trafo is treated same as from bus in line since pu is calculated with ref to this side
        trafo_row[row['hv_bus']]=-b
        data4pf.append(trafo_row)
        labels4pf.append('pft'+str(trafo_id)+'_'+str(row['lv_bus'])+'_'+str(row['hv_bus']))
        labels4pinj.append(row['lv_bus'])
        data4pf.append(-trafo_row)
        labels4pf.append('pft'+str(trafo_id)+'_'+str(row['hv_bus'])+'_'+str(row['lv_bus']))
        labels4pinj.append(row['hv_bus'])

    data4pf=pd.DataFrame(data4pf)
    labels4pf=pd.DataFrame(labels4pf, columns=['label'])
    labels4pinj=pd.DataFrame(labels4pinj, columns=['from_bus'])
    pf=pd.concat([labels4pinj,labels4pf,data4pf],axis=1)

    labels4pinj=[]
    data4pinj=[]
    for bus_id in range(n_buses):
        pf_per_bus=pf[pf['from_bus']==bus_id]
        data4pinj.append(-pf_per_bus.iloc[:,2:].sum().values) #negative sum since injection is opposite to pf
        labels4pinj.append('p'+str(bus_id))

    labels4pinj=pd.DataFrame(labels4pinj, columns=['label'])
    data4pinj=pd.DataFrame(data4pinj)
    p=pd.concat([labels4pinj,data4pinj], axis=1)

    pf=pf.drop('from_bus', axis=1)
    h=pd.concat([pf,p],axis=0)
    h.set_index('label', drop=True, inplace=True)

    return h



def gen_meas(net, all_meas,h4all, output_path, inst_err):

    inst_err_v=0.5*inst_err

    h=[]

    n_buses=len(net.bus)

    selected_meas = all_meas.loc[all_meas['meas_picked'] == True]
    n_meas = len(selected_meas)
    selected_meas = selected_meas.drop(['meas_picked'], axis=1)

    selected_buses=selected_meas.loc[selected_meas['element_type']=='bus']
    selected_buses_v = selected_buses.loc[selected_buses['meas_type'] == 'v']
    selected_buses_p = selected_buses.loc[selected_buses['meas_type'] == 'p']
    selected_buses_q = selected_buses.loc[selected_buses['meas_type'] == 'q']

    selected_lines=selected_meas.loc[selected_meas['element_type']=='line']
    selected_lines_p = selected_lines.loc[selected_lines['meas_type'] == 'p']
    selected_lines_q = selected_lines.loc[selected_lines['meas_type'] == 'q']

    selected_trafos=selected_meas.loc[selected_meas['element_type']=='trafo']
    selected_trafos_p = selected_trafos.loc[selected_trafos['meas_type'] == 'p']
    selected_trafos_q = selected_trafos.loc[selected_trafos['meas_type'] == 'q']


    print('Generating measurements for net..')
    cnt=-1

    #Voltage Magnitudes at buses
    if not selected_buses_v.empty:
        for index, row in selected_buses_v.iterrows():
            element=row['element']
            value=net.res_bus['vm_pu'].loc[element]
            name='v' + str(element)
            cnt+=1
            pp.create_measurement(net, 'v','bus',value,np.abs(inst_err_v*value),element, name=name)
            dummy_row=pd.DataFrame(np.zeros(n_buses), columns=[name]).T
            h.append(dummy_row)


    #Active Power Injection at buses
    if not selected_buses_p.empty:
        for index, row in selected_buses_p.iterrows():
            element=row['element']
            value=net.res_bus['p_mw'].loc[element]
            name='p'+str(element)
            cnt+=1
            pp.create_measurement(net, 'p','bus',value,np.abs(inst_err*value),element, name=name)
            real_row = pd.DataFrame(h4all.loc[name].values, columns=[name]).T
            h.append(real_row)

    #Reactive Power Injection at buses
    if not selected_buses_q.empty:
        for index, row in selected_buses_q.iterrows():
            element=row['element']
            value=net.res_bus['q_mvar'].loc[element]
            name = 'q' + str(element)
            cnt+=1
            pp.create_measurement(net, 'q','bus',value,np.abs(inst_err*value),element, name=name)
            dummy_row=pd.DataFrame(np.zeros(n_buses), columns=[name]).T
            h.append(dummy_row)

    #Active Power flows in lines
    if not selected_lines_p.empty:
        for index, row in selected_lines_p.iterrows():
            element=row['element']
            side=row['side']
            side_id = row['side_idx']
            other_side_id = row['other_side_idx']
            name = 'pfl' +str(element)+'_'+ str(side_id) + '_' + str(other_side_id)
            if side=='from':
                value=net.res_line['p_from_mw'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'p','line',value,np.abs(inst_err*value),element, side, name=name)
                real_row = pd.DataFrame(h4all.loc[name].values, columns=[name]).T
                h.append(real_row)
            elif side=='to':
                value = net.res_line['p_to_mw'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'p', 'line', value,np.abs(inst_err*value), element, side,name=name)
                real_row = pd.DataFrame(h4all.loc[name].values, columns=[name]).T
                h.append(real_row)

    # Reactive Power flows in lines
    if not selected_lines_q.empty:
        for index, row in selected_lines_q.iterrows():
            element=row['element']
            side=row['side']
            side_id = row['side_idx']
            other_side_id = row['other_side_idx']
            name = 'qfl' +str(element)+'_'+ str(side_id) + '_' + str(other_side_id)
            if side=='from':
                value=net.res_line['q_from_mvar'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'q','line',value,np.abs(inst_err*value),element, side,name=name)
                dummy_row = pd.DataFrame(np.zeros(n_buses), columns=[
                    name]).T  
                h.append(dummy_row)
            elif side=='to':
                value = net.res_line['q_to_mvar'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'q', 'line', value,np.abs(inst_err*value), element, side,name=name)
                dummy_row = pd.DataFrame(np.zeros(n_buses), columns=[
                    name]).T  
                h.append(dummy_row)


    # Active Power flows in trafos
    if not selected_trafos_p.empty:
        for index, row in selected_trafos_p.iterrows():
            element=row['element']
            side=row['side']
            side_id = row['side_idx']
            other_side_id = row['other_side_idx']
            name = 'pft' +str(element)+'_'+ str(side_id) + '_' + str(other_side_id)
            if side=='lv':
                value=net.res_trafo['p_lv_mw'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'p','trafo',value,np.abs(inst_err*value),element, side,name=name)
                real_row = pd.DataFrame(h4all.loc[name].values, columns=[name]).T
                h.append(real_row)

            elif side=='hv':
                value = net.res_trafo['p_hv_mw'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'p', 'trafo', value,np.abs(inst_err*value), element, side,name=name)
                real_row = pd.DataFrame(h4all.loc[name].values, columns=[name]).T
                h.append(real_row)


    # Reactive Power flows in trafos
    if not selected_trafos_q.empty:
        for index, row in selected_trafos_q.iterrows():
            element=row['element']
            side=row['side']
            side_id = row['side_idx']
            other_side_id = row['other_side_idx']
            name = 'qft'+str(element)+'_' + str(side_id) + '_' + str(other_side_id)
            if side=='lv':
                value=net.res_trafo['q_lv_mvar'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'q','trafo',value,np.abs(inst_err*value),element, side,name=name)
                dummy_row = pd.DataFrame(np.zeros(n_buses), columns=[
                    name]).T  
                h.append(dummy_row)
            elif side=='hv':
                value = net.res_trafo['q_hv_mvar'].loc[element]
                cnt += 1
                pp.create_measurement(net, 'q', 'trafo', value,np.abs(inst_err*value), element, side,name=name)
                dummy_row = pd.DataFrame(np.zeros(n_buses), columns=[
                    name]).T  
                h.append(dummy_row)


    h=pd.concat(h)
    h.to_csv(output_path+'h.csv')
    h_reordered=h.T
    h_reordered=h_reordered.reindex(net.res_bus.index).T #Reorder columns of h to match GT ordering
    h_reordered.to_csv(output_path+'h_reordered.csv')
    h_no_slack = h_reordered.drop(net.ext_grid.bus.values, axis=1)
    h_no_slack.to_csv(output_path + 'h_no_slack.csv')
    
    print('Done!')
    return h, h_reordered, h_no_slack #net include the new tables reulting from creating measurements




###########################################################


def update_meas(net):

    select_buses_v = (net.measurement['element_type'] == 'bus') & (net.measurement['measurement_type'] == 'v')

    select_buses_p = (net.measurement['element_type'] == 'bus') & (net.measurement['measurement_type'] == 'p')

    select_buses_q = (net.measurement['element_type'] == 'bus') & (net.measurement['measurement_type'] == 'q')

    select_lines_p_from=(net.measurement['element_type'] == 'line') & (net.measurement['measurement_type'] == 'p') & (net.measurement['side'] == 'from')
    select_lines_p_to=(net.measurement['element_type'] == 'line') & (net.measurement['measurement_type'] == 'p') & (net.measurement['side'] == 'to')
    select_lines_q_from=(net.measurement['element_type'] == 'line') & (net.measurement['measurement_type'] == 'q') & (net.measurement['side'] == 'from')
    select_lines_q_to=(net.measurement['element_type'] == 'line') & (net.measurement['measurement_type'] == 'q') & (net.measurement['side'] == 'to')

    select_trafos_p_lv = (net.measurement['element_type'] == 'trafo') & (net.measurement['measurement_type'] == 'p') & (net.measurement['side'] == 'lv')
    select_trafos_p_hv = (net.measurement['element_type'] == 'trafo') & (net.measurement['measurement_type'] == 'p') & (net.measurement['side'] == 'hv')
    select_trafos_q_lv = (net.measurement['element_type'] == 'trafo') & (net.measurement['measurement_type'] == 'q') & (net.measurement['side'] == 'lv')
    select_trafos_q_hv = (net.measurement['element_type'] == 'trafo') & (net.measurement['measurement_type'] == 'q') & (net.measurement['side'] == 'hv')


    # Voltage Magnitudes at buses
    if not net.measurement[select_buses_v].empty:
        elements=net.measurement[select_buses_v]['element']
        net.measurement.loc[select_buses_v,'value']=net.res_bus.loc[elements]['vm_pu'].values #VIMP TIP to update pandas cells based on selection

    # Active Power Injection at buses
    if not net.measurement[select_buses_p].empty:
        elements=net.measurement[select_buses_p]['element']
        net.measurement.loc[select_buses_p,'value'] =net.res_bus.loc[elements]['p_mw'].values

    # Reactive Power Injection at buses
    if not net.measurement[select_buses_q].empty:
        elements = net.measurement[select_buses_q]['element']
        net.measurement.loc[select_buses_q,'value'] = net.res_bus.loc[elements]['q_mvar'].values

    # Active Power flows in lines (from)
    if not net.measurement[select_lines_p_from].empty:
        elements = net.measurement[select_lines_p_from]['element']
        net.measurement.loc[select_lines_p_from,'value'] = net.res_line.loc[elements]['p_from_mw'].values

    # Active Power flows in lines (to)
    if not net.measurement[select_lines_p_to].empty:
        elements = net.measurement[select_lines_p_to]['element']
        net.measurement.loc[select_lines_p_to,'value'] = net.res_line.loc[elements]['p_to_mw'].values

    # Reactive Power flows in lines (from)
    if not net.measurement[select_lines_q_from].empty:
        elements = net.measurement[select_lines_q_from]['element']
        net.measurement.loc[select_lines_q_from,'value'] = net.res_line.loc[elements]['q_from_mvar'].values

    # Reactive Power flows in lines (to)
    if not net.measurement[select_lines_q_to].empty:
        elements = net.measurement[select_lines_q_to]['element']
        net.measurement.loc[select_lines_q_to,'value'] = net.res_line.loc[elements]['q_to_mvar'].values

    # Active Power flows in trafos (lv)
    if not net.measurement[select_trafos_p_lv].empty:
        elements = net.measurement[select_trafos_p_lv]['element']
        net.measurement.loc[select_trafos_p_lv,'value'] = net.res_trafo.loc[elements]['p_lv_mw'].values

    # Active Power flows in trafos (hv)
    if not net.measurement[select_trafos_p_hv].empty:
        elements = net.measurement[select_trafos_p_hv]['element']
        net.measurement.loc[select_trafos_p_hv,'value'] = net.res_trafo.loc[elements]['p_hv_mw'].values

    # Reactive Power flows in trafos (lv)
    if not net.measurement[select_trafos_q_lv].empty:
        elements = net.measurement[select_trafos_q_lv]['element']
        net.measurement.loc[select_trafos_q_lv,'value'] = net.res_trafo.loc[elements]['q_lv_mvar'].values

    # Reactive Power flows in trafos (hv)
    if not net.measurement[select_trafos_q_hv].empty:
        elements = net.measurement[select_trafos_q_hv]['element']
        net.measurement.loc[select_trafos_q_hv,'value'] = net.res_trafo.loc[elements]['q_hv_mvar'].values

    return



def gen_clean_scen_unfrm(base_net, n_l_scenarios,set_id):
    print('gen_clean_scen_unfrm: Generating BASE CLEAN scenario 0 ... ')
    nets = [copy.deepcopy(base_net)]  # construct a list holding all scenarios including base scenario
    nets_ids=[set_id+str(0)]
    this_net = copy.deepcopy(base_net)

    n_loads = len(this_net.load)
    print('\n')
    for i in range(n_l_scenarios - 1):
        print('Generating CLEAN scenario No. {:3}... '.format(i + 1))
        # delta_P = np.random.normal(0, l_scenarios_std_dev, n_loads) # use these if you are interested in Gaussian variation of load. Preferably, define a new function for that.
        # delta_Q = np.random.normal(0, l_scenarios_std_dev, n_loads)
        factor = np.random.uniform(0.1, 1.1,
                                   n_loads)  # samples vector of length n_loads with values from 0.1(included) to 1.1 (excluded)
        this_net.load['p_mw'] = this_net.load['p_mw'] * factor
        this_net.load['q_mvar'] = this_net.load['q_mvar'] * factor
        #carry out pfa for each clean net and update meas
        print('Running Power Flow Analysis for net {:3}'.format(i + 1))

        pp.runpp(this_net)


        print('Updating measurements of net {:3}'.format(i + 1))
        update_meas(this_net)

        nets.append(this_net)  # nets.append(copy.deepcopy(this_net))
        nets_ids.append(set_id+str(i+1))

        this_net = copy.deepcopy(base_net)  

    return  nets_ids,nets

def duplicate_scenarios(nets_ids,nets, rpt_per_elmnt):
    print('\n')
    print('Duplicating each input (usually clean) scenario {} times...'.format(str(rpt_per_elmnt)))
    new_list=[]
    new_ids=[]
    for i in range(len(nets)):
        for j in range(rpt_per_elmnt):
            new_list.append(copy.deepcopy(nets[i]))
            new_ids.append(copy.deepcopy(nets_ids[i]))
    return new_ids,new_list




def meas2features(nets_ids,nets ): #nets and nets_ids are both lists
    print('Convert measurements to features..')
    features = nets[0].measurement['name']
    examples = []
    for _,net in enumerate(nets):
        example = net.measurement['value'].values
        examples.append(example)
    data_id=pd.DataFrame(nets_ids, columns=['l_scenario_id'])
    data_values=pd.DataFrame(examples, columns=[*features.to_list()])
    data=pd.concat([data_id,data_values ],axis=1)
    print('Done!')
    return data

def pf_states2features(nets_ids, nets):
    print('Convert estimated states to features..')
    examples=[]
    indices = nets[0].res_bus.index
    indices = np.char.array(indices)
    vm_features = np.chararray(len(indices), itemsize=3)
    vm_features[:] = 'vm_'
    vm_features = vm_features + indices
    va_features = np.chararray(len(indices), itemsize=3)
    va_features[:] = 'va_'
    va_features = va_features + indices
    features =np.concatenate([vm_features,va_features])
    for _, net in enumerate(nets):
        #try:
        example=np.concatenate([net.res_bus['vm_pu'], net.res_bus['va_degree']*np.pi/180]) #convert angle into radians
        examples.append(example)
        #except:
            #pass
    data_id=pd.DataFrame(nets_ids, columns=['l_scenario_id'])
    data_values=pd.DataFrame(examples, columns=features.astype('U13'))
    data=pd.concat([data_id,data_values ],axis=1)
    print('Done!')
    return data



#####################################################

def pf_states2features(nets_ids, nets):
    print('Convert estimated states to features..')
    examples=[]
    indices = nets[0].res_bus.index
    indices = np.char.array(indices)
    vm_features = np.chararray(len(indices), itemsize=3)
    vm_features[:] = 'vm_'
    vm_features = vm_features + indices
    va_features = np.chararray(len(indices), itemsize=3)
    va_features[:] = 'va_'
    va_features = va_features + indices
    features =np.concatenate([vm_features,va_features])
    for _, net in enumerate(nets):
        #try:
        example=np.concatenate([net.res_bus['vm_pu'], net.res_bus['va_degree']*np.pi/180]) #convert angle into radians
        examples.append(example)
        #except:
            #pass
    data_id=pd.DataFrame(nets_ids, columns=['l_scenario_id'])
    data_values=pd.DataFrame(examples, columns=features.astype('U13'))
    data=pd.concat([data_id,data_values ],axis=1)
    print('Done!')
    return data


def pfdc_states2features(nets_ids, nets):
    print('Convert estimated states to features..')
    examples=[]
    indices = nets[0].res_bus.index
    indices = np.char.array(indices)
    va_features = np.chararray(len(indices), itemsize=3)
    va_features[:] = 'va_'
    va_features = va_features + indices
    features =np.concatenate([va_features])
    for _, net in enumerate(nets):
        #try:
        example=np.concatenate([net.res_bus['va_degree']*np.pi/180]) #convert angle into radians
        examples.append(example)
        #except:
            #pass
    data_id=pd.DataFrame(nets_ids, columns=['l_scenario_id'])
    data_values=pd.DataFrame(examples, columns=features.astype('U13'))
    data=pd.concat([data_id,data_values ],axis=1)
    print('Done!')
    return data



#######################################################3


#Generating Noise
def gen_noisy_meas(run_hp,ids,scenarios):
    print('\n')
    #noisy_scenarios = copy.deepcopy(clean_scenarios)
    print('Add noise to measurements..')
    for noisy_scen_idx, noisy_scen in enumerate(scenarios):
        # n_meas_per_scenario = len(noisy_scen.measurement)
        meas_values_vec = noisy_scen.measurement['value'].values
        meas_std_dev_vec = noisy_scen.measurement['std_dev'].values

        if run_hp['noise_on_meas']=='gaussian':#noise imposed on measurements either gaussian or uniform
            noise_scenario_vec = np.random.normal(loc=meas_values_vec, scale=meas_std_dev_vec, size=meas_values_vec.shape[0])
        elif run_hp['noise_on_meas']=='uniform':
            noise_scenario_vec = np.random.uniform(low=meas_values_vec-meas_std_dev_vec, high=meas_values_vec+meas_std_dev_vec, size=meas_values_vec.shape[0])
        else:
            print('Error. Noise imposed on clean scenarios shall be either gaussian or uniform')


        # Replace clean measurements values by noisy vector
        noisy_scen.measurement['value'] = noise_scenario_vec

    return ids,scenarios  # These are clean scenarios modified by noise vector








###################################################################

def gen_meas_picker(net):
    # net = self.base_l_scenario
    m_template = pd.DataFrame()

    for bus_id, row in net.bus.iterrows():
        m_bus_vm = [False, 'v', 'bus', bus_id, bus_id, bus_id, bus_id]
        m_bus_p = [False, 'p', 'bus', bus_id, bus_id, bus_id, bus_id]
        m_bus_q = [False, 'q', 'bus', bus_id, bus_id, bus_id, bus_id]

        m_bus_df = pd.DataFrame([m_bus_vm, m_bus_p, m_bus_q])
        m_template = m_template.append(m_bus_df)

    for line_id, row in net.line.iterrows():
        m_line_p_from = [True, 'p', 'line', line_id, 'from', net.line['from_bus'].loc[line_id],net.line['to_bus'].loc[line_id]]
        m_line_p_to = [True, 'p', 'line', line_id, 'to', net.line['to_bus'].loc[line_id], net.line['from_bus'].loc[line_id]]
        m_line_q_from = [True, 'q', 'line', line_id, 'from', net.line['from_bus'].loc[line_id],  net.line['to_bus'].loc[line_id]]
        m_line_q_to = [True, 'q', 'line', line_id, 'to', net.line['to_bus'].loc[line_id], net.line['from_bus'].loc[line_id]]
        m_line_i_from = [False, 'i', 'line', line_id, 'from', net.line['from_bus'].loc[line_id], net.line['to_bus'].loc[line_id]]
        m_line_i_to = [False, 'i', 'line', line_id, 'to', net.line['to_bus'].loc[line_id], net.line['from_bus'].loc[line_id]]

        m_line_df = pd.DataFrame(
            [m_line_p_from, m_line_p_to, m_line_q_from, m_line_q_to, m_line_i_from, m_line_i_to])
        m_template = m_template.append(m_line_df)

    for trafo_id, row in net.trafo.iterrows():
        m_trafo_p_hv = [True, 'p', 'trafo', trafo_id, 'hv', net.trafo['hv_bus'].loc[trafo_id], net.trafo['lv_bus'].loc[trafo_id]]
        m_trafo_p_lv = [True, 'p', 'trafo', trafo_id, 'lv', net.trafo['lv_bus'].loc[trafo_id], net.trafo['hv_bus'].loc[trafo_id]]
        m_trafo_q_hv = [True, 'q', 'trafo', trafo_id, 'hv', net.trafo['hv_bus'].loc[trafo_id], net.trafo['lv_bus'].loc[trafo_id]]
        m_trafo_q_lv = [True, 'q', 'trafo', trafo_id, 'lv', net.trafo['lv_bus'].loc[trafo_id], net.trafo['hv_bus'].loc[trafo_id]]
        m_trafo_i_hv = [False, 'i', 'trafo', trafo_id, 'hv', net.trafo['hv_bus'].loc[trafo_id], net.trafo['lv_bus'].loc[trafo_id]]
        m_trafo_i_lv = [False, 'i', 'trafo', trafo_id, 'lv', net.trafo['lv_bus'].loc[trafo_id], net.trafo['hv_bus'].loc[trafo_id]]

        m_trafo_df = pd.DataFrame([m_trafo_p_hv, m_trafo_p_lv, m_trafo_q_hv, m_trafo_q_lv, m_trafo_i_hv, m_trafo_i_lv])
        m_template = m_template.append(m_trafo_df)

    m_template.columns = ['meas_picked', 'meas_type', 'element_type', 'element', 'side', 'side_idx', 'other_side_idx']

    m_template.to_csv('../runs/meas_template.csv', index=False)
    print('Please go to ../runs/meas_template.csv and select the measurements you need for your study.')

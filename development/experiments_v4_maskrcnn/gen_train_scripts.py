import numpy as np
import os
import pdb
import sys

GPU_NODES_TO_EXCLUDE = None # "gypsum-gpu[030,035,039,096,097,098,099,122,146]"

EXP_GROUP_NAME = '10'
ROOT = EXP_GROUP_NAME
MAX_ITER = 150000
CKPT_PERIOD = 5000

ADAPTOR = "linear" # linear, multi-layer, no: None
TRAINDATA_NET_ANCHOR_CH_IMSZ = [
    (3, "resnet101-FPN", 10, i, 1000) for i in range(1, 11)
]
TRAINDATA_NET_ANCHOR_CH_IMSZ.extend([
    (3, "mrcnn-r101-FPN", 10, i, 1000) for i in range(1, 11)
])
SEED = [1]
PRETRAIN_LR = [("det", 0.001),]
FILTER_EMPTY = [False,]

if ADAPTOR == "linear":
    adaptor_brief = "lin"
elif ADAPTOR == "multi-layer":
    adaptor_brief = "mul"
script_dir = os.path.join(ROOT, 'scripts')
slurm_dir = os.path.join(ROOT, 'slurm')
log_dir = os.path.join(ROOT, 'logs')
os.makedirs(script_dir, exist_ok=True)
os.makedirs(slurm_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
launch_file = open(os.path.join(script_dir, 'launch_train.sh'), 'w')
launch_file.write('#!/bin/bash\n')

exp_idx = 0
for seed in SEED:
    for (train_dataset, network, anchor_strategy, channel_strategy, imsize) in TRAINDATA_NET_ANCHOR_CH_IMSZ:
        for (pretrain, lr) in PRETRAIN_LR:
            for filter_empty in FILTER_EMPTY:
                exp_name = f"{EXP_GROUP_NAME}_{train_dataset}_seed{seed}" \
                           f"_{network}_{pretrain}ptr_anc{anchor_strategy}" \
                           f"_{adaptor_brief}adap_chnl{channel_strategy}" \
                           f"_imsz{imsize}" \
                           f"{'_flt' if filter_empty else ''}" \
                           f"_lr{lr:.3f}_it{MAX_ITER//1000}k"
                script_path = os.path.join(script_dir, exp_name+'.sbatch')
                output_dir = os.path.join(log_dir, exp_name)
                os.makedirs(output_dir, exist_ok=True)

                with open(script_path, 'w') as f:
                    f.write('#!/bin/bash\n')
                    f.write('hostname\n')
                    f.write(
                        ''.join((
                            f'python train_roost_detector.py',
                            f' --train_dataset {train_dataset}'
                            f' --imsize {imsize}',
                            f' --filter_empty' if filter_empty else '',
                            f' --seed {seed}',
                            f' --network {network} --pretrain {pretrain} --anchor_strategy {anchor_strategy}',
                            f' --adaptor {ADAPTOR} --channel_strategy {channel_strategy}'
                            f' --lr {lr} --max_iter {MAX_ITER}',
                            f' --checkpoint_period {CKPT_PERIOD} --output_dir {output_dir}',
                        ))
                    )
                partition = "gypsum-2080ti" if exp_idx < 20 else "gypsum-1080ti" # TODO
                launch_file.write(
                    ''.join((
                        f'sbatch -o {slurm_dir}/{exp_name}_%J.out',
                        f' -p {partition} --gres=gpu:1',
                        f' --exclude={GPU_NODES_TO_EXCLUDE}' if GPU_NODES_TO_EXCLUDE else '',
                        f' --mem=100000 {script_path}\n',
                    ))
                )
                exp_idx += 1

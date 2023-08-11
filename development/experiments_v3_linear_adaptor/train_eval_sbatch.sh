#!/bin/sh
#
#SBATCH --job-name=150
#SBATCH -o /mnt/nfs/scratch1/gperezsarabi/darkecology/roost-system/development/experiments/gypsum_logs/150.txt
#SBATCH --partition=rtx8000-long
#SBATCH --gres=gpu:1
#SBATCH --mem=32GB

source activate roostsys

MODEL="150"
ADAPTOR="linear"
INPUT_CHANNELS=3
IMSIZE=1100
BACKBONE="resnet101-FPN"
ITER=50000
DATASET=1
TEST_DATASET=1

bash train_eval.sh 0 "$MODEL" "$ADAPTOR" $INPUT_CHANNELS $IMSIZE "$BACKBONE" $ITER $DATASET $TEST_DATASET

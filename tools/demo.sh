#!/bin/bash
hostname
SPECIES=$1
STATION=$2
START=$3
END=$4
SUN_ACTIVITY=$5
MIN_BEFORE=$6
MIN_AFTER=$7
OUTPUT_ROOT=$8
MODEL_VERSION=$9
DATASET=${10}
SRC_SLURM=${11}
DST_HOST=${12}
DST_IMG=${13}
DST_PRED=${14}
DST_ARRAY=${15}
DST_OTHERS=${16}

python demo.py \
--species ${SPECIES} --station ${STATION} --start ${START} --end ${END} \
--sun_activity ${SUN_ACTIVITY} --min_before ${MIN_BEFORE} --min_after ${MIN_AFTER} \
--data_root ${OUTPUT_ROOT} --model_version ${MODEL_VERSION}

# transfer outputs
cd ${OUTPUT_ROOT}
# (1) images to visualize dz05 and vr05
ssh ${DST_HOST} mkdir -p ${DST_IMG}/${DATASET}
rsync -avz ui/img/* ${DST_HOST}:${DST_IMG}/${DATASET}/
# (2) csv for scans_and_tracks
ssh ${DST_HOST} mkdir -p ${DST_PRED}/${DATASET}
rsync -avz ui/scans_and_tracks/* ${DST_HOST}:${DST_PRED}/${DATASET}/
# (3) arrays
rsync -a arrays/ ${DST_HOST}:${DST_ARRAY}
# (4) logs and empty scans directory
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/${DATASET}/logs
rsync -a logs/ ${DST_HOST}:${DST_OTHERS}/${DATASET}/logs/
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/${DATASET}/scans
rsync -a scans/ ${DST_HOST}:${DST_OTHERS}/${DATASET}/scans/
# (5) slurm_logs
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/slurm_logs
scp -r ${SRC_SLURM}/${DATASET} ${DST_HOST}:${DST_OTHERS}/slurm_logs/

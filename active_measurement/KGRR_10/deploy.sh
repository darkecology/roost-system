#!/bin/bash
hostname
SPECIES=$1
STATION=$2
START=$3
YEAR=${START:0:4}
END=$4
SUN_ACTIVITY=$5
MIN_BEFORE=$6
MIN_AFTER=$7
OUTPUT_ROOT=$8
DATASET=$9  # e.g., am_SSSS_ckpt
SRC_SLURM=${10}

DST_HOST=${11}
DST_IMG=${12}
DST_PRED=${13}
DST_OTHERS=${14}

python deploy.py \
--species ${SPECIES} --station ${STATION} --start ${START} --end ${END} \
--sun_activity ${SUN_ACTIVITY} --min_before ${MIN_BEFORE} --min_after ${MIN_AFTER} \
--data_root ${OUTPUT_ROOT}/${DATASET} --keep_scans

##### Transfer outputs. Only transfer the currently processed station-year. #####
## Transfer outputs for the UI in the verbose mode and with compression
## (1) images to visualize dz05 and vr05
#PATTERN="*/${YEAR}/*/*/${STATION}/*"  # ${} will be expanded, * remains as is
#echo "##### Transferring images: $PATTERN #####"
#ssh ${DST_HOST} mkdir -p ${DST_IMG}/${DATASET}
#rsync --remove-source-files -avz \
#--include='*/' \
#--include="$PATTERN" \
#--exclude='*' \
#${OUTPUT_ROOT}/${DATASET}/ui/img/ \
#${DST_HOST}:${DST_IMG}/${DATASET}/
#
## (2) bounding boxes and counts
#PATTERN="*${STATION}_${YEAR}*"
#echo "##### Transferring detections: $PATTERN #####"
#ssh ${DST_HOST} mkdir -p ${DST_PRED}/${DATASET}
#rsync --remove-source-files -avz \
#--include="$PATTERN" \
#--exclude='*' \
#${OUTPUT_ROOT}/${DATASET}/ui/scans_and_tracks/ \
#${DST_HOST}:${DST_PRED}/${DATASET}/
#
## (4) logs
#PATTERN="${STATION}/${YEAR}/*"
#echo "##### Transferring logs: $PATTERN #####"
#ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/${DATASET}/logs
#rsync --remove-source-files -av \
#--include="${STATION}/" \
#--include="${STATION}/${YEAR}/" \
#--include="$PATTERN" \
#--exclude='*' \
#${OUTPUT_ROOT}/${DATASET}/logs/ \
#${DST_HOST}:${DST_OTHERS}/${DATASET}/logs/

# (6) slurm_logs -> we will send manually later because these files still change
#echo "##### Transferring slurm_logs #####"
#ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/slurm_logs/${DATASET}
#rsync --remove-source-files -av \
#${SRC_SLURM}/${DATASET}/ \
#${DST_HOST}:${DST_OTHERS}/slurm_logs/${DATASET}/

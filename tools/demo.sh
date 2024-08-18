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
MODEL_VERSION=$9
DATASET=${10}  # e.g., us_sunrise_v3
SRC_SLURM=${11}

DST_HOST=${12}
DST_IMG=${13}
DST_PRED=${14}
DST_ARRAY=${15}
DST_OTHERS=${16}

python demo.py \
--species ${SPECIES} --station ${STATION} --start ${START} --end ${END} \
--sun_activity ${SUN_ACTIVITY} --min_before ${MIN_BEFORE} --min_after ${MIN_AFTER} \
--data_root ${OUTPUT_ROOT}/${DATASET} --model_version ${MODEL_VERSION} --dataset ${DATASET}

##### Transfer outputs. Only transfer the currently processed station-year. #####
# Transfer outputs for the UI in the verbose mode and with compression
# (1) images to visualize dz05 and vr05
PATTERN="${OUTPUT_ROOT}/${DATASET}/ui/img/*/${YEAR}/*/*/${STATION}/*"  # ${} will be expanded, * remains as is
echo "Transferring: $PATTERN"
ssh ${DST_HOST} mkdir -p ${DST_IMG}/${DATASET}
rsync --remove-source-files -avz --include="$PATTERN" --exclude='*' \
${OUTPUT_ROOT}/${DATASET}/ui/img/* \
${DST_HOST}:${DST_IMG}/${DATASET}/

# (2) bounding boxes and counts
PATTERN="${OUTPUT_ROOT}/${DATASET}/ui/scans_and_tracks/*${STATION}_${YEAR}*"
echo "Transferring: $PATTERN"
ssh ${DST_HOST} mkdir -p ${DST_PRED}/${DATASET}
rsync --remove-source-files -avz --include="$PATTERN" --exclude='*' \
${OUTPUT_ROOT}/${DATASET}/ui/scans_and_tracks/* \
${DST_HOST}:${DST_PRED}/${DATASET}/

# Transfer other outputs for the record
# (3) arrays
PATTERN="${OUTPUT_ROOT}/${DATASET}/arrays/${YEAR}/*/*/${STATION}/*"
echo "Transferring: $PATTERN"
ssh ${DST_HOST} mkdir -p ${DST_ARRAY}
rsync --remove-source-files -az --include="$PATTERN" --exclude='*' \
${OUTPUT_ROOT}/${DATASET}/arrays/ \
${DST_HOST}:${DST_ARRAY}

# (4) logs
PATTERN="${OUTPUT_ROOT}/${DATASET}/logs/${STATION}/${YEAR}/*"
echo "Transferring: $PATTERN"
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/${DATASET}/logs
rsync --remove-source-files -a --include="$PATTERN" --exclude='*' \
${OUTPUT_ROOT}/${DATASET}/logs/ \
${DST_HOST}:${DST_OTHERS}/${DATASET}/logs/

# (5) empty scans directory
PATTERN="${OUTPUT_ROOT}/${DATASET}/scans/${YEAR}/*/*/${STATION}*"
echo "Transferring: $PATTERN"
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/${DATASET}/scans
rsync --remove-source-files -a --include="$PATTERN" --exclude='*' \
${OUTPUT_ROOT}/${DATASET}/scans/ \
${DST_HOST}:${DST_OTHERS}/${DATASET}/scans/

# (6) slurm_logs
PATTERN="${SRC_SLURM}/${DATASET}/${STATION}/${STATION}_${YEAR}*"
echo "Transferring: $PATTERN"
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/slurm_logs
rsync --remove-source-files -a --include="$PATTERN" --exclude='*' \
${SRC_SLURM}/${DATASET} \
${DST_HOST}:${DST_OTHERS}/slurm_logs/